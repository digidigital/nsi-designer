"""
forms_presets.py
----------------
PresetsForm widget for the NSI Script Designer UI.

Contents:
- PresetsForm: Encapsulates selection of install location and auto-adjusts
  the Execution Level and Scope fields. Triggers regeneration on change.
"""

from PySide6.QtWidgets import QWidget, QFormLayout, QComboBox
from .helpers import AutoLabel
from ..model import ProjectModel

class PresetsForm(QWidget):
    """Form widget for install location, execution level, and scope."""
    def __init__(self, project: ProjectModel, regen_callback):
        super().__init__()
        self.project = project
        self.regen = regen_callback
        self.layout = QFormLayout(self)

        self.cb_install_loc = QComboBox()
        self.cb_install_loc.addItems([
            "64-bit (ProgramFiles64)",
            "32-bit (ProgramFiles32)",
            "Per-user (AppData)"
        ])

        self.cb_exec_level = AutoLabel(self.project.exec_level)
        self.cb_scope = AutoLabel(self.project.scope)

        self.layout.addRow("Install location:", self.cb_install_loc)
        self.layout.addRow("Execution level:", self.cb_exec_level)
        self.layout.addRow("Scope:", self.cb_scope)

        self.cb_install_loc.currentTextChanged.connect(self._on_install_loc_changed)

    def _on_install_loc_changed(self, text: str):
        """Update install location preset and auto-adjust Execution Level/Scope labels."""
        if "Per-user" in text:
            self.project.install_dir_preset = "Per-user"
            self.cb_exec_level.setText("user")
            self.cb_scope.setText("Per-user")
            self.project.exec_level = "user"
            self.project.scope = "Per-user"
        else:
            preset = "64-bit" if "64-bit" in text else "32-bit"
            self.project.install_dir_preset = preset
            self.cb_exec_level.setText("admin")
            self.cb_scope.setText("System-wide")
            self.project.exec_level = "admin"
            self.project.scope = "System-wide"
        self.regen()

    def load_from_model(self, project: ProjectModel):
        """Load values from project model into the form."""
        self.project = project
        self.cb_install_loc.setCurrentIndex(
            0 if project.install_dir_preset == "64-bit" else
            1 if project.install_dir_preset == "32-bit" else 2
        )
        self.cb_exec_level.setText(project.exec_level)
        self.cb_scope.setText(project.scope)

    def update_model(self):
        """Update project model from form fields."""
        text = self.cb_install_loc.currentText()
        if "Per-user" in text:
            self.project.install_dir_preset = "Per-user"
            self.project.exec_level = "user"
            self.project.scope = "Per-user"
        else:
            preset = "64-bit" if "64-bit" in text else "32-bit"
            self.project.install_dir_preset = preset
            self.project.exec_level = "admin"
            self.project.scope = "System-wide"
