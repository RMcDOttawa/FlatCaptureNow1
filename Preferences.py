from PyQt5.QtCore import QSettings

from BinningSpec import BinningSpec
from FilterSpec import FilterSpec


class Preferences(QSettings):
    # Settings are:
    USE_FILTER_WHEEL = "use_filter_wheel"
    FLAT_FRAME_DEFAULT_COUNT_SETTING = "flat_frame_default_count"
    FILTER_SPEC_LIST_SETTING = "filter_spec_list"
    BINNING_SPEC_LIST_SETTING = "binning_spec_list"
    TARGET_ADU_SETTING = "target_adus"
    TARGET_ADU_TOLERANCE = "target_adu_tolerance"   # A % stored as a float between 0 and 1
    WARM_WHEN_DONE_FLAG = "warm_up_when_done"
    SERVER_ADDRESS_SETTING = "server_address"
    PORT_NUMBER_SETTING = "port_number"

    def __init__(self):
        QSettings.__init__(self, "EarwigHavenObservatory.com", "FlatCaptureNow1")

    # Getters and setters for the possible settings

    def get_use_filter_wheel(self) -> bool:
        return self.value(self.USE_FILTER_WHEEL)

    def set_use_filter_wheel(self, value: bool):
        self.setValue(self.USE_FILTER_WHEEL, value)

    def get_default_frame_count(self) -> int:
        return self.value(self.FLAT_FRAME_DEFAULT_COUNT_SETTING)

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
        return self.value(self.TARGET_ADU_SETTING)

    def set_target_adus(self, value: float):
        self.setValue(self.TARGET_ADU_SETTING, value)

    def get_adu_tolerance(self) -> float:
        return self.value(self.TARGET_ADU_TOLERANCE)

    def set_adu_tolerance(self, value: float):
        self.setValue(self.TARGET_ADU_TOLERANCE, value)

    def get_server_address(self) -> str:
        return self.value(self.SERVER_ADDRESS_SETTING)

    def set_server_address(self, value: str):
        self.setValue(self.SERVER_ADDRESS_SETTING, value)

    def get_port_number(self) -> int:
        return self.value(self.PORT_NUMBER_SETTING)

    def set_port_number(self, value: int):
        self.setValue(self.PORT_NUMBER_SETTING, value)

    def get_warm_when_done(self) -> bool:
        return self.value(self.WARM_WHEN_DONE_FLAG)

    def set_warm_when_done(self, value: bool):
        self.setValue(self.WARM_WHEN_DONE_FLAG, value)

    # Defaults when no settings file exists

    def set_defaults(self):
        if self.contains(self.FLAT_FRAME_DEFAULT_COUNT_SETTING):
            pass  # Settings are set
        else:
            self.setValue(self.USE_FILTER_WHEEL, True)
            self.setValue(self.FLAT_FRAME_DEFAULT_COUNT_SETTING, 32)
            self.setValue(self.TARGET_ADU_SETTING, 25000)
            self.setValue(self.TARGET_ADU_TOLERANCE, 0.10)  # 10%
            self.setValue(self.WARM_WHEN_DONE_FLAG, True)
            self.setValue(self.SERVER_ADDRESS_SETTING, "localhost")
            self.setValue(self.PORT_NUMBER_SETTING, 3040)
            binning_list: [BinningSpec] = (BinningSpec(1, False, True),
                                           BinningSpec(2, False, True),
                                           BinningSpec(3, True, False),
                                           BinningSpec(4, False, False))
            self.setValue(self.BINNING_SPEC_LIST_SETTING, binning_list)
            filter_list: [FilterSpec] = (FilterSpec(1, "Luminance", True),
                                         FilterSpec(2, "Red", True),
                                         FilterSpec(3, "Green", True),
                                         FilterSpec(4, "Blue", True),
                                         FilterSpec(5, "Ha", True),
                                         FilterSpec(6, "", False),
                                         FilterSpec(7, "", False),
                                         FilterSpec(8, "", False))
            self.setValue(self.FILTER_SPEC_LIST_SETTING, filter_list)
