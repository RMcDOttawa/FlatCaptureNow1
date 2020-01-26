#!/bin/bash -x
rm FlatCaptureNow1.spec
rm -rf dist
rm -rf build
pyinstaller FlatCaptureNow1.py \
		    --onefile \
		    --windowed \
			--noconfirm \
			--add-data MainWindow.ui:. \
			--add-data PrefsWindow.ui:. \
			--add-data SessionConsole.ui:./
