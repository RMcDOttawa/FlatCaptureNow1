from datetime import datetime, timedelta
from time import sleep
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal

from Constants import Constants
from DataModel import DataModel
from Ditherer import Ditherer
from FilterSpec import FilterSpec
from Preferences import Preferences
from SessionController import SessionController
from TheSkyX import TheSkyX
from WorkItem import WorkItem


#
#   The worker thread that actually does the flat-frame acquisition
#

class SessionThread(QObject):
    # Signals we emit
    finished = pyqtSignal()
    consoleLine = pyqtSignal(str, int)  # String, indentation level
    startRowIndex = pyqtSignal(int)
    startProgressBar = pyqtSignal(int)  # Initialize progress bar, for maximum this much
    updateProgressBar = pyqtSignal(int)  # Update the bar with this value of progress toward maximum
    finishProgressBar = pyqtSignal()  # Finished with progress bar, hide it
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

        # We maintain a dict of download times indexed by binning, stored in the
        # preferences so the values from last session are our initial guesses this time
        self._download_times: {int: float} = {}

    # Invoked by the thread-start signal after the thread is comfortably running,
    # this is the method that does the actual work of frame acquisition.
    # We're not doing anything about cooling the camera - we assume
    # that we are at the end of a session, so the camera is already at temperature.

    def run_session(self):
        """Run the flat-frame acquisition thread main program"""

        self.consoleLine.emit(f"Session Started at server {self._server_address}:{self._server_port}", 1)

        if self.pre_session_mount_control():

            # Time downloads of the binnings in use so we can estimate completion times
            self._download_times = self.measure_download_times()
            ditherer: Optional[Ditherer] = self.set_up_dithering()
            # Run through the work list, one item at a time, watching for early
            # exit if cancellation is requested
            work_item_index: int = 0
            for work_item in self._work_items:
                if self._controller.thread_cancelled():
                    break
                if not self.process_one_work_item(work_item_index, work_item, ditherer):
                    # Failure in the work item, so we fail out of the loop
                    break
                work_item_index += 1
                self.reset_dithering(ditherer)

            if self._controller.thread_running():
                # Normal termination (not cancelled) so we can do the warm-up
                self.handle_warm_up()
                self.post_session_mount_control()

        self.consoleLine.emit("Session Ended" if self._controller.thread_running()
                              else "Session Cancelled", 1)
        sleep(Constants.DELAY_AT_FINISH)
        self.finished.emit()

    # Various mount control things that are optionally done before acquisition
    #       Home the mount
    #       Slew to the light source
    #       Stop tracking
    def pre_session_mount_control(self) -> bool:
        success = True
        # Are we doing mount control at all?
        if self._data_model.get_control_mount():
            # Home the mount if requested
            if self._data_model.get_home_mount():
                success = self.home_mount()
            # Slew to light source if requested
            if success and self._data_model.get_slew_to_light_source():
                success = self.slew_to_light_source()
            # Stop tracking if requested
            if success and self._data_model.get_tracking_off():
                success = self.turn_tracking_off()
        return success

    # Various mount control things that are optionally done after acquisition
    #       Park the mount
    def post_session_mount_control(self) -> bool:
        success = True
        # Are we doing mount control at all?
        if self._data_model.get_control_mount():
            if self._data_model.get_park_when_done():
                success = self.park_mount()
        return success

    def home_mount(self) -> bool:
        self.consoleLine.emit("Homing mount", 1)
        (success, message) = self._server.home_mount(asynchronous=False)
        if not success:
            self.consoleLine.emit(f"Error homing mount: {message}", 2)
        return success

    def slew_to_light_source(self) -> bool:
        self.consoleLine.emit("Slewing to location of light source", 1)
        (success, message) = self._server.start_slew_to(alt=self._data_model.get_source_alt(),
                                                        az=self._data_model.get_source_az(),
                                                        asynchronous=False)
        if not success:
            self.consoleLine.emit(f"Error slewing mount: {message}", 2)
        return success

    # Tell TheSkyX to stop mount tracking so we don't drift away from the light source
    # return an indicator of whether this succeeded

    def turn_tracking_off(self) -> bool:
        """Stop the mount tracking so it stays pointed to the light source"""
        (success, message) = self._server.set_tracking(False)
        if success:
            self.consoleLine.emit("Tracking stopped.", 1)
        else:
            self.consoleLine.emit(f"Error stopping tracking: {message}", 1)
        return success

    # Set up optional dithering.  Create a dithering object if dithering is
    # requested, otherwise return a null object.  The object stores the original
    # location of the light source.  We may or may not have Slewed to the light
    # source, so we'll query the mount for its current location and use that
    # as the reference from which dithering proceeds. If mount location fails,
    # return a null object - we'll keep imaging, just without dithering

    def set_up_dithering(self) -> Optional[Ditherer]:
        """Set up dithering control object to optionally dither acquired frames"""
        if self._data_model.get_control_mount() and self._data_model.get_dither_flats():
            # We assume mount is pointed at target, either by our slew or
            # manual operation.  Get its location for the dither controller
            (success, current_alt, current_az, message) = self._server.get_scope_alt_az()
            if success:
                ditherer = Ditherer(current_alt, current_az,
                                    self._data_model.get_dither_radius(),
                                    self._data_model.get_dither_max_radius())
                self.consoleLine.emit(f"Dithering flats: {ditherer}", 1)
            else:
                ditherer = None
                self.consoleLine.emit(f"Error locating mount: {message}", 1)
        else:
            ditherer = None
        return ditherer

    # At the end of a work item, if dithering was in use we will have spiraled
    # away from the target. Here we reset the dithering calculations, and slew back to
    # the original target location.
    def reset_dithering(self, ditherer: Optional[Ditherer]):
        """Reset dithering object at the end of a set, so next set starts fresh"""
        if ditherer is not None:
            original_alt = ditherer.get_start_alt()
            original_az = ditherer.get_start_az()
            ditherer.reset()
            (success, message) = self._server.start_slew_to(original_alt, original_az, asynchronous=False)
            if not success:
                self.consoleLine.emit(f"Error resetting dither: {message}", 1)

    # Process the given work item (a number of frames of one spec).
    # If dithering is in use, move scope slightly for each frame, in
    # a pattern controlled by the given dithering object
    # Return a success indicator
    def process_one_work_item(self, work_item_index: int,
                              work_item: WorkItem,
                              ditherer: Optional[Ditherer]) -> bool:
        """Process a single work item - a number of frames of given specification"""

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
                        self.start_progress_bar(work_item)
                        if self.acquire_frames(work_item_index, work_item, ditherer):
                            success = True

            # If we failed or were cancelled, clean up
        if self._controller.thread_cancelled():
            self.clean_up_from_cancel()
        elif not success:
            self.clean_up_from_failure()
        return success

    # If user has requested dithering of frames
    # Turn off camera cooler so it can warm up while we're busy closing the dome
    # (I usually start the flat frames running with a light panel, then do all the physical
    # close-down of the dome, such as closing the dome and putting the cover on it, while
    # they are gathering.  If they finish while I'm still puttering, this lets the camera
    # start to warm up gently.

    def handle_warm_up(self):
        """Handle optional post-session warm up of CCD"""
        if self._data_model.get_warm_when_done():
            self.consoleLine.emit("Turning off camera cooling as requested", 1)
            self._server.set_camera_cooling(cooling_on=False, target_temperature=0)

    # If the option is set, park and disconnect the mount
    def park_mount(self):
        """Park and disconnect mount when done, if requested"""
        self.consoleLine.emit("Parking and disconnecting mount", 1)
        (success, message) = self._server.park_and_disconnect_mount()
        if not success:
            self.consoleLine.emit(f"Error parking: {message}", 1)
        return success

    def connect_camera(self) -> bool:
        """Ask server to connect to camera"""
        (success, message) = self._server.connect_to_camera()
        if not success:
            self.consoleLine.emit(f"** Error connecting to camera: {message}", 2)
        return success

    def connect_filter_wheel(self) -> bool:
        """Ask server to connect to filter wheel"""
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

        if self._data_model.get_use_filter_wheel():
            if filter_wanted.get_slot_number() == self._last_filter_slot:
                # No change necessary
                success = True
            else:
                self._last_filter_slot = filter_wanted.get_slot_number()
                filter_index = self._last_filter_slot - 1
                # Changing filter to index{filter_index}
                (success, message) = self._server.select_filter(filter_index)
                if not success:
                    self.consoleLine.emit(f"** Error selecting filter {filter_wanted.get_slot_number()}: {message}", 2)
        else:
            # No filter wheel, ignoring
            success = True
        return success

    def start_progress_bar(self, work_item: WorkItem):
        """Start progress bar before we begin acquiring a set of frames"""
        progress_bar_max = work_item.get_number_of_frames()
        self.startProgressBar.emit(progress_bar_max)

    # Acquire the number of frames, of the specification, in the given work item.
    # We start with an estimate of the right exposure, based on what worked last time.
    # after each frame we measure the average ADUs, and keep the frame only if it is within
    # spec.  Then we refine the exposure.  This way the first one or two exposures may be rejected
    # as we search for a good exposure, then the others will adjust as acquisition proceeds.  This
    # will allow for changes such as the sky (if sky flats) gradually brightening, or allows
    # the operator to adjust the brightness of a light panel.

    # In case conditions become unworkable, we will keep track of how many frames IN A ROW hae
    # been rejected, and fail if a threshold is exceeded.

    # Because we don't want to save FITs files for frames that are rejected, we take frames with
    # autosave OFF, then manually save the frame once we know we like it.

    def acquire_frames(self, work_item_index: int,
                       work_item: WorkItem,
                       ditherer: Optional[Ditherer]) -> bool:
        """Acquire all the frames in this work item (given exposure, filter, and binning)"""

        binning = work_item.get_binning()
        filter_name = work_item.get_filter_spec().get_name()
        assert FilterSpec.valid_filter_name(filter_name)
        frames_accepted = 0
        rejected_in_a_row = 0
        exposure = work_item.initial_exposure_estimate()
        success = True
        # Loop for the desired number of frames or until cancel or failure
        repeat_try = False

        while (frames_accepted < work_item.get_number_of_frames()) and success and self._controller.thread_running():
            # Set scope location if dithering is in use
            if repeat_try:
                # We don't do a dither move if we are trying again on a given frame after an ADU failure
                pass
            else:
                # This is a new frame, not a retry, so do a dither move
                success = self.dither_next_frame(ditherer)
            if success:
                repeat_try = False
                # Acquire one frame, saving to disk, and get its average adu value
                self.consoleLine.emit(f"Exposing frame {frames_accepted + 1} for {exposure:.2f} seconds.", 2)
                (success, frame_adus, message) = self.take_one_flat_frame(exposure, binning, autosave_file=False)
                if success:
                    # Is this frame within acceptable adu range?
                    if self.adus_within_tolerance(work_item, frame_adus):
                        if self._controller.get_show_adus():
                            self.consoleLine.emit(f"{frame_adus:,.0f} ADUs: Close enough, keeping this frame.", 3)
                        (success, message) = self.save_acquired_frame(filter_name, exposure,
                                                                      binning, frames_accepted + 1)
                        if success:
                            rejected_in_a_row = 0
                            frames_accepted += 1
                            self.updateProgressBar.emit(frames_accepted)
                            self.framesComplete.emit(work_item_index, frames_accepted)
                        else:
                            self.consoleLine.emit(f"Error saving image file: {message}", 2)
                    else:
                        rejected_in_a_row += 1
                        self.consoleLine.emit(f"{frame_adus:,.0f} ADUs: Rejected, adjusting exposure.", 3)
                        repeat_try = True  # Prevent dither on retry
                        if rejected_in_a_row > Constants.MAX_FRAMES_REJECTED_IN_A_ROW:
                            self.consoleLine.emit("Too many rejected frames, stopping session.", 2)
                            success = False
                    if success:
                        exposure = self.refine_exposure(exposure,
                                                        frame_adus,
                                                        work_item.get_target_adu(),
                                                        feedback_messages=False)
                        work_item.update_initial_exposure_estimate(exposure)
                else:
                    self.consoleLine.emit(f"Error taking frame: {message}", 2)

        return success

    # If dithering is in use, move the scope as appropriate.  The ditherer object handles
    # the move locations.  It will instruct us to either:
    #       Don't move it, as it is on-target
    #       Move to a given alt-az, which is on the dithering radius near the target
    #   If dithering is not in use, we just do nothing

    def dither_next_frame(self, ditherer: Optional[Ditherer]) -> bool:
        """Do appropriate next slew to dither the next acquired frame"""
        if ditherer is None:
            # Dithering is not in use
            success = True
        else:
            (move_scope, to_alt, to_az) = ditherer.next_frame()
            if move_scope:
                # self.consoleLine.emit(f"  Dithering move to {to_alt:.5f}, {to_az:.5f}", 2)
                (success, message) = self._server.start_slew_to(to_alt, to_az, asynchronous=False)
                if not success:
                    self.consoleLine.emit(f"Error in dithering move: {message}", 2)
            else:
                # print("  Scope is on target, don't move")
                success = True
        return success

    def take_one_flat_frame(self, exposure: float, binning: int, autosave_file: bool) -> (bool, float, str):
        """Take a single flat frame with given specs. Start asynchronous then wait for it"""
        frame_adus = 0
        (success, message) = self._server.take_flat_frame(exposure, binning,
                                                          asynchronous=True,
                                                          autosave_file=autosave_file)
        if success:
            wait_time = exposure
            if binning in self._download_times:
                wait_time += self._download_times[binning]
            else:
                print(f"Warning: missing binning {binning} in download times {self._download_times}")
            self.cancellable_wait(wait_time, progress_bar=False)
            success = False
            if self._controller.thread_running():
                if self.wait_for_camera_to_finish():
                    (success, frame_adus, message) = self._server.get_adus_from_last_image()
        return success, frame_adus, message

    # Wait given time, but do it in little bits, checking for thread cancellation.
    # return an indicator that thread is still up and running (not cancelled)

    def cancellable_wait(self, wait_time: float, progress_bar: bool) -> bool:
        """Wait a given time in a cancellable loop"""
        # print(f"cancellable_wait({wait_time})")
        # We'll multiply the progress bar value by 100 so we can ignore the fractional part
        if progress_bar:
            self.startProgressBar.emit(max(1, int(round(wait_time * 100))))
        accumulated_wait_time = 0.0
        while (accumulated_wait_time < wait_time) and self._controller.thread_running():
            # print(f"   Accumulated {accumulated_wait_time}")
            sleep(Constants.CANCELLABLE_WAIT_INCREMENTS)
            accumulated_wait_time += Constants.CANCELLABLE_WAIT_INCREMENTS
            if progress_bar:
                self.updateProgressBar.emit(max(1, int(round(accumulated_wait_time * 100))))
        if progress_bar:
            self.finishProgressBar.emit()
        return self._controller.thread_running()

    # We've waited an appropriate time for an asynch image to happen.  Now we resync with the
    # camera by waiting until it reports finished.  Return an "ok to continue" indicator

    def wait_for_camera_to_finish(self) -> bool:
        """Re-sync with image acquisition already begun, waiting for completion"""
        # print("wait_for_camera_completion")
        success = False
        total_time_waiting = 0.0
        (complete_check_successful, is_complete, message) = self._server.get_exposure_is_complete()
        while self._controller.thread_running() \
                and complete_check_successful \
                and not is_complete \
                and total_time_waiting < Constants.CAMERA_RESYNCH_TIMEOUT:
            sleep(Constants.CAMERA_RESYNCH_CHECK_INTERVAL)
            total_time_waiting += Constants.CAMERA_RESYNCH_CHECK_INTERVAL
            (complete_check_successful, is_complete, message) = self._server.get_exposure_is_complete()

        if not self._controller.thread_running():
            pass
            # Session is cancelled, we don't need to do anything except stop
        elif not complete_check_successful:
            # Error happened checking camera, return an error and display the message
            self.consoleLine.emit(f"Error waiting for camera: {message}", 2)
            success = False
        elif total_time_waiting >= Constants.CAMERA_RESYNCH_TIMEOUT:
            # We timed out - the camera is not responding for some reason
            success = False
            self.consoleLine.emit("Timed out waiting for camera to finish", 2)
        else:
            assert is_complete
            success = True
        return success

    def clean_up_from_cancel(self):
        """Cancel clicked - do any necessary cleanup"""
        (query_success, is_complete, message) = self._server.get_exposure_is_complete()
        if query_success:
            if is_complete:
                pass  # Nothing to cancel
            else:
                # An exposure is running, send an abort
                (abort_success, message) = self._server.abort_image()
                if abort_success:
                    pass  # The abort worked, we're happy
                else:
                    pass  # We're cancelling anyway, don't clutter with message
        else:
            pass  # We're cancelling anyway, don't clutter with message

    def clean_up_from_failure(self):
        """Session stopped due to some kind of failure - do any necessary cleanup"""
        pass

    # Test if the given ADU value from an exposure is close to the target ADU level

    @staticmethod
    def adus_within_tolerance(work_item: WorkItem, test_adus: float) -> bool:
        """Determine if the given ADU count from a frame is close enough to the target"""
        difference = abs(test_adus - work_item.get_target_adu())
        difference_ratio = difference / work_item.get_target_adu()
        within = difference_ratio <= work_item.get_adu_tolerance()
        return within

    # A trial exposure has produced ADU levels out of range and we'll improve the estimate
    # We know how many ADUs the trial exposure produced, and how many we actually want.
    # Assume the relationship is linear - apply the "miss factor" of the ADUs to the exposure time

    def refine_exposure(self, tried_exposure: float,
                        resulting_adus: float,
                        target_adus: float,
                        feedback_messages: bool) -> float:
        """Refine the exposure from a frame to get closer to the desired target ADU level"""
        if resulting_adus > target_adus:
            if feedback_messages:
                self.consoleLine.emit(f"{resulting_adus:,.0f} ADU too high, reducing exposure", 4)
        else:
            if feedback_messages:
                self.consoleLine.emit(f"{resulting_adus:,.0f} ADU too low, increasing exposure", 4)
        miss_factor = resulting_adus / target_adus
        new_exposure = tried_exposure / miss_factor
        return new_exposure

    def measure_download_times(self) -> {int: float}:
        """Measure download times for all binnings in the work list by taking and timing bias frames"""
        self.consoleLine.emit("Measuring download times", 1)
        download_times: {int: float} = {}
        for work_item in self._work_items:
            binning = work_item.get_binning()
            if binning not in download_times:
                # We haven't measure this one yet
                (success, download_time) = self.time_download(binning)
                download_times[binning] = download_time if success else 0
        return download_times

    def time_download(self, binning: int) -> (bool, float):
        """Time how long download of given binning takes by timing a zero-length bias frame"""
        time_before: datetime = datetime.now()
        (success, message) = self._server.take_bias_frame(binning, auto_save_file=False, asynchronous=False)
        if success:
            time_after: datetime = datetime.now()
            time_to_download: timedelta = time_after - time_before
            seconds = time_to_download.seconds
            self.consoleLine.emit(f"Binned {binning} x {binning}: {seconds} seconds", 2)
        else:
            self.consoleLine.emit(f"Error timing download: {message}", 2)
            seconds = 0
        return success, seconds

    def save_acquired_frame(self,
                            filter_name: str,
                            exposure: float,
                            binning: int,
                            sequence: int) -> (bool, str):
        """Have the just-acquired frame saved to an appropriate location"""
        if self._data_model.get_save_files_locally():
            (success, message) = \
                self._server.save_acquired_frame_to_local_directory(
                    self._data_model.get_local_path(),
                    filter_name,
                    exposure,
                    binning,
                    sequence)
        else:
            (success, message) = \
                self._server.save_acquired_frame_to_autosave(
                    filter_name,
                    exposure,
                    binning,
                    sequence)
        return success, message
