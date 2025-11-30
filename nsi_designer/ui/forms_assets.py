"""
forms_assets.py
---------------
This module contains the AssetsForm widget used in the NSI Script Designer UI.

Contents:
- AssetsForm: A QWidget that encapsulates asset selection fields such as install icon,
  uninstall icon, welcome bitmap, and license file. Provides helper methods to load
  values from the project model and update them back. Restores original UI behavior
  with choose/clear buttons and regen callback.
"""

from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QHBoxLayout, QPushButton
from ..model import ProjectModel
from .helpers import choose_asset

class AssetsForm(QWidget):
    """Form widget for selecting installer assets (icons, bitmaps, license file)."""
    def __init__(self, project: ProjectModel, regen_callback):
        super().__init__()
        self.project = project
        self.regen = regen_callback
        self.layout = QFormLayout(self)

        # Helper to create asset row with choose/clear buttons
        def mk_asset_row(line_edit: QLineEdit, title: str, filters: list, attr: str) -> QWidget:
            """Create asset row with choose/clear buttons wired to project + regen."""
            w = QWidget()
            hl = QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            line_edit.setReadOnly(True)
            btn_choose = QPushButton("Choose…")
            btn_clear = QPushButton("Clear")
            hl.addWidget(line_edit, 1)
            hl.addWidget(btn_choose)
            hl.addWidget(btn_clear)

            # Wire buttons
            btn_choose.clicked.connect(lambda: choose_asset(line_edit, title, filters, attr, self.project, self.regen))
            btn_clear.clicked.connect(lambda: (line_edit.setText(""), setattr(self.project, attr, ""), self.regen()))

            return w

        # Asset fields
        self.le_install_icon = QLineEdit(self.project.install_icon_path)
        self.le_uninstall_icon = QLineEdit(self.project.uninstall_icon_path)
        self.le_welcome_bmp = QLineEdit(self.project.welcome_bitmap_path)
        self.le_license = QLineEdit(self.project.license_file_path)

        # Create rows with proper wiring
        install_icon_row = mk_asset_row(self.le_install_icon, "Select icon", ["*.ico", "*.png", "*.jpg"], "install_icon_path")
        uninstall_icon_row = mk_asset_row(self.le_uninstall_icon, "Select uninstall icon", ["*.ico", "*.png", "*.jpg"], "uninstall_icon_path")
        welcome_row = mk_asset_row(self.le_welcome_bmp, "Select welcome image", ["*.bmp", "*.png", "*.jpg"], "welcome_bitmap_path")
        license_row = mk_asset_row(self.le_license, "Select license file", ["*.rtf"], "license_file_path")

        # Add to form
        self.layout.addRow("Install icon:", install_icon_row)
        self.layout.addRow("Uninstall icon:", uninstall_icon_row)
        self.layout.addRow("Welcome bitmap:", welcome_row)
        self.layout.addRow("License file:", license_row)

    def load_from_model(self, project: ProjectModel):
        """Load asset paths from project model into form."""
        self.project = project
        self.le_install_icon.setText(project.install_icon_path)
        self.le_uninstall_icon.setText(project.uninstall_icon_path)
        self.le_welcome_bmp.setText(project.welcome_bitmap_path)
        self.le_license.setText(project.license_file_path)

    def update_model(self):
        """Update project model from form fields."""
        self.project.install_icon_path = self.le_install_icon.text()
        self.project.uninstall_icon_path = self.le_uninstall_icon.text()
        self.project.welcome_bitmap_path = self.le_welcome_bmp.text()
        self.project.license_file_path = self.le_license.text()
