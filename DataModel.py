# All the data relevant to this flat-frames session.
# Storing this in a file captures everything needed.
import json
from json import JSONDecodeError
from typing import Optional

from BinningSpec import BinningSpec
from Constants import Constants
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
        self._save_files_locally = False    # local or remote?
        self._local_path = Constants.LOCAL_PATH_NOT_SET   # Path to save folder if local
        self._flat_frame_count_table: Optional[FlatFrameTable] = None  # Rows=filters, columns=binning
        self._filter_specs: [FilterSpec] = []
        self._binning_specs: [BinningSpec] = []
        self._control_mount: bool = False
        self._home_mount: bool = False
        self._slew_to_light_source: bool = False
        self._source_alt: float = 0
        self._source_az: float = 0
        self._park_when_done: bool = False
        self._tracking_off: bool = False
        self._dither_flats: bool = False
        self._dither_radius: float = 1
        self._dither_max_radius: float = 5

    # Initialize from given preferences - this is the normal way to create a data model
    # since it will pick up all the users' saved default settings

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
        model.set_save_files_locally(False)
        model.set_flat_frame_count_table(FlatFrameTable(
            preferences.get_default_frame_count(),
            preferences.get_filter_spec_list(),
            preferences.get_binning_spec_list()))
        model.set_source_alt(float(preferences.get_source_alt()))
        model.set_source_az(float(preferences.get_source_az()))
        model.set_dither_flats(bool(preferences.get_dither_flats()))
        model.set_dither_radius(float(preferences.get_dither_radius()))
        model.set_dither_max_radius(float(preferences.get_dither_max_radius()))

        return model

    # Make up a data model by reading from a previously-saved json file

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

    # Getters and setters
    def get_default_frame_count(self) -> int:
        return self._default_frame_count

    def set_default_frame_count(self, count: int):
        self._default_frame_count = count

    def get_target_adus(self) -> float:
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

    def get_use_filter_wheel(self) -> bool:
        return self._use_filter_wheel

    def set_use_filter_wheel(self, flag: bool):
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

    def get_save_files_locally(self) -> bool:
        return self._save_files_locally

    def set_save_files_locally(self, flag: bool):
        self._save_files_locally = flag

    def get_local_path(self) -> str:
        return self._local_path

    def set_local_path(self, value: str):
        self._local_path = value

    def get_control_mount(self) -> bool:
        return self._control_mount

    def set_control_mount(self, flag: bool):
        self._control_mount = flag

    def get_home_mount(self) -> bool:
        return self._home_mount

    def set_home_mount(self, flag: bool):
        self._home_mount = flag

    def get_tracking_off(self) -> bool:
        return self._tracking_off

    def set_tracking_off(self, flag):
        self._tracking_off = flag

    def get_slew_to_light_source(self) -> bool:
        return self._slew_to_light_source

    def set_slew_to_light_source(self, flag: bool):
        self._slew_to_light_source = flag

    def get_source_alt(self) -> float:
        return self._source_alt

    def set_source_alt(self, alt: float):
        self._source_alt = alt

    def get_source_az(self) -> float:
        return self._source_az

    def set_source_az(self, az: float):
        self._source_az = az

    def get_park_when_done(self) -> bool:
        return self._park_when_done

    def set_park_when_done(self, flag: bool):
        self._park_when_done = flag

    def get_dither_flats(self) -> bool:
        return self._dither_flats

    def set_dither_flats(self, flag: bool):
        self._dither_flats = flag

    def get_dither_radius(self) -> float:
        return self._dither_radius

    def set_dither_radius(self, radius: float):
        self._dither_radius = radius

    def get_dither_max_radius(self) -> float:
        return self._dither_max_radius

    def set_dither_max_radius(self, max_radius: float):
        self._dither_max_radius = max_radius

    # Count how many of the filterSpecs are enabled.
    # This becomes the number of rows in the displayed plan table
    def count_enabled_filters(self) -> int:
        """report how many filters are enabled for use"""
        enabled_filters: [FilterSpec] = self.get_enabled_filters()
        return len(enabled_filters)

    def get_enabled_filters(self) -> [FilterSpec]:
        """Get the list of filters enabled for use"""
        fs: FilterSpec
        filter_spec_list: [FilterSpec] = [fs for fs in self._filter_specs if fs.get_is_used()
                                          and FilterSpec.valid_filter_name(fs.get_name())]
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
        """Map index of filter row in ui to index of that filter in the filter spec list"""
        displayed_filters: [FilterSpec] = self.get_enabled_filters()
        this_filter: FilterSpec = displayed_filters[displayed_row_index]
        result: int = this_filter.get_slot_number() - 1
        return result

    # Map displayed column index (binning) to actual table index
    def map_display_to_raw_binning_index(self, displayed_column_index: int) -> int:
        """Map index of binning row in ui to index of that binning in the binning spec list"""
        displayed_binnings: [BinningSpec] = self.get_enabled_binnings()
        this_binning: BinningSpec = displayed_binnings[displayed_column_index]
        result: int = this_binning.get_binning_value() - 1
        return result

    def serialize_to_json(self) -> str:
        """Serialize this data model to a json string for saving to a file"""
        serialized = json.dumps(self.__dict__, cls=DataModelEncoder, indent=4)
        return serialized

    def update_from_loaded_json(self, loaded_model):
        """Update the current data model from the given loaded json dict"""
        self.set_default_frame_count(self.protect_load(loaded_model, "_default_frame_count", 32))
        self.set_target_adus(self.protect_load(loaded_model, "_target_adus", 25000))
        self.set_adu_tolerance(self.protect_load(loaded_model, "_adu_tolerance", .1))
        self.set_server_address(self.protect_load(loaded_model, "_server_address", "localhost"))
        self.set_port_number(self.protect_load(loaded_model, "_port_number", 3040))
        self.set_warm_when_done(self.protect_load(loaded_model, "_warm_when_done", False))
        self.set_use_filter_wheel(self.protect_load(loaded_model, "_use_filter_wheel", True))
        self.set_filter_specs(self.protect_load(loaded_model, "_filter_specs", []))
        self.set_binning_specs(self.protect_load(loaded_model, "_binning_specs", []))
        self.set_flat_frame_count_table(self.protect_load(loaded_model, "_flat_frame_count_table", []))
        self.set_save_files_locally(self.protect_load(loaded_model, "_save_files_locally", False))
        self.set_local_path(self.protect_load(loaded_model, "_local_path", ""))
        self.set_slew_to_light_source(self.protect_load(loaded_model, "_slew_to_light_source", False))
        self.set_source_alt(self.protect_load(loaded_model, "_source_alt", 0))
        self.set_source_az(self.protect_load(loaded_model, "_source_az", 0))
        self.set_park_when_done(self.protect_load(loaded_model, "_park_when_done", False))
        self.set_control_mount(self.protect_load(loaded_model, "_control_mount", False))
        self.set_home_mount(self.protect_load(loaded_model, "_home_mount", False))
        self.set_tracking_off(self.protect_load(loaded_model, "_tracking_off", False))
        self.set_dither_flats(self.protect_load(loaded_model, "_dither_flats", False))
        self.set_dither_radius(self.protect_load(loaded_model, "_dither_radius", False))
        self.set_dither_max_radius(self.protect_load(loaded_model, "_dither_max_radius", False))

    @staticmethod
    def protect_load(dictionary, key, default):
        return dictionary[key] if key in dictionary else default

    # Is the given dictionary a valid representation of a data model for this app?
    # We'll check if the expected dict names, and no others, are present.  This is
    # to check that a claimed json file is truly a valid data model representation.
    # Note: we could go another level deep in obsessing over this by checking the
    # data TYPES of the fields, but we don't.

    required_dict_names = ("_default_frame_count", "_target_adus", "_adu_tolerance",
                           "_server_address", "_port_number", "_warm_when_done",
                           "_use_filter_wheel", "_filter_specs", "_binning_specs",
                           "_control_mount", "_home_mount", "_slew_to_light_source",
                           "_flat_frame_count_table", "_save_files_locally", "_local_path",
                           "_park_when_done", "_dither_flats", "_dither_radius",
                           "_dither_max_radius")

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
        self.__dict__.update(source_model.__dict__)
        return
