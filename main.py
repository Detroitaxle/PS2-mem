"""
PS2 Save Manager - Main Entry Point
"""

import sys
from PySide6.QtWidgets import QApplication
from ui_main_window import MainWindow

def main():
    """Main function"""
    app = QApplication(sys.argv)
    app.setApplicationName("PS2 Save Manager")
    app.setOrganizationName("PS2 Tools")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

