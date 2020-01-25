# All the data relevant to this flat-frames session.
# Storing this in a file captures everything needed.
import json
from json import JSONDecodeError

from BinningSpec import BinningSpec
from DataModelDecoder import DataModelDecoder
from DataModelEncoder import DataModelEncoder
from FilterSpec import FilterSpec
from FlatFrameTable import FlatFrameTable
from Preferences import Preferences


class DataModel:

    # Initialize an empty one
    def __init__(self):
        # The fields associated with this data model
        self._default_frame_count: int = 0
        self._target_adus: float = 0
        self._adu_tolerance: float = 0
        self._server_address: str = ""
        self._port_number: int = 0
        self._warm_when_done: bool = False
        self._use_filter_wheel: bool = False
        self._flat_frame_count_table: FlatFrameTable  # Rows=filters, columns=binning
        self._filter_specs: [FilterSpec]
        self._binning_specs: [BinningSpec]

    # Initialize from given preferences
    @classmethod
    def make_from_preferences(cls, preferences: Preferences):
        """Create a DataModel instance from the saved preferences"""
        model = DataModel()
        model.set_default_frame_count(preferences.get_default_frame_count())
        model.set_target_adus(preferences.get_target_adus())
        model.set_adu_tolerance(preferences.get_adu_tolerance())
        model.set_server_address(preferences.get_server_address())
        model.set_port_number(preferences.get_port_number())
        model.set_warm_when_done(preferences.get_warm_when_done())
        model.set_use_filter_wheel(preferences.get_use_filter_wheel())
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
        # print(f"Set default frame count to {count}")
        self._default_frame_count = count

    def get_target_adus(self) -> float:
        return self._target_adus

    def set_target_adus(self, adus: float):
        # print(f"Set target adus to {adus}")
        self._target_adus = adus

    def get_adu_tolerance(self) -> float:
        return self._adu_tolerance

    def set_adu_tolerance(self, tolerance: float):
        # print(f"Set adu tolerance to {tolerance}")
        self._adu_tolerance = tolerance

    def get_server_address(self) -> str:
        return self._server_address

    def set_server_address(self, address: str):
        # print(f"Set server address to {address}")
        self._server_address = address

    def get_port_number(self) -> int:
        return self._port_number

    def set_port_number(self, port: int):
        # print(f"Set port number to {port}")
        self._port_number = port

    def get_warm_when_done(self) -> bool:
        return self._warm_when_done

    def set_warm_when_done(self, flag: bool):
        # print(f"Set warm-when-done to {flag}")
        self._warm_when_done = flag

    def get_use_filter_wheel(self) -> bool:
        return self._use_filter_wheel

    def set_use_filter_wheel(self, flag: bool):
        # print(f"Set _use_filter_wheel to {flag}")
        self._use_filter_wheel = flag

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
        """report how many filters are enabled for use"""
        enabled_filters: [FilterSpec] = self.get_enabled_filters()
        return len(enabled_filters)

    def get_enabled_filters(self) -> [FilterSpec]:
        """Get the list of filters enabled for use"""
        fs: FilterSpec
        filter_spec_list: [FilterSpec] = [fs for fs in self._filter_specs if fs.get_is_used()]
        return filter_spec_list

    def count_enabled_binnings(self) -> int:
        """Report how many binning values are enabled for use"""
        enabled_binnings: [BinningSpec] = self.get_enabled_binnings()
        return len(enabled_binnings)

    def get_enabled_binnings(self) -> [BinningSpec]:
        """Get the list of binning values enabled for use"""
        bs: BinningSpec
        binning_spec_list: [BinningSpec] = [bs for bs in self._binning_specs
                                            if (bs.get_is_default() or bs.get_is_available())]
        return binning_spec_list

    # Map displayed row index (filter) to actual table index
    def map_display_to_raw_filter_index(self, displayed_row_index: int) -> int:
        """Map index of filter row in ui to index of that filter in the filterspec list"""
        # print(f"map_display_to_raw_filter_index({displayed_row_index})")
        displayed_filters: [FilterSpec] = self.get_enabled_filters()
        this_filter: FilterSpec = displayed_filters[displayed_row_index]
        result: int = this_filter.get_slot_number() - 1
        # print(f"   Returns {result}")
        return result

    # Map displayed column index (binning) to actual table index
    def map_display_to_raw_binning_index(self, displayed_column_index: int) -> int:
        """Map index of binning row in ui to index of that binning in the binningspec list"""
        # print(f"map_display_to_raw_binning_index({displayed_column_index})")
        displayed_binnings: [BinningSpec] = self.get_enabled_binnings()
        this_binning: BinningSpec = displayed_binnings[displayed_column_index]
        result: int = this_binning.get_binning_value() - 1
        # print(f"   Returns {result}")
        return result

    def serialize_to_json(self) -> str:
        """Serialize this data model to a json string for saving to a file"""
        # print("serializeToJson")
        serialized = json.dumps(self.__dict__, cls=DataModelEncoder, indent=4)
        return serialized

    def update_from_loaded_json(self, loaded_model):
        """Update the current data model from the given loaded json dict"""
        self.set_default_frame_count(loaded_model["_default_frame_count"])
        self.set_target_adus(loaded_model["_target_adus"])
        self.set_adu_tolerance(loaded_model["_adu_tolerance"])
        self.set_server_address(loaded_model["_server_address"])
        self.set_port_number(loaded_model["_port_number"])
        self.set_warm_when_done(loaded_model["_warm_when_done"])
        self.set_use_filter_wheel(loaded_model["_use_filter_wheel"])
        self.set_filter_specs(loaded_model["_filter_specs"])
        self.set_binning_specs(loaded_model["_binning_specs"])
        self.set_flat_frame_count_table(loaded_model["_flat_frame_count_table"])

    @classmethod
    def make_from_file_named(cls, file_name):
        """Create a new data model by reading the json encoding in the given file"""
        loaded_model = None
        try:
            with open(file_name, "r") as file:
                loaded_json = json.load(file, cls=DataModelDecoder)
                if loaded_json is None:
                    print(f"File \"{file_name}\" is not a saved FlatCaptureNow1 file (wrong object type)")
                    return None
                if not DataModel.valid_json_model(loaded_json):
                    print(f"File \"{file_name}\" is not a saved FlatCaptureNow1 file (wrong object type)")
                    return None
                loaded_model = DataModel()
                loaded_model.update_from_loaded_json(loaded_json)
        except FileNotFoundError:
            print(f"File \"{file_name}\" not found")
        except JSONDecodeError:
            print(f"File \"{file_name}\" is not a saved FlatCaptureNow1 file (not json)")
        return loaded_model

    # Is the given dictionary a valid representation of a data model for this app?
    # We'll check if the expected dict names, and no others, are present

    required_dict_names = ("_default_frame_count", "_target_adus", "_adu_tolerance",
                           "_server_address", "_port_number", "_warm_when_done",
                           "_use_filter_wheel", "_filter_specs", "_binning_specs",
                           "_flat_frame_count_table")

    @classmethod
    def valid_json_model(cls, loaded_json_model: {}) -> bool:
        """confirm that the given json dict is a valid data model representation"""
        seems_valid = True
        # Are all the required fields present?
        for required_name in DataModel.required_dict_names:
            if required_name not in loaded_json_model:
                seems_valid = False

        # Are there any fields present that shouldn't be?
        for given_name in loaded_json_model.keys():
            if given_name not in DataModel.required_dict_names:
                seems_valid = False

        return seems_valid

    # Copy all the attribute values from the given model into self
    def load_from_model(self, source_model):
        # print("loadFromModel")
        self.__dict__.update(source_model.__dict__)
        return
