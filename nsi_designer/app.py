from __future__ import annotations
import os
import subprocess
from typing import Dict
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PySide6.QtCore import QSettings
from .model import ProjectModel
from .generator import build_script
from .assets import (
    copy_or_convert_icon, copy_or_convert_bitmap, copy_license, ensure_dir
)
from .ui_main import MainWindow


def _default_export_dir() -> str:
    home = os.path.expanduser("~")
    return os.path.join(home, "NSI_Exports")


def _generate_preview_text(project: ProjectModel) -> str:
    exported_paths = {
        "exe_path": project.exe_path or "",
        "exe_dir": os.path.dirname(project.exe_path) if project.exe_path else "",
        "install_icon_path": os.path.basename(project.install_icon_path) if project.install_icon_path else "",
        "uninstall_icon_path": os.path.basename(project.uninstall_icon_path) if project.uninstall_icon_path else "",
        "welcome_bitmap_path": os.path.basename(project.welcome_bitmap_path) if project.welcome_bitmap_path else "",
        "license_file_path": os.path.basename(project.license_file_path) if project.license_file_path else "",
    }
    return build_script(project, exported_paths)


def _export_project(project: ProjectModel) -> None:
    export_dir = QFileDialog.getExistingDirectory(
        None, "Choose export directory", project.export_dir or _default_export_dir()
    )
    if not export_dir:
        return
    project.export_dir = export_dir
    settings = QSettings("NSIDesigner", "NSIDesignerApp")
    settings.setValue("last_export_dir", export_dir)

    root_dir = export_dir
    ensure_dir(root_dir)

    exported_paths: Dict[str, str] = {}

    # Keep exe path and directory only (no copy)
    if project.exe_path:
        exported_paths["exe_path"] = project.exe_path
        exported_paths["exe_dir"] = os.path.dirname(project.exe_path)

    try:
        # Assets: convert/copy into export root
        if project.install_icon_path:
            ico_dst = copy_or_convert_icon(project.install_icon_path, root_dir)
            if ico_dst:
                exported_paths["install_icon_path"] = os.path.basename(ico_dst)

        if project.uninstall_icon_path:
            unico_dst = copy_or_convert_icon(project.uninstall_icon_path, root_dir)
            if unico_dst:
                exported_paths["uninstall_icon_path"] = os.path.basename(unico_dst)

        if project.welcome_bitmap_path:
            bmp_dst = copy_or_convert_bitmap(project.welcome_bitmap_path, root_dir)
            if bmp_dst:
                exported_paths["welcome_bitmap_path"] = os.path.basename(bmp_dst)

        if project.license_file_path:
            lic_dst = copy_license(project.license_file_path, root_dir)
            if lic_dst:
                exported_paths["license_file_path"] = os.path.basename(lic_dst)

        # Build and write script
        script_text = build_script(project, exported_paths)
        script_name = f"{project.app_name}_{project.version}.nsi".replace(" ", "_")
        script_path = os.path.join(root_dir, script_name)
        with open(script_path, "w", encoding=project.encoding_codec(), newline="\r\n") as f:
            f.write(script_text)
    except Exception as e:
        QMessageBox.information(
            None,
            "Export failed",
            f"An error occured:\n{str(e)}",
        )
        return

    QMessageBox.information(
        None,
        "Export completed",
        f"Exported script:\n{script_path}\n\nExe dir: {exported_paths.get('exe_dir','')}",
    )


def _compile_with_nsis(project: ProjectModel) -> None:
    settings = QSettings("NSIDesigner", "NSIDesignerApp")
    nsis_path = settings.value("nsis_path", project.nsis_path)

    def ask_path():
        path, _ = QFileDialog.getOpenFileName(None, "Select makensis.exe", "", "NSIS makensis (makensis.exe)")
        return path

    if not nsis_path or not os.path.isfile(nsis_path):
        nsis_path = ask_path()
        if not nsis_path:
            QMessageBox.warning(None, "NSIS not found", "makensis.exe path is required to compile.")
            return
        settings.setValue("nsis_path", nsis_path)
        project.nsis_path = nsis_path

    export_dir = settings.value("last_export_dir", project.export_dir or _default_export_dir())
    if not export_dir or not os.path.isdir(export_dir):
        QMessageBox.warning(None, "No export directory", "Export a script first.")
        return

    scripts = [f for f in os.listdir(export_dir) if f.lower().endswith(".nsi")]
    if not scripts:
        QMessageBox.warning(None, "No script", "No .nsi script found in export directory.")
        return
    scripts.sort()
    script_path = os.path.join(export_dir, scripts[-1])
    try:
        subprocess.run([nsis_path, script_path], check=True)
        QMessageBox.information(None, "Compilation finished", f"makensis completed.\nScript: {script_path}")
    except subprocess.CalledProcessError as e:
        QMessageBox.critical(None, "Compilation error", f"makensis failed:\n{e}")


def main():
    app = QApplication([])
    settings = QSettings("NSIDesigner", "NSIDesignerApp")
    project = ProjectModel()
    last_export_dir = settings.value("last_export_dir", "")
    if last_export_dir:
        project.export_dir = last_export_dir
    nsis_path = settings.value("nsis_path", "")
    if nsis_path:
        project.nsis_path = nsis_path
    window = MainWindow(
        project=project,
        on_generate=_generate_preview_text,
        on_export=_export_project,
        on_compile=_compile_with_nsis,
    )
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
