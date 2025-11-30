"""
helpers.py
-----------
Shared helper classes and functions used across the UI.

Contents:
- AutoLabel: Label component preserving currentText() compatibility.
- calc_estimated_size_kb: Utility to calculate estimated installation size in KB.
- choose_asset: Helper to open file chooser dialogs for assets.
- choose_file: Generic file chooser that updates a QLineEdit and a project attribute, then calls regen.
"""

import os
from typing import List, Callable
from PySide6.QtWidgets import QLabel, QLineEdit, QFileDialog

class AutoLabel(QLabel):
    """Drop-in replacement for QComboBox that only displays text but keeps currentText() API."""
    def __init__(self, text=""):
        super().__init__(text)
        self._text = text

    def setText(self, text: str):
        """Set label text and store internally."""
        super().setText(text)
        self._text = text

    def currentText(self) -> str:
        """Return stored text (mimics QComboBox.currentText)."""
        return self._text

    def setCurrentText(self, text: str):
        """Set text via currentText API for compatibility."""
        self.setText(text)


def calc_estimated_size_kb(inst_dir: str) -> int:
    """Calculate estimated installation size in KB for given directory."""
    total_bytes = 0
    for root, _, files in os.walk(inst_dir):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total_bytes += os.path.getsize(fp)
            except OSError:
                pass
    return (total_bytes + 1023) // 1024


def choose_asset(line_edit: QLineEdit, title: str, filters: List[str], attr: str,
                 project, regen: Callable):
    """Open file chooser for asset, update project attribute and refresh preview."""
    flt = ";;".join([f"{f} ({f})" for f in filters])
    path, _ = QFileDialog.getOpenFileName(None, title, "", flt)
    if path:
        line_edit.setText(path)
        setattr(project, attr, path)
        regen()


def choose_file(line_edit: QLineEdit, title: str, filters: List[str], attr: str,
                project, regen: Callable):
    """Generic file chooser for single files (e.g., executable)."""
    flt = ";;".join([f"{f} ({f})" for f in filters])
    path, _ = QFileDialog.getOpenFileName(None, title, "", flt)
    if path:
        line_edit.setText(path)
        setattr(project, attr, path)
        regen()


