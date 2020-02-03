from PyQt5.QtCore import QSettings, QSize

from BinningSpec import BinningSpec
from FilterSpec import FilterSpec


class Preferences(QSettings):
    # Settings are:
    USE_FILTER_WHEEL = "use_filter_wheel"
    FLAT_FRAME_DEFAULT_COUNT_SETTING = "flat_frame_default_count"
    FILTER_SPEC_LIST_SETTING = "filter_spec_list"
    BINNING_SPEC_LIST_SETTING = "binning_spec_list"
    TARGET_ADU_SETTING = "target_adus"
    TARGET_ADU_TOLERANCE = "target_adu_tolerance"  # A % stored as a float between 0 and 1
    WARM_WHEN_DONE_FLAG = "warm_up_when_done"
    SERVER_ADDRESS_SETTING = "server_address"
    PORT_NUMBER_SETTING = "port_number"
    FILTER_BIN_EXPOSURE_TABLE = "filter_bin_exposure_table"
    MAIN_WINDOW_SIZE_SETTING = "main_window_size"
    PREFS_WINDOW_SIZE_SETTING = "prefs_window_size"
    SESSION_WINDOW_SIZE_SETTING = "session_window_size"
    STANDARD_FONT_SIZE_SETTING = "standard_font_size"
    SLEW_TO_SOURCE = "slew_to_source"
    SOURCE_ALT = "source_alt"
    SOURCE_AZ = "source_az"

    def __init__(self):
        QSettings.__init__(self, "EarwigHavenObservatory.com", "FlatCaptureNow1")

    # Getters and setters for the possible settings

    def get_use_filter_wheel(self) -> bool:
        return bool(self.value(self.USE_FILTER_WHEEL))

    def set_use_filter_wheel(self, value: bool):
        self.setValue(self.USE_FILTER_WHEEL, value)

    def get_default_frame_count(self) -> int:
        return int(self.value(self.FLAT_FRAME_DEFAULT_COUNT_SETTING))

    def set_default_frame_count(self, value: int):
        self.setValue(self.FLAT_FRAME_DEFAULT_COUNT_SETTING, value)

    def get_filter_spec_list(self) -> [FilterSpec]:
        return self.value(self.FILTER_SPEC_LIST_SETTING)

    def set_filter_spec_list(self, value: [FilterSpec]):
        self.setValue(self.FILTER_SPEC_LIST_SETTING, value)

    def get_binning_spec_list(self) -> [BinningSpec]:
        return self.value(self.BINNING_SPEC_LIST_SETTING)

    def set_binning_spec_list(self, value: [BinningSpec]):
        self.setValue(self.BINNING_SPEC_LIST_SETTING, value)

    def get_target_adus(self) -> float:
        return float(self.value(self.TARGET_ADU_SETTING))

    def set_target_adus(self, value: float):
        self.setValue(self.TARGET_ADU_SETTING, value)

    def get_adu_tolerance(self) -> float:
        return float(self.value(self.TARGET_ADU_TOLERANCE))

    def set_adu_tolerance(self, value: float):
        self.setValue(self.TARGET_ADU_TOLERANCE, value)

    def get_server_address(self) -> str:
        return self.value(self.SERVER_ADDRESS_SETTING)

    def set_server_address(self, value: str):
        self.setValue(self.SERVER_ADDRESS_SETTING, value)

    def get_port_number(self) -> int:
        return int(self.value(self.PORT_NUMBER_SETTING))

    def set_port_number(self, value: int):
        self.setValue(self.PORT_NUMBER_SETTING, value)

    def get_warm_when_done(self) -> bool:
        return bool(self.value(self.WARM_WHEN_DONE_FLAG))

    def set_warm_when_done(self, value: bool):
        self.setValue(self.WARM_WHEN_DONE_FLAG, value)

    def get_standard_font_size(self) -> int:
        return int(self.value(self.STANDARD_FONT_SIZE_SETTING))

    def set_standard_font_size(self, value: int):
        self.setValue(self.STANDARD_FONT_SIZE_SETTING, value)

    def get_main_window_size(self) -> QSize:
        return self.value(self.MAIN_WINDOW_SIZE_SETTING) \
            if self.contains(self.MAIN_WINDOW_SIZE_SETTING) else None

    def set_main_window_size(self, size: QSize):
        self.setValue(self.MAIN_WINDOW_SIZE_SETTING, size)

    def get_prefs_window_size(self) -> QSize:
        return self.value(self.PREFS_WINDOW_SIZE_SETTING) \
            if self.contains(self.PREFS_WINDOW_SIZE_SETTING) else None

    def set_prefs_window_size(self, size: QSize):
        self.setValue(self.PREFS_WINDOW_SIZE_SETTING, size)

    def get_session_window_size(self) -> QSize:
        return self.value(self.SESSION_WINDOW_SIZE_SETTING) \
            if self.contains(self.SESSION_WINDOW_SIZE_SETTING) else None

    def set_session_window_size(self, size: QSize):
        self.setValue(self.SESSION_WINDOW_SIZE_SETTING, size)

    def get_slew_to_source(self) -> bool:
        return self.value(self.SLEW_TO_SOURCE)

    def set_slew_to_source(self, flag: bool):
        self.setValue(self.SLEW_TO_SOURCE, flag)

    def get_source_alt(self) -> float:
        return float(self.value(self.SOURCE_ALT))

    def set_source_alt(self, alt: float):
        self.setValue(self.SOURCE_ALT, alt)

    def get_source_az(self) -> float:
        return float(self.value(self.SOURCE_AZ))

    def set_source_az(self, az: float):
        self.setValue(self.SOURCE_AZ, az)

    def get_initial_exposure(self, filter_slot: int, binning: int):
        """Fetch the last exposure used for given filter and binning as initial guess for new session"""

        exposure_table = self.value(self.FILTER_BIN_EXPOSURE_TABLE)
        binning_index = binning - 1
        result = 10
        if exposure_table is not None:
            if filter_slot in exposure_table:
                tuple_for_filter = exposure_table[filter_slot]
                if (binning_index >= 0) and (binning_index < len(tuple_for_filter)):
                    result = tuple_for_filter[binning_index]
                else:
                    print(f"Preferences doesnt contain exposure entry for filter {filter_slot} and binning {binning}")
            else:
                print(f"Preferences has no exposure length entry for filter {filter_slot}")
        else:
            print("No exposure estimate table in preferences")
        return result

    def update_initial_exposure(self, filter_slot: int, binning: int, new_exposure: float):
        """Save exposure used for filter and binning to use as initial exposure next time"""

        exposure_table = self.value(self.FILTER_BIN_EXPOSURE_TABLE)
        binning_index = binning - 1
        result = 10
        if exposure_table is not None:
            if filter_slot in exposure_table:
                tuple_for_filter = exposure_table[filter_slot]
                if (binning_index >= 0) and (binning_index < len(tuple_for_filter)):
                    tuple_for_filter[binning_index] = new_exposure
                    exposure_table[filter_slot] = tuple_for_filter
                    self.setValue(self.FILTER_BIN_EXPOSURE_TABLE, exposure_table)
                else:
                    print(
                        f"Preferences doesnt contain exposure entry for filter {filter_slot} and binning {binning}")
            else:
                print(f"Preferences has no exposure length entry for filter {filter_slot}")
        else:
            print("No exposure estimate table in preferences")
        return result

    # Get initial exposure estimate for a given filter (slot number) and binning value

    # Defaults when no settings file exists

    def set_defaults(self):
        """Set default values that are used if no preferences are already established"""
        self.set_default_value(self.USE_FILTER_WHEEL, True)
        self.set_default_value(self.FLAT_FRAME_DEFAULT_COUNT_SETTING, 32)
        self.set_default_value(self.TARGET_ADU_SETTING, 25000)
        self.set_default_value(self.TARGET_ADU_TOLERANCE, 0.05)  # 5%
        self.set_default_value(self.WARM_WHEN_DONE_FLAG, True)
        self.set_default_value(self.SERVER_ADDRESS_SETTING, "localhost")
        self.set_default_value(self.PORT_NUMBER_SETTING, 3040)
        self.set_default_value(self.STANDARD_FONT_SIZE_SETTING, 12)
        binning_list: [BinningSpec] = (BinningSpec(1, False, True),
                                       BinningSpec(2, False, True),
                                       BinningSpec(3, True, False),
                                       BinningSpec(4, False, False))
        self.set_default_value(self.BINNING_SPEC_LIST_SETTING, binning_list)
        filter_list: [FilterSpec] = (FilterSpec(1, "Red", True),
                                     FilterSpec(2, "Green", True),
                                     FilterSpec(3, "Blue", True),
                                     FilterSpec(4, "Luminance", True),
                                     FilterSpec(5, "Ha", True),
                                     FilterSpec(6, "", False),
                                     FilterSpec(7, "", False),
                                     FilterSpec(8, "", False))
        self.set_default_value(self.FILTER_SPEC_LIST_SETTING, filter_list)
        # The initial exposures table is a dictionary indexed by filter slot number,
        # with the value of that entry a list of 4 exposure times by binning (1-4)
        # The values are estimates and don't matter that much as they are refined as
        # they are actually used.
        exposure_table = self.default_initial_exposure_estimates_table()
        self.set_default_value(self.FILTER_BIN_EXPOSURE_TABLE, exposure_table)
        self.set_default_value(self.SLEW_TO_SOURCE, False)
        self.set_default_value(self.SOURCE_ALT, 45)
        self.set_default_value(self.SOURCE_AZ, 180)

    def set_default_value(self, pref_name, value):
        """Set preference field to given value if there is not already a value set"""
        if self.value(pref_name) is None:
            self.setValue(pref_name, value)

    def reset_saved_exposure_estimates(self):
        """Clear saved exposure estimates so they are recalculated next time they are needed"""
        exposure_table = self.default_initial_exposure_estimates_table()
        self.setValue(self.FILTER_BIN_EXPOSURE_TABLE, exposure_table)

    # The values and comments below reflect my personal filter assignments.
    # It doesn't matter if the user has different ones, as it will only affect
    # the very first time they search for a good exposure, and might result in them
    # taking one or two extra test exposures.  After the firs time the good values are
    # recorded.  - Richard
    @staticmethod
    def default_initial_exposure_estimates_table() -> {int: [int]}:
        return {1: [10, 10, 10, 10],  # Red
                2: [10, 10, 10, 10],  # Green
                3: [10, 10, 10, 10],  # Blue
                4: [10, 10, 10, 10],  # Luminance
                5: [90, 45, 25, 15],  # Hydrogen Alpha
                6: [90, 10, 10, 10],
                7: [90, 10, 10, 10],
                8: [90, 10, 10, 10]}
