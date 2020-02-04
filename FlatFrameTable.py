# Represent a table of the number of flat frames to take for each combination
# of filters and binnings.  Rows (outer list) are filters ;
# columns (inner list) are binnings.  Rows are indexed by filter number (minus 1)
# and columns from 0 to 3 (for binnings 1x1, 2x2, 3x3, and 4x4)

from BinningSpec import BinningSpec
from FilterSpec import FilterSpec


# Class representing the list of flat frame sets to be taken in this session
# The table is one row per filter, and one column per binning value, with each cell
# being the number of frames of that combination to be acquired
# e.g.
#                   1 x 1       2 x 2       3 x 3
#  Red                             32
#  Green                           32
#  Blue                            32
#  Luminance           32          32          32


class FlatFrameTable:

    def __init__(self, frame_count: int, filters: [FilterSpec], binnings: [BinningSpec]):
        self._filters: [FilterSpec] = filters
        self._binnings: [BinningSpec] = binnings
        self._frame_count = frame_count
        self._table_rows = self.generate_frames_table(filters, binnings, frame_count)

    def generate_frames_table(self, filters: [FilterSpec],
                              binnings: [BinningSpec],
                              frame_count: int):
        """Generate flat frame table from given list of filters and binnings"""
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
                    bs: BinningSpec = self._binnings[binning_index]
                    if bs.get_is_default():
                        all_rows[filter_index][binning_index] = frame_count
        return all_rows

    def get_table_item(self, row_index: int, column_index: int) -> int:
        """Return the number of frames for a given row,column cell"""
        result = self._table_rows[row_index][column_index]
        return result

    def set_table_item(self, row_index: int, column_index: int, frames_count):
        """Set the number of frames at a given row,column cell"""
        self._table_rows[row_index][column_index] = frames_count

    def reset_to_defaults(self):
        """Reset all the cells to defaults specified by the preferences"""
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
        """Set all table cells to zero"""
        self.set_all_to(0)

    def set_all_to_default(self):
        """Set all table cells to the default frame count"""
        self.set_all_to(self._frame_count)

    def set_all_to(self, value: int):
        """Set all table cells to the given value"""
        row_index: int
        col_index: int
        num_columns = len(self._table_rows[0])
        for row_index in range(len(self._table_rows)):
            for col_index in range(num_columns):
                self._table_rows[row_index][col_index] = value

    # Encode for JSON
    def encode(self):
        """Encode the table as a json dict object"""
        return {
            "_type": "FlatFrameTable",
            "_value": self.__dict__
        }

    @classmethod
    def decode(cls, obj):
        """Create a table by decoding the given json dict object"""
        assert (obj["_type"] == "FlatFrameTable")
        value_dict = obj["_value"]
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
        """Create table from the given saved values"""
        new_fft = FlatFrameTable(frame_count, filter_spec_list, binning_spec_list)
        new_fft._table_rows = table_rows
        return new_fft
