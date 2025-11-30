"""
main_window.py
--------------
MainWindow for the NSI Script Designer UI.

Contents:
- MainWindow: Orchestrates sub-widgets and ensures the project model is kept in sync.
  Forces a defensive sync before generating preview, exporting, and compiling.
"""

from typing import Callable
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QMainWindow, QSplitter, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog, QComboBox, QApplication
)
from PySide6.QtGui import QAction
from ..model import ProjectModel
from .forms_metadata import MetadataForm
from .forms_presets import PresetsForm
from .forms_assets import AssetsForm
from .tables_registry import RegistryTable
from .tables_env import EnvTable
from .dialogs import LanguageDialog

class MainWindow(QMainWindow):
    """Main application window for NSI Script Designer."""
    def __init__(self, project: ProjectModel,
                 on_generate: Callable[[ProjectModel], str],
                 on_export: Callable[[ProjectModel], None],
                 on_compile: Callable[[ProjectModel], None]):
        super().__init__()
        self.setWindowTitle("NSI Script Designer")
        self.project = project
        self.generate = on_generate
        self.do_export = on_export
        self.do_compile = on_compile

        # Window sizing
        screen = self.screen() or QApplication.primaryScreen()
        geometry = screen.availableGeometry()
        self.resize(geometry.width(), 600)
        self.move(geometry.x(), geometry.y())

        # Menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        act_new = QAction("New Project", self)
        act_open = QAction("Open Project...", self)
        act_save = QAction("Save Project...", self)
        file_menu.addAction(act_new)
        file_menu.addAction(act_open)
        file_menu.addAction(act_save)
        act_new.triggered.connect(self._new_project)
        act_open.triggered.connect(self._open_project)
        act_save.triggered.connect(self._save_project)

        # Central layout
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        splitter = QSplitter(Qt.Horizontal)
        root_layout.addWidget(splitter)

        # Left pane
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(8)

        # Sub-widgets
        self.meta_form = MetadataForm(project, self._regen)
        self.presets_form = PresetsForm(project, self._regen)
        self.assets_form = AssetsForm(project, self._regen)
        self.registry_table = RegistryTable(project, self._regen)
        self.env_table = EnvTable(project, self._regen)

        # Assemble left
        left_layout.addWidget(QLabel("Metadata"))
        left_layout.addWidget(self.meta_form)
        left_layout.addWidget(QLabel("Presets"))
        left_layout.addWidget(self.presets_form)
        left_layout.addWidget(QLabel("Assets"))
        left_layout.addWidget(self.assets_form)
        left_layout.addWidget(QLabel("Languages"))
        self.le_languages = QLineEdit(", ".join(self.project.languages))
        self.le_languages.setReadOnly(True)
        btn_lang_select = QPushButton("Select…")
        lang_row = QHBoxLayout()
        lang_row.addWidget(self.le_languages, 1)
        lang_row.addWidget(btn_lang_select)
        left_layout.addLayout(lang_row)
        left_layout.addWidget(QLabel("Registry entries"))
        left_layout.addWidget(self.registry_table)
        btn_add_reg = QPushButton("Add registry row")
        btn_del_reg = QPushButton("Remove selected registry row")
        reg_row = QHBoxLayout()
        reg_row.addWidget(btn_add_reg)
        reg_row.addWidget(btn_del_reg)
        left_layout.addLayout(reg_row)
        left_layout.addWidget(QLabel("Environment variables"))
        left_layout.addWidget(self.env_table)
        btn_add_env = QPushButton("Add env row")
        btn_del_env = QPushButton("Remove selected env row")
        env_row = QHBoxLayout()
        env_row.addWidget(btn_add_env)
        env_row.addWidget(btn_del_env)
        left_layout.addLayout(env_row)

        # Bottom bar
        bottom_row = QHBoxLayout()
        self.cb_encoding = QComboBox()
        self.cb_encoding.addItems(["ANSI", "UTF-8"])
        self.cb_encoding.setCurrentText(self.project.encoding)
        self.cb_encoding.currentTextChanged.connect(self._on_encoding_changed)
        btn_export = QPushButton("Export NSIS script and assets")
        btn_compile = QPushButton("Compile last export with NSIS")
        bottom_row.addWidget(QLabel("Encoding:"))
        bottom_row.addWidget(self.cb_encoding)
        bottom_row.addStretch(1)
        bottom_row.addWidget(btn_export)
        bottom_row.addWidget(btn_compile)
        left_layout.addLayout(bottom_row)

        splitter.addWidget(left)

        # Right pane
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(8)
        right_layout.addWidget(QLabel("Preview"))
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        right_layout.addWidget(self.preview, 1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        # Wiring
        btn_lang_select.clicked.connect(self._select_languages)
        btn_add_reg.clicked.connect(self.registry_table.add_registry_row)
        btn_del_reg.clicked.connect(lambda: self._delete_selected_row(self.registry_table))
        btn_add_env.clicked.connect(self.env_table.add_env_row)
        btn_del_env.clicked.connect(lambda: self._delete_selected_row(self.env_table))
        btn_export.clicked.connect(self._export_action)
        btn_compile.clicked.connect(self._compile_action)

        self._regen()

    # Defensive sync: ensure UI -> model before actions
    def _sync_all_forms_into_model(self):
        self.meta_form.update_model()
        self.presets_form.update_model()
        self.assets_form.update_model()
        # tables sync themselves on edit, but force regen to reflect latest
        # registry_table/env_table already update project on item change

    def _regen(self):
        """Regenerate preview text from project model."""
        # Always sync from forms first to avoid stale data
        self._sync_all_forms_into_model()
        self.preview.setPlainText(self.generate(self.project))

    def _on_encoding_changed(self, enc: str):
        """Update project encoding and regenerate."""
        self.project.encoding = enc
        self._regen()

    def _export_action(self):
        """Export with a fresh sync, then call export."""
        self._sync_all_forms_into_model()
        self.do_export(self.project)

    def _compile_action(self):
        """Compile with a fresh sync, then call compile."""
        self._sync_all_forms_into_model()
        self.do_compile(self.project)

    def _new_project(self):
        """Create a new blank project and reset export state."""
        self.project = ProjectModel()
        self.project.export_dir = None
        self.project.has_exported_in_session = False
        self._reload_from_project()

    def _open_project(self):
        """Open a project from JSON file."""
        path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "JSON (*.json)")
        if path:
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
            self.project = ProjectModel.from_json(data)
            self.project.export_dir = None
            self.project.has_exported_in_session = False
            self._reload_from_project()

    def _save_project(self):
        """Save current project to JSON file."""
        path, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.project.to_json())

    def _reload_from_project(self):
        """Update all UI fields from current project model."""
        self.meta_form.load_from_model(self.project)
        self.presets_form.load_from_model(self.project)
        self.assets_form.load_from_model(self.project)
        self.registry_table.load_from_model(self.project)
        self.env_table.load_from_model(self.project)
        self.le_languages.setText(", ".join(self.project.languages))
        self.cb_encoding.setCurrentText(self.project.encoding)
        self._regen()

    def _select_languages(self):
        """Open language selection dialog and update project."""
        dlg = LanguageDialog(self, selected=self.project.languages)
        if dlg.exec():
            langs = dlg.get_selection()
            self.project.languages = langs
            self.le_languages.setText(", ".join(langs))
            self._regen()

    def _delete_selected_row(self, table_widget):
        """Delete selected row from a given table widget and update project."""
        selected = table_widget.selectedIndexes()
        if selected:
            row = selected[0].row()
            table_widget.removeRow(row)
            if isinstance(table_widget, RegistryTable):
                del self.project.registry_rows[row]
            elif isinstance(table_widget, EnvTable):
                del self.project.env_rows[row]
            self._regen()
