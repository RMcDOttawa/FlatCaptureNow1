from typing import Callable

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant
from PyQt5.QtGui import QFont, QColor, QBrush

from BinningSpec import BinningSpec
from DataModel import DataModel
from FilterSpec import FilterSpec
from Preferences import Preferences
from SharedUtils import SharedUtils
from Validators import Validators


class SessionPlanTableModel(QAbstractTableModel):

    def __init__(self, data_model: DataModel,
                 preferences: Preferences,
                 dirty_reporting_method: Callable,
                 validity_reporting_method: Callable):
        QAbstractTableModel.__init__(self)
        self._dirty_reporting_method = dirty_reporting_method
        self._validity_reporting_method = validity_reporting_method
        self._data_model: DataModel = data_model
        self._preferences: Preferences = preferences

        self._cell_validity = [[True for _row in range(self.columnCount(QModelIndex()))]
                               for _col in range(self.rowCount(QModelIndex()))]

        # Check validity of all cells on loading in case bad data were saved
        self.prevalidate_all_cells()

    def set_cell_validity(self, index: QModelIndex, validity: bool):
        self._cell_validity[index.row()][index.column()] = validity

    # We've just loaded data for a table.  In case the data we were handed contained
    # any invalid cells, we'll re-do the validation for all of them.  In order to display
    # bad data (with red background), this table is the only place where invalid data can
    # end up in the data model, thus the need for this test.

    def prevalidate_all_cells(self):
        for row_index in range(self.rowCount(QModelIndex())):
            for column_index in range(self.columnCount(QModelIndex())):
                raw_row_index: int = self._data_model.map_display_to_raw_filter_index(row_index)
                raw_column_index: int = self._data_model.map_display_to_raw_binning_index(column_index)
                cell_contents = str(self._data_model.get_flat_frame_count_table().get_table_item(raw_row_index,
                                                                                                 raw_column_index))
                converted_value = Validators.valid_int_in_range(cell_contents, 0, 32767)
                validity_index_string = f"{row_index},{column_index}"
                index: QModelIndex = self.index(row_index, column_index)
                if converted_value is None:
                    # Invalid data.  Signal it by turning the cell red and tell
                    # the user interface about this so the proceed button will be
                    # disabled until it's fixed
                    self.set_cell_validity(index, False)
                    self._validity_reporting_method(validity_index_string, False)
                else:
                    # Turn of any error colour that might have been set for this cell
                    self.set_cell_validity(index, True)
                    self._validity_reporting_method(validity_index_string, True)

    # Methods required by the parent abstract data model

    # noinspection PyMethodOverriding
    def rowCount(self, parent: QModelIndex) -> int:
        if self._data_model.get_use_filter_wheel():
            num_rows = self._data_model.count_enabled_filters()
        else:
            num_rows = 1
        return num_rows

    # noinspection PyMethodOverriding
    def columnCount(self, parent: QModelIndex) -> int:
        return self._data_model.count_enabled_binnings()
        # return FrameSet.NUMBER_OF_DISPLAY_FIELDS

    # Get data element to display in a table cell
    # noinspection PyMethodOverriding
    def data(self, index: QModelIndex, role: Qt.DisplayRole):
        row_index: int = index.row()
        column_index: int = index.column()
        if role == Qt.DisplayRole:
            # We need to map these coordinates to the big table, since not all
            # filters and binnings here might be in use.
            raw_row_index: int = self._data_model.map_display_to_raw_filter_index(row_index)
            raw_column_index: int = self._data_model.map_display_to_raw_binning_index(column_index)
            result = str(self._data_model.get_flat_frame_count_table().get_table_item(raw_row_index,
                                                                                      raw_column_index))
        elif role == Qt.FontRole:
            # Font information for the data in this cell
            standard_font_size = self._preferences.get_standard_font_size()
            font = QFont()
            font.setPointSize(standard_font_size)
            result = font
        elif role == Qt.BackgroundRole:
            # What colour should this cell be?
            # Either red, if we've detected an error, or white
            cell_colour: QColor = SharedUtils.valid_or_error_field_color(self._cell_validity[row_index][column_index])
            result = QBrush(cell_colour)
        else:
            result = QVariant()
        return result

    # noinspection PyMethodOverriding
    def headerData(self, item_number, orientation, role):
        result = QVariant()
        if (role == Qt.DisplayRole) and (orientation == Qt.Horizontal):
            binnings_in_use: [BinningSpec] = self._data_model.get_enabled_binnings()
            assert (item_number >= 0) and item_number < len(binnings_in_use)
            binning: int = binnings_in_use[item_number].get_binning_value()
            return f" {binning} x {binning} "
        elif (role == Qt.DisplayRole) and (orientation == Qt.Vertical):
            if self._data_model.get_use_filter_wheel():
                filters_in_use: [FilterSpec] = self._data_model.get_enabled_filters()
                assert (item_number >= 0) and item_number < len(filters_in_use)
                fs: FilterSpec = filters_in_use[item_number]
                return f" {fs.get_slot_number()}: {fs.get_name()} "
            else:
                return "No filter wheel"
        elif (role == Qt.FontRole) and (orientation == Qt.Vertical):
            # Font information for the headers in the left margin
            standard_font_size = self._preferences.get_standard_font_size()
            font = QFont()
            font.setPointSize(standard_font_size)
            font.setBold(True)
            result = font
        elif (role == Qt.FontRole) and (orientation == Qt.Horizontal):
            # Font information for the headers above the top row
            standard_font_size = self._preferences.get_standard_font_size()
            font = QFont()
            font.setPointSize(standard_font_size)
            font.setBold(True)
            result = font
        return result

    # Return an indication that the cell is editable
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid:
            return Qt.ItemIsEnabled
        return QAbstractTableModel.flags(self, index) | Qt.ItemIsEditable

    # noinspection PyMethodOverriding
    def setData(self, index: QModelIndex, value: str, role: int):
        proposed_value = value.strip()
        if index.isValid() and (role == Qt.EditRole) and (len(proposed_value) > 0):
            # print(f"setData on {index.row()},{index.column()}: {proposed_value}")
            converted_value = Validators.valid_int_in_range(proposed_value, 0, 32767)
            validity_index_string = f"{index.row()},{index.column()}"
            raw_row_index: int = self._data_model.map_display_to_raw_filter_index(index.row())
            raw_column_index: int = self._data_model.map_display_to_raw_binning_index(index.column())
            if converted_value is None:
                # Invalid data.  Signal it by turning the cell red and tell
                # the user interface about this so the proceed button will be
                # disabled until it's fixed
                self.set_cell_validity(index, False)
                self._validity_reporting_method(validity_index_string, False)
                self._data_model.get_flat_frame_count_table().set_table_item(raw_row_index, raw_column_index,
                                                                             proposed_value)
            else:
                self._data_model.get_flat_frame_count_table().set_table_item(raw_row_index, raw_column_index,
                                                                             converted_value)
                self._dirty_reporting_method(True)
                # Turn of any error colour that might have been set for this cell
                self.set_cell_validity(index, True)
                self._validity_reporting_method(validity_index_string, True)
        return True

    # Added methods for the model

    def zero_all_cells(self):
        """Set all cells in the plan to zero"""
        self._data_model.get_flat_frame_count_table().set_all_to_zero()
        self.redraw_table()

    def fill_all_cells(self):
        """Set all cells in the plan according to the defaults"""
        self._data_model.get_flat_frame_count_table().set_all_to_default()
        self.redraw_table()

    def redraw_table(self):
        """ Force the table to redraw"""
        top_left: QModelIndex = self.index(0, 0)
        bottom_right: QModelIndex = self.index(self._data_model.count_enabled_binnings() - 1,
                                               self._data_model.count_enabled_filters() - 1)
        self.dataChanged.emit(top_left, bottom_right)

    def restore_defaults(self):
        self._data_model.get_flat_frame_count_table().reset_to_defaults()
        self.redraw_table()
