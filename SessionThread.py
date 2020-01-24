from time import sleep

from PyQt5.QtCore import QObject, pyqtSignal

from DataModel import DataModel
from FilterSpec import FilterSpec
from Preferences import Preferences
from SessionController import SessionController
from TheSkyX import TheSkyX
from WorkItem import WorkItem

#
#   The worker thread that actually does the flat-frame acquisition
#

class SessionThread(QObject):
    # Class constants
    DELAY_AT_FINISH = 2  # Wait 2 seconds at end for output to appear on UI
    EXPOSURE_SEARCH_ATTEMPTS_LIMIT = 100  # Convergence failure if can't find

    # Signals we emit
    finished = pyqtSignal()
    consoleLine = pyqtSignal(str, int)  # String, indentation level
    startRowIndex = pyqtSignal(int)
    startProgressBar = pyqtSignal(int)  # Initialize progress bar, for maximum this much
    updateProgressBar = pyqtSignal(int)  # Update the bar with this value of progress toward maximum
    framesComplete = pyqtSignal(int, int)  # Row index, frames complete

    # frameAcquired = pyqtSignal(FrameSet, int)  # A frame has been successfully acquired

    # Creator
    def __init__(self, data_model: DataModel,
                 preferences: Preferences,
                 work_items: [WorkItem],
                 controller: SessionController,
                 server_address: str,
                 server_port: int,
                 warm_when_done: bool):
        # print(f"SessionThread created")
        QObject.__init__(self)
        self._data_model = data_model
        self._preferences = preferences
        self._work_items = work_items
        self._controller = controller
        self._server_address = server_address
        self._server_port = server_port
        self._warm_when_done = warm_when_done
        self._last_filter_slot = -1
        self._server = TheSkyX(self._server_address, self._server_port)

    # Invoked by the thread-start signal after the thread is comfortably running,
    # this is the method that does the actual work of frame acquisition.
    # We're not doing anything about cooling the camera - we assume
    # that we are at the end of a session, so the camera is already at temperature.

    def run_session(self):
        """Run the flat-frame acquisition thread main program"""
        # print("run_session entered")
        self.consoleLine.emit(f"Session Started at server {self._server_address}:{self._server_port}", 1)

        # Run through the work list, one item at a time, watching for early
        # exit if cancellation is requested
        work_item_index: int = 0
        for work_item in self._work_items:
            if self._controller.thread_cancelled():
                break
            if not self.process_one_work_item(work_item_index, work_item):
                # Failure in the work item, so we fail out of the loop
                break
            work_item_index += 1

        if self._controller.thread_running():
            # Normal termination (not cancelled) so we can do the warm-up
            self.handle_warm_up()

        self.consoleLine.emit("Session Ended" if self._controller.thread_running() else "Session Cancelled", 1)
        sleep(SessionThread.DELAY_AT_FINISH)
        self.finished.emit()
        # print("run_session exits")

    # Process the given work item (a number of frames of one spec)
    # Return a success indicator
    def process_one_work_item(self, work_item_index: int, work_item: WorkItem) -> bool:
        """Process a single work item - a number of frames of given specification"""
        # print(f"process_one_work_item({work_item_index}, {work_item})")
        success: bool = False
        if work_item.get_number_of_frames() <= work_item.get_num_completed():
            # Nothing to do
            success = True
        else:
            # Tell the world we are starting this line so UI can highlight that row
            self.startRowIndex.emit(work_item_index)

            # Console message about what we're about to do
            if self._data_model.get_use_filter_wheel():
                filter_phrase = f" with filter {work_item.hybrid_filter_name()}"
            else:
                filter_phrase = ""
            self.consoleLine.emit(f"Capture {work_item.get_number_of_frames()} flats"
                                  + filter_phrase + " binned "
                                  + f"{work_item.get_binning()} x {work_item.get_binning()}", 1)

            # Set up and do the acquisition of the frames for this work item
            if self.connect_camera():
                if self.connect_filter_wheel():
                    if self.select_filter(work_item.get_filter_spec()):
                        exposure: float
                        (success, exposure) = self.find_initial_exposure(work_item)
                        if success:
                            self.start_progress_bar(work_item)
                            if self.acquire_frames(work_item_index, work_item, exposure):
                                success = True

            # If we failed or were cancelled, clean up
            # Note we can't interrupt/abort any camera operation that may be in progress
            # since in this program we are doing synchronous acquisition rather than doing
            # the additional work of asynchronous and then re-synchronization.  So if there is
            # a camera exposure underway, the user just has to wait.
        if self._controller.thread_cancelled():
            self.clean_up_from_cancel()
        elif not success:
            self.clean_up_from_failure()
        return success

    # Turn off camera cooler so it can warm up while we're busy closing the dome
    # (I usually start the flat frames running with a light panel, then do all the physical
    # close-down of the dome, such as closing the dome and putting the cover on it, while
    # they are gathering.  If they finish while I'm still puttering, this lets the camera
    # start to warm up gently.

    def handle_warm_up(self):
        """Handle optional post-session warm up of CCD"""
        # print("handle_warm_up")
        if self._data_model.get_warm_when_done():
            self.consoleLine.emit("Turning off camera cooling as requested", 1)
            self._server.set_camera_cooling(cooling_on=False, target_temperature=0)

    def connect_camera(self) -> bool:
        """Ask server to connect to camera"""
        # print("connect_camera")
        (success, message) = self._server.connect_to_camera()
        if not success:
            self.consoleLine.emit(f"** Error connecting to camera: {message}", 2)
        return success

    def connect_filter_wheel(self) -> bool:
        """Ask server to connect to filter wheel"""
        # print("connect_filter_wheel")
        if self._data_model.get_use_filter_wheel():
            (success, message) = self._server.connect_to_filter_wheel()
            if not success:
                self.consoleLine.emit(f"** Error connecting to filter wheel: {message}", 2)
        else:
            success = True
        return success

    # If the filter for this work item is different than the one already in use,
    # ask the filter wheel to change to the new filter.  We do this "different from last"
    # check to avoid sending unnecessary commands to the filter wheel, because some filter
    # wheels will move to select the new filter even if already selected, and we want to
    # avoid slight changes in the registration of the wheels, so we are building up flat
    # frames that are identically aligned on each given filter.
    # Of course, if we're not even using a filter wheel, we just return with success

    # Return a success indicator

    def select_filter(self, filter_wanted: FilterSpec) -> bool:
        """Ask server to inform camera of new filter to be used for next frame"""
        # print(f"select_filter: {filter_wanted}")
        if self._data_model.get_use_filter_wheel():
            if filter_wanted.get_slot_number() == self._last_filter_slot:
                # print("  No change necessary")
                success = True
            else:
                self._last_filter_slot = filter_wanted.get_slot_number()
                filter_index = self._last_filter_slot - 1
                # print(f"  Changing filter to index{filter_index}")
                (success, message) = self._server.select_filter(filter_index)
                if not success:
                    self.consoleLine.emit(f"** Error selecting filter {filter_wanted.get_slot_number()}: {message}", 2)
        else:
            # print("  No filter wheel, ignoring")
            success = True
        return success

    # Find the initial exposure we'll use for the flat frame.
    # We start with a guess, then refine by linear extrapolation using the distance from desired ADU.
    # Return a success indicator, and the exposure

    def find_initial_exposure(self, work_item: WorkItem) -> (bool, float):
        """Find the initial exposure to use for this set of frames"""
        # print(f"find_initial_exposure: {work_item}")
        message: str = ""
        self.consoleLine.emit("Searching for exposure length", 2)
        # Initial guess and initial bracket with arbitrary high and low bounds
        trial_exposure: float = work_item.initial_exposure_estimate()
        if trial_exposure is None:
            trial_exposure = 10
        # print(f"  Initial exposure {trial_exposure}")
        attempts = 0

        success: bool = False
        # Loop until we find a solution or there is a failure or cancellation
        while self._controller.thread_running() and not success:
            attempts += 1
            if attempts >= SessionThread.EXPOSURE_SEARCH_ATTEMPTS_LIMIT:
                self.consoleLine.emit(f"Failed to find exposure after {attempts} attempts", 2)
                break
            self.consoleLine.emit(f"Try {trial_exposure:.3f} seconds", 3)
            (frame_success, trial_result_adus, message) = self._server.get_flat_frame_avg_adus(trial_exposure,
                                                                                               work_item.get_binning())
            if frame_success:
                if self.adus_within_tolerance(work_item, trial_result_adus):
                    # This exposure value is good enough, succeed out of loop
                    self.consoleLine.emit(
                        f"{trial_exposure:.3f} seconds gave {trial_result_adus:,.0f} ADUs, within tolerance", 2)
                    success = True
                else:
                    # Frame acquired OK but not close enough to target ADUs
                    # Improve the guess and allow the loop to continue
                    trial_exposure = self.refine_exposure(trial_exposure,
                                                          trial_result_adus,
                                                          work_item.get_target_adu(),
                                                          feedback_messages=True)
            else:
                # Error returned from the camera, fail out of the loop
                self.consoleLine.emit(f"Error taking frame: {message}", 1)
                break
        return success, trial_exposure

    def start_progress_bar(self, work_item: WorkItem):
        """Start progress bar before we begin acquiring a set of frames"""
        # print(f"start_progress_bar: {work_item}")
        progress_bar_max = work_item.get_number_of_frames()
        self.startProgressBar.emit(progress_bar_max)

    def acquire_frames(self, work_item_index: int, work_item: WorkItem, exposure: float) -> bool:
        """Acquire all the frames in this work item (given exposure, filter, and binning)"""
        # print(f"acquire_frames: {work_item_index}, {work_item}, {exposure}")
        self.consoleLine.emit(f"Acquiring {work_item.get_number_of_frames()} frames starting with this exposure.", 2)
        binning = work_item.get_binning()
        frames_taken = 0
        success = True
        # Loop for the desired number of frames or until cancel or failure
        while (frames_taken < work_item.get_number_of_frames()) and success and self._controller.thread_running():
            # Acquire one frame, saving to disk, and get its average adu value
            (success, frame_adus, message) = self._server.take_flat_frame(exposure, binning, autosave_file=True)
            if success:
                frames_taken += 1
                self.consoleLine.emit(f"{frames_taken}: Exposed {exposure:.3f} seconds, {frame_adus:,.0f} ADUs", 3)
                # Update the progress bar to reflect another frame done
                self.updateProgressBar.emit(frames_taken)
                # Update the "done" value in the session table
                self.framesComplete.emit(work_item_index, frames_taken)
                # Use that just-acquired frame to further refine the exposure we use
                exposure = self.refine_exposure(exposure, frame_adus,
                                                                    work_item.get_target_adu(),
                                                                    feedback_messages=False)
                work_item.update_initial_exposure_estimate(new_exposure=exposure)
            else:
                self.consoleLine.emit(f"Error taking flat frame: {message}", 2)

        return success

    def clean_up_from_cancel(self):
        """Cancel clicked - do any necessary cleanup"""
        pass
        # print("clean_up_from_cancel")

    def clean_up_from_failure(self):
        """Session stopped due to some kind of failure - do any necessary cleanup"""
        pass
        # print("clean_up_from_failure")

    # Test if the given ADU value from an exposure is close to the target ADU level

    @staticmethod
    def adus_within_tolerance(work_item: WorkItem, test_adus: float) -> bool:
        """Determine if the given ADU count from a frame is close enough to the target"""
        # print(f"adus_within_tolerance({work_item},{test_adus})")
        difference = abs(test_adus - work_item.get_target_adu())
        difference_ratio = difference / work_item.get_target_adu()
        within = difference_ratio <= work_item.get_adu_tolerance()
        # print(f"  Difference ratio {difference_ratio}, within tolerance: {within}")
        return within

    # A trial exposure has produced ADU levels out of range and we'll improve the estimate
    # We know how many ADUs the trial exposure produced, and how many we actually want.
    # Assume the relationship is linear - apply the "miss factor" of the ADUs to the exposure time

    def refine_exposure(self, tried_exposure: float,
                        resulting_adus: float,
                        target_adus: float,
                        feedback_messages: bool) -> float:
        """Refine the exposure from a frame to get closer to the desired target ADU level"""
        # print(f"refine_exposure({tried_exposure},{resulting_adus},{target_adus})")
        if resulting_adus > target_adus:
            if feedback_messages:
                self.consoleLine.emit(f"{resulting_adus:,.0f} ADU too high, reducing exposure", 4)
        else:
            if feedback_messages:
                self.consoleLine.emit(f"{resulting_adus:,.0f} ADU too low, increasing exposure", 4)
        miss_factor = resulting_adus / target_adus
        new_exposure = tried_exposure / miss_factor
        # print(f"  Miss factor {miss_factor}, new exposure {new_exposure}")
        return new_exposure
