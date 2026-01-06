"""
Main Window for PS2 Save Manager - Enhanced for multi-card operations
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QSplitter, QMenuBar, QMenu, QStatusBar,
    QToolBar, QMessageBox
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QKeySequence, QAction
from ui_card_pane import CardPane
from styles import DARK_THEME

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PS2 Save Manager")
        self.setGeometry(100, 100, 1400, 800)
        self.settings = QSettings("PS2Tools", "PS2SaveManager")
        self.init_ui()
        self.apply_theme()
        self.connect_signals()
        self.restore_geometry()
    
    def init_ui(self):
        """Initialize the UI"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Create splitter for panes
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Create card panes (default to 2, but can expand to 4)
        self.panes = []
        for i in range(2):  # Start with 2 panes for 2-card operations
            pane = CardPane(i + 1)
            self.panes.append(pane)
            self.splitter.addWidget(pane)
        
        # Set equal sizes for 2 cards
        self.splitter.setSizes([700, 700])
        layout.addWidget(self.splitter)
        
        # Log window
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setPlaceholderText("Operation log will appear here...")
        layout.addWidget(self.log_text)
        
        # Menu bar
        self.create_menu_bar()
        
        # Toolbar
        self.create_toolbar()
        
        # Status bar
        self.statusBar().showMessage("Ready - Open 2 memory cards to start")
        
        # Initial log message
        self.log_message("PS2 Save Manager started", "info")
        self.log_message("Tip: Open 2 memory cards to easily copy/move saves between them", "info")
    
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_card1_action = QAction("Open Card 1...", self)
        open_card1_action.setShortcut(QKeySequence("Ctrl+1"))
        open_card1_action.triggered.connect(lambda: self.panes[0].open_file())
        file_menu.addAction(open_card1_action)
        
        open_card2_action = QAction("Open Card 2...", self)
        open_card2_action.setShortcut(QKeySequence("Ctrl+2"))
        open_card2_action.triggered.connect(lambda: self.panes[1].open_file())
        file_menu.addAction(open_card2_action)
        
        file_menu.addSeparator()
        
        create_card1_action = QAction("Create New Card 1...", self)
        create_card1_action.triggered.connect(lambda: self.panes[0].create_new_card())
        file_menu.addAction(create_card1_action)
        
        create_card2_action = QAction("Create New Card 2...", self)
        create_card2_action.triggered.connect(lambda: self.panes[1].create_new_card())
        file_menu.addAction(create_card2_action)
        
        file_menu.addSeparator()
        
        save_all_action = QAction("Save All Changes", self)
        save_all_action.setShortcut(QKeySequence("Ctrl+S"))
        save_all_action.triggered.connect(self.save_all_cards)
        file_menu.addAction(save_all_action)
        
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        add_pane_action = QAction("Add Pane (3)", self)
        add_pane_action.triggered.connect(lambda: self.add_pane(3))
        view_menu.addAction(add_pane_action)
        
        add_pane_action = QAction("Add Pane (4)", self)
        add_pane_action.triggered.connect(lambda: self.add_pane(4))
        view_menu.addAction(add_pane_action)
        
        view_menu.addSeparator()
        
        reset_layout_action = QAction("Reset Layout", self)
        reset_layout_action.triggered.connect(self.reset_layout)
        view_menu.addAction(reset_layout_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self.show_about)
        help_menu.addAction("Keyboard Shortcuts", self.show_shortcuts)
    
    def create_toolbar(self):
        """Create toolbar"""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        # Quick open buttons
        open_card1_btn = toolbar.addAction("Open Card 1")
        open_card1_btn.triggered.connect(lambda: self.panes[0].open_file())
        
        open_card2_btn = toolbar.addAction("Open Card 2")
        open_card2_btn.triggered.connect(lambda: self.panes[1].open_file())
        
        toolbar.addSeparator()
        
        save_all_btn = toolbar.addAction("Save All")
        save_all_btn.triggered.connect(self.save_all_cards)
    
    def connect_signals(self):
        """Connect signals between panes"""
        for pane in self.panes:
            # Connect copy/move requests
            pane.copy_save_requested.connect(self.handle_copy_save)
            pane.move_save_requested.connect(self.handle_move_save)
            pane.log_message.connect(self.log_message)
    
    def handle_copy_save(self, source_save, source_parser, destination_pane_index):
        """Handle copy save request"""
        if destination_pane_index >= len(self.panes):
            return
        
        dest_pane = self.panes[destination_pane_index]
        dest_pane.copy_save_to(source_save, source_parser)
    
    def handle_move_save(self, source_save, source_parser, destination_pane_index):
        """Handle move save request"""
        if destination_pane_index >= len(self.panes):
            return
        
        dest_pane = self.panes[destination_pane_index]
        dest_pane.move_save_to(source_save, source_parser)
    
    def add_pane(self, pane_number: int):
        """Add an additional pane"""
        if len(self.panes) >= 4:
            QMessageBox.information(self, "Limit Reached", "Maximum of 4 panes supported")
            return
        
        if pane_number <= len(self.panes):
            return
        
        pane = CardPane(pane_number)
        pane.log_message.connect(self.log_message)
        pane.copy_save_requested.connect(self.handle_copy_save)
        pane.move_save_requested.connect(self.handle_move_save)
        self.panes.append(pane)
        self.splitter.addWidget(pane)
        
        # Adjust sizes
        total_panes = len(self.panes)
        equal_size = 1400 // total_panes
        self.splitter.setSizes([equal_size] * total_panes)
        
        self.log_message(f"Added pane {pane_number}", "info")
    
    def reset_layout(self):
        """Reset pane layout to equal sizes"""
        total_panes = len(self.panes)
        equal_size = 1400 // total_panes
        self.splitter.setSizes([equal_size] * total_panes)
    
    def save_all_cards(self):
        """Save all modified cards"""
        saved_count = 0
        for i, pane in enumerate(self.panes):
            if pane.parser and pane.parser.modified:
                if pane.parser.save():
                    saved_count += 1
                    pane.save_btn.setEnabled(False)
                    self.log_message(f"Saved Card {i+1}", "info")
        
        if saved_count > 0:
            self.log_message(f"Saved {saved_count} card(s)", "info")
        else:
            self.log_message("No changes to save", "info")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About PS2 Save Manager",
            "PS2 Save Manager v1.0\n\n"
            "A tool for managing PlayStation 2 memory card files.\n"
            "Supports .ps2 and .bin formats.\n\n"
            "Features:\n"
            "• Open up to 4 memory cards simultaneously\n"
            "• Copy/Move saves between cards\n"
            "• Rename, delete, and export saves\n"
            "• Drag and drop support"
        )
    
    def show_shortcuts(self):
        """Show keyboard shortcuts"""
        QMessageBox.information(
            self,
            "Keyboard Shortcuts",
            "Keyboard Shortcuts:\n\n"
            "Ctrl+1 - Open Card 1\n"
            "Ctrl+2 - Open Card 2\n"
            "Ctrl+S - Save All Changes\n\n"
            "Right-click on a save for context menu:\n"
            "• Copy to Card...\n"
            "• Move to Card...\n"
            "• Rename\n"
            "• Delete\n"
            "• Export"
        )
    
    def log_message(self, message: str, level: str = "info"):
        """Log a message"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "error":
            color = "#ff6b6b"
            prefix = "[ERROR]"
        elif level == "warning":
            color = "#ffa500"
            prefix = "[WARN]"
        else:
            color = "#4ecdc4"
            prefix = "[INFO]"
        
        formatted_message = f'<span style="color: {color};">[{timestamp}] {prefix}</span> {message}'
        self.log_text.append(formatted_message)
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Update status bar
        if level == "error":
            self.statusBar().showMessage(message, 5000)
    
    def apply_theme(self):
        """Apply dark theme"""
        self.setStyleSheet(DARK_THEME)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Check for unsaved changes
        has_unsaved = any(pane.parser and pane.parser.modified for pane in self.panes)
        
        if has_unsaved:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Save before closing?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Yes:
                self.save_all_cards()
                event.accept()
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
            else:
                event.accept()
        else:
            event.accept()
        
        # Save window geometry
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
    
    def restore_geometry(self):
        """Restore window geometry"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

