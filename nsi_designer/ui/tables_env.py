"""
tables_env.py
-------------
EnvTable widget for the NSI Script Designer UI.

Contents:
- EnvTable: QTableWidget subclass that encapsulates environment variable rows.
  Syncs data with the project model on add and on user edits.
"""

from typing import List, Callable
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QComboBox
from PySide6.QtGui import QPalette
from ..model import ProjectModel, EnvRow, ENV_MODE_OPTIONS

class EnvTable(QTableWidget):
    """Table widget for editing environment variables."""
    def __init__(self, project: ProjectModel, regen_callback: Callable):
        super().__init__(0, 3)
        self.project = project
        self.regen = regen_callback
        self.setHorizontalHeaderLabels(["Name", "Value", "Mode"])
        self.horizontalHeader().setStretchLastSection(True)

        # Sync when table items change (user edits)
        self.itemChanged.connect(self.on_item_changed)

    def add_env_row(self, add_to_model: bool = True):
        """Add a new environment variable row to the table, optionally to the project model."""
        row = self.rowCount()
        self.insertRow(row)
        self.setItem(row, 0, QTableWidgetItem(""))  # Name
        self.setItem(row, 1, QTableWidgetItem(""))  # Value

        cb_mode = QComboBox()
        cb_mode.addItems(ENV_MODE_OPTIONS)
        cb_mode.currentTextChanged.connect(lambda _: self.sync_env_from_table())
        self.setCellWidget(row, 2, cb_mode)

        if add_to_model:
            # Only append to the model when explicitly requested
            self.project.env_rows.append(EnvRow())

        self.regen()

    def on_item_changed(self, item: QTableWidgetItem):
        """React to changes in the Name column to enforce PATH behavior."""
        if item.column() == 0:  # Name column
            row = item.row()
            name_text = item.text().strip().lower()
            mode_widget = self.cellWidget(row, 2)
            if isinstance(mode_widget, QComboBox):
                if name_text == "path":
                    # Force to append and lock
                    if "append" in ENV_MODE_OPTIONS:
                        mode_widget.setCurrentText("append")
                    mode_widget.setEnabled(False)
                    # Grey out visually
                    pal = mode_widget.palette()
                    pal.setColor(QPalette.Base, pal.color(QPalette.Disabled, QPalette.Base))
                    pal.setColor(QPalette.Text, pal.color(QPalette.Disabled, QPalette.Text))
                    mode_widget.setPalette(pal)
                    mode_widget.setToolTip("PATH must always be appended; mode locked.")
                else:
                    # Free again
                    mode_widget.setEnabled(True)
                    mode_widget.setPalette(self.style().standardPalette())
                    mode_widget.setToolTip("")
        # Always sync after changes
        self.sync_env_from_table()

    def sync_env_from_table(self):
        """Synchronize environment variable rows from table into project model."""
        rows: List[EnvRow] = []
        for r in range(self.rowCount()):
            name_item = self.item(r, 0)
            value_item = self.item(r, 1)
            mode_widget = self.cellWidget(r, 2)
            mode_val = mode_widget.currentText() if isinstance(mode_widget, QComboBox) else "set"
            rows.append(EnvRow(
                name=name_item.text() if name_item else "",
                value=value_item.text() if value_item else "",
                mode=mode_val,
            ))
        self.project.env_rows = rows
        self.regen()

    def load_from_model(self, project: ProjectModel):
        """Rebuild table from project model environment variable rows."""
        self.blockSignals(True)
        try:
            self.project = project
            self.setRowCount(0)
           
            for row in project.env_rows:
                self.add_env_row(add_to_model=False)
                r = self.rowCount() - 1
                self.item(r, 0).setText(row.name)
                self.item(r, 1).setText(row.value)
                mode_widget = self.cellWidget(r, 2)
                if mode_widget:
                    mode_widget.setCurrentText(row.mode)
                    # Apply PATH rule immediately
                    if row.name.strip().lower() == "path":
                        mode_widget.setCurrentText("append")
                        mode_widget.setEnabled(False)
                        pal = mode_widget.palette()
                        pal.setColor(QPalette.Base, pal.color(QPalette.Disabled, QPalette.Base))
                        pal.setColor(QPalette.Text, pal.color(QPalette.Disabled, QPalette.Text))
                        mode_widget.setPalette(pal)
                        mode_widget.setToolTip("PATH must always be appended; mode locked.")
        finally:
            self.blockSignals(False)
