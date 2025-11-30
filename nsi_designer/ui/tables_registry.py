"""
tables_registry.py
------------------
RegistryTable widget for the NSI Script Designer UI.

Contents:
- RegistryTable: QTableWidget subclass that encapsulates registry entry rows.
  Syncs data with the project model on add and on user edits.
"""

from typing import List, Callable
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QComboBox
from ..model import ProjectModel, RegistryRow, REG_ROOT_OPTIONS

class RegistryTable(QTableWidget):
    """Table widget for editing registry entries."""
    def __init__(self, project: ProjectModel, regen_callback: Callable):
        super().__init__(0, 5)
        self.project = project
        self.regen = regen_callback
        self.setHorizontalHeaderLabels(["Root", "Sub-Key", "Key-Name", "Value", "Type"])
        self.horizontalHeader().setStretchLastSection(True)

        # Sync when table items change (user edits)
        self.itemChanged.connect(lambda _: self.sync_registry_from_table())

    def add_registry_row(self, add_to_model: bool = True):
        """Add a new registry row to the table and project model."""
        row = self.rowCount()
        self.insertRow(row)
        cb_root = QComboBox()
        cb_root.addItems(REG_ROOT_OPTIONS)
        cb_root.currentTextChanged.connect(lambda _: self.sync_registry_from_table())
        self.setCellWidget(row, 0, cb_root)
        for col in (1, 2, 3):
            self.setItem(row, col, QTableWidgetItem(""))

        cb_type = QComboBox()
        cb_type.addItems(["string", "dword"])
        cb_type.currentTextChanged.connect(lambda _: self.sync_registry_from_table())
        self.setCellWidget(row, 4, cb_type)
        
        if add_to_model:
            # Only append to the model when explicitly requested
            self.project.registry_rows.append(RegistryRow())
        self.regen()

    def sync_registry_from_table(self):
        """Synchronize registry rows from table into project model."""
        rows: List[RegistryRow] = []
        for r in range(self.rowCount()):
            root_widget = self.cellWidget(r, 0)
            root_val = root_widget.currentText() if isinstance(root_widget, QComboBox) else "HKLM"
            key_item = self.item(r, 1)
            value_item = self.item(r, 2)
            data_item = self.item(r, 3)
            type_widget = self.cellWidget(r, 4)
            reg_type = type_widget.currentText() if isinstance(type_widget, QComboBox) else "string"

            rows.append(RegistryRow(
                root=root_val,
                key=key_item.text() if key_item else "",
                value=value_item.text() if value_item else "",
                data=data_item.text() if data_item else "",
                reg_type=reg_type,
            ))
        self.project.registry_rows = rows
        self.regen()

    def load_from_model(self, project: ProjectModel):
        """Rebuild table from project model registry rows."""
        self.blockSignals(True)
        try:
            self.project = project
            self.setRowCount(0)
            for row in project.registry_rows:
                self.add_registry_row(add_to_model=False)
                r = self.rowCount() - 1
                root_widget = self.cellWidget(r, 0)
                if root_widget:
                    root_widget.setCurrentText(row.root)
                self.item(r, 1).setText(row.key)
                self.item(r, 2).setText(row.value)           
                self.item(r, 3).setText(row.data)
                type_widget = self.cellWidget(r, 4)
                if type_widget:
                    type_widget.setCurrentText(getattr(row, "reg_type", "string"))
        finally:
            self.blockSignals(False)
