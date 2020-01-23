# Represent a table of the number of flat frames to take for each combination
# of filters and binnings.  Rows (outer list) are filters ;
# columns (inner list) are binnings.  Rows are indexed by filter number (minus 1)
# and columns from 0 to 3 (for binnings 1x1, 2x2, 3x3, and 4x4)
import json

from BinningSpec import BinningSpec
from FilterSpec import FilterSpec


class FlatFrameTable:

    def __init__(self, frame_count: int, filters: [FilterSpec], binnings: [BinningSpec]):
        self._filters: [FilterSpec] = filters
        self._binnings: [BinningSpec] = binnings
        self._frame_count = frame_count
        self._table_rows = self.generate_frames_table(filters, binnings, frame_count)

    def generate_frames_table(self, filters: [FilterSpec], binnings: [BinningSpec], frame_count: int):
        # print("generate_frames_table")
        num_rows = len(filters)
        num_columns = len(binnings)

        # Initialize matrix with zeros.
        # List of rows, with each row a list of cells in columns of that row
        one_row: [int] = [0] * num_columns
        all_rows = []
        # Duplicate this row.  Don't use * to do it, as we end up with multiple pointers to the
        # same row rather than unique rows
        for i in range(num_rows):
            all_rows.append(one_row.copy())
        # Put the default value into cells where binning is "default"
        for filter_index in range(num_rows):
            fs: FilterSpec = self._filters[filter_index]
            if fs.get_is_used():
                for binning_index in range(num_columns):
                    # print(f"  Test filter {filter_index}, binning {binning_index}")
                    bs: BinningSpec = self._binnings[binning_index]
                    if bs.get_is_default():
                        all_rows[filter_index][binning_index] = frame_count
        return all_rows

    def get_table_item(self, row_index: int, column_index: int) -> int:
        # print(f"get_table_item({row_index},{column_index})")
        result = self._table_rows[row_index][column_index]
        # print(f"    get_table_item({row_index},{column_index}) returns {result}")
        return result

    def set_table_item(self, row_index: int, column_index: int, frames_count: int):
        # print(f"set_table_item({row_index},{column_index}, {frames_count})")
        # print(f"  Table before: {self._table_rows}")
        self._table_rows[row_index][column_index] = frames_count
        # print(f"  Table after: {self._table_rows}")

    def reset_to_defaults(self):
        num_rows = len(self._filters)
        num_columns = len(self._binnings)
        for filter_index in range(num_rows):
            for binning_index in range(num_columns):
                bs: BinningSpec = self._binnings[binning_index]
                if bs.get_is_default():
                    self._table_rows[filter_index][binning_index] = self._frame_count
                else:
                    self._table_rows[filter_index][binning_index] = 0

    def set_all_to_zero(self):
        self.set_all_to(0)

    def set_all_to_default(self):
        self.set_all_to(self._frame_count)

    def set_all_to(self, value: int):
        # print("set_all_to")
        row_index: int
        col_index: int
        num_columns = len(self._table_rows[0])
        for row_index in range(len(self._table_rows)):
            for col_index in range(num_columns):
                self._table_rows[row_index][col_index] = value

   # Encode for JSON
    def encode(self):
        return {
            "_type": "FlatFrameTable",
            "_value": self.__dict__
        }

    @classmethod
    def decode(cls, obj):
        # print(f"FlatFrameTable/decode({obj}")
        assert (obj["_type"] == "FlatFrameTable")
        value_dict = obj["_value"]
        # print(f"  value_dict: {value_dict}")
        frame_count: int = value_dict["_frame_count"]
        filter_spec_list: [FilterSpec] = value_dict["_filters"]
        binning_spec_list: [BinningSpec] = value_dict["_binnings"]
        table_rows: [[int]] = value_dict["_table_rows"]
        return FlatFrameTable.create_from_saved(frame_count, filter_spec_list, binning_spec_list, table_rows)

    @classmethod
    def create_from_saved(cls, frame_count: int,
                          filter_spec_list: [FilterSpec],
                          binning_spec_list: [BinningSpec],
                          table_rows: [[int]]):
        # print("create_from_saved")
        new_fft = FlatFrameTable(frame_count, filter_spec_list, binning_spec_list)
        new_fft._table_rows = table_rows
        return new_fft

