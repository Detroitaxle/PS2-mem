"""
Save Inspector Dialog
Shows detailed information about a PS2 save game
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt
from ps2_card_parser import PS2Save
from typing import Dict

class SaveInspectorDialog(QDialog):
    """Dialog to inspect save game details"""
    
    def __init__(self, save: PS2Save, info: Dict, parent=None):
        super().__init__(parent)
        self.save = save
        self.info = info
        self.setWindowTitle(f"Inspect Save: {save.directory_name}")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        
        # Basic Information Group
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout()
        
        basic_layout.addRow("Directory Name:", QLabel(self.info.get('directory_name', 'N/A')))
        basic_layout.addRow("Product Code:", QLabel(self.info.get('product_code', 'N/A')))
        basic_layout.addRow("Title:", QLabel(self.info.get('title', 'N/A')))
        basic_layout.addRow("Last Modified:", QLabel(self.info.get('last_modified', 'N/A')))
        basic_layout.addRow("Starting Cluster:", QLabel(str(self.info.get('cluster', 'N/A'))))
        basic_layout.addRow("Size (bytes):", QLabel(f"{self.info.get('size', 0):,}"))
        basic_layout.addRow("Raw Data Size:", QLabel(f"{self.info.get('raw_data_size', 0):,} bytes"))
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # File Information Group
        file_group = QGroupBox("File Information")
        file_layout = QVBoxLayout()
        
        files_text = QTextEdit()
        files_text.setReadOnly(True)
        files_text.setMaximumHeight(100)
        
        files = self.info.get('files', [])
        if files:
            files_text.setPlainText('\n'.join(files))
        else:
            files_text.setPlainText("No file information available")
        
        file_layout.addWidget(files_text)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Icon.sys Information
        if self.info.get('icon_sys'):
            icon_group = QGroupBox("Icon.sys Information")
            icon_layout = QFormLayout()
            
            icon_info = self.info['icon_sys']
            icon_layout.addRow("Found:", QLabel("Yes"))
            icon_layout.addRow("Title:", QLabel(icon_info.get('title', 'N/A')))
            
            icon_group.setLayout(icon_layout)
            layout.addWidget(icon_group)
        
        # Error Information (if any)
        if 'error' in self.info:
            error_group = QGroupBox("Error Information")
            error_layout = QVBoxLayout()
            
            error_text = QTextEdit()
            error_text.setReadOnly(True)
            error_text.setMaximumHeight(80)
            error_text.setPlainText(self.info['error'])
            error_text.setStyleSheet("color: #ff6b6b;")
            
            error_layout.addWidget(error_text)
            error_group.setLayout(error_layout)
            layout.addWidget(error_group)
        
        # Raw Data Information
        data_group = QGroupBox("Raw Data Information")
        data_layout = QFormLayout()
        
        data_layout.addRow("Estimated Clusters:", QLabel(str(self.info.get('estimated_files', 0))))
        data_layout.addRow("Cluster Size:", QLabel("1024 bytes"))
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

