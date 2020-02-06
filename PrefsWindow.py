from typing import Optional

from PyQt5 import uic
from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtWidgets import QDialog, QRadioButton, QCheckBox, QLineEdit, QMessageBox

import SharedUtils
from BinningSpec import BinningSpec
from Constants import Constants
from DataModel import DataModel
from FilterSpec import FilterSpec
from Preferences import Preferences
from RmNetUtils import RmNetUtils
from SharedUtils import SharedUtils
from TheSkyX import TheSkyX
from Validators import Validators


#
#   User interface controller for the dialog used to edit the program preferences
#


class PrefsWindow(QDialog):

    def __init__(self):
        QDialog.__init__(self, flags=Qt.Dialog)
        self.ui = uic.loadUi(SharedUtils.path_for_file_in_program_directory("PrefsWindow.ui"))
        self._preferences: Optional[Preferences] = None
        self._data_model: Optional[DataModel] = None

    def set_up_ui(self, preferences: Preferences):
        """Set UI fields in the dialog from the given preferences settings"""
        self._preferences = preferences
        self.connect_responders()
        self.load_ui_from_prefs(preferences)

        # If a window size is saved, set the window size
        window_size = self._preferences.get_prefs_window_size()
        if window_size is not None:
            self.ui.resize(window_size)

        # Watch events go by so we can save resize information
        self.ui.installEventFilter(self)

        # Set font sizes of all elements using fonts to the saved font size
        standard_font_size = self._preferences.get_standard_font_size()
        SharedUtils.set_font_sizes(parent=self.ui,
                                   standard_size=standard_font_size,
                                   title_prefix=Constants.MAIN_TITLE_LABEL_PREFIX,
                                   title_increment=Constants.MAIN_TITLE_FONT_SIZE_INCREMENT,
                                   subtitle_prefix=Constants.SUBTITLE_LABEL_PREFIX,
                                   subtitle_increment=Constants.SUBTITLE_FONT_SIZE_INCREMENT
                                   )

    def connect_responders(self):
        """Connect UI fields and controls to the methods that respond to them"""

        # Catch clicks to filter Use checkboxes.  All go to the same
        # method, and that method uses the widget name to discriminate
        # so we'll use a loop to set up the responders for all 8, both the
        # button and the name field
        for item_number in range(1, 8 + 1):
            # Checkbox for that filter
            check_box_name: str = f"useFilter_{item_number}"
            this_check_box: QCheckBox = self.ui.findChild(QCheckBox, check_box_name)
            assert this_check_box is not None
            this_check_box.clicked.connect(self.filter_use_clicked)
            # Line edit field for that filter
            edit_name = f"filterName_{item_number}"
            this_edit_field: QLineEdit = self.ui.findChild(QLineEdit, edit_name)
            assert this_edit_field is not None
            this_edit_field.editingFinished.connect(self.filter_name_changed)

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

        # Use Filter Wheel
        self.ui.useFilterWheel.clicked.connect(self.use_filter_wheel_clicked)

        # Server address and port number
        self.ui.serverAddress.editingFinished.connect(self.server_address_changed)
        self.ui.portNumber.editingFinished.connect(self.port_number_changed)

        # Reset the stored time estimates
        self.ui.resetEstimatesButton.clicked.connect(self.reset_estimates_clicked)

        # Slewing telescope to the location of the light source
        self.ui.sourceAlt.editingFinished.connect(self.source_alt_changed)
        self.ui.sourceAz.editingFinished.connect(self.source_az_changed)
        self.ui.readScopeButton.clicked.connect(self.read_scope_clicked)

        # Close button
        self.ui.closeButton.clicked.connect(self.close_button_clicked)

    def load_ui_from_prefs(self, preferences: Preferences):
        """Load the UI fields from the given preferences"""

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

         # Information about slewing to the flat light source

        self.ui.sourceAlt.setText(str(round(preferences.get_source_alt(), 4)))
        self.ui.sourceAz.setText(str(round(preferences.get_source_az(), 4)))

        # Filter specifications
        filter_specs = preferences.get_filter_spec_list()
        fs: FilterSpec
        for fs in filter_specs:
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
    # know which and it's not worth the extra code - just validate and set them all
    def filter_use_clicked(self):
        """Change the filters-in-use in preferences from the checked checkboxes"""

        filter_specs = self._preferences.get_filter_spec_list()
        fs: FilterSpec
        for fs in filter_specs:
            check_box_name: str = f"useFilter_{fs.get_slot_number()}"
            this_check_box: QCheckBox = self.ui.findChild(QCheckBox, check_box_name)
            assert this_check_box is not None
            box_is_checked = this_check_box.isChecked()
            fs.set_is_used(box_is_checked)
            # If this filter is now set to "use", there must be a name specified.
            # Check this. If there isn't a name, set field to red to draw attention
            self.validate_filter_name_field(fs, can_be_blank=not box_is_checked)

        self._preferences.set_filter_spec_list(filter_specs)

    def filter_name_changed(self):
        """Set filter name in prefs from the changed value in the UI"""
        filter_specs = self._preferences.get_filter_spec_list()
        fs: FilterSpec
        for fs in filter_specs:
            name_field_name: str = f"filterName_{fs.get_slot_number()}"
            this_field: QLineEdit = self.ui.findChild(QLineEdit, name_field_name)
            assert this_field is not None
            proposed_name = this_field.text().strip()
            if self.validate_filter_name_field(fs, can_be_blank=not fs.get_is_used()):
                fs.set_name(proposed_name)
        self._preferences.set_filter_spec_list(filter_specs)

    # Validate the filter name field for the given filter.
    # Ensure it is a valid filter or, optionally, it can be blanks.
    # Colour it red if bad (and return validity flag)

    def validate_filter_name_field(self, fs: FilterSpec, can_be_blank=False) -> bool:
        # print(f"validate_filter_name_field({fs},{can_be_blank})")
        # First we validate the format of the name, and whether it can be blank
        name_field_name: str = f"filterName_{fs.get_slot_number()}"
        this_field: QLineEdit = self.ui.findChild(QLineEdit, name_field_name)
        assert this_field is not None
        proposed_name = this_field.text().strip()
        if len(proposed_name) == 0:
            name_valid = can_be_blank
        else:
            name_valid = FilterSpec.valid_filter_name(proposed_name)

        # If the name is otherwise valid, we check that it would be unique in the list
        if name_valid and len(proposed_name) > 0:
            other_fs: FilterSpec
            for other_fs in self._preferences.get_filter_spec_list():
                if other_fs.get_slot_number() != fs.get_slot_number():  # Only compare to other filters
                    if other_fs.get_name().strip() == proposed_name:
                        # Collision with existing name other than the one we're setting
                        name_valid = False

        SharedUtils.background_validity_color(this_field, name_valid)
        # print(f"validate_filter_name_field({fs},{can_be_blank}) returns {name_valid}")
        return name_valid

    def binning_group_clicked(self):
        """Change binnings in preferences from changed binnings in UI"""
        binning_specs = self._preferences.get_binning_spec_list()
        bs: BinningSpec
        for bs in binning_specs:
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
        """Validate and store a changed 'number of flat frames' value"""
        proposed_new_number: str = self.ui.numFlats.text()
        new_number = Validators.valid_int_in_range(proposed_new_number, 0, 256)
        valid = new_number is not None
        if valid:
            self._preferences.set_default_frame_count(new_number)
        SharedUtils.background_validity_color(self.ui.numFlats, valid)

    def target_adus_changed(self):
        """Validate and store a changed 'target ADUs' value"""
        proposed_new_number: str = self.ui.targetADUs.text()
        new_number = Validators.valid_float_in_range(proposed_new_number, 1, 500000)
        valid = new_number is not None
        if valid:
            self._preferences.set_target_adus(new_number)
        SharedUtils.background_validity_color(self.ui.targetADUs, valid)

    def server_address_changed(self):
        """Validate and store a changed 'server address' value"""
        proposed_new_address: str = self.ui.serverAddress.text()
        valid = RmNetUtils.valid_server_address(proposed_new_address)
        if valid:
            self._preferences.set_server_address(proposed_new_address)
        SharedUtils.background_validity_color(self.ui.serverAddress, valid)

    def port_number_changed(self):
        """Validate and store a changed 'server port number' value"""
        proposed_new_number: str = self.ui.portNumber.text()
        new_number = Validators.valid_int_in_range(proposed_new_number, 1, 65536)
        valid = new_number is not None
        if valid:
            self._preferences.set_port_number(new_number)
        SharedUtils.background_validity_color(self.ui.portNumber, valid)

    def adu_tolerance_changed(self):
        """Validate and store a changed 'ADU tolerance' value"""
        proposed_new_number: str = self.ui.aduTolerance.text()
        new_number = Validators.valid_float_in_range(proposed_new_number, 0, 100)
        valid = new_number is not None
        if valid:
            self._preferences.set_adu_tolerance(new_number / 100.0)
        SharedUtils.background_validity_color(self.ui.aduTolerance, valid)

    def use_filter_wheel_clicked(self):
        """Store value of just-toggled 'use filter wheel' checkbox"""
        self._preferences.set_use_filter_wheel(self.ui.useFilterWheel.isChecked())
        self.enable_filter_fields()

    def close_button_clicked(self):
        """Close Button on UI is equivalent to the close action"""
        self.ui.close()

    # Enable the filter fields only if "use filter wheel" is turned on
    def enable_filter_fields(self):
        """Enable or disable filter fields depending on the 'use filter wheel' checkbox"""
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

    # Reset Time Estimates clicked.  We set the stored initial exposure time estimates
    # back to factory default settings.  Do a "are you sure" dialog first.

    def reset_estimates_clicked(self):
        """'Reset Estimates' button clicked - do a confirmation dialog then reset them"""
        message_dialog = QMessageBox()
        message_dialog.setWindowTitle("Reset Initial Exposures")
        message_dialog.setText("Reset stored exposure estimates?")
        message_dialog.setInformativeText("This will reset the saved initial exposure estimates for the filters. "
                                          + "Next time you run, they will be recalculated, taking a little longer. "
                                          + "Are you sure?")
        message_dialog.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        message_dialog.setDefaultButton(QMessageBox.Ok)
        dialog_result = message_dialog.exec_()
        if dialog_result == QMessageBox.Ok:
            self._preferences.reset_saved_exposure_estimates()

    def source_alt_changed(self):
        """Validate and store light source altitude"""
        proposed_new_number: str = self.ui.sourceAlt.text()
        new_number: Optional[float] = Validators.valid_float_in_range(proposed_new_number, -90, +90)
        valid = new_number is not None
        if valid:
            self._preferences.set_source_alt(new_number)
        SharedUtils.background_validity_color(self.ui.sourceAlt, valid)

    def source_az_changed(self):
        """Validate and store light source azimuth"""
        proposed_new_number: str = self.ui.sourceAz.text()
        new_number: Optional[float] = Validators.valid_float_in_range(proposed_new_number, -360, +360)
        valid = new_number is not None
        if valid:
            self._preferences.set_source_az(new_number)
        SharedUtils.background_validity_color(self.ui.sourceAz, valid)

    def read_scope_clicked(self):
        """Read current alt/az from mount and store as slew target in preferences"""
        # Get a server object
        server = TheSkyX(self._preferences.get_server_address(),
                         self._preferences.get_port_number())

        # Ask for scope settings
        (success, scope_alt, scope_az, message) = server.get_scope_alt_az()

        # If success put them in place
        if success:
            self._preferences.set_source_alt(scope_alt)
            self._preferences.set_source_az(scope_az)
            self.ui.sourceAlt.setText(str(round(scope_alt, 4)))
            self.ui.sourceAz.setText(str(round(scope_az, 4)))
            self.ui.slewMessage.setText("Read OK")
        else:
            self.ui.slewMessage.setText(message)

    # Catch window resizing so we can record the changed size

    def eventFilter(self, event_object: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Resize:
            window_size = event.size()
            self._preferences.set_prefs_window_size(window_size)
        return False  # Explain that we didn't handle event, should be passed upward
