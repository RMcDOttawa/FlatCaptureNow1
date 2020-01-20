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

# TODO Store successful exposure values for filter/bin combos in preferences (must be clearable)
# TODO Save and read session plan into file