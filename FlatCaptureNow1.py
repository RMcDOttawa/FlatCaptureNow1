import sys

from PyQt5 import QtWidgets

from MainWindow import MainWindow

app = QtWidgets.QApplication(sys.argv)

window = MainWindow()
window.ui.show()

app.exec_()

