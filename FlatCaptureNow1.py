import sys

from PyQt5 import QtWidgets

from DataModel import DataModel
from MainWindow import MainWindow
from Preferences import Preferences

app = QtWidgets.QApplication(sys.argv)
preferences: Preferences = Preferences()
preferences.set_defaults()
data_model = DataModel.make_from_preferences(preferences)
window = MainWindow(data_model, preferences)
window.ui.show()

app.exec_()

# TODO Allow quit while modal dialog open

# TODO Make filter wheel optional (they may have OSC or monochrome)
# TODO Filter Optional: reflect flag changes from main window back to data model
# TODO Filter Optional: change main window filter display based on use flag
# TODO Optional filter wheel: Main table: one row labelled "no filter wheel"
# TODO Optional filter wheel: FilterSpec records if no filter
# TODO Optional filter wheel: Session table: work item omits filter name
# TODO Optional filter wheel: Don't connect to filter wheel if not using
# TODO Optional filter wheel: Don't select filter if not using

# TODO Store successful exposure values for filter/bin combos in preferences (must be clearable)
# TODO Save and read session plan into file