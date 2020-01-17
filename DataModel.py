# All the data relevant to this flat-frames session.
# Storing this in a file captures everything needed.
from BinningSpec import BinningSpec
from FilterSpec import FilterSpec
from FlatFrameSet import FlatFrameSet
from FlatFrameTable import FlatFrameTable
from Preferences import Preferences


class DataModel:

    # Initialize an empty one
    def __init__(self):
        # The fields associated with this data model
        self._default_frame_count: int = 0
        self._target_adus: int = 0
        self._adu_tolerance: float = 0
        self._server_address: str = ""
        self._port_number: int = 0
        self._warm_when_done: bool = False
        self._flat_frame_count_table: FlatFrameTable    # Rows=filters, columns=binning
        self._filter_specs: [FilterSpec]
        self._binning_specs: [BinningSpec]

    # Initialize from given preferences
    @classmethod
    def make_from_preferences(cls, preferences: Preferences):
        model = DataModel()
        model.set_default_frame_count(preferences.get_default_frame_count())
        model.set_target_adus(preferences.get_target_adus())
        model.set_adu_tolerance(preferences.get_adu_tolerance())
        model.set_server_address(preferences.get_server_address())
        model.set_port_number(preferences.get_port_number())
        model.set_warm_when_done(preferences.get_warm_when_done())
        model.set_filter_specs(preferences.get_filter_spec_list())
        model.set_binning_specs(preferences.get_binning_spec_list())
        model.set_flat_frame_count_table(FlatFrameTable(
            preferences.get_default_frame_count(),
            preferences.get_filter_spec_list(),
            preferences.get_binning_spec_list()))
        return model

    # Getters and setters
    def get_default_frame_count(self) -> int:
        return self._default_frame_count

    def set_default_frame_count(self, count: int):
        self._default_frame_count = count

    def get_target_adus(self) -> int:
        return self._target_adus

    def set_target_adus(self, adus: float):
        self._target_adus = adus

    def get_adu_tolerance(self) -> float:
        return self._adu_tolerance

    def set_adu_tolerance(self, tolerance: float):
        self._adu_tolerance = tolerance

    def get_server_address(self) -> str:
        return self._server_address

    def set_server_address(self, address: str):
        self._server_address = address

    def get_port_number(self) -> int:
        return self._port_number

    def set_port_number(self, port: int):
        self._port_number = port

    def get_warm_when_done(self) -> bool:
        return self._warm_when_done

    def set_warm_when_done(self, flag: bool):
        self._warm_when_done = flag

    def get_flat_frame_count_table(self) -> FlatFrameTable:
        return self._flat_frame_count_table

    def set_flat_frame_count_table(self, table: FlatFrameTable):
        self._flat_frame_count_table = table

    def get_filter_specs(self) -> [FilterSpec]:
        return self._filter_specs

    def set_filter_specs(self, filter_specs: [FilterSpec]):
        self._filter_specs = filter_specs

    def get_binning_specs(self) -> [BinningSpec]:
        return self._binning_specs

    def set_binning_specs(self, binning_specs: [BinningSpec]):
        self._binning_specs = binning_specs

    # Count how many of the filterSpecs are enabled.
    # This becomes the number of rows in the displayed plan table
    def count_enabled_filters(self) -> int:
        enabled_filters: [FilterSpec] = self.get_enabled_filters()
        return len(enabled_filters)

    def get_enabled_filters(self) -> [FilterSpec]:
        fs: FilterSpec
        list: [FilterSpec] = [fs for fs in self._filter_specs if fs.get_is_used()]
        return list

    def count_enabled_binnings(self) -> int:
        enabled_binnings: [BinningSpec] = self.get_enabled_binnings()
        return len(enabled_binnings)

    def get_enabled_binnings(self) -> [BinningSpec]:
        bs: BinningSpec
        list: [BinningSpec] = [bs for bs in self._binning_specs
                               if (bs.get_is_default() or bs.get_is_available())]
        return list

    # Map displayed row index (filter) to actual table index
    def map_display_to_raw_filter_index(self, displayed_row_index: int) -> int:
        # print(f"map_display_to_raw_filter_index({displayed_row_index})")
        displayed_filters: [FilterSpec] = self.get_enabled_filters()
        this_filter: FilterSpec = displayed_filters[displayed_row_index]
        result: int = this_filter.get_slot_number() - 1
        # print(f"   Returns {result}")
        return result

    # Map displayed column index (binning) to actual table index
    def map_display_to_raw_binning_index(self, displayed_column_index: int) -> int:
        # print(f"map_display_to_raw_binning_index({displayed_column_index})")
        displayed_binnings: [BinningSpec] = self.get_enabled_binnings()
        this_binning: BinningSpec = displayed_binnings[displayed_column_index]
        result: int = this_binning.get_binning_value() - 1
        # print(f"   Returns {result}")
        return result

