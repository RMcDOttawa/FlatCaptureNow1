from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QRadioButton, QCheckBox, QLineEdit

from BinningSpec import BinningSpec
from FilterSpec import FilterSpec
from Preferences import Preferences
from RmNetUtils import RmNetUtils
from Validators import Validators


class PrefsWindow(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.ui = uic.loadUi("PrefsWindow.ui")
        self._preferences = None

    def set_up_ui(self, preferences: Preferences):
        # print("PrefsWindow/set_up_ui")
        self._preferences = preferences
        self.connect_responders()
        self.load_ui_from_prefs(preferences)

    def connect_responders(self):
        # Catch clicks to filter Use checkboxes.  All go to the same
        # method, and that method uses the widget name to discriminate
        self.ui.useFilter_1.clicked.connect(self.filter_use_clicked)
        self.ui.useFilter_2.clicked.connect(self.filter_use_clicked)
        self.ui.useFilter_3.clicked.connect(self.filter_use_clicked)
        self.ui.useFilter_4.clicked.connect(self.filter_use_clicked)
        self.ui.useFilter_5.clicked.connect(self.filter_use_clicked)
        self.ui.useFilter_6.clicked.connect(self.filter_use_clicked)
        self.ui.useFilter_7.clicked.connect(self.filter_use_clicked)
        self.ui.useFilter_8.clicked.connect(self.filter_use_clicked)

        # Filter names have been changed
        self.ui.filterName_1.editingFinished.connect(self.filter_name_changed)
        self.ui.filterName_2.editingFinished.connect(self.filter_name_changed)
        self.ui.filterName_3.editingFinished.connect(self.filter_name_changed)
        self.ui.filterName_4.editingFinished.connect(self.filter_name_changed)
        self.ui.filterName_5.editingFinished.connect(self.filter_name_changed)
        self.ui.filterName_6.editingFinished.connect(self.filter_name_changed)
        self.ui.filterName_7.editingFinished.connect(self.filter_name_changed)
        self.ui.filterName_8.editingFinished.connect(self.filter_name_changed)

        # Radio groups for binning
        self.ui.binGroup_1.buttonClicked.connect(self.binning_group_clicked)
        self.ui.binGroup_2.buttonClicked.connect(self.binning_group_clicked)
        self.ui.binGroup_3.buttonClicked.connect(self.binning_group_clicked)
        self.ui.binGroup_4.buttonClicked.connect(self.binning_group_clicked)

        # Number of flats to use by default
        self.ui.numFlats.editingFinished.connect(self.number_of_flats_changed)

        # Target ADUs
        self.ui.targetADUs.editingFinished.connect(self.target_adus_changed)
        self.ui.aduTolerance.editingFinished.connect(self.adu_tolerance_changed)

        # Warm up when done
        self.ui.warmWhenDone.clicked.connect(self.warm_when_done_clicked)

        # Use Filter Wheel
        self.ui.useFilterWheel.clicked.connect(self.use_filter_wheel_clicked)

        # Server address and port number
        self.ui.serverAddress.editingFinished.connect(self.server_address_changed)
        self.ui.portNumber.editingFinished.connect(self.port_number_changed)

        # Close button
        self.ui.closeButton.clicked.connect(self.close_button_clicked)

    def load_ui_from_prefs(self, preferences: Preferences):
        # print("load_ui_from_prefs")

        # Filter wheel?
        ufw = preferences.get_use_filter_wheel()
        self.ui.useFilterWheel.setChecked(ufw if ufw is not None else False)
        self.enable_filter_fields()

        # Number of flats
        self.ui.numFlats.setText(str(preferences.get_default_frame_count()))

        # Target ADUs
        self.ui.targetADUs.setText(str(preferences.get_target_adus()))
        self.ui.aduTolerance.setText(str(preferences.get_adu_tolerance() * 100.0))

        # Server address and port number
        self.ui.serverAddress.setText(preferences.get_server_address())
        self.ui.portNumber.setText(str(preferences.get_port_number()))

        # Warm up when done

        wwd = preferences.get_warm_when_done()
        self.ui.warmWhenDone.setChecked(wwd if wwd is not None else False)

        # Filter specifications
        filter_specs = preferences.get_filter_spec_list()
        fs: FilterSpec
        for fs in filter_specs:
            # print(f"  Filter Spec: {fs}")
            check_box_name: str = f"useFilter_{fs.get_slot_number()}"
            this_check_box: QCheckBox = self.ui.findChild(QCheckBox, check_box_name)
            assert this_check_box is not None
            this_check_box.setChecked(fs.get_is_used())
            name_field_name: str = f"filterName_{fs.get_slot_number()}"
            this_name_field: QLineEdit = self.ui.findChild(QLineEdit, name_field_name)
            assert this_name_field is not None
            this_name_field.setText(fs.get_name())

        # Binning specifications
        binning_specs = preferences.get_binning_spec_list()
        bs: BinningSpec
        for bs in binning_specs:
            # print(f"  Binning Spec: {bs}")
            this_default_name: str = f"binDefault_{bs.get_binning_value()}"
            this_available_name: str = f"binAvailable_{bs.get_binning_value()}"
            this_off_name: str = f"binOff_{bs.get_binning_value()}"
            default_button: QRadioButton = self.ui.findChild(QRadioButton, this_default_name)
            assert default_button is not None
            available_button: QRadioButton = self.ui.findChild(QRadioButton, this_available_name)
            assert available_button is not None
            off_button: QRadioButton = self.ui.findChild(QRadioButton, this_off_name)
            assert off_button is not None
            if bs.get_is_default():
                default_button.setChecked(True)
            elif bs.get_is_available():
                available_button.setChecked(True)
            else:
                off_button.setChecked(True)

    # Responders

    # One of the filter use checkboxes has been changed.  We don't
    # know which and it's not worth the extra code - just set them all
    def filter_use_clicked(self):
        # print(f"filter_use_clicked:")
        filter_specs = self._preferences.get_filter_spec_list()
        fs: FilterSpec
        for fs in filter_specs:
            # print(f"  Filter Spec: {fs}")
            check_box_name: str = f"useFilter_{fs.get_slot_number()}"
            this_check_box: QCheckBox = self.ui.findChild(QCheckBox, check_box_name)
            assert this_check_box is not None
            fs.set_is_used(this_check_box.isChecked())
        self._preferences.set_filter_spec_list(filter_specs)

    def filter_name_changed(self):
        # print(f"filter_name_changed:")
        filter_specs = self._preferences.get_filter_spec_list()
        fs: FilterSpec
        for fs in filter_specs:
            # print(f"  Filter Spec: {fs}")
            name_field_name: str = f"filterName_{fs.get_slot_number()}"
            this_field: QLineEdit = self.ui.findChild(QLineEdit, name_field_name)
            assert this_field is not None
            fs.set_name(this_field.text())
        self._preferences.set_filter_spec_list(filter_specs)

    def binning_group_clicked(self):
        print(f"binning_group_clicked ")
        binning_specs = self._preferences.get_binning_spec_list()
        bs: BinningSpec
        for bs in binning_specs:
            # print(f"  Binning Spec: {bs}")
            this_default_name: str = f"binDefault_{bs.get_binning_value()}"
            this_available_name: str = f"binAvailable_{bs.get_binning_value()}"
            this_off_name: str = f"binOff_{bs.get_binning_value()}"
            default_button: QRadioButton = self.ui.findChild(QRadioButton, this_default_name)
            assert default_button is not None
            available_button: QRadioButton = self.ui.findChild(QRadioButton, this_available_name)
            assert available_button is not None
            off_button: QRadioButton = self.ui.findChild(QRadioButton, this_off_name)
            assert off_button is not None
            if default_button.isChecked():
                bs.set_is_default(True)
                bs.set_is_available(False)
            elif available_button.isChecked():
                bs.set_is_default(False)
                bs.set_is_available(True)
            else:
                assert off_button.isChecked()
                bs.set_is_default(False)
                bs.set_is_available(False)
        self._preferences.set_binning_spec_list(binning_specs)

    def number_of_flats_changed(self):
        # print("number_of_flats_changed")
        proposed_new_number: str = self.ui.numFlats.text()
        new_number: int = Validators.valid_int_in_range(proposed_new_number, 0, 256)
        if new_number is not None:
            self._preferences.set_default_frame_count(new_number)
        else:
            self.ui.numFlats.setText("???")

    def target_adus_changed(self):
        # print("target_adus_changed")
        proposed_new_number: str = self.ui.targetADUs.text()
        new_number: float = Validators.valid_float_in_range(proposed_new_number, 1, 500000)
        if new_number is not None:
            self._preferences.set_target_adus(new_number)
        else:
            self.ui.targetADUs.setText("???")

    def server_address_changed(self):
        # print("server_address_changed")
        proposed_new_address: str = self.ui.serverAddress.text()
        if RmNetUtils.valid_server_address(proposed_new_address):
            self._preferences.set_server_address(proposed_new_address)
        else:
            self.ui.serverAddress.setText("* Invalid *")

    def port_number_changed(self):
        # print("port_number_changed")
        proposed_new_number: str = self.ui.portNumber.text()
        new_number: int = Validators.valid_int_in_range(proposed_new_number, 1, 65536)
        if new_number is not None:
            self._preferences.set_port_number(new_number)
        else:
            self.ui.portNumber.setText("* Invalid *")

    def adu_tolerance_changed(self):
        # print("adu_tolerance_changed")
        proposed_new_number: str = self.ui.aduTolerance.text()
        new_number: float = Validators.valid_float_in_range(proposed_new_number, 0, 100)
        if new_number is not None:
            self._preferences.set_adu_tolerance(new_number / 100.0)
        else:
            self.ui.aduTolerance.setText("???")

    def warm_when_done_clicked(self):
        # print("warm_when_done_clicked")
        self._preferences.set_warm_when_done(self.ui.warmWhenDone.isChecked())

    def use_filter_wheel_clicked(self):
        # print("use_filter_wheel_clicked")
        self._preferences.set_use_filter_wheel(self.ui.useFilterWheel.isChecked())
        self.enable_filter_fields()

    def close_button_clicked(self):
        # print("close_button_clicked")
        self.ui.close()

    # Enable the filter fields only if "use filter wheel" is turned on
    def enable_filter_fields(self):
        print("enable_filter_fields")
        # TODO enable_filter_fields
        enabled = self.ui.useFilterWheel.isChecked()
        filter_specs = self._preferences.get_filter_spec_list()
        fs: FilterSpec
        for fs in filter_specs:
            use_filter_field_name: str = f"useFilter_{fs.get_slot_number()}"
            use_filter_field: QCheckBox = self.ui.findChild(QCheckBox, use_filter_field_name)
            assert use_filter_field is not None
            filter_name_field_name: str = f"filterName_{fs.get_slot_number()}"
            filter_name_field: QLineEdit = self.ui.findChild(QLineEdit, filter_name_field_name)
            assert filter_name_field is not None
            use_filter_field.setEnabled(enabled)
            filter_name_field.setEnabled(enabled)
