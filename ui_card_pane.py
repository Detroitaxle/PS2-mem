"""
Memory Card Pane Widget - Enhanced for multi-card operations
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QListWidget, QListWidgetItem, QLabel, QFileDialog,
    QMessageBox, QMenu, QInputDialog, QProgressDialog
)
from PySide6.QtCore import Qt, Signal
from ps2_card_parser import PS2CardParser, PS2Save
from typing import Optional

try:
    from ui_save_inspector import SaveInspectorDialog
except ImportError:
    SaveInspectorDialog = None

class SaveListItem(QListWidgetItem):
    """Custom list item that holds a PS2Save object"""
    def __init__(self, save: PS2Save, parent=None):
        super().__init__(parent)
        self.save = save
        self.setText(f"{save.title}\n{save.product_code} | {save.last_modified.strftime('%Y-%m-%d %H:%M')}")
        self.setToolTip(f"Title: {save.title}\nProduct Code: {save.product_code}\nSize: {save.size} bytes")

class CardPane(QWidget):
    """Widget representing a single memory card pane"""
    
    # Signals
    save_selected = Signal(PS2Save)
    log_message = Signal(str, str)  # message, level (info/error)
    copy_save_requested = Signal(object, object, int)  # source_save, source_parser, destination_pane_index
    move_save_requested = Signal(object, object, int)  # source_save, source_parser, destination_pane_index
    
    def __init__(self, pane_number: int, parent=None):
        super().__init__(parent)
        self.pane_number = pane_number
        self.parser: Optional[PS2CardParser] = None
        self.file_path = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        self.file_label = QLabel(f"Memory Card {self.pane_number}: No file loaded")
        self.file_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        header_layout.addWidget(self.file_label)
        
        self.open_btn = QPushButton("Open...")
        self.open_btn.clicked.connect(self.open_file)
        header_layout.addWidget(self.open_btn)
        
        self.create_btn = QPushButton("Create New...")
        self.create_btn.clicked.connect(self.create_new_card)
        header_layout.addWidget(self.create_btn)
        
        self.format_btn = QPushButton("Format")
        self.format_btn.clicked.connect(self.format_card)
        self.format_btn.setEnabled(False)
        header_layout.addWidget(self.format_btn)
        
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self.save_changes)
        self.save_btn.setEnabled(False)
        header_layout.addWidget(self.save_btn)
        
        layout.addLayout(header_layout)
        
        # Save list with drag and drop
        self.save_list = QListWidget()
        self.save_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.save_list.customContextMenuRequested.connect(self.show_context_menu)
        self.save_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        # Enable drag and drop
        self.save_list.setDragEnabled(True)
        self.save_list.setAcceptDrops(True)
        self.save_list.setDropIndicatorShown(True)
        self.save_list.setDefaultDropAction(Qt.MoveAction)
        
        layout.addWidget(self.save_list)
        
        # Status label
        self.status_label = QLabel("No saves loaded")
        self.status_label.setStyleSheet("color: #888888; font-size: 9pt;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def open_file(self):
        """Open a memory card file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Open Memory Card {self.pane_number}",
            "",
            "PS2 Memory Cards (*.ps2 *.bin);;All Files (*)"
        )
        
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path: str):
        """Load a memory card file"""
        try:
            self.parser = PS2CardParser(file_path)
            self.file_path = file_path
            filename = file_path.split('/')[-1].split('\\')[-1]
            self.file_label.setText(f"Memory Card {self.pane_number}: {filename}")
            self.format_btn.setEnabled(True)
            self.refresh_saves()
            self.log_message.emit(f"Loaded memory card {self.pane_number}: {filename}", "info")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load memory card:\n{str(e)}")
            self.log_message.emit(f"Error loading {file_path}: {str(e)}", "error")
    
    def refresh_saves(self):
        """Refresh the save list"""
        if not self.parser:
            return
        
        try:
            self.save_list.clear()
            self.status_label.setText("Loading saves...")
            
            # Process events to keep UI responsive
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
            
            saves = self.parser.list_saves()
            
            for save in saves:
                item = SaveListItem(save)
                self.save_list.addItem(item)
            
            self.status_label.setText(f"{len(saves)} save(s) found")
            self.save_btn.setEnabled(self.parser.modified)
        except Exception as e:
            self.status_label.setText(f"Error loading saves: {str(e)}")
            self.log_message.emit(f"Error refreshing saves: {str(e)}", "error")
    
    def show_context_menu(self, position):
        """Show context menu for save item"""
        item = self.save_list.itemAt(position)
        if not item or not isinstance(item, SaveListItem):
            return
        
        save = item.save
        menu = QMenu(self)
        
        # Copy/Move to other cards
        copy_menu = menu.addMenu("Copy to Card...")
        move_menu = menu.addMenu("Move to Card...")
        
        # Get parent window to find other panes
        parent_window = self.parent()
        while parent_window and not hasattr(parent_window, 'panes'):
            parent_window = parent_window.parent()
        
        if parent_window and hasattr(parent_window, 'panes'):
            for i, pane in enumerate(parent_window.panes):
                if pane != self and pane.parser:
                    pane_name = f"Card {pane.pane_number}"
                    copy_action = copy_menu.addAction(pane_name)
                    move_action = move_menu.addAction(pane_name)
                    copy_action.triggered.connect(
                        lambda checked, idx=i: self.copy_to_card(idx)
                    )
                    move_action.triggered.connect(
                        lambda checked, idx=i: self.move_to_card(idx)
                    )
        
        menu.addSeparator()
        inspect_action = menu.addAction("Inspect Save...")
        menu.addSeparator()
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")
        menu.addSeparator()
        export_psu_action = menu.addAction("Export as .psu")
        export_max_action = menu.addAction("Export as .max")
        
        action = menu.exec_(self.save_list.mapToGlobal(position))
        
        if action == inspect_action:
            self.inspect_save(save)
        elif action == rename_action:
            self.rename_save(save)
        elif action == delete_action:
            self.delete_save(save)
        elif action == export_psu_action:
            self.export_save(save, 'psu')
        elif action == export_max_action:
            self.export_save(save, 'max')
    
    def copy_to_card(self, destination_pane_index: int):
        """Copy selected save to another card"""
        item = self.save_list.currentItem()
        if not item or not isinstance(item, SaveListItem):
            return
        
        if not self.parser:
            return
        
        # Get destination pane
        parent_window = self.parent()
        while parent_window and not hasattr(parent_window, 'panes'):
            parent_window = parent_window.parent()
        
        if not parent_window or not hasattr(parent_window, 'panes'):
            return
        
        if destination_pane_index >= len(parent_window.panes):
            return
        
        dest_pane = parent_window.panes[destination_pane_index]
        if not dest_pane.parser:
            QMessageBox.warning(self, "Error", f"Memory Card {dest_pane.pane_number} is not loaded")
            return
        
        self.copy_save_requested.emit(item.save, self.parser, destination_pane_index)
    
    def move_to_card(self, destination_pane_index: int):
        """Move selected save to another card"""
        item = self.save_list.currentItem()
        if not item or not isinstance(item, SaveListItem):
            return
        
        if not self.parser:
            return
        
        # Get destination pane
        parent_window = self.parent()
        while parent_window and not hasattr(parent_window, 'panes'):
            parent_window = parent_window.parent()
        
        if not parent_window or not hasattr(parent_window, 'panes'):
            return
        
        if destination_pane_index >= len(parent_window.panes):
            return
        
        dest_pane = parent_window.panes[destination_pane_index]
        if not dest_pane.parser:
            QMessageBox.warning(self, "Error", f"Memory Card {dest_pane.pane_number} is not loaded")
            return
        
        reply = QMessageBox.question(
            self,
            "Move Save",
            f"Move '{item.save.title}' from Card {self.pane_number} to Card {dest_pane.pane_number}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.move_save_requested.emit(item.save, self.parser, destination_pane_index)
    
    def rename_save(self, save: PS2Save):
        """Rename a save"""
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Save",
            f"Enter new name for '{save.title}':",
            text=save.directory_name
        )
        
        if ok and new_name:
            if self.parser.rename_save(save, new_name):
                self.refresh_saves()
                self.log_message.emit(f"Renamed save: {save.title} -> {new_name}", "info")
            else:
                QMessageBox.warning(self, "Error", "Failed to rename save")
                self.log_message.emit(f"Failed to rename save: {save.title}", "error")
    
    def delete_save(self, save: PS2Save):
        """Delete a save"""
        reply = QMessageBox.question(
            self,
            "Delete Save",
            f"Are you sure you want to delete '{save.title}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.parser.delete_save(save):
                self.refresh_saves()
                self.log_message.emit(f"Deleted save: {save.title}", "info")
            else:
                QMessageBox.warning(self, "Error", "Failed to delete save")
                self.log_message.emit(f"Failed to delete save: {save.title}", "error")
    
    def export_save(self, save: PS2Save, format: str):
        """Export a save"""
        ext = '.psu' if format == 'psu' else '.max'
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export Save as {format.upper()}",
            f"{save.title}{ext}",
            f"{format.upper()} Files (*{ext});;All Files (*)"
        )
        
        if file_path:
            if self.parser.export_save(save, file_path, format):
                self.log_message.emit(f"Exported save: {save.title} to {file_path}", "info")
            else:
                QMessageBox.warning(self, "Error", "Failed to export save")
                self.log_message.emit(f"Failed to export save: {save.title}", "error")
    
    def on_item_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on save item"""
        if isinstance(item, SaveListItem):
            self.save_selected.emit(item.save)
    
    def save_changes(self):
        """Save changes to file"""
        if not self.parser:
            return
        
        if self.parser.save():
            self.log_message.emit(f"Saved changes to {self.file_path}", "info")
            self.save_btn.setEnabled(False)
        else:
            QMessageBox.critical(self, "Error", "Failed to save changes")
            self.log_message.emit(f"Failed to save changes to {self.file_path}", "error")
    
    def copy_save_to(self, source_save: PS2Save, source_parser: PS2CardParser) -> bool:
        """Copy a save from another pane"""
        if not self.parser:
            return False
        
        try:
            # Show progress dialog
            progress = QProgressDialog(f"Copying '{source_save.title}'...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setValue(0)
            progress.show()
            
            def update_progress(value, message):
                progress.setValue(int(value))
                progress.setLabelText(message)
                if progress.wasCanceled():
                    return False
                return True
            
            result = source_parser.copy_save_to(self.parser, source_save, update_progress)
            
            progress.close()
            
            if result:
                self.refresh_saves()
                save_title = source_save.title if source_save.title else source_save.directory_name
                self.log_message.emit(
                    f"Copied '{save_title}' from Card {source_parser.file_path} to Card {self.pane_number}",
                    "info"
                )
                return True
            else:
                save_title = source_save.title if source_save.title else source_save.directory_name
                error_msg = f"Failed to copy save '{save_title}'. Possible reasons: no free space, invalid save data, or card corruption."
                QMessageBox.warning(self, "Copy Failed", error_msg)
                self.log_message.emit(f"Failed to copy save: {save_title}", "error")
                return False
                
        except Exception as e:
            save_title = source_save.title if source_save.title else source_save.directory_name
            error_msg = f"Error copying save '{save_title}': {str(e)}"
            QMessageBox.critical(self, "Error", error_msg)
            self.log_message.emit(f"Error copying save: {error_msg}", "error")
            return False
    
    def move_save_to(self, source_save: PS2Save, source_parser: PS2CardParser) -> bool:
        """Move a save from another pane (copy then delete)"""
        if self.copy_save_to(source_save, source_parser):
            # Delete from source
            if source_parser.delete_save(source_save):
                # Refresh source pane
                parent_window = self.parent()
                while parent_window and not hasattr(parent_window, 'panes'):
                    parent_window = parent_window.parent()
                
                if parent_window and hasattr(parent_window, 'panes'):
                    for pane in parent_window.panes:
                        if pane.parser == source_parser:
                            pane.refresh_saves()
                            break
                
                self.log_message.emit(
                    f"Moved '{source_save.title}' from Card {source_parser.file_path} to Card {self.pane_number}",
                    "info"
                )
                return True
        
        return False
    
    def create_new_card(self):
        """Create a new memory card file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Create New Memory Card {self.pane_number}",
            "",
            "PS2 Memory Cards (*.ps2 *.bin);;All Files (*)"
        )
        
        if file_path:
            # Ask for size
            from PySide6.QtWidgets import QInputDialog
            size, ok = QInputDialog.getItem(
                self,
                "Card Size",
                "Select memory card size:",
                ["8 MB", "16 MB", "32 MB"],
                0,
                False
            )
            
            if ok:
                size_mb = int(size.split()[0])
                if PS2CardParser.create_new_card(file_path, size_mb):
                    self.load_file(file_path)
                    self.log_message.emit(f"Created new {size_mb}MB memory card: {file_path}", "info")
                else:
                    QMessageBox.critical(self, "Error", "Failed to create memory card")
                    self.log_message.emit(f"Failed to create memory card: {file_path}", "error")
    
    def format_card(self):
        """Format the current memory card"""
        if not self.parser:
            return
        
        reply = QMessageBox.question(
            self,
            "Format Memory Card",
            f"Are you sure you want to format this memory card?\n\n"
            f"This will DELETE ALL SAVES and cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.parser.format_card():
                self.refresh_saves()
                self.log_message.emit(f"Formatted memory card {self.pane_number}", "info")
                QMessageBox.information(self, "Success", "Memory card formatted successfully")
            else:
                QMessageBox.critical(self, "Error", "Failed to format memory card")
                self.log_message.emit(f"Failed to format memory card {self.pane_number}", "error")
    
    def inspect_save(self, save: PS2Save):
        """Inspect a save and show detailed information"""
        if not self.parser:
            return
        
        if SaveInspectorDialog is None:
            QMessageBox.warning(self, "Error", "Save inspector dialog not available")
            return
        
        try:
            info = self.parser.inspect_save(save)
            dialog = SaveInspectorDialog(save, info, self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to inspect save:\n{str(e)}")
            self.log_message.emit(f"Error inspecting save: {str(e)}", "error")

