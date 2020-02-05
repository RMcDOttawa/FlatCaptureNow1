import json
import os
from typing import Optional

from PyQt5 import uic, QtWidgets
from PyQt5.QtCore import QModelIndex, Qt, QObject, QEvent, QTimer
from PyQt5.QtWidgets import QMainWindow, QDialog, QWidget, QFileDialog, QMessageBox, QAbstractButton, QLineEdit

from Constants import Constants
from DataModel import DataModel
from DataModelDecoder import DataModelDecoder
from Preferences import Preferences
from PrefsWindow import PrefsWindow
from RmNetUtils import RmNetUtils
from SessionConsole import SessionConsole
from SessionPlanTableModel import SessionPlanTableModel
from SharedUtils import SharedUtils
from TheSkyX import TheSkyX
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
        self._slew_cancelled: bool = False
        self._slew_elapsed: float = 0
        self._slew_timer: Optional[QTimer] = None
        self._slew_server: Optional[TheSkyX] = None
        self._slew_pulse_state: bool = True

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
        """Enable the proceed button only if all fields are valid and a path is determined"""
        all_fields_good = all(val for val in self._field_validity.values())

        local_good = (self._data_model.get_save_files_locally()
                      and self._data_model.get_local_path() != Constants.LOCAL_PATH_NOT_SET)
        remote_good = not self._data_model.get_save_files_locally()
        path_good = local_good or remote_good

        self.ui.proceedButton.setEnabled(all_fields_good and path_good)

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

        # Location of save folder radio set
        self.ui.useAutosave.clicked.connect(self.autosave_group_clicked)
        self.ui.useLocal.clicked.connect(self.autosave_group_clicked)

        # Buttons to set and display save folder
        self.ui.setLocal.clicked.connect(self.set_local_folder_clicked)
        self.ui.queryAutosave.clicked.connect(self.query_autosave_path_clicked)

        # Bulk change buttons
        self.ui.defaultsButton.clicked.connect(self.defaults_button_clicked)
        self.ui.allOnButton.clicked.connect(self.all_on_button_clicked)
        self.ui.allOffButton.clicked.connect(self.all_off_button_clicked)

        # Proceed button
        self.ui.proceedButton.clicked.connect(self.proceed_button_clicked)

        # Filter wheel
        self.ui.useFilterWheel.clicked.connect(self.use_filter_wheel_clicked)

        # Slewing to light source
        self.ui.slewToSource.clicked.connect(self.slew_checkbox_clicked)
        self.ui.sourceAlt.editingFinished.connect(self.source_alt_changed)
        self.ui.sourceAz.editingFinished.connect(self.source_az_changed)
        self.ui.readScopeButton.clicked.connect(self.read_scope_clicked)
        self.ui.slewButton.clicked.connect(self.slew_button_clicked)
        self.ui.cancelSlewButton.clicked.connect(self.cancel_slew_clicked)

        # Fields other than the session plan table
        self.ui.serverAddress.editingFinished.connect(self.server_address_changed)
        self.ui.portNumber.editingFinished.connect(self.port_number_changed)
        self.ui.targetAdus.editingFinished.connect(self.target_adus_changed)
        self.ui.aduTolerance.editingFinished.connect(self.adu_tolerance_changed)
        self.ui.warmWhenDone.clicked.connect(self.warm_when_done_changed)

        # Catch "about to quit" from Application so we can protect against data loss
        # noinspection PyArgumentList
        app = QtWidgets.QApplication.instance()
        assert (app is not None)
        app.aboutToQuit.connect(self.app_about_to_quit)

    # Responders

    # They all follow this pattern - we'll thoroughly comment this one - apply concepts to others

    def port_number_changed(self):
        """Validate and store port number"""

        # Get the value they typed into the field.  It could be invalid.
        proposed_value: str = self.ui.portNumber.text()

        # Check for validity;  convert if numeric
        converted_value = Validators.valid_int_in_range(proposed_value, 0, 65535)
        valid = converted_value is not None

        if valid:
            # It's valid.  That means we're going to accept it, so the document needs saving
            if converted_value != self._data_model.get_port_number():
                self.set_is_dirty(True)
            # New value into the data model
            self._data_model.set_port_number(converted_value)

        # Record in dict that this field is valid/invalid for fast enabling of Proceed button
        self.set_field_validity(self.ui.portNumber, valid)

        # Visually indicate valid or invalid via background colour of the field
        SharedUtils.background_validity_color(self.ui.portNumber, valid)

    def server_address_changed(self):
        """Validate and store server address"""

        proposed_value: str = self.ui.serverAddress.text()
        valid = RmNetUtils.valid_server_address(proposed_value)
        if valid:
            if proposed_value != self._data_model.get_server_address():
                self.set_is_dirty(True)
            self._data_model.set_server_address(proposed_value)
            self.respond_to_server_locality(proposed_value)
        self.set_field_validity(self.ui.serverAddress, valid)
        SharedUtils.background_validity_color(self.ui.serverAddress, valid)

    def target_adus_changed(self):
        """Validate and store target ADU level"""
        proposed_value: str = self.ui.targetAdus.text()
        converted_value = Validators.valid_float_in_range(proposed_value, 0, 1000000)
        valid = converted_value is not None
        if valid:
            if converted_value != self._data_model.get_target_adus():
                self.set_is_dirty(True)
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
            if to_fraction != self._data_model.get_adu_tolerance():
                self.set_is_dirty(True)
            self._data_model.set_adu_tolerance(to_fraction)
        self.set_field_validity(self.ui.targetAdus, valid)
        SharedUtils.background_validity_color(self.ui.aduTolerance, valid)

    def warm_when_done_changed(self):
        """Store the new state of the 'warm when done' checkbox"""
        if self.ui.warmWhenDone.isChecked() \
                != self._data_model.get_warm_when_done():
            self.set_is_dirty(True)
        self._data_model.set_warm_when_done(self.ui.warmWhenDone.isChecked())

    # Radio group for where flats go (local or autosave) has been clicked
    def autosave_group_clicked(self):
        changed = self.ui.useLocal.isChecked() != self._data_model.get_save_files_locally()
        if changed:
            self.set_is_dirty(True)
            if self._data_model.get_save_files_locally():
                self.ui.pathName.setText("")
        self._data_model.set_save_files_locally(self.ui.useLocal.isChecked())
        if self._data_model.get_save_files_locally():
            self.ui.pathName.setText(self._data_model.get_local_path())
            self.ui.queryAutosave.setEnabled(False)
        else:
            self.ui.queryAutosave.setEnabled(True)
        self.enable_proceed_button()

    # Preferences menu has been selected.  Open the preferences dialog
    def preferences_menu_triggered(self):
        """Respond to preferences menu by opening preferences dialog"""
        dialog: PrefsWindow = PrefsWindow()
        dialog.set_up_ui(self._preferences, self._data_model)
        QDialog.DialogCode = dialog.ui.exec_()

    # Set the UI fields from the preferences object given
    def set_ui_from_data_model(self, data_model: DataModel):
        """Set the fields in the UI from the given data model"""
        # Server address and port
        self.ui.serverAddress.setText(data_model.get_server_address())
        self.ui.portNumber.setText(str(data_model.get_port_number()))
        self.respond_to_server_locality(data_model.get_server_address())

        # Target ADU and tolerance
        self.ui.targetAdus.setText(str(data_model.get_target_adus()))
        adu_tol = data_model.get_adu_tolerance()
        self.ui.aduTolerance.setText(str(adu_tol * 100.0))

        # Warm up when done?
        self.ui.warmWhenDone.setChecked(data_model.get_warm_when_done())

        # Filter wheel
        self.ui.useFilterWheel.setChecked(data_model.get_use_filter_wheel())

        # Remote or local server?
        self.ui.useLocal.setChecked(data_model.get_save_files_locally())
        self.ui.useAutosave.setChecked(not data_model.get_save_files_locally())
        self.ui.pathName.setText(data_model.get_local_path()
                                 if data_model.get_save_files_locally() else "")

        # Slew to light source before acquiring frames?
        slew_to_source = data_model.get_slew_to_light_source()
        self.ui.slewToSource.setChecked(slew_to_source)
        self.ui.sourceAlt.setText(str(round(data_model.get_source_alt(), 5)))
        self.ui.sourceAz.setText(str(round(data_model.get_source_az(), 5)))

        # Set up table model representing the session plan, and connect it to the table

        self._table_model = SessionPlanTableModel(data_model, self._preferences,
                                                  self.set_is_dirty, self.set_field_validity)
        self.ui.sessionPlanTable.setModel(self._table_model)

        self.enable_proceed_button()
        self.enable_slew_button()

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
        if self.ui.useFilterWheel.isChecked() \
                != self._data_model.get_use_filter_wheel():
            self.set_is_dirty(True)
        self._data_model.set_use_filter_wheel(self.ui.useFilterWheel.isChecked())
        # Re-do table since use of filters has changed
        self._table_model = SessionPlanTableModel(self._data_model, self._preferences,
                                                  self.set_is_dirty, self.set_field_validity)
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

    def app_about_to_quit(self):
        self.protect_unsaved_close()

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

    # We have changed (or loaded) the server name.  Determine (best guess) if this is the
    # same computer we're running on, or a different one, and use that to enable parts of the
    # UI that depend on the server being on the same computer we're one

    def respond_to_server_locality(self, server_address: str):
        is_local = RmNetUtils.address_is_this_computer(server_address)
        self.ui.useLocal.setEnabled(is_local)
        self.ui.setLocal.setEnabled(is_local)
        where_msg = "TheSkyX is running on this machine" if is_local \
            else "TheSkyX is running remotely"
        self.ui.whereRunning.setText(where_msg)
        if not is_local:
            self.ui.pathName.setText("")
            self.ui.useAutosave.setChecked(True)
            self.ui.useLocal.setChecked(False)

    # TheSkyX is running on this machine, so we can use a file-save dialog to select
    # the folder where the saved frames will go.  Do that.

    def set_local_folder_clicked(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.DirectoryOnly)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        if dialog.exec_():
            path_names = dialog.selectedFiles()
            assert len(path_names) > 0
            if self._data_model.get_local_path() != path_names[0]:
                self.set_is_dirty(True)
            self.ui.pathName.setText(path_names[0])
            self._data_model.set_local_path(path_names[0])
            self.enable_proceed_button()
        else:
            print("Cancelled")

    # User has asked us to ask TheSkyX for the autosave path.
    # Try;  if we get a response, display it.

    def query_autosave_path_clicked(self):
        server = TheSkyX(self._data_model.get_server_address(), self._data_model.get_port_number())
        (success, path, message) = server.get_camera_autosave_path()
        if success:
            self.ui.pathName.setText(path)
        else:
            self.ui.pathName.setText(message)
            # self.ui.pathName.setText("Unable to query TheSkyX")

    # Enable the Slew To Source button only if the alt and az coordinates are good
    def enable_slew_button(self):
        # For now, just ensure enabled.  Since the alt-az fields are loaded
        # valid and kept valid, slew can't really be invalid
        self.ui.slewToSource.setEnabled(True)

    def slew_checkbox_clicked(self):
        if self.ui.slewToSource.isChecked() \
                != self._data_model.get_slew_to_light_source():
            self.set_is_dirty(True)
        self._data_model.set_slew_to_light_source(self.ui.slewToSource.isChecked())

    def source_alt_changed(self):
        """Validate and store the altitude of the light source"""
        proposed_value: str = self.ui.sourceAlt.text()
        converted_value: Optional[float] = Validators.valid_float_in_range(proposed_value, -90, +90)
        valid = converted_value is not None
        if valid:
            if converted_value != self._data_model.get_source_alt():
                self.set_is_dirty(True)
            self._data_model.set_source_alt(converted_value)
        self.set_field_validity(self.ui.sourceAlt, valid)
        SharedUtils.background_validity_color(self.ui.sourceAlt, valid)

    def source_az_changed(self):
        """Validate and store the azimuth of the light source"""
        proposed_value: str = self.ui.sourceAz.text()
        converted_value: Optional[float] = Validators.valid_float_in_range(proposed_value, -360, +360)
        valid = converted_value is not None
        if valid:
            if converted_value != self._data_model.get_source_az():
                self.set_is_dirty(True)
            self._data_model.set_source_az(converted_value)
        self.set_field_validity(self.ui.sourceAz, valid)
        SharedUtils.background_validity_color(self.ui.sourceAz, valid)

    def read_scope_clicked(self):
        """Read current alt/az from mount and store as slew target in data model"""
        # Get a server object
        server = TheSkyX(self._data_model.get_server_address(),
                         self._data_model.get_port_number())

        # Ask for scope settings
        (success, scope_alt, scope_az, message) = server.get_scope_alt_az()

        # If success put them in place
        if success:
            self.set_is_dirty(True)
            self._data_model.set_source_alt(scope_alt)
            self._data_model.set_source_az(scope_az)
            self.ui.sourceAlt.setText(str(round(scope_alt, 5)))
            self.ui.sourceAz.setText(str(round(scope_az, 5)))
            self.ui.slewMessage.setText("Read OK")
        else:
            self.ui.slewMessage.setText(message)

    # User has asked us to manually slew to the light source.
    # Start the slew.  Slewing is asynchronous, so poll the scope to see when it is done.
    # While it's running, we'll pulse a "slewing" message with a timer, and have a "cancel"
    # button enabled to stop the slew.

    def slew_button_clicked(self):
        """Ask the mount to slew the scope to the position of the light source"""

        # Start asynchronous slew
        server = TheSkyX(self._data_model.get_server_address(),
                         self._data_model.get_port_number())
        (success, message) = server.start_slew_to(self._data_model.get_source_alt(),
                                                  self._data_model.get_source_az())
        if success:
            self._slew_cancelled = False
            self._slew_elapsed = 0
            self._slew_server = server
            self._slew_pulse_state = False
            # Enable the Cancel button, disable the other UI buttons
            SharedUtils.set_enable_all_widgets(self.ui, QAbstractButton, False)
            SharedUtils.set_enable_all_widgets(self.ui, QLineEdit, False)
            self.ui.sessionPlanTable.setEnabled(False)
            self.ui.cancelSlewButton.setEnabled(True)

            # Message that we're slewing
            self.ui.slewMessage.setText("Slewing")

            # Start a timer to pulse the slewing message and check for completion
            timer = QTimer()
            self._slew_timer = timer
            timer.timeout.connect(self.slew_timer_fired)
            timer.start(Constants.SLEW_DONE_POLLING_INTERVAL * 1000)
        else:
            self.ui.slewMessage.setText(message)

    def slew_timer_fired(self):
        """Regularly-ticking timer to watch slew in progress"""
        self._slew_elapsed += Constants.SLEW_DONE_POLLING_INTERVAL
        # print(f"Slew Timer. Elapsed {self._slew_elapsed}")
        slew_is_finished = True
        if self._slew_cancelled:
            self.ui.slewMessage.setText("Slew Cancelled")
        elif self._slew_elapsed > Constants.SLEW_MAXIMUM_WAIT:
            self.ui.slewMessage.setText("Slew Timed Out")
        else:
            (success, complete) = self._slew_server.slew_is_complete()
            if success:
                if complete:
                    self.ui.slewMessage.setText("Slew Complete")
                else:
                    # Slew is healthy but not finished, let it keep running
                    slew_is_finished = False
            else:
                self.ui.slewMessage.setText("Error from server")
        if slew_is_finished:
            self._slew_timer.stop()
            self.slew_complete()
        else:
            # Visually pulse the slew message
            self._slew_pulse_state = not self._slew_pulse_state
            color = "red" if self._slew_pulse_state else "black"
            self.ui.slewMessage.setStyleSheet(f"color: {color}")

    def cancel_slew_clicked(self):
        """Set a flag that will cause the slew timer to cancel"""
        self._slew_cancelled = True
        (_, _) = self._slew_server.abort_slew()

    def slew_complete(self):
        """Wrap-up UI feedback when initiated slew is complete"""
        # Reset the enable/disable of buttons
        SharedUtils.set_enable_all_widgets(self.ui, QAbstractButton, True)
        SharedUtils.set_enable_all_widgets(self.ui, QLineEdit, True)
        self.ui.sessionPlanTable.setEnabled(True)
        self.ui.cancelSlewButton.setEnabled(False)
        self.enable_proceed_button()
        self._slew_timer = None
        self._slew_server = None
        self.ui.slewMessage.setStyleSheet(f"color: black")
