"""
dialogs.py
-----------
This module contains dialog classes used in the NSI Script Designer UI.

Contents:
- LanguageDialog: A modal dialog that allows the user to select installer languages.
"""

from typing import List
from PySide6.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QCheckBox, QDialogButtonBox
from ..model import AVAILABLE_LANGUAGES

class LanguageDialog(QDialog):
    """Dialog for selecting installer languages."""
    def __init__(self, parent=None, selected: List[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Select languages")
        self.setModal(True)
        self.resize(420, 360)
        self.selected = set(selected or [])
        layout = QVBoxLayout(self)
        grid = QGridLayout()
        self.checkboxes: List[QCheckBox] = []
        for i, lang in enumerate(AVAILABLE_LANGUAGES):
            cb = QCheckBox(lang)
            cb.setChecked(lang in self.selected or (lang == "English" and not selected))
            self.checkboxes.append(cb)
            grid.addWidget(cb, i // 2, i % 2)
        layout.addLayout(grid)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_selection(self) -> List[str]:
        """Return selected languages, always including English."""
        langs = [cb.text() for cb in self.checkboxes if cb.isChecked()]
        if "English" not in langs:
            langs.insert(0, "English")
        return langs
