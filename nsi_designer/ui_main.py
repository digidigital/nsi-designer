from __future__ import annotations
from typing import Callable, List
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QMainWindow, QSplitter, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDialog,
    QDialogButtonBox, QCheckBox, QGridLayout
)
from PySide6.QtGui import QAction
from .model import ProjectModel, RegistryRow, EnvRow, REG_ROOT_OPTIONS, ENV_MODE_OPTIONS, AVAILABLE_LANGUAGES


class LanguageDialog(QDialog):
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
        langs = [cb.text() for cb in self.checkboxes if cb.isChecked()]
        if "English" not in langs:
            langs.insert(0, "English")
        return langs


class MainWindow(QMainWindow):
    def __init__(self, project: ProjectModel, on_generate: Callable[[ProjectModel], str],
                 on_export: Callable[[ProjectModel], None],
                 on_compile: Callable[[ProjectModel], None]):
        super().__init__()
        self.setWindowTitle("NSI Script Designer")
        # Get the screen where this window will appear
        screen = self.screen() or QApplication.primaryScreen()
        geometry = screen.availableGeometry()

        # Resize to full available width, keep a fixed height (e.g. 600)
        self.resize(geometry.width(), 600)

        # Move to top-left of the available area
        self.move(geometry.x(), geometry.y())
        
        self.project = project
        self.generate = on_generate
        self.do_export = on_export
        self.do_compile = on_compile

        # --- Menu bar ---
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

        # --- Central layout ---
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

        # Metadata form
        meta_form = QFormLayout()
        self.le_appname = QLineEdit(self.project.app_name)
        self.le_company = QLineEdit(self.project.company_name)
        self.le_version = QLineEdit(self.project.version)
        self.le_caption = QLineEdit(self.project.caption)
        self.le_about = QLineEdit(self.project.about_url)
        self.le_branding = QLineEdit(self.project.branding_text)

        exe_row = QWidget()
        exe_layout = QHBoxLayout(exe_row)
        exe_layout.setContentsMargins(0, 0, 0, 0)
        self.le_exe = QLineEdit(self.project.exe_path)
        btn_exe_choose = QPushButton("Choose…")
        btn_exe_clear = QPushButton("Clear")
        exe_layout.addWidget(self.le_exe, 1)
        exe_layout.addWidget(btn_exe_choose)
        exe_layout.addWidget(btn_exe_clear)

        meta_form.addRow("Application name:", self.le_appname)
        meta_form.addRow("Company name:", self.le_company)
        meta_form.addRow("Version:", self.le_version)
        meta_form.addRow("Caption:", self.le_caption)
        meta_form.addRow("About URL:", self.le_about)
        meta_form.addRow("Branding text:", self.le_branding)
        meta_form.addRow("Executable file:", exe_row)
        # Presets
        preset_form = QFormLayout()
        self.cb_install_loc = QComboBox()
        self.cb_install_loc.addItems(["64-bit (ProgramFiles64)", "32-bit (ProgramFiles32)", "Per-user (AppData)"])
        self.cb_exec_level = QComboBox()
        self.cb_exec_level.addItems(["admin", "user"])
        self.cb_scope = QComboBox()
        self.cb_scope.addItems(["System-wide", "Per-user"])
        preset_form.addRow("Install location:", self.cb_install_loc)
        preset_form.addRow("Execution level:", self.cb_exec_level)
        preset_form.addRow("Scope:", self.cb_scope)

        # Assets
        assets_form = QFormLayout()
        def mk_asset_row(line_edit: QLineEdit) -> QWidget:
            w = QWidget()
            hl = QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            line_edit.setReadOnly(True)
            btn_choose = QPushButton("Choose…")
            btn_clear = QPushButton("Clear")
            hl.addWidget(line_edit, 1)
            hl.addWidget(btn_choose)
            hl.addWidget(btn_clear)
            w.btn_choose = btn_choose
            w.btn_clear = btn_clear
            return w

        self.le_install_icon = QLineEdit(self.project.install_icon_path)
        self.le_uninstall_icon = QLineEdit(self.project.uninstall_icon_path)
        self.le_welcome_bmp = QLineEdit(self.project.welcome_bitmap_path)
        self.le_license = QLineEdit(self.project.license_file_path)

        install_icon_row = mk_asset_row(self.le_install_icon)
        uninstall_icon_row = mk_asset_row(self.le_uninstall_icon)
        welcome_row = mk_asset_row(self.le_welcome_bmp)
        license_row = mk_asset_row(self.le_license)

        assets_form.addRow("Install icon:", install_icon_row)
        assets_form.addRow("Uninstall icon:", uninstall_icon_row)
        assets_form.addRow("Welcome bitmap:", welcome_row)
        assets_form.addRow("License file:", license_row)

        # Languages
        lang_row = QWidget()
        lang_layout = QHBoxLayout(lang_row)
        self.le_languages = QLineEdit(", ".join(self.project.languages))
        self.le_languages.setReadOnly(True)
        btn_lang_select = QPushButton("Select…")
        lang_layout.addWidget(self.le_languages, 1)
        lang_layout.addWidget(btn_lang_select)

        # Registry table
        self.tbl_registry = QTableWidget(0, 5)
        self.tbl_registry.setHorizontalHeaderLabels(["Root", "Sub-Key", "Key-Name", "Value", "Type"])
        self.tbl_registry.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        btn_add_reg = QPushButton("Add registry row")
        btn_del_reg = QPushButton("Remove selected registry row")

        # Env table
        self.tbl_env = QTableWidget(0, 3)
        self.tbl_env.setHorizontalHeaderLabels(["Name", "Value", "Mode"])
        self.tbl_env.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        btn_add_env = QPushButton("Add env row")
        btn_del_env = QPushButton("Remove selected env row")

        # Bottom bar
        bottom_row = QWidget()
        bottom_layout = QHBoxLayout(bottom_row)
        self.cb_encoding = QComboBox()
        self.cb_encoding.addItems(["ANSI" , "UTF-8"])
        btn_export = QPushButton("Export NSIS script and assets")
        btn_compile = QPushButton("Compile with NSIS")
        bottom_layout.addWidget(QLabel("Encoding:"))
        bottom_layout.addWidget(self.cb_encoding)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(btn_export)
        bottom_layout.addWidget(btn_compile)

        # Assemble left
        left_layout.addWidget(QLabel("Metadata"))
        left_layout.addLayout(meta_form)
        left_layout.addWidget(QLabel("Presets"))
        left_layout.addLayout(preset_form)
        left_layout.addWidget(QLabel("Assets"))
        left_layout.addLayout(assets_form)
        left_layout.addWidget(QLabel("Languages"))
        left_layout.addWidget(lang_row)
        left_layout.addWidget(QLabel("Registry entries"))
        left_layout.addWidget(self.tbl_registry)
        reg_btns_row = QWidget()
        rbl = QHBoxLayout(reg_btns_row)
        rbl.addWidget(btn_add_reg)
        rbl.addWidget(btn_del_reg)
        rbl.addStretch(1)
        left_layout.addWidget(reg_btns_row)
        left_layout.addWidget(QLabel("Environment variables"))
        left_layout.addWidget(self.tbl_env)
        env_btns_row = QWidget()
        ebl = QHBoxLayout(env_btns_row)
        ebl.addWidget(btn_add_env)
        ebl.addWidget(btn_del_env)
        ebl.addStretch(1)
        left_layout.addWidget(env_btns_row)
        left_layout.addStretch(1)
        left_layout.addWidget(bottom_row)
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

        # --- Wiring ---
        def regen():
            self.preview.setPlainText(self.generate(self.project))

        # Metadata
        self.le_appname.textChanged.connect(lambda t: setattr(self.project, "app_name", t) or regen())
        self.le_company.textChanged.connect(lambda t: setattr(self.project, "company_name", t) or regen())
        self.le_version.textChanged.connect(lambda t: setattr(self.project, "version", t) or regen())
        self.le_caption.textChanged.connect(lambda t: setattr(self.project, "caption", t) or regen())
        self.le_about.textChanged.connect(lambda t: setattr(self.project, "about_url", t) or regen())
        self.le_branding.textChanged.connect(lambda t: setattr(self.project, "branding_text", t) or regen())

        # Executable
        btn_exe_choose.clicked.connect(self._choose_exe)
        btn_exe_clear.clicked.connect(lambda: (self.le_exe.setText(""), setattr(self.project, "exe_path", ""), regen()))
        self.le_exe.textChanged.connect(lambda t: setattr(self.project, "exe_path", t) or regen())

        # Presets
        self.cb_install_loc.currentTextChanged.connect(self._on_install_loc_changed(regen))
        self.cb_exec_level.currentTextChanged.connect(lambda t: setattr(self.project, "exec_level", t) or regen())
        self.cb_scope.currentTextChanged.connect(lambda t: setattr(self.project, "scope", t) or regen())

        # Assets
        install_icon_row.btn_choose.clicked.connect(lambda: self._choose_asset(self.le_install_icon, "Select icon", ["*.ico","*.png","*.jpg"], "install_icon_path", regen))
        install_icon_row.btn_clear.clicked.connect(lambda: (self.le_install_icon.setText(""), setattr(self.project, "install_icon_path", ""), regen()))
        uninstall_icon_row.btn_choose.clicked.connect(lambda: self._choose_asset(self.le_uninstall_icon, "Select uninstall icon", ["*.ico","*.png","*.jpg"], "uninstall_icon_path", regen))
        uninstall_icon_row.btn_clear.clicked.connect(lambda: (self.le_uninstall_icon.setText(""), setattr(self.project, "uninstall_icon_path", ""), regen()))
        welcome_row.btn_choose.clicked.connect(lambda: self._choose_asset(self.le_welcome_bmp, "Select welcome image", ["*.bmp","*.png","*.jpg"], "welcome_bitmap_path", regen))
        welcome_row.btn_clear.clicked.connect(lambda: (self.le_welcome_bmp.setText(""), setattr(self.project, "welcome_bitmap_path", ""), regen()))
        license_row.btn_choose.clicked.connect(lambda: self._choose_asset(self.le_license, "Select license file", ["*.rtf"], "license_file_path", regen))
        license_row.btn_clear.clicked.connect(lambda: (self.le_license.setText(""), setattr(self.project, "license_file_path", ""), regen()))

        # Languages
        btn_lang_select.clicked.connect(self._select_languages)

        # Registry table
        btn_add_reg.clicked.connect(lambda: self._add_registry_row(regen))
        btn_del_reg.clicked.connect(lambda: self._delete_selected_row(self.tbl_registry, self.project.registry_rows, regen))
        self.tbl_registry.itemChanged.connect(lambda _: self._sync_registry_from_table(regen))

        # Env table
        btn_add_env.clicked.connect(lambda: self._add_env_row(regen))
        btn_del_env.clicked.connect(lambda: self._delete_selected_row(self.tbl_env, self.project.env_rows, regen))
        self.tbl_env.itemChanged.connect(lambda _: self._sync_env_from_table(regen))

        # Bottom
        self.cb_encoding.currentTextChanged.connect(lambda t: setattr(self.project, "encoding", t) or regen())
        btn_export.clicked.connect(lambda: self.do_export(self.project))
        btn_compile.clicked.connect(lambda: self.do_compile(self.project))

        regen()
    # --- Menu actions ---
    def _new_project(self):
        self.project = ProjectModel()
        self._reload_from_project()

    def _open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "JSON (*.json)")
        if path:
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
            self.project = ProjectModel.from_json(data)
            self._reload_from_project()

    def _save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.project.to_json())

    def _reload_from_project(self):
        """Update all UI fields from current project model."""
        p = self.project
        self.le_appname.setText(p.app_name)
        self.le_company.setText(p.company_name)
        self.le_version.setText(p.version)
        self.le_caption.setText(p.caption)
        self.le_about.setText(p.about_url)
        self.le_branding.setText(p.branding_text)
        self.le_exe.setText(p.exe_path)
        self.cb_install_loc.setCurrentIndex(0 if p.install_dir_preset=="64-bit" else 1 if p.install_dir_preset=="32-bit" else 2)
        self.cb_exec_level.setCurrentText(p.exec_level)
        self.cb_scope.setCurrentText(p.scope)
        self.le_install_icon.setText(p.install_icon_path)
        self.le_uninstall_icon.setText(p.uninstall_icon_path)
        self.le_welcome_bmp.setText(p.welcome_bitmap_path)
        self.le_license.setText(p.license_file_path)
        self.le_languages.setText(", ".join(p.languages))
        self.cb_encoding.setCurrentText(p.encoding)
        # Rebuild tables
        self.tbl_registry.setRowCount(0)
        for row in p.registry_rows:
            self._add_registry_row(lambda: None)
            r = self.tbl_registry.rowCount()-1
            root_widget = self.tbl_registry.cellWidget(r,0)
            if root_widget: root_widget.setCurrentText(row.root)
            self.tbl_registry.item(r,1).setText(row.key)
            self.tbl_registry.item(r,2).setText(row.value)
            self.tbl_registry.item(r,3).setText(row.data)
            type_widget = self.tbl_registry.cellWidget(r,4)
            if type_widget:
                type_widget.setCurrentText(getattr(row, "reg_type", "string"))

        self.tbl_env.setRowCount(0)
        for row in p.env_rows:
            self._add_env_row(lambda: None)
            r = self.tbl_env.rowCount()-1
            self.tbl_env.item(r,0).setText(row.name)
            self.tbl_env.item(r,1).setText(row.value)
            mode_widget = self.tbl_env.cellWidget(r,2)
            if mode_widget: mode_widget.setCurrentText(row.mode)
        self.preview.setPlainText(self.generate(self.project))

    # --- Helpers ---
    def _choose_exe(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose executable", "", "Executable (*.exe)")
        if path:
            self.le_exe.setText(path)

    def _choose_asset(self, line_edit: QLineEdit, title: str, filters: List[str], attr: str, regen: Callable):
        flt = ";;".join([f"{f} ({f})" for f in filters])
        path, _ = QFileDialog.getOpenFileName(self, title, "", flt)
        if path:
            line_edit.setText(path)
            setattr(self.project, attr, path)
            regen()

    def _on_install_loc_changed(self, regen: Callable):
        def _handler(text: str):
            preset = "64-bit" if "64-bit" in text else "32-bit" if "32-bit" in text else "Per-user"
            setattr(self.project, "install_dir_preset", preset)
            regen()
        return _handler

    def _select_languages(self):
        dlg = LanguageDialog(self, selected=self.project.languages)
        if dlg.exec():
            langs = dlg.get_selection()
            self.project.languages = langs
            self.le_languages.setText(", ".join(langs))
            self.preview.setPlainText(self.generate(self.project))

    def _add_registry_row(self, regen: Callable):
        row = self.tbl_registry.rowCount()
        self.tbl_registry.insertRow(row)
        cb_root = QComboBox()
        cb_root.addItems(REG_ROOT_OPTIONS)
        cb_root.currentTextChanged.connect(lambda _: self._sync_registry_from_table(regen))
        self.tbl_registry.setCellWidget(row, 0, cb_root)
        for col in (1, 2, 3):
            self.tbl_registry.setItem(row, col, QTableWidgetItem(""))

        cb_type = QComboBox()
        cb_type.addItems(["string", "dword"])
        cb_type.currentTextChanged.connect(lambda _: self._sync_registry_from_table(regen))
        self.tbl_registry.setCellWidget(row, 4, cb_type)

        self.project.registry_rows.append(RegistryRow())
        regen()


    def _sync_registry_from_table(self, regen: Callable):
        rows: List[RegistryRow] = []
        for r in range(self.tbl_registry.rowCount()):
            root_widget = self.tbl_registry.cellWidget(r, 0)
            root_val = root_widget.currentText() if isinstance(root_widget, QComboBox) else "HKLM"
            key_item = self.tbl_registry.item(r, 1)
            value_item = self.tbl_registry.item(r, 2)
            data_item = self.tbl_registry.item(r, 3)
            type_widget = self.tbl_registry.cellWidget(r, 4)
            reg_type = type_widget.currentText() if isinstance(type_widget, QComboBox) else "string"

            rows.append(RegistryRow(
                root=root_val,
                key=key_item.text() if key_item else "",
                value=value_item.text() if value_item else "",
                data=data_item.text() if data_item else "",
                reg_type=reg_type,
            ))
        self.project.registry_rows = rows
        regen()

    def _add_env_row(self, regen: Callable):
        row = self.tbl_env.rowCount()
        self.tbl_env.insertRow(row)
        self.tbl_env.setItem(row, 0, QTableWidgetItem(""))
        self.tbl_env.setItem(row, 1, QTableWidgetItem(""))
        cb_mode = QComboBox()
        cb_mode.addItems(ENV_MODE_OPTIONS)
        cb_mode.currentTextChanged.connect(lambda _: self._sync_env_from_table(regen))
        self.tbl_env.setCellWidget(row, 2, cb_mode)
        self.project.env_rows.append(EnvRow())
        regen()

    def _sync_env_from_table(self, regen: Callable):
        rows: List[EnvRow] = []
        for r in range(self.tbl_env.rowCount()):
            name_item = self.tbl_env.item(r, 0)
            value_item = self.tbl_env.item(r, 1)
            mode_widget = self.tbl_env.cellWidget(r, 2)
            mode_val = mode_widget.currentText() if isinstance(mode_widget, QComboBox) else "set"
            rows.append(EnvRow(
                name=name_item.text() if name_item else "",
                value=value_item.text() if value_item else "",
                mode=mode_val,
            ))
        self.project.env_rows = rows
        regen()

    def _delete_selected_row(self, table: QTableWidget, model_list: list, regen: Callable):
        row = table.currentRow()
        if row >= 0 and row < len(model_list):
            table.removeRow(row)
            del model_list[row]
            regen()
