import sys

from PyQt5 import QtWidgets

from DataModel import DataModel
from MainWindow import MainWindow
from Preferences import Preferences

# Program to orchestrate TheSkyX, running as a server somewhere and listening on a known port,
# to collect a set of flat frames.

# Create QT-based application

app = QtWidgets.QApplication(sys.argv)
preferences: Preferences = Preferences()
preferences.set_defaults()
# Data model for this application.  If we were given a file name as an argument,
# load the data model from that file.  If not, create a new data model with default
# values as recorded in the application preferences

# sys.argv is a list. The first item is the application name, so there needs to be
# a second item for it to be a file name

if len(sys.argv) >= 2:
    file_name = sys.argv[1]
    data_model = DataModel.make_from_file_named(file_name)
    if data_model is None:
        print(f"Unable to read data model from file {file_name}")
        sys.exit(100)
else:
    data_model = DataModel.make_from_preferences(preferences)
    if data_model is None:
        print(f"Unable to create data model from preferences")
        sys.exit(101)

# Create main window displaying the data model, and run the event loop

window = MainWindow(data_model, preferences)
window.set_up_ui()
window.ui.show()

app.exec_()
