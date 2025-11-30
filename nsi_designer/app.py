from __future__ import annotations
import os
import winreg
from typing import Dict
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QProgressDialog
from PySide6.QtCore import QSettings, Qt, QProcess
from .model import ProjectModel
from .generator import build_script
from .assets import (
    copy_or_convert_icon, copy_or_convert_bitmap, copy_license, ensure_dir
)
from .ui import MainWindow


def _default_export_dir() -> str:
    '''Return the default export directory path.'''
    home = os.path.expanduser("~")
    return home


def _generate_preview_text(project: ProjectModel) -> str:
    '''Generate preview NSIS script text from the current project model.'''
    try:
        exported_paths = {
            "exe_path": project.exe_path or "",
            "exe_dir": os.path.dirname(project.exe_path) if project.exe_path else "",
            "install_icon_path": os.path.basename(project.install_icon_path) if project.install_icon_path else "",
            "uninstall_icon_path": os.path.basename(project.uninstall_icon_path) if project.uninstall_icon_path else "",
            "welcome_bitmap_path": os.path.basename(project.welcome_bitmap_path) if project.welcome_bitmap_path else "",
            "license_file_path": os.path.basename(project.license_file_path) if project.license_file_path else "",
        }
        return build_script(project, exported_paths)
    except Exception as e:
        return f"; Error generating preview: {e}"


def _export_project(project: ProjectModel) -> None:
    '''Export the current project to NSIS script and assets.'''
    try:
        export_dir = QFileDialog.getExistingDirectory(
            None, "Choose export directory", project.export_dir or _default_export_dir()
        )
        if not export_dir:
            return
        project.export_dir = export_dir
        project.has_exported_in_session = True

        root_dir = export_dir
        ensure_dir(root_dir)

        exported_paths: Dict[str, str] = {}

        if project.exe_path:
            exported_paths["exe_path"] = project.exe_path
            exported_paths["exe_dir"] = os.path.dirname(project.exe_path)

        try:
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

            script_text = build_script(project, exported_paths)
            script_name = f"{project.app_name}_{project.version}.nsi".replace(" ", "_")
            script_path = os.path.join(root_dir, script_name)
            with open(script_path, "w", encoding=project.encoding_codec(), newline="\r\n") as f:
                f.write(script_text)

            # --- NEW: also save JSON alongside the .nsi script ---
            json_name = os.path.splitext(script_name)[0] + ".json"
            json_path = os.path.join(root_dir, json_name)
            with open(json_path, "w", encoding="utf-8") as jf:
                jf.write(project.to_json())
            # -----------------------------------------------------

        except Exception as e:
            QMessageBox.critical(None, "Export failed", f"An error occurred:\n{e}")
            return

        QMessageBox.information(
            None,
            "Export completed",
            f"Exported script:\n{script_path}\n\nAlso saved project JSON:\n{json_path}\n\nExe dir: {exported_paths.get('exe_dir','')}",
        )
    except Exception as e:
        QMessageBox.critical(None, "Export failed", f"Unexpected error:\n{e}")


def _compile_with_nsis(project: ProjectModel, parent_window=None) -> None:
    '''Compile the exported NSIS script using makensis.exe with progress dialog and cancel support.'''
    try:
        if not getattr(project, "has_exported_in_session", False):
            QMessageBox.warning(None, "Export required",
                                "Please export an NSIS script in this session before compiling.")
            return

        settings = QSettings("NSIDesigner", "NSIDesignerApp")
        nsis_path = settings.value("nsis_path", project.nsis_path)

        def ask_path():
            '''Ask user to select makensis.exe manually.'''
            path, _ = QFileDialog.getOpenFileName(
                None, "Select makensis.exe", "", "NSIS makensis (makensis.exe)"
            )
            return path

        def find_nsis_in_registry():
            '''Try to locate makensis.exe via Windows registry keys.'''
            possible_keys = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\NSIS"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\NSIS"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\NSIS"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Wow6432Node\NSIS"),
            ]
            for hive, key in possible_keys:
                try:
                    with winreg.OpenKey(hive, key) as regkey:
                        for value_name in ("InstallDir", ""):
                            try:
                                val, _ = winreg.QueryValueEx(regkey, value_name)
                                candidate = os.path.join(val, "makensis.exe")
                                if os.path.isfile(candidate):
                                    return candidate
                            except FileNotFoundError:
                                pass
                except Exception:
                    continue
            return None

        if not nsis_path or not os.path.isfile(nsis_path):
            nsis_path = find_nsis_in_registry()
            if not nsis_path:
                nsis_path = ask_path()
                if not nsis_path:
                    QMessageBox.warning(None, "NSIS not found", "makensis.exe path is required to compile.")
                    return
            settings.setValue("nsis_path", nsis_path)
            project.nsis_path = nsis_path

        export_dir = project.export_dir
        if not export_dir or not os.path.isdir(export_dir):
            QMessageBox.warning(None, "No export directory", "Export a script first.")
            return

        scripts = [f for f in os.listdir(export_dir) if f.lower().endswith(".nsi")]
        if not scripts:
            QMessageBox.warning(None, "No script", "No .nsi script found in export directory.")
            return
        scripts.sort()
        script_path = os.path.join(export_dir, scripts[-1])

        progress = QProgressDialog("Compiling script...", "Cancel", 0, 0, None)
        progress.setWindowTitle("NSI-Designer")
        progress.setWindowFlags(progress.windowFlags() & ~Qt.WindowMaximizeButtonHint)
        progress.setFixedSize(400, 120)
        progress.setWindowModality(Qt.ApplicationModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setCancelButtonText("Cancel")
        progress.show()

        if parent_window is not None:
            parent_window._nsis_progress = progress

        process = QProcess(None)
        process.setProgram(nsis_path)
        process.setArguments([script_path])

        if parent_window is not None:
            parent_window._nsis_process = process

        def _cleanup_ui():
            '''Close progress dialog safely.'''
            try:
                if progress and progress.isVisible():
                    progress.cancel()
            except Exception:
                pass

        def on_finished(exitCode, exitStatus):
            '''Handle process finished event.'''
            try:
                _cleanup_ui()
                if exitCode == 0:
                    QMessageBox.information(parent_window, "Compilation finished",
                                            f"makensis completed.\nScript: {script_path}")
                else:
                    QMessageBox.critical(parent_window, "Compilation error",
                                         f"makensis failed with code {exitCode}")
            except Exception as e:
                QMessageBox.critical(parent_window, "Error", f"Unexpected error in on_finished:\n{e}")
            finally:
                if parent_window is not None:
                    parent_window._nsis_process = None
                    parent_window._nsis_progress = None

        def on_error(error):
            '''Handle process error event.'''
            try:
                _cleanup_ui()
                QMessageBox.critical(parent_window, "Compilation error",
                                     f"makensis crashed: {error}")
            except Exception as e:
                QMessageBox.critical(parent_window, "Error", f"Unexpected error in on_error:\n{e}")
            finally:
                if parent_window is not None:
                    parent_window._nsis_process = None
                    parent_window._nsis_progress = None

        def on_stdout():
            '''Handle process stdout event.'''
            try:
                out = process.readAllStandardOutput().data().decode(errors="ignore")
                print("[makensis stdout]", out)
            except Exception as e:
                print("[stdout error]", e)

        def on_stderr():
            '''Handle process stderr event.'''
            try:
                err = process.readAllStandardError().data().decode(errors="ignore")
                print("[makensis stderr]", err)
            except Exception as e:
                print("[stderr error]", e)

        # Connect signals
        process.finished.connect(on_finished)
        process.errorOccurred.connect(on_error)
        process.readyReadStandardOutput.connect(on_stdout)
        process.readyReadStandardError.connect(on_stderr)
        
        # Cancel: try graceful terminate, then force kill if needed
        def on_canceled():
            '''Handle cancel button pressed event.'''
            try:
                if process.state() != QProcess.NotRunning:
                    process.terminate()
                    if not process.waitForFinished(3000):
                        process.kill()
                _cleanup_ui()
            except Exception as e:
                QMessageBox.critical(parent_window, "Cancel error", f"Error canceling process:\n{e}")
            finally:
                if parent_window is not None:
                    parent_window._nsis_process = None
                    parent_window._nsis_progress = None

        progress.canceled.connect(on_canceled)

        # Start compilation
        process.start()
    except Exception as e:
        QMessageBox.critical(parent_window, "Compilation error", f"Unexpected error:\n{e}")


def main():
    '''Main entry point for NSI Designer application.'''
    try:
        app = QApplication([])
        settings = QSettings("NSIDesigner", "NSIDesignerApp")
        project = ProjectModel()
        project.export_dir = None
        project.has_exported_in_session = False
        nsis_path = settings.value("nsis_path", "")
        if nsis_path:
            project.nsis_path = nsis_path

        window = MainWindow(
            project=project,
            on_generate=_generate_preview_text,
            on_export=_export_project,
            on_compile=lambda p: _compile_with_nsis(p, window),
        )
        window.show()
        app.exec()
    except Exception as e:
        QMessageBox.critical(None, "Fatal error", f"Unexpected error in main:\n{e}")


if __name__ == "__main__":
    main()
