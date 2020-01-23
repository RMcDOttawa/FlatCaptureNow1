import json
import os

from PyQt5 import uic
from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtWidgets import QMainWindow, QDialog, QWidget, QFileDialog, QMessageBox

from DataModel import DataModel
from DataModelDecoder import DataModelDecoder
from Preferences import Preferences
from PrefsWindow import PrefsWindow
from RmNetUtils import RmNetUtils
from SessionConsole import SessionConsole
from SessionPlanTableModel import SessionPlanTableModel
from Validators import Validators


class MainWindow(QMainWindow):

    UNSAVED_WINDOW_TITLE = "(Unsaved Document)"
    SAVED_FILE_EXTENSION = ".ewho3"

    # This version of the constructor is used to open a window
    # populated by the default values from the preferences object
    def __init__(self, data_model: DataModel, preferences: Preferences):
        QMainWindow.__init__(self)
        self._table_model: SessionPlanTableModel
        self._is_dirty: bool = False  # Dirty means unsaved changes exist
        self.ui = uic.loadUi("MainWindow.ui")
        self._data_model: DataModel = data_model
        self._preferences: Preferences = preferences
        self.connect_responders()
        self.set_ui_from_data_model(data_model)
        self.ui.setWindowTitle(MainWindow.UNSAVED_WINDOW_TITLE)
        self._file_path = ""

    def set_is_dirty(self, is_dirty: bool):
        # print(f"set_is_dirty({is_dirty})")
        self._is_dirty = is_dirty

    # Connect UI controls to methods here for response
    def connect_responders(self):

        # Menu items
        self.ui.actionPreferences.triggered.connect(self.preferences_menu_triggered)
        self.ui.actionNew.triggered.connect(self.new_menu_triggered)
        self.ui.actionOpen.triggered.connect(self.open_menu_triggered)
        self.ui.actionSave.triggered.connect(self.save_menu_triggered)
        self.ui.actionSave_As.triggered.connect(self.save_as_menu_triggered)

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
        proposed_value: str = self.ui.serverAddress.text()
        if RmNetUtils.valid_server_address(proposed_value):
            self._data_model.set_server_address(proposed_value)
            self.set_is_dirty(True)
            self.ui.messageField.setText("")
        else:
            self.ui.messageField.setText("Invalid Server Address")

    def port_number_changed(self):
        proposed_value: str = self.ui.portNumber.text()
        converted_value: int = Validators.valid_int_in_range(proposed_value, 0, 65535)
        if converted_value is not None:
            self._data_model.set_port_number(converted_value)
            self.set_is_dirty(True)
            self.ui.messageField.setText("")
        else:
            self.ui.messageField.setText("Invalid Port Number")

    def target_adus_changed(self):
        proposed_value: str = self.ui.targetAdus.text()
        converted_value: float = Validators.valid_float_in_range(proposed_value, 0, 1000000)
        if converted_value is not None:
            self._data_model.set_target_adus(converted_value)
            self.set_is_dirty(True)
            self.ui.messageField.setText("")
        else:
            self.ui.messageField.setText("Invalid Target ADU number")

    def adu_tolerance_changed(self):
        proposed_value = self.ui.aduTolerance.text()
        converted_value = Validators.valid_float_in_range(proposed_value, 0, 100)
        if converted_value is not None:
            self._data_model.set_adu_tolerance(converted_value / 100.0)
            self.set_is_dirty(True)
            self.ui.messageField.setText("")
        else:
            self.ui.messageField.setText("Invalid ADU tolerance number")

    def warm_when_done_changed(self):
        self._data_model.set_warm_when_done(self.ui.warmWhenDone.isChecked())
        self.set_is_dirty(True)

    # Preferences menu has been selected.  Open the preferences dialog
    def preferences_menu_triggered(self):
        # print("preferences_menu_triggered")
        dialog: PrefsWindow = PrefsWindow()
        dialog.set_up_ui(self._preferences)
        QDialog.DialogCode = dialog.ui.exec_()
        # print(f"   Dialog result: {result}")

    # Set the UI fields from the preferences object given
    def set_ui_from_data_model(self, data_model: DataModel):

        # Server address and port
        self.ui.serverAddress.setText(data_model.get_server_address())
        self.ui.portNumber.setText(str(data_model.get_port_number()))

        # Target ADU and tolerance
        self.ui.targetAdus.setText(str(data_model.get_target_adus()))
        adu_tol = data_model.get_adu_tolerance()
        self.ui.aduTolerance.setText(str(adu_tol*100.0))

        # Warm up when done?
        self.ui.warmWhenDone.setChecked(data_model.get_warm_when_done())

        # Filter wheel
        self.ui.useFilterWheel.setChecked(data_model.get_use_filter_wheel())

        # Set up table model representing the session plan, and connect it to the table
        self._table_model = SessionPlanTableModel(data_model, self.set_is_dirty)
        self.ui.sessionPlanTable.setModel(self._table_model)

    def defaults_button_clicked(self):
        # print("defaults_button_clicked")
        self.set_is_dirty(True)
        self._table_model.restore_defaults()

    def all_on_button_clicked(self):
        # print("all_on_button_clicked")
        self.set_is_dirty(True)
        self._table_model.fill_all_cells()

    def all_off_button_clicked(self):
        # print("all_off_button_clicked")
        self.set_is_dirty(True)
        self._table_model.zero_all_cells()

    def use_filter_wheel_clicked(self):
        # print("use_filter_wheel_clicked")
        self.set_is_dirty(True)
        self._data_model.set_use_filter_wheel(self.ui.useFilterWheel.isChecked())
        # Re-do table since use of filters has changed
        self._table_model = SessionPlanTableModel(self._data_model, self.set_is_dirty)
        self.ui.sessionPlanTable.setModel(self._table_model)

    # User has clicked "Proceed" - go ahead with the flat-frame captures
    def proceed_button_clicked(self):
        # print("proceed_button_clicked")
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
        current_index: QModelIndex = self.ui.sessionPlanTable.currentIndex()
        current_item: QWidget = self.ui.sessionPlanTable.indexWidget(current_index)
        if current_item is not None:
            current_is_modified: bool = current_item.isModified()
            if current_is_modified:
                self.set_is_dirty(True)
                new_text: str = current_item.text()
                self._table_model.setData(current_index, new_text, Qt.EditRole)

    def new_menu_triggered(self):
        print("new_menu_triggered")

    def open_menu_triggered(self):
        print("open_menu_triggered")
        last_opened_path = self._preferences.value("last_opened_path")
        if last_opened_path is None:
            last_opened_path = ""

        # Get file name to open
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", last_opened_path,
                                                   f"FrameSet Plans(*{MainWindow.SAVED_FILE_EXTENSION})")
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
        print("save_menu_triggered")
        self.commit_edit_in_progress()
        if self._file_path == "":
            self.save_as_menu_triggered()
        else:
            self.write_to_file(self._file_path)

    def save_as_menu_triggered(self):
        print("save_as_menu_triggered")
        file_name, _ = \
            QFileDialog.getSaveFileName(self,
                                        "Flat Frames Plan File",
                                        "",
                                        f"Flat Frame Plans(*{MainWindow.SAVED_FILE_EXTENSION})")
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
        with open(file_name, "w") as saving_file:
            saving_file.write(self._data_model.serialize_to_json())
        self.set_is_dirty(False)
        #  Remember this path in preferences so we come here next time

    # Set the title of the open window to the given file name, minus the extension
    def set_window_title(self, full_file_name: str):
        # print(f"set_window_title({full_file_name})")
        without_extension = os.path.splitext(full_file_name)[0]
        self.ui.setWindowTitle(without_extension)

    def protect_unsaved_close(self):
        # print("protect_unsaved_close")
        if self._is_dirty:
            # print("   File is dirty, check if save wanted")
            message_dialog = QMessageBox()
            message_dialog.setWindowTitle("Unsaved Changes")
            message_dialog.setText("You have unsaved changes")
            message_dialog.setInformativeText("Would you like to save the file or discard these changes?")
            message_dialog.setStandardButtons(QMessageBox.Save | QMessageBox.Discard)
            message_dialog.setDefaultButton(QMessageBox.Save)
            dialog_result = message_dialog.exec_()
            # print(f"   Dialog returned {dialog_result}")
            if dialog_result == QMessageBox.Save:
                # print("      SAVE button was pressed")
                # Saving will un-dirty the document
                self.save_menu_triggered()
            else:
                # print("      DISCARD button was pressed")
                # Since they don't want to save, consider the document not-dirty
                self.set_is_dirty(False)
        else:
            # print("   File is not dirty, allow close to proceed")
            pass

