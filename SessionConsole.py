from time import strftime

from PyQt5 import uic
from PyQt5.QtCore import Qt, QThread, QMutex, QItemSelection, QModelIndex, QItemSelectionModel, QEvent, QObject
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QDialog, QListWidgetItem

from BinningSpec import BinningSpec
from Constants import Constants
from DataModel import DataModel
from FilterSpec import FilterSpec
from MultiOsUtil import MultiOsUtil
from Preferences import Preferences
from SessionController import SessionController
from SessionPlanTableModel import SessionPlanTableModel
from SessionThread import SessionThread
from WorkItem import WorkItem
from WorkItemTableModel import WorkItemTableModel


#
# UI controller for the dialog used to monitor the acquisition session while it is in progress.
# This UI contains a list of the frames to be acquired with the current one highlighted,
# a frame with a scrolling message log, and a "cancel" button
#


class SessionConsole(QDialog):

    # Creator
    def __init__(self, data_model: DataModel, preferences: Preferences, table_model: SessionPlanTableModel):

        QDialog.__init__(self, flags=Qt.Dialog)
        self._data_model = data_model
        self._table_model = table_model
        self._preferences = preferences

        self.ui = uic.loadUi(MultiOsUtil.path_for_file_in_program_directory("SessionConsole.ui"))

        self.ui.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint
                               | Qt.WindowMinMaxButtonsHint)
        self._work_items = self.create_work_item_list(data_model, table_model)

        self._work_items_table_model = WorkItemTableModel(data_model, preferences, self._work_items)
        self.ui.sessionTable.setModel(self._work_items_table_model)

        # If a window size is saved, set the window size
        window_size = self._preferences.get_session_window_size()
        if window_size is not None:
            self.ui.resize(window_size)

        # Watch events so we can see window resizing
        self.ui.installEventFilter(self)

        # Mutex to serialize signal handling from thread
        self._signal_mutex = QMutex()

        # Resize columns to contents
        self.ui.sessionTable.setVisible(False)
        self.ui.sessionTable.resizeColumnsToContents()
        self.ui.sessionTable.setVisible(True)

        # Initially we don't want to see the progress bar
        self.ui.progressBar.setVisible(False)

        # Button responders
        self.ui.closeButton.clicked.connect(self.close_button_clicked)
        self.ui.cancelButton.clicked.connect(self.cancel_button_clicked)

        self._session_controller = SessionController()

        # While the session thread is running, we want the Cancel button enabled and
        # the Close button disabled
        self.ui.cancelButton.setEnabled(True)
        self.ui.closeButton.setEnabled(False)

        # Set font sizes of all elements using fonts to the saved font size
        standard_font_size = self._preferences.get_standard_font_size()
        MultiOsUtil.set_font_sizes(parent=self.ui,
                                   standard_size=standard_font_size,
                                   title_prefix=Constants.MAIN_TITLE_LABEL_PREFIX,
                                   title_increment=Constants.MAIN_TITLE_FONT_SIZE_INCREMENT,
                                   subtitle_prefix=Constants.SUBTITLE_LABEL_PREFIX,
                                   subtitle_increment=Constants.SUBTITLE_FONT_SIZE_INCREMENT
                                   )

        # Create and start the thread that does the actual frame acquisition
        self._session_thread: SessionThread = SessionThread(data_model=self._data_model,
                                                            preferences=self._preferences,
                                                            work_items=self._work_items,
                                                            controller=self._session_controller,
                                                            server_address=self._data_model.get_server_address(),
                                                            server_port=self._data_model.get_port_number(),
                                                            warm_when_done=self._data_model.get_warm_when_done())
        assert self._session_controller is not None

        # Create thread and attach worker object to it
        self._thread = QThread()
        self._session_thread.moveToThread(self._thread)

        # Have the thread-started signal invoke the actual worker object
        self._thread.started.connect(self._session_thread.run_session)
        self._thread.finished.connect(self.thread_finished)

        # Set up signals to receive signals from the thread
        self._session_thread.finished.connect(self._thread.quit)
        self._session_thread.consoleLine.connect(self.console_line)
        self._session_thread.startRowIndex.connect(self.start_row_index)
        self._session_thread.startProgressBar.connect(self.start_progress_bar)
        self._session_thread.updateProgressBar.connect(self.update_progress_bar)
        self._session_thread.finishProgressBar.connect(self.finish_progress_bar)
        self._session_thread.framesComplete.connect(self.display_frames_complete)

        # Run the thread
        self._thread.start()

    # Method that receives the "thread finished" signal, to clean up
    # from the thread
    def thread_finished(self):
        """Receive signal that thread has finished, and clean up"""
        self._thread = None
        self._session_controller = None
        # Reverse the status of the buttons: enable close, disable cancel
        self.ui.closeButton.setEnabled(True)
        self.ui.cancelButton.setEnabled(False)
        self.ui.progressBar.setVisible(False)

    # Receive signal that we're starting a work item corresponding to a given row index
    # in the work item table, so we can highlight (and scroll to) that row
    def start_row_index(self, row_index: int):
        """Receive signal that a new row in table has started, so we can highlight it"""

        # Create a selection corresponding to this row in the table
        self._signal_mutex.lock()
        selection: QItemSelection = QItemSelection()
        model_index_top_left: QModelIndex = self._table_model.createIndex(row_index, 0)
        model_index_bottom_right: QModelIndex = \
            self._table_model.createIndex(row_index,
                                          WorkItemTableModel.NUMBER_OF_COLUMNS - 1)
        selection.select(model_index_top_left, model_index_bottom_right)
        # Set the selection to that row so it highlights
        selection_model: QItemSelectionModel = self.ui.sessionTable.selectionModel()
        selection_model.clearSelection()
        selection_model.select(selection, QItemSelectionModel.Select)
        # Scroll to ensure the selected row is in view
        self.ui.sessionTable.scrollTo(model_index_top_left)
        self._signal_mutex.unlock()

    def create_work_item_list(self, data_model: DataModel,
                              table_model: SessionPlanTableModel) -> [WorkItem]:
        """Create the list of work items from the session plan"""

        result: [WorkItem] = []
        model_rows: int = table_model.rowCount(QModelIndex(), ) if data_model.get_use_filter_wheel() else 1
        model_columns: int = table_model.columnCount(QModelIndex())

        # Every combination of row and column with a nonzero entry is a work item
        for row_index in range(model_rows):
            for column_index in range(model_columns):
                index = table_model.createIndex(row_index, column_index)
                cell_value = int(table_model.data(index, Qt.DisplayRole))
                if cell_value != 0:
                    raw_row_index: int = data_model.map_display_to_raw_filter_index(row_index)
                    raw_column_index: int = data_model.map_display_to_raw_binning_index(column_index)
                    filter_spec: FilterSpec = data_model.get_filter_specs()[raw_row_index]

                    binning: BinningSpec = data_model.get_binning_specs()[raw_column_index]

                    work_item = WorkItem(cell_value, filter_spec, binning.get_binning_value(),
                                         data_model.get_target_adus(), data_model.get_adu_tolerance(),
                                         self._preferences)
                    result.append(work_item)
        return result

    # Shows the console as modal.
    # First we will spin-off the worker task so it can update the console data

    def close_button_clicked(self):
        """Close button clicked - close the session dialog"""
        self.ui.close()

    def cancel_button_clicked(self):
        """Cancel button clicked - set flag to cause worker thread to stop"""
        self._session_controller.cancel_thread()
        self.console_line("Cancel requested.", 1)

    # A signal has come from the thread to display a line in the console frame
    def console_line(self, message: str, level: int):
        """Receive signal from worker to add a line to the console frame"""
        self._signal_mutex.lock()
        time_formatted = strftime("%H:%M:%S ")
        indent_string = ""
        if level > 1:
            indentation_block = " " * Constants.SESSION_CONSOLE_INDENTATION_DEPTH
            indent_string = indentation_block * (level - 1)

        # Create the text line to go in the console
        list_item: QListWidgetItem = QListWidgetItem(time_formatted + " " + indent_string + message)

        # Set its font size according to the settings
        item_font: QFont = list_item.font()
        item_font.setPointSize(self._preferences.get_standard_font_size())
        list_item.setFont(item_font)

        # Add to bottom of console and scroll to it
        self.ui.consoleList.addItem(list_item)
        self.ui.consoleList.scrollToItem(list_item)
        self._signal_mutex.unlock()

    # Signal from worker thread to start a progress bar with given maximum range

    def start_progress_bar(self, bar_max: int):
        """Start a progress bar for a long task"""
        self.ui.progressBar.setMaximum(bar_max)
        self.ui.progressBar.setValue(0)
        self.ui.progressBar.setVisible(True)

    def update_progress_bar(self, bar_value: int):
        """Update the progress bar with the given completion value"""
        self.ui.progressBar.setValue(bar_value)

    def finish_progress_bar(self):
        """Turn off the completed progress bar"""
        self.ui.progressBar.setVisible(False)

    def display_frames_complete(self, row_index: int, frames_complete: int):
        """Display the number of frames complete for the given row index in the table"""
        self._work_items_table_model.set_frames_complete(row_index, frames_complete)
    # Catch window resizing so we can record the changed size

    def eventFilter(self, object: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Resize:
            window_size = event.size()
            self._preferences.set_session_window_size(window_size)
        return False  # Explain that we didn't handle event, should be passed upward
