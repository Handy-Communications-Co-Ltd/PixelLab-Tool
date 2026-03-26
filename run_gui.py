"""Entry point for PyInstaller exe build."""
import warnings
warnings.filterwarnings("ignore", message="Unable to find acceptable character detection")

import sys
import os

# Ensure the package directory is on the path
if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
    sys.path.insert(0, base_dir)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, base_dir)

from pixellab_tool.gui import main

if __name__ == "__main__":
    main()
