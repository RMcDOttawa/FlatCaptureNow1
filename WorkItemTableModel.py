from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant

from DataModel import DataModel
from WorkItem import WorkItem


class WorkItemTableModel(QAbstractTableModel):
    NUMBER_OF_COLUMNS = 4
    HEADINGS: [str] = ("#", "Filter", "Bin", "Done")
    FRAMES_ITEM_INDEX = 0
    FILTER_ITEM_INDEX = 1
    BINNING_ITEM_INDEX = 2
    COMPLETED_ITEM_INDEX = 3

    def __init__(self, data_model: DataModel, work_items: [WorkItem]):
        QAbstractTableModel.__init__(self)
        self._work_items = work_items
        self._data_model = data_model

    # Methods required by the parent abstract data model

    # noinspection PyMethodOverriding
    def rowCount(self, parent_model_index: QModelIndex) -> int:
        return len(self._work_items)

    # noinspection PyMethodOverriding
    def columnCount(self, parent_model_index: QModelIndex) -> int:
        return WorkItemTableModel.NUMBER_OF_COLUMNS

    # Get data element to display in a table cell
    # noinspection PyMethodOverriding
    def data(self, index: QModelIndex, role: Qt.DisplayRole):
        row_index: int = index.row()
        column_index: int = index.column()
        if role == Qt.DisplayRole:
            assert (row_index >= 0) and (row_index < len(self._work_items))
            work_item: WorkItem = self._work_items[row_index]
            if column_index == WorkItemTableModel.FRAMES_ITEM_INDEX:
                return str(work_item.get_number_of_frames())
            elif column_index == WorkItemTableModel.FILTER_ITEM_INDEX:
                return work_item.hybrid_filter_name() if self._data_model.get_use_filter_wheel() else "No filter"
            elif column_index == WorkItemTableModel.BINNING_ITEM_INDEX:
                return f"{work_item.get_binning()} x {work_item.get_binning()}"
            else:
                assert column_index == WorkItemTableModel.COMPLETED_ITEM_INDEX
                return str(work_item.get_num_completed())
        else:
            result = QVariant()
        return result

    # noinspection PyMethodOverriding
    def headerData(self, item_number, orientation, role):
        result = QVariant()
        if (role == Qt.DisplayRole) and (orientation == Qt.Horizontal):
            assert (item_number >= 0) and (item_number < len(WorkItemTableModel.HEADINGS))
            result = WorkItemTableModel.HEADINGS[item_number]
        return result

        # self._work_items_table_model.set_frames_complete(row_index, frames_complete)

    # A frame has been taken.  Update the work item displayed in the given row index
    # with the new # complete
    def set_frames_complete(self, row_index: int, frames_complete: int):
        work_item: WorkItem = self._work_items[row_index]
        work_item.set_num_completed(frames_complete)
        # Ask this cell to redraw
        top_left: QModelIndex = self.index(row_index, self.COMPLETED_ITEM_INDEX)
        bottom_right: QModelIndex = self.index(row_index, self.COMPLETED_ITEM_INDEX)
        self.dataChanged.emit(top_left, bottom_right)
