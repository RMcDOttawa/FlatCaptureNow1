import json
import os
from typing import Optional

from PyQt5 import uic
from PyQt5.QtCore import QModelIndex, Qt, QObject, QEvent
from PyQt5.QtWidgets import QMainWindow, QDialog, QWidget, QFileDialog, QMessageBox

from Constants import Constants
from DataModel import DataModel
from DataModelDecoder import DataModelDecoder
from SharedUtils import SharedUtils
from Preferences import Preferences
from PrefsWindow import PrefsWindow
from RmNetUtils import RmNetUtils
from SessionConsole import SessionConsole
from SessionPlanTableModel import SessionPlanTableModel
from Validators import Validators


#
#   User interface controller for main window
#

class MainWindow(QMainWindow):

    # This version of the constructor is used to open a window
    # populated by the default values from the preferences object
    def __init__(self, data_model: DataModel, preferences: Preferences):
        QMainWindow.__init__(self, flags=Qt.Window)
        self._table_model: Optional[SessionPlanTableModel] = None
        self._is_dirty: bool = False  # Dirty means unsaved changes exist

        self.ui = uic.loadUi(SharedUtils.path_for_file_in_program_directory("MainWindow.ui"))

        self._data_model: DataModel = data_model
        self._preferences: Preferences = preferences
        self.connect_responders()


        # a dict will keep track of the validity of all fields, so we can easily
        # tell if everything is OK to proceed
        # The dict is usually keyed by the QWidget we have validated. But in the case
        # of a table cell, it will be keyed by a string index of the cell.  THis doesn't
        # matter since we never query the table in any manner except checking for any FALSE values
        self._field_validity: {object, bool} = {}

        self.set_ui_from_data_model(data_model)
        self.ui.setWindowTitle(Constants.UNSAVED_WINDOW_TITLE)
        self._file_path = ""

        # If a window size is saved, set the window size
        window_size = self._preferences.get_main_window_size()
        if window_size is not None:
            self.ui.resize(window_size)

        # Set font sizes of all elements with fonts to the saved font size
        standard_font_size = self._preferences.get_standard_font_size()
        SharedUtils.set_font_sizes(parent=self.ui,
                                   standard_size=standard_font_size,
                                   title_prefix=Constants.MAIN_TITLE_LABEL_PREFIX,
                                   title_increment=Constants.MAIN_TITLE_FONT_SIZE_INCREMENT,
                                   subtitle_prefix=Constants.SUBTITLE_LABEL_PREFIX,
                                   subtitle_increment=Constants.SUBTITLE_FONT_SIZE_INCREMENT
                                   )

    def set_field_validity(self, field, validity: bool):
        self._field_validity[field] = validity
        self.enable_proceed_button()

    def enable_proceed_button(self):
        all_good = all(val for val in self._field_validity.values())
        self.ui.proceedButton.setEnabled(all_good)


    def set_is_dirty(self, is_dirty: bool):
        """Record whether the open file is dirty (has unsaved changes)"""
        self._is_dirty = is_dirty

    def set_up_ui(self):
        """Do UI setup that must be done after init finished"""
        self.ui.installEventFilter(self)

    # Connect UI controls to methods here for response
    def connect_responders(self):
        """Connect UI fields and controls to the methods that respond to them"""

        # Menu items
        self.ui.actionPreferences.triggered.connect(self.preferences_menu_triggered)
        self.ui.actionNew.triggered.connect(self.new_menu_triggered)
        self.ui.actionOpen.triggered.connect(self.open_menu_triggered)
        self.ui.actionSave.triggered.connect(self.save_menu_triggered)
        self.ui.actionSave_As.triggered.connect(self.save_as_menu_triggered)
        self.ui.actionLarger.triggered.connect(self.font_larger_menu)
        self.ui.actionSmaller.triggered.connect(self.font_smaller_menu)
        self.ui.actionReset.triggered.connect(self.font_reset_menu)

        # Bulk change buttons
        self.ui.defaultsButton.clicked.connect(self.defaults_button_clicked)
        self.ui.allOnButton.clicked.connect(self.all_on_button_clicked)
        self.ui.allOffButton.clicked.connect(self.all_off_button_clicked)

        # Proceed button
        self.ui.proceedButton.clicked.connect(self.proceed_button_clicked)

        # Filter wheel
        self.ui.useFilterWheel.clicked.connect(self.use_filter_wheel_clicked)

        # Fields other than the session plan table
        self.ui.serverAddress.editingFinished.connect(self.server_address_changed)
        self.ui.portNumber.editingFinished.connect(self.port_number_changed)
        self.ui.targetAdus.editingFinished.connect(self.target_adus_changed)
        self.ui.aduTolerance.editingFinished.connect(self.adu_tolerance_changed)
        self.ui.warmWhenDone.clicked.connect(self.warm_when_done_changed)

    # Responders

    def server_address_changed(self):
        """Validate and store server address"""
        proposed_value: str = self.ui.serverAddress.text()
        valid = RmNetUtils.valid_server_address(proposed_value)
        if valid:
            self.set_is_dirty(proposed_value != self._data_model.get_server_address())
            self._data_model.set_server_address(proposed_value)
        self.set_field_validity(self.ui.serverAddress, valid)
        SharedUtils.background_validity_color(self.ui.serverAddress, valid)

    def port_number_changed(self):
        """Validate and store port number"""
        proposed_value: str = self.ui.portNumber.text()
        converted_value = Validators.valid_int_in_range(proposed_value, 0, 65535)
        valid = converted_value is not None
        if valid:
            self.set_is_dirty(converted_value != self._data_model.get_port_number())
            self._data_model.set_port_number(converted_value)
        self.set_field_validity(self.ui.portNumber, valid)
        SharedUtils.background_validity_color(self.ui.portNumber, valid)

    def target_adus_changed(self):
        """Validate and store target ADU level"""
        proposed_value: str = self.ui.targetAdus.text()
        converted_value = Validators.valid_float_in_range(proposed_value, 0, 1000000)
        valid = converted_value is not None
        if valid:
            self.set_is_dirty(converted_value != self._data_model.get_target_adus())
            self._data_model.set_target_adus(converted_value)
        self.set_field_validity(self.ui.targetAdus, valid)
        SharedUtils.background_validity_color(self.ui.targetAdus, valid)

    def adu_tolerance_changed(self):
        """Validate and store ADU tolerance percentage"""
        proposed_value = self.ui.aduTolerance.text()
        converted_value = Validators.valid_float_in_range(proposed_value, 0, 100)
        valid = converted_value is not None
        if valid:
            to_fraction = converted_value / 100.0
            self.set_is_dirty(to_fraction != self._data_model.get_adu_tolerance())
            self._data_model.set_adu_tolerance(to_fraction)
        self.set_field_validity(self.ui.targetAdus, valid)
        SharedUtils.background_validity_color(self.ui.aduTolerance, valid)

    def warm_when_done_changed(self):
        """Store the new state of the 'warm when done' checkbox"""
        self.set_is_dirty(self.ui.warmWhenDone.isChecked()
                          != self._data_model.get_warm_when_done())
        self._data_model.set_warm_when_done(self.ui.warmWhenDone.isChecked())

    # Preferences menu has been selected.  Open the preferences dialog
    def preferences_menu_triggered(self):
        """Respond to preferences menu by opening preferences dialog"""
        dialog: PrefsWindow = PrefsWindow()
        dialog.set_up_ui(self._preferences)
        QDialog.DialogCode = dialog.ui.exec_()

    # Set the UI fields from the preferences object given
    def set_ui_from_data_model(self, data_model: DataModel):
        """Set the fields in the UI from the given data model"""
        # Server address and port
        self.ui.serverAddress.setText(data_model.get_server_address())
        self.ui.portNumber.setText(str(data_model.get_port_number()))

        # Target ADU and tolerance
        self.ui.targetAdus.setText(str(data_model.get_target_adus()))
        adu_tol = data_model.get_adu_tolerance()
        self.ui.aduTolerance.setText(str(adu_tol * 100.0))

        # Warm up when done?
        self.ui.warmWhenDone.setChecked(data_model.get_warm_when_done())

        # Filter wheel
        self.ui.useFilterWheel.setChecked(data_model.get_use_filter_wheel())

        # Set up table model representing the session plan, and connect it to the table

        self._table_model = SessionPlanTableModel(data_model, self._preferences,
                                                  self.set_is_dirty, self.set_field_validity)
        self.ui.sessionPlanTable.setModel(self._table_model)

        self.enable_proceed_button()

    def defaults_button_clicked(self):
        """Respond to 'defaults' button by setting table to default setup"""
        self.set_is_dirty(True)
        self._table_model.restore_defaults()

    def all_on_button_clicked(self):
        """Respond to 'all on' button by setting all table cells to default frame count"""
        self.set_is_dirty(True)
        self._table_model.fill_all_cells()

    def all_off_button_clicked(self):
        """Respond to 'all on' button by setting all table cells to zero frame count"""
        self.set_is_dirty(True)
        self._table_model.zero_all_cells()

    def use_filter_wheel_clicked(self):
        """Store state of 'use filter wheel' checkbox and adjust UI accordingly"""
        self.set_is_dirty(self.ui.useFilterWheel.isChecked()
                          != self._data_model.get_use_filter_wheel())
        self._data_model.set_use_filter_wheel(self.ui.useFilterWheel.isChecked())
        # Re-do table since use of filters has changed
        self._table_model = SessionPlanTableModel(self._data_model, self._preferences, self.set_is_dirty)
        self.ui.sessionPlanTable.setModel(self._table_model)

    # User has clicked "Proceed" - go ahead with the flat-frame captures
    def proceed_button_clicked(self):
        """Respond to 'proceed' button by starting acquisition thread"""

        # Force any other field edits-in-progress to take
        self.server_address_changed()
        self.port_number_changed()
        self.target_adus_changed()
        self.adu_tolerance_changed()
        self.warm_when_done_changed()

        # In case the user is in the middle of a table cell edit, but hasn't hit return,
        # we need to force that edit to take effect.  They will expect the change they've
        # typed to be in place when the Proceed happens.
        self.commit_edit_in_progress()
        session_console = SessionConsole(self._data_model, self._preferences, self._table_model)
        QDialog.DialogCode = session_console.ui.exec_()

    # In case the user is in the middle of a cell edit, but hasn't hit return,
    # we need to force that edit to take effect.  They will expect the change they've
    # typed to be in place when the Proceed happens.

    def commit_edit_in_progress(self):
        """Commit any edit-in-progress in the UI to the relevant data model value"""
        current_index: QModelIndex = self.ui.sessionPlanTable.currentIndex()
        current_item: QWidget = self.ui.sessionPlanTable.indexWidget(current_index)
        if current_item is not None:
            current_is_modified: bool = current_item.isModified()
            if current_is_modified:
                self.set_is_dirty(True)
                new_text: str = current_item.text()
                self._table_model.setData(current_index, new_text, Qt.EditRole)

    def new_menu_triggered(self):
        """Respond to 'new' menu by opening a new default plan file"""
        print("new_menu_triggered")
        # Protected save in case unsaved changes will get wiped
        self.protect_unsaved_close()
        # Get a new data model with default values, load those defaults into
        # the in-use model
        new_model = DataModel.make_from_preferences(self._preferences)
        self._data_model.load_from_model(new_model)
        # Populate window
        self.set_ui_from_data_model(self._data_model)
        # Set window title to unsaved
        self.ui.setWindowTitle(self.UNSAVED_WINDOW_TITLE)
        self.set_is_dirty(False)

    def open_menu_triggered(self):
        """Respond to 'open' menu by prompting for file and opening it"""

        last_opened_path = self._preferences.value("last_opened_path")
        if last_opened_path is None:
            last_opened_path = ""

        # Get file name to open
        dialog = QFileDialog()
        file_name, _ = QFileDialog.getOpenFileName(dialog, "Open File", last_opened_path,
                                                   f"FrameSet Plans(*{Constants.SAVED_FILE_EXTENSION})",
                                                   options=QFileDialog.ReadOnly)
        if file_name != "":
            self.protect_unsaved_close()
            # Read the saved file and load the data model with it
            with open(file_name, "r") as file:
                loaded_model = json.load(file, cls=DataModelDecoder)
                self._data_model.update_from_loaded_json(loaded_model)

            # Populate window with new data model
            self.set_ui_from_data_model(self._data_model)
            #  Set window title to reflect the opened file
            self.set_window_title(file_name)
            #  Just loaded the data, so it can't be dirty yet
            self.set_is_dirty(False)
            #  Remember the file path so plain "save" works.
            self._file_path = file_name

            #  Remember this path in preferences so we come here next time
            self._preferences.setValue("last_opened_path", file_name)

    # Save again over the already-established file.
    # If no file is established, treat this as "save as"
    def save_menu_triggered(self):
        """Respond to 'save' menu by saving current plan to established file"""

        self.commit_edit_in_progress()
        if self._file_path == "":
            self.save_as_menu_triggered()
        else:
            self.write_to_file(self._file_path)

    def save_as_menu_triggered(self):
        """Respond to 'save as' menu by prompting for new file name and saving to it"""

        dialog = QFileDialog()
        file_name, _ = \
            QFileDialog.getSaveFileName(dialog,
                                        caption="Flat Frames Plan File",
                                        directory="",
                                        filter=f"Flat Frame Plans(*{Constants.SAVED_FILE_EXTENSION})",
                                        options=QFileDialog.Options())
        if file_name == "":
            # User cancelled from dialog, so don't do the save
            pass
        else:
            self.commit_edit_in_progress()
            self.write_to_file(file_name)
            self.set_window_title(file_name)
            self._file_path = file_name
            self._preferences.setValue("last_opened_path", file_name)

    def write_to_file(self, file_name):
        """Write data model, json-encoded, to specified file"""
        with open(file_name, "w") as saving_file:
            saving_file.write(self._data_model.serialize_to_json())
        self.set_is_dirty(False)
        #  Remember this path in preferences so we come here next time

    # Set the title of the open window to the given file name, minus the extension
    def set_window_title(self, full_file_name: str):
        """Set UI window title to given file name"""
        without_extension = os.path.splitext(full_file_name)[0]
        self.ui.setWindowTitle(without_extension)

    def protect_unsaved_close(self):
        """If unsaved changes exist, prompt user to save the file"""

        if self._is_dirty:
            # File is dirty, check if save wanted
            message_dialog = QMessageBox()
            message_dialog.setWindowTitle("Unsaved Changes")
            message_dialog.setText("You have unsaved changes")
            message_dialog.setInformativeText("Would you like to save the file or discard these changes?")
            message_dialog.setStandardButtons(QMessageBox.Save | QMessageBox.Discard)
            message_dialog.setDefaultButton(QMessageBox.Save)
            dialog_result = message_dialog.exec_()
            if dialog_result == QMessageBox.Save:
                # Saving will un-dirty the document
                self.save_menu_triggered()
            else:
                # Since they don't want to save, consider the document not-dirty
                self.set_is_dirty(False)
        else:
            # File is not dirty, allow close to proceed
            pass

    # Catch window resizing so we can record the changed size

    def eventFilter(self, triggering_object: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Resize:
            window_size = event.size()
            self._preferences.set_main_window_size(window_size)
        return False  # Didn't handle event

    # Menus to change font size

    def font_larger_menu(self):
        self.increment_font_size(self.ui, increment=+1)

    def font_smaller_menu(self):
        self.increment_font_size(self.ui, increment=-1)

    def font_reset_menu(self):
        self._preferences.set_standard_font_size(Constants.RESET_FONT_SIZE)
        SharedUtils.set_font_sizes(parent=self.ui,
                                   standard_size=Constants.RESET_FONT_SIZE,
                                   title_prefix=Constants.MAIN_TITLE_LABEL_PREFIX,
                                   title_increment=Constants.MAIN_TITLE_FONT_SIZE_INCREMENT,
                                   subtitle_prefix=Constants.SUBTITLE_LABEL_PREFIX,
                                   subtitle_increment=Constants.SUBTITLE_FONT_SIZE_INCREMENT)

    def increment_font_size(self, parent: QObject, increment: int):
        old_standard_font_size = self._preferences.get_standard_font_size()
        new_standard_font_size = old_standard_font_size + increment
        self._preferences.set_standard_font_size(new_standard_font_size)
        SharedUtils.set_font_sizes(parent=parent,
                                   standard_size=new_standard_font_size,
                                   title_prefix=Constants.MAIN_TITLE_LABEL_PREFIX,
                                   title_increment=Constants.MAIN_TITLE_FONT_SIZE_INCREMENT,
                                   subtitle_prefix=Constants.SUBTITLE_LABEL_PREFIX,
                                   subtitle_increment=Constants.SUBTITLE_FONT_SIZE_INCREMENT)

