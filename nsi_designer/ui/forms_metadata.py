"""
forms_metadata.py
-----------------
MetadataForm widget for the NSI Script Designer UI.

Contents:
- MetadataForm: Encapsulates metadata fields (app name, version, company, caption,
  branding text, URLs, comments) and the executable file row with choose/clear buttons.
  All fields are wired to update the model and trigger regeneration on change.
"""

from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton
from ..model import ProjectModel
from .helpers import choose_file, calc_estimated_size_kb
import os

class MetadataForm(QWidget):
    """Form widget for editing project metadata fields, including executable file row."""
    def __init__(self, project: ProjectModel, regen_callback):
        super().__init__()
        self.project = project
        self.regen = regen_callback
        self.layout = QGridLayout(self)

        # Application name + Version
        lbl_app = QLabel("Application name:")
        self.le_appname = QLineEdit(self.project.app_name)
        self.le_appname.textEdited.connect(self._on_app_name_changed)
        lbl_ver = QLabel("Version:")
        self.le_version = QLineEdit(self.project.version)
        self.le_version.textEdited.connect(self._on_version_changed)
        self.layout.addWidget(lbl_app, 0, 0)
        self.layout.addWidget(self.le_appname, 0, 1)
        self.layout.addWidget(lbl_ver, 0, 2)
        self.layout.addWidget(self.le_version, 0, 3)

        # Company name
        lbl_company = QLabel("Company name:")
        self.le_company = QLineEdit(self.project.company_name)
        self.le_company.textEdited.connect(self._on_company_changed)
        self.layout.addWidget(lbl_company, 1, 0)
        self.layout.addWidget(self.le_company, 1, 1, 1, 3)

        # Caption
        lbl_caption = QLabel("Caption:")
        self.le_caption = QLineEdit(self.project.caption)
        self.le_caption.textEdited.connect(self._on_caption_changed)
        self.layout.addWidget(lbl_caption, 2, 0)
        self.layout.addWidget(self.le_caption, 2, 1, 1, 3)

        # Branding text
        lbl_branding = QLabel("Branding text:")
        self.le_branding = QLineEdit(self.project.branding_text)
        self.le_branding.textEdited.connect(self._on_branding_changed)
        self.layout.addWidget(lbl_branding, 3, 0)
        self.layout.addWidget(self.le_branding, 3, 1, 1, 3)

        # About URL + Help URL
        lbl_about = QLabel("About URL:")
        self.le_about = QLineEdit(self.project.about_url)
        self.le_about.textEdited.connect(self._on_about_changed)
        lbl_help = QLabel("Help URL:")
        self.le_help = QLineEdit(self.project.help_url)
        self.le_help.textEdited.connect(self._on_help_changed)
        self.layout.addWidget(lbl_about, 4, 0)
        self.layout.addWidget(self.le_about, 4, 1)
        self.layout.addWidget(lbl_help, 4, 2)
        self.layout.addWidget(self.le_help, 4, 3)

        # Update URL + Contact
        lbl_update = QLabel("Update URL:")
        self.le_update = QLineEdit(self.project.update_url)
        self.le_update.textEdited.connect(self._on_update_changed)
        lbl_contact = QLabel("Email:")
        self.le_contact = QLineEdit(self.project.contact)
        self.le_contact.textEdited.connect(self._on_contact_changed)
        self.layout.addWidget(lbl_update, 5, 0)
        self.layout.addWidget(self.le_update, 5, 1)
        self.layout.addWidget(lbl_contact, 5, 2)
        self.layout.addWidget(self.le_contact, 5, 3)

        # Comments
        lbl_comments = QLabel("Comments:")
        self.le_comments = QLineEdit(self.project.comments)
        self.le_comments.textEdited.connect(self._on_comments_changed)
        self.layout.addWidget(lbl_comments, 6, 0)
        self.layout.addWidget(self.le_comments, 6, 1, 1, 3)

        # Executable file row with choose/clear buttons
        lbl_exe = QLabel("Executable file:")
        exe_row = QWidget()
        exe_layout = QHBoxLayout(exe_row)
        exe_layout.setContentsMargins(0, 0, 0, 0)
        self.le_exe = QLineEdit(self.project.exe_path)
        self.le_exe.textChanged.connect(self._on_exe_changed)
        btn_exe_choose = QPushButton("Choose…")
        btn_exe_clear = QPushButton("Clear")
        btn_exe_choose.clicked.connect(
            lambda: choose_file(self.le_exe, "Select executable", ["*.exe"], "exe_path", self.project, self.regen)
        )
        btn_exe_clear.clicked.connect(lambda: (self.le_exe.setText(""), self._on_exe_changed("")))
        exe_layout.addWidget(self.le_exe, 1)
        exe_layout.addWidget(btn_exe_choose)
        exe_layout.addWidget(btn_exe_clear)
        self.layout.addWidget(lbl_exe, 7, 0)
        self.layout.addWidget(exe_row, 7, 1, 1, 3)

    # --- Change handlers update project and regen ---
    def _on_app_name_changed(self, val: str): self.project.app_name = val; self.regen()
    def _on_version_changed(self, val: str): self.project.version = val; self.regen()
    def _on_company_changed(self, val: str): self.project.company_name = val; self.regen()
    def _on_caption_changed(self, val: str): self.project.caption = val; self.regen()
    def _on_branding_changed(self, val: str): self.project.branding_text = val; self.regen()
    def _on_about_changed(self, val: str): self.project.about_url = val; self.regen()
    def _on_help_changed(self, val: str): self.project.help_url = val; self.regen()
    def _on_update_changed(self, val: str): self.project.update_url = val; self.regen()
    def _on_contact_changed(self, val: str): self.project.contact = val; self.regen()
    def _on_comments_changed(self, val: str): self.project.comments = val; self.regen()

    def _on_exe_changed(self, val: str):
        """Update exe path in project, recalc estimated size, then regenerate preview."""
        self.project.exe_path = val
        if val and os.path.isfile(val):
            kb = calc_estimated_size_kb(os.path.dirname(val))
            self.project.estimated_size = kb
        else:
            self.project.estimated_size = 0
        self.regen()

    def load_from_model(self, project: ProjectModel):
        """Load metadata fields from project model into form."""
        self.project = project
        self.le_appname.setText(project.app_name)
        self.le_company.setText(project.company_name)
        self.le_version.setText(project.version)
        self.le_caption.setText(project.caption)
        self.le_branding.setText(project.branding_text)
        self.le_about.setText(project.about_url)
        self.le_help.setText(project.help_url)
        self.le_update.setText(project.update_url)
        self.le_contact.setText(project.contact)
        self.le_comments.setText(project.comments)
        self.le_exe.setText(project.exe_path)

    def update_model(self):
        """Update project model from form fields (defensive sync)."""
        self.project.app_name = self.le_appname.text()
        self.project.company_name = self.le_company.text()
        self.project.version = self.le_version.text()
        self.project.caption = self.le_caption.text()
        self.project.branding_text = self.le_branding.text()
        self.project.about_url = self.le_about.text()
        self.project.help_url = self.le_help.text()
        self.project.update_url = self.le_update.text()
        self.project.contact = self.le_contact.text()
        self.project.comments = self.le_comments.text()
        self.project.exe_path = self.le_exe.text()
