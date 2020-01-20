from PyQt5 import uic
from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtWidgets import QMainWindow, QDialog, QWidget

from DataModel import DataModel
from Preferences import Preferences
from PrefsWindow import PrefsWindow
from RmNetUtils import RmNetUtils
from SessionConsole import SessionConsole
from SessionPlanTableModel import SessionPlanTableModel
from Validators import Validators


class MainWindow(QMainWindow):

    # This version of the constructor is used to open a window
    # populated by the default values from the preferences object
    def __init__(self, data_model: DataModel, preferences: Preferences):
        QMainWindow.__init__(self)
        self._table_model: SessionPlanTableModel
        self.ui = uic.loadUi("MainWindow.ui")
        self._data_model: DataModel = data_model
        self._preferences: Preferences = preferences
        self.connect_responders()
        self.set_ui_from_data_model(data_model)

    # Connect UI controls to methods here for response
    def connect_responders(self):

        # Preferences menu
        self.ui.actionPreferences.triggered.connect(self.preferences_menu_triggered)

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
            self.ui.messageField.setText("")
        else:
            self.ui.messageField.setText("Invalid Server Address")

    def port_number_changed(self):
        proposed_value: str = self.ui.portNumber.text()
        converted_value: int = Validators.valid_int_in_range(proposed_value, 0, 65535)
        if converted_value is not None:
            self._data_model.set_port_number(converted_value)
            self.ui.messageField.setText("")
        else:
            self.ui.messageField.setText("Invalid Port Number")

    def target_adus_changed(self):
        proposed_value: str = self.ui.targetAdus.text()
        converted_value: float = Validators.valid_float_in_range(proposed_value, 0, 1000000)
        if converted_value is not None:
            self._data_model.set_target_adus(converted_value)
            self.ui.messageField.setText("")
        else:
            self.ui.messageField.setText("Invalid Target ADU number")

    def adu_tolerance_changed(self):
        proposed_value = self.ui.aduTolerance.text()
        converted_value = Validators.valid_float_in_range(proposed_value, 0, 100)
        if converted_value is not None:
            self._data_model.set_adu_tolerance(converted_value / 100.0)
            self.ui.messageField.setText("")
        else:
            self.ui.messageField.setText("Invalid ADU tolerance number")

    def warm_when_done_changed(self):
        self._data_model.set_warm_when_done(self.ui.warmWhenDone.isChecked())

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
        self._table_model = SessionPlanTableModel(data_model)
        self.ui.sessionPlanTable.setModel(self._table_model)

    def defaults_button_clicked(self):
        # print("defaults_button_clicked")
        self._table_model.restore_defaults()

    def all_on_button_clicked(self):
        # print("all_on_button_clicked")
        self._table_model.fill_all_cells()

    def all_off_button_clicked(self):
        # print("all_off_button_clicked")
        self._table_model.zero_all_cells()

    def use_filter_wheel_clicked(self):
        # print("use_filter_wheel_clicked")
        self._data_model.set_use_filter_wheel(self.ui.useFilterWheel.isChecked())
        # Re-do table since use of filters has changed
        self._table_model = SessionPlanTableModel(self._data_model)
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
                new_text: str = current_item.text()
                self._table_model.setData(current_index, new_text, Qt.EditRole)
