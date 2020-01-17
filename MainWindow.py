from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QDialog

from DataModel import DataModel
from Preferences import Preferences
from PrefsWindow import PrefsWindow
from SessionPlanTableModel import SessionPlanTableModel


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

    # Responders

    # Preferences menu has been selected.  Open the preferences dialog
    def preferences_menu_triggered(self):
        # print("preferences_menu_triggered")
        dialog: PrefsWindow = PrefsWindow()
        dialog.set_up_ui(self._preferences)
        result: QDialog.DialogCode = dialog.ui.exec_()
        # print(f"   Dialog result: {result}")

    # Set the UI fields from the preferences object given
    def set_ui_from_data_model(self, data_model: DataModel):

        # Server address and port
        self.ui.serverAddress.setText(data_model.get_server_address())
        self.ui.portNumber.setText(str(data_model.get_port_number()))

        # Target ADU and tolerance
        self.ui.targetAdus.setText(str(data_model.get_target_adus()))
        self.ui.aduTolerance.setText(str(data_model.get_adu_tolerance()*100.0))

        # Warm up when done?
        self.ui.warmWhenDone.setChecked(data_model.get_warm_when_done())

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
