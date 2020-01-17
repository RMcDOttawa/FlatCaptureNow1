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
