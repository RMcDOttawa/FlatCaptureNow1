from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant, QPoint

from BinningSpec import BinningSpec
from DataModel import DataModel
from FilterSpec import FilterSpec
from Validators import Validators


class SessionPlanTableModel(QAbstractTableModel):

    def __init__(self, data_model: DataModel, dirty_reporting_method):
        QAbstractTableModel.__init__(self)
        self._dirty_reporting_method = dirty_reporting_method
        self._data_model = data_model

    # Methods required by the parent abstract data model

    def rowCount(self, parent_model_index: QModelIndex) -> int:
        # print(f"rowCount({parent_model_index}")
        if self._data_model.get_use_filter_wheel():
            num_rows = self._data_model.count_enabled_filters()
        else:
            num_rows = 1
        return num_rows

    def columnCount(self, parent_model_index: QModelIndex) -> int:
        # print(f"columnCount({parent_model_index}")
        return self._data_model.count_enabled_binnings()
        # return FrameSet.NUMBER_OF_DISPLAY_FIELDS

    # Get data element to display in a table cell
    def data(self, index: QModelIndex, role: Qt.DisplayRole):
        row_index: int = index.row()
        column_index: int = index.column()
        if role == Qt.DisplayRole:
            # print(f"Get cell data for ({row_index},{column_index})")
            # We need to map these coordinates to the big table, since not all
            # filters and binnings here might be in use.
            raw_row_index: int = self._data_model.map_display_to_raw_filter_index(row_index)
            raw_column_index: int = self._data_model.map_display_to_raw_binning_index(column_index)
            # print(f"   Raw indices ({raw_row_index},{raw_column_index})")
            result = str(self._data_model.get_flat_frame_count_table().get_table_item(raw_row_index,
                                                                                      raw_column_index))
        else:
            result = QVariant()
        return result

    def headerData(self, item_number, orientation, role):
        # print(f"headerData({item_number}, {orientation}, {role})")
        result = QVariant()
        if (role == Qt.DisplayRole) and (orientation == Qt.Horizontal):
            binnings_in_use: [BinningSpec] = self._data_model.get_enabled_binnings()
            assert (item_number >= 0) and item_number < len(binnings_in_use)
            binning: int = binnings_in_use[item_number].get_binning_value()
            return f"{binning} x {binning}"
        elif (role == Qt.DisplayRole) and (orientation == Qt.Vertical):
            if self._data_model.get_use_filter_wheel():
                filters_in_use: [FilterSpec] = self._data_model.get_enabled_filters()
                assert (item_number >= 0) and item_number < len(filters_in_use)
                fs: FilterSpec = filters_in_use[item_number]
                return f"{fs.get_slot_number()}: {fs.get_name()}"
            else:
                return "No filter wheel"
        return result

    # Return an indication that the cell is editable
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        # print(f"SessionPlanTableModel/flags({index.row()},{index.column()})")
        if not index.isValid:
            return Qt.ItemIsEnabled
        return QAbstractTableModel.flags(self, index) | Qt.ItemIsEditable

    def setData(self, index: QModelIndex, value: str, role: int):
        # print(f"SessionPlanTableModel/setData: ({index.row()},{index.column()}), {value}, {role}")
        result: bool = False
        if index.isValid() and role == Qt.EditRole:
            converted_value: int = Validators.valid_int_in_range(value, 0, 32767)
            if converted_value is not None:
                raw_row_index: int = self._data_model.map_display_to_raw_filter_index(index.row())
                raw_column_index: int = self._data_model.map_display_to_raw_binning_index(index.column())
                self._data_model.get_flat_frame_count_table().set_table_item(raw_row_index, raw_column_index,
                                                                             converted_value)
                self._dirty_reporting_method(True)
                result = True
        return result

    # Added methods for the model

    def zero_all_cells(self):
        """Set all cells in the plan to zero"""
        # print("zero_all_cells")
        self._data_model.get_flat_frame_count_table().set_all_to_zero()
        self.redraw_table()

    def fill_all_cells(self):
        """Set all cells in the plan according to the defaults"""
        # print("zero_all_cells")
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
