from __future__ import annotations
from typing import List
from copy import deepcopy
from .model import ProjectModel
import re
import platform

GENERATOR_VERSION = '0.1.3'

def normalize_registry_key(key: str) -> str:
    if not isinstance(key, str):
        return ""
    normalized = re.sub(r'(?<!\\)\\(?!\\)', r'\\\\', key)
    normalized = normalized.strip("\\")
    return normalized

def normalize_registry_rows(rows: List, default_hive: str, adjustments: List[str]) -> List:
    normalized_registry_rows = []
    for row in rows:
        normalized_row = deepcopy(row)
        original_root = normalized_row.root or default_hive
        if original_root not in ("HKLM", "HKCU"):
            adjustments.append(
                f"Registry root '{original_root}' corrected to '{default_hive}' (unsupported or inconsistent)"
            )
            normalized_row.root = default_hive
        elif original_root != default_hive:
            adjustments.append(
                f"Registry root '{original_root}' corrected to '{default_hive}' (scope-based default)"
            )
            normalized_row.root = default_hive

        raw_key = normalized_row.key or ""
        normalized_key = normalize_registry_key(raw_key)


        if not normalized_row.key.strip or not (normalized_row.data or "").strip():

            adjustments.append(f"Registry row skipped due to empty sub-key/value (sub-key={normalized_row.key},  value={normalized_row.data})")
            continue

        if getattr(normalized_row, "reg_type", "string") == "dword":
            data_str = (normalized_row.data or "").strip()
            if not is_valid_dword(data_str):
                adjustments.append(
                    f"Registry DWORD skipped due to invalid numeric data: '{normalized_row.data}' "
                    f"at {normalized_row.root}\\{normalized_key}\\{normalized_row.value}"
                )
                continue

        normalized_row.key = normalized_key
        normalized_registry_rows.append(normalized_row)

    return normalized_registry_rows

def build_script(model: ProjectModel, exported_paths: dict[str, str]) -> str:
    validate_presets(model)
    adjustments: List[str] = []

    derived_exec_level = "user" if model.is_per_user() else "admin"
    exec_level = derived_exec_level
    if model.execution_level_macro() != derived_exec_level:
        adjustments.append(
            f"Execution level corrected: '{model.exec_level}' -> '{derived_exec_level}' (derived from scope)"
        )

    appname = sanitize_values(model.app_name) or "App without a name"
    version = sanitize_values(model.version) or "0.1.0"
    company = sanitize_values(model.company_name) or "Unknown Company"
    about = sanitize_values(model.about_url, mode="registry") or ""
    comments = sanitize_values(model.comments) or ""
    contact = sanitize_values(model.contact, mode="registry") or ""
    update = sanitize_values(model.update_url, mode="registry") or ""
    help_url = sanitize_values(model.help_url, mode="registry") or ""
    caption = sanitize_values(model.caption) or "Installation Wizard"
    branding = sanitize_values(model.branding_text) or ""
    size = model.estimated_size or 0
    encoding = model.encoding or "ANSI"
    compressor = model.compression or "lzma"
    install_dir = model.install_dir_base()
    reg_view_bits = model.reg_view_bits()
    exe_path = exported_paths.get("exe_path", "")
    exe_dir = exported_paths.get("exe_dir", "").replace('/', '\\')
    exe_basename = exe_path.split("\\")[-1].split("/")[-1] if exe_path else ""

    if not exe_basename:
        raise ValueError('No executable file selected')

    machine = platform.machine().lower()
    if "arm" in machine:
        arch = "ARM32" if "32" in str(reg_view_bits) else "ARM64"
    else:
        arch = "x86" if "32" in str(reg_view_bits) else "x86_64"

    out_file = f"{appname}-{version}-{arch}.exe"  
    out_file = sanitize_values(out_file).replace(' ', '_')

    install_icon = exported_paths.get("install_icon_path")
    uninstall_icon = exported_paths.get("uninstall_icon_path")
    welcome_bmp = exported_paths.get("welcome_bitmap_path")
    license_rtf = exported_paths.get("license_file_path")

    default_hive = "HKCU" if model.is_per_user() else "HKLM"
    uninstall_root = "HKCU" if model.is_per_user() else "HKLM"
    install_dir_reg_root = "HKCU" if model.is_per_user() else "HKLM"

    languages = model.languages[:]
    if "English" not in languages:
        languages.insert(0, "English")

    lines: List[str] = []
    lines += [
        ";=============================================================================",
        f"; {appname} Installer",
        f"; Generated with NSI Designer {GENERATOR_VERSION}",  
        "; (Tested with NSIS 3.11)",
        "; https://github.com/digidigital/nsi-designer",
        ";",
        "; SYNOPSIS",
        f";   {out_file} [/S] [/NOICONS] [/LOG[=FILE]] [/D=PATH]",
        ";",
        "; OPTIONS",
        ";   /S",
        ";       Run the installer silently (no UI)",
        ";",
        ";   /NOICONS",
        ";       Suppress creation of desktop and Start Menu shortcuts",
        ";",
        ";   /LOG[=FILE]",
        ";       Enable logging. If FILE (Path with filename) is given, log is written there",
        f";       If FILE is omitted, defaults to %TEMP%\\{appname}_install.log",
        ";",
        ";   /D=PATH",
        ";       Override installation directory", 
        ";       (must be the last argument and WITHOUT quotation marks)",
        ";=============================================================================",
        "Unicode true" if encoding == "UTF-8" else "; ANSI Installer",
        "",
        f'!define APPNAME "{appname}"',
        f'!define COMPANYNAME "{company}"',
        f'!define VERSION "{version}"',
        f'!define EXEFILE "{exe_basename}"',
        f'!define ABOUTURL "{about}"',
        f'!define HELPLINK "{help_url}"',
        f'!define UPDATEURL "{update}"',
        f'!define SIZE {size}',
        f'!define COMMENTS "{comments}"',
        f'!define CONTACT "{contact}"',
        f'OutFile "{out_file}"',
        "",
        f'Name "${{APPNAME}} ${{VERSION}}"',
        f'Caption "{caption}"',
        "",
        f'SetCompressor /SOLID {compressor}',
        f'RequestExecutionLevel {exec_level}',
        "",
        "!include \"WinMessages.nsh\"",
        "!include \"MUI2.nsh\"",
        "!include \"FileFunc.nsh\"",
        "!include \"StrFunc.nsh\"",
        "!insertmacro GetParameters",
        "!insertmacro GetOptions",
        "!insertmacro GetParent",
        "",
        f'!define MUI_PRODUCT "${{APPNAME}}"',
        f'!define MUI_VERSION "${{VERSION}}"',
    ]
    if install_icon:
        lines.append(f'!define MUI_ICON "{install_icon}"')
    if uninstall_icon:
        lines.append(f'!define MUI_UNICON "{uninstall_icon}"')
    if welcome_bmp:
        lines.append(f'!define MUI_WELCOMEFINISHPAGE_BITMAP "{welcome_bmp}"')

    lines.append("")
    if welcome_bmp:
        lines.append('!insertmacro MUI_PAGE_WELCOME')
    if license_rtf:
        lines.append(f'!insertmacro MUI_PAGE_LICENSE "{license_rtf}"')
    lines += [
        "!insertmacro MUI_PAGE_DIRECTORY",
        "!insertmacro MUI_PAGE_INSTFILES",
        "!insertmacro MUI_UNPAGE_CONFIRM",
        "!insertmacro MUI_UNPAGE_INSTFILES",
        "",
    ]
    for lang in languages:
        lines.append(f'!insertmacro MUI_LANGUAGE "{lang}"')
    lines.append("")
    if branding:
        lines.append(f'BrandingText "{branding}"')
    lines.append("")
    lines += [
        f'InstallDir "{install_dir}"',
        f'InstallDirRegKey {install_dir_reg_root} "Software\\\\${{APPNAME}}" "Install_Dir"',
        "",
        "Var NOICONS",
        "Var LOGFILE",
        "Var LOGHANDLE",
    ]
    lines += [
        ";=============================================================================",
        ";--- Helper: write a message to log file if logging is enabled ---",
        "Function WriteLog",
        "  Exch $0",
        '  StrCmp $LOGHANDLE "" 0 +3',
        "    Exch $0",
        "    Return",
        '  FileWrite $LOGHANDLE "$0$\\r$\\n"',
        "  Exch $0",
        "FunctionEnd",
        "",
        ";=============================================================================",
        ";--- Init: parse /NOICONS and /LOG[=FILE] ---",
        "Function .onInit",
        "  ${GetParameters} $R0",
        "",
        "  ClearErrors",
        '  ${GetOptions} $R0 "/NOICONS" $R1',
        "  IfErrors +2",
        '    StrCpy $NOICONS "1"',
        "",
        "  ClearErrors",
        '  ${GetOptions} $R0 "/LOG=" $R1',
        "  IfErrors tryPlainLog",
        "    StrCpy $LOGFILE $R1",
        "    Goto setupLog",
        "",
        "  tryPlainLog:",
        "  ClearErrors",
        '  ${GetOptions} $R0 "/LOG" $R1',
        "  IfErrors endLog",
        '    StrCpy $LOGFILE "$TEMP\\${APPNAME}_install.log"',
        "    Goto setupLog",
        "",
        "  setupLog:",
        "    ${GetParent} $LOGFILE $R2",
        '    CreateDirectory "$R2"',
        "    ClearErrors",
        "    FileOpen $LOGHANDLE $LOGFILE w",
        "    IfErrors 0 +3",
        '      MessageBox MB_ICONEXCLAMATION "Failed to open log file: $LOGFILE"',
        '      StrCpy $LOGHANDLE ""',
        '    Push "Logging enabled: $LOGFILE"',
        "    Call WriteLog",
        "",
        "  endLog:",
        "FunctionEnd",
        "",
    ]

    # --- Conditionally add semicolon list helpers if environment variables need append/remove ---
    has_env = bool(model.env_rows)
    has_env_append = any(env.mode != "set" for env in model.env_rows)
    if has_env and has_env_append:
        lines += [
            ";=============================================================================",
            ";--- Remove an element from a semicolon-separated list ---",
            "${Using:StrFunc} StrRep",
            "Function RemoveFromSemicolonList",
            "  Exch $1",
            "  Exch",
            "  Exch $0",
            '  ${StrRep} $0 $0 "$1;" ""',
            '  ${StrRep} $0 $0 ";$1" ""',
            '  ${StrRep} $0 $0 "$1" ""',
            '  ${StrRep} $0 $0 ";;" ";"',
            "  StrCpy $2 $0 1",
            '  StrCmp $2 ";" 0 +2',
            '    StrCpy $0 $0 "" 1',
            "  StrLen $3 $0",
            "  IntOp $3 $3 - 1",
            "  StrCpy $2 $0 1 $3",
            '  StrCmp $2 ";" 0 +2',
            "    StrCpy $0 $0 $3",
            "  Push $0",
            "FunctionEnd",
            "",
            ";=============================================================================",
            ";--- Remove an element from a semicolon-separated list (Uninstall variant) ---",
            "${Using:StrFunc} UnStrRep",
            "Function un.RemoveFromSemicolonList",
            "  Exch $1",
            "  Exch",
            "  Exch $0",
            '  ${UnStrRep} $0 $0 "$1;" ""',
            '  ${UnStrRep} $0 $0 ";$1" ""',
            '  ${UnStrRep} $0 $0 "$1" ""',
            '  ${UnStrRep} $0 $0 ";;" ";"',
            "  StrCpy $2 $0 1",
            '  StrCmp $2 ";" 0 +2',
            '    StrCpy $0 $0 "" 1',
            "  StrLen $3 $0",
            "  IntOp $3 $3 - 1",
            "  StrCpy $2 $0 1 $3",
            '  StrCmp $2 ";" 0 +2',
            "    StrCpy $0 $0 $3",
            "  Push $0",
            "FunctionEnd",
            "",
            ";=============================================================================",
            ";--- Add an element to a semicolon-separated list (no duplicates) ---",
            "Function AddToSemicolonList",
            "  Exch $1",
            "  Exch",
            "  Exch $0",
            "  Push $0",
            "  Push $1",
            "  Call RemoveFromSemicolonList",
            "  Pop $2",
            "  StrCmp $0 $2 0 +2",
            "    StrCpy $0 $2",
            ' StrCmp $0 "" 0 +3',
            '  StrCpy $0 "$1"',
            "  Goto doneAdd",
            ' StrCpy $0 "$0;$1"',
            " doneAdd:",
            "  Push $0",
            "FunctionEnd",
            "",
        ]
    # --- Rule B/G: Normalize registry rows (auto-correct hive; skip invalid key/value; validate dword numeric) ---
    normalized_registry_rows = normalize_registry_rows(model.registry_rows, default_hive, adjustments)
    lines += [
        ";=============================================================================",
        'Section "Install"',
        f"  SetRegView {reg_view_bits}",
        f"  SetShellVarContext {'current' if model.is_per_user() else 'all'}",
        "",
        '  Push "Installation started"',
        "  Call WriteLog",
        "",
        "  SetOutPath \"$INSTDIR\"",
        "  ; Copy application files (recursively) from exported exe directory",
        f'  File /r "{exe_dir}\\*.*"',
        "",
    ]

    if normalized_registry_rows:
        lines += [
            "  ; Write custom registry entries",
            '  Push "Writing custom registry entries"',
            "  Call WriteLog",
        ]
        for row in normalized_registry_rows:
            root = row.root or default_hive
            key = row.key or ""
            value = row.value or ""
            data = row.data or ""
            reg_type = getattr(row, "reg_type", "string")

            if reg_type == "string":
                lines.append(f'  WriteRegStr {root} "{key}" \'{value}\' \'{data}\'')
                lines.append(f'  Push \'WriteRegStr {root} {key} {value}={data}\'')
                lines.append("  Call WriteLog")
            elif reg_type == "dword":
                lines.append(f'  WriteRegDWORD {root} "{key}" \'{value}\' {data}')
                lines.append(f'  Push \'WriteRegDWORD {root} {key} {value}={data}\'')
                lines.append("  Call WriteLog")

        lines += [
            "  ; Notify system about potential shell changes",
            '  Push "Trigger ShellChangeNotify"',
            "  Call WriteLog",
            "  System::Call \'shell32::SHChangeNotify(i 0x08000000, i 0x0000, p 0, p 0)\'",
        ]

    # Environment variables (install)
    if has_env:
        lines += [
            "",
            "  ; Environment variables",
            "  SetRegView 64" if not model.is_per_user() else "  ; HKCU (per-user) does not require specific RegView",
            "  ; Environment variables: set or append to existing semicolon-separated lists",
        ]
        for env in model.env_rows:
            name = env.name or ""
            val = env.value or ""
            root, env_key = ("HKCU", r"Environment") if model.is_per_user() else (
                "HKLM", "SYSTEM\\\\CurrentControlSet\\\\Control\\\\Session Manager\\\\Environment")

            if env.mode == "set":
                lines.append(f'  ; Set {name} to provided value (overwrites existing)')
                lines.append(f'  Push "Setting environment variable {name}={val}"')
                lines.append("  Call WriteLog")
                lines.append(f'  WriteRegExpandStr {root} "{env_key}" \'{name}\' \'{val}\'')
            else:
                lines += [
                    f'  ; Append value to {name} without duplicates',
                    f'  Push "Appending to environment variable {name}: {val}"',
                    "  Call WriteLog",
                    f'  ReadRegStr $0 {root} "{env_key}" "{name}"',
                    '  Push "$0"',
                    f'  Push "{val}"',
                    '  Call AddToSemicolonList',
                    '  Pop $1',
                    f'  WriteRegExpandStr {root} "{env_key}" \'{name}\' "$1"',
                ]

        lines += [
            "  ; Notify system about environment variable changes",
            '  Push "Broadcasting WM_SETTINGCHANGE for Environment"',
            "  Call WriteLog",
            "  System::Call \'User32::SendMessageTimeoutW(i 0xffff, i ${WM_SETTINGCHANGE}, i 0, w \"Environment\", i 0, i 5000, *i .r0)\'",
        ]

    lines += [
        "",
        "  ; Uninstall registration (Add/Remove Programs)",
        "  SetRegView 64",
        '  Push "Registering uninstaller in Add/Remove Programs"',
        "  Call WriteLog",
        f'  WriteRegStr {uninstall_root} "Software\\\\${{APPNAME}}" "Install_Dir" "$INSTDIR"',
        f'  WriteRegStr {uninstall_root} "Software\\\\${{APPNAME}}" "Publisher" "${{COMPANYNAME}}"',
        f'  WriteRegStr {uninstall_root} "Software\\\\${{APPNAME}}" "Version" "${{VERSION}}"',
        f'  WriteRegStr {uninstall_root} "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\${{APPNAME}}" "DisplayName" \'${{APPNAME}} ${{VERSION}}\'',
        f'  WriteRegStr {uninstall_root} "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\${{APPNAME}}" "DisplayVersion" \'${{VERSION}}\'',
        f'  WriteRegStr {uninstall_root} "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\${{APPNAME}}" "UninstallString" \'"$INSTDIR\\\\Uninstall.exe"\'',
        f'  WriteRegStr {uninstall_root} "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\${{APPNAME}}" "QuietUninstallString" \'"$INSTDIR\\\\Uninstall.exe" /S\'',
        f'  WriteRegStr {uninstall_root} "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\${{APPNAME}}" "DisplayIcon" \'"$INSTDIR\\\\${{EXEFILE}}"\'',
        f'  WriteRegStr {uninstall_root} "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\${{APPNAME}}" "Publisher" \'${{COMPANYNAME}}\'',
        f'  WriteRegExpandStr {uninstall_root} "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\${{APPNAME}}" "InstallLocation" \'$INSTDIR\'',
        f'  WriteRegStr {uninstall_root} "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\${{APPNAME}}" "HelpLink" \'${{HELPLINK}}\'' if help_url else '  ; Skipping HelpLink',
        f'  WriteRegStr {uninstall_root} "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\${{APPNAME}}" "URLInfoAbout" \'${{ABOUTURL}}\'' if about else '  ; Skipping URLInfoAbout',
        f'  WriteRegStr {uninstall_root} "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\${{APPNAME}}" "Contact" \'${{CONTACT}}\'' if contact else '  ; Skipping Contact email',
        f'  WriteRegStr {uninstall_root} "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\${{APPNAME}}" "Comments" \'${{COMMENTS}}\'' if comments else '  ; Skippping Comments',
        f'  WriteRegStr {uninstall_root} "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\${{APPNAME}}" "UpdateURL" \'${{UPDATEURL}}\'' if update else '  ; Skipping UpdateURL',
        f'  WriteRegDWORD {uninstall_root} "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\${{APPNAME}}" "EstimatedSize" ${{SIZE}}' if size else '  ; Skipping EstimatedSize',
        f'  WriteRegDWORD {uninstall_root} "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\${{APPNAME}}" "NoModify" 1',
        f'  WriteRegDWORD {uninstall_root} "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\${{APPNAME}}" "NoRepair" 1',
        '  WriteUninstaller "$INSTDIR\\\\Uninstall.exe"',
        "",
        "  ; Shortcuts",
        '  StrCmp $NOICONS "1" skipShortcuts',
        '    Push "Creating shortcuts"',
        "    Call WriteLog",
        f'    CreateDirectory "$SMPROGRAMS\\\\${{APPNAME}}"',
        f'    CreateShortCut "$SMPROGRAMS\\\\${{APPNAME}}\\\\${{APPNAME}}.lnk" "$INSTDIR\\\\${{EXEFILE}}"',
        f'    CreateShortCut "$DESKTOP\\\\${{APPNAME}}.lnk" "$INSTDIR\\\\${{EXEFILE}}"',
        "  skipShortcuts:",
        "",
        '  Push "Installation finished successfully"',
        "  Call WriteLog",
        "SectionEnd",
    ]
    lines += [
        ";=============================================================================",
        'Section "Uninstall"',
        f"  SetRegView {reg_view_bits}",
        f"  SetShellVarContext {'current' if model.is_per_user() else 'all'}",
        "",
        "  ; Remove shortcuts",
        f'  Delete "$SMPROGRAMS\\\\${{APPNAME}}\\\\${{APPNAME}}.lnk"',
        f'  RMDir "$SMPROGRAMS\\\\${{APPNAME}}"',
        f'  Delete "$DESKTOP\\\\${{APPNAME}}.lnk"',
    ]

    if normalized_registry_rows:
        lines += [
            "",
            "  ; Remove custom registry entries (mirrors install writes)",
        ]
        for row in normalized_registry_rows:
            root = row.root or default_hive
            key = (row.key or "").strip("\\")
            value = row.value or ""
            lines.append(f'  DeleteRegValue {root} "{key}" "{value}"')
            lines.append(f'  DeleteRegKey /ifempty {root} "{key}"')
        
        lines += [
            "  ; Notify system about potential shell changes",
            "  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0x0000, p 0, p 0)'",
        ]

    lines += [
        "",
        "  ; Remove uninstall registry keys",
        "  SetRegView 64",
        f'  DeleteRegKey {uninstall_root} "Software\\\\${{APPNAME}}"',
        f'  DeleteRegKey {uninstall_root} "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Uninstall\\\\${{APPNAME}}"',
    ]

    if has_env:
        lines += [
            " ; Environment variables",
            " SetRegView 64" if not model.is_per_user() else "  ; HKCU (per-user) does not require specific RegView",
            "",
            "  ; Remove or update environment variables",
        ]
        for env in model.env_rows:
            name = env.name or ""
            val = env.value or ""
            root, env_key = ("HKCU", r"Environment") if model.is_per_user() else (
                "HKLM", "SYSTEM\\\\CurrentControlSet\\\\Control\\\\Session Manager\\\\Environment")

            if env.mode == "set":
                lines.append(f'  ; Delete variable {name} (was set by installer)')
                lines.append(f'  DeleteRegValue {root} "{env_key}" "{name}"')
            else:
                lines += [
                    f'  ; Remove appended fragment from {name}',
                    f'  ReadRegStr $0 {root} "{env_key}" "{name}"',
                    f'  StrCmp "$0" "" done_{name}',

                    '  Push "$0"',
                    f'  Push "{val}"',
                    '  Call un.RemoveFromSemicolonList',
                    '  Pop $1',

                    f'  StrCmp $1 "" 0 write_{name}',
                    f'    DeleteRegValue {root} "{env_key}" "{name}"',
                    f'    Goto done_{name}',

                    f'  write_{name}:',
                    f'    WriteRegExpandStr {root} "{env_key}" "{name}" "$1"',

                    f'  done_{name}:',
                ]

        lines += [
            "  ; Notify system about environment variable changes",
            "  System::Call 'User32::SendMessageTimeoutW(i 0xffff, i ${WM_SETTINGCHANGE}, i 0, w \"Environment\", i 0, i 5000, *i .r0)'",
        ]

    lines += [
        "",
        '  ; Remove installed directory recursively',
        '  RMDir /r "$INSTDIR"',
        "",
        "SectionEnd",
    ]
    if adjustments:
        lines += [
            "",
            ";=============================================================================",
            "; Automatic adjustments",
            "; The generator applied the following corrections for consistency and robustness:",
        ]
        for note in adjustments:
            lines.append(f"; - {note}")
        lines += [
            ";=============================================================================",
            "",
        ]

    script = "\n".join(lines)
    return script


def sanitize_values(name: str, mode: str = "auto") -> str:
    if not isinstance(name, str):
        raise TypeError("Name must be a string")

    if mode == "auto":
        lowered = name.lower().strip()
        if lowered.endswith((".exe", ".com", ".bat", ".cmd", ".msi")):
            mode = "file"
        else:
            mode = "registry"

    sanitized = name
    if mode == "file":
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", sanitized)
    elif mode == "registry":
        sanitized = re.sub(r'[\\]', "_", sanitized)
        sanitized = re.sub(r'[\x00-\x1F]', "_", sanitized)
    else:
        raise ValueError("Mode must be 'file', 'registry', or 'auto'")

    sanitized = re.sub(r'[\x00-\x1F]', "_", sanitized)
    sanitized = re.sub(r'_+', "_", sanitized)
    sanitized = sanitized.strip("_")
    return sanitized


def validate_presets(model) -> None:
    preset = model.install_dir_preset
    scope = model.scope
    level = model.exec_level

    if preset == "Per-user" and scope != "Per-user":
        raise ValueError(
            f"Invalid combination: install_dir_preset='{preset}' requires scope='Per-user', "
            f"but scope='{scope}' was chosen."
        )
    if scope == "Per-user" and level != "user":
        raise ValueError(
            f"Invalid combination: scope='Per-user' requires exec_level='user', "
            f"but exec_level='{level}' was chosen."
        )
    if scope == "System-wide" and level != "admin":
        raise ValueError(
            f"Invalid combination: scope='System-wide' requires exec_level='admin', "
            f"but exec_level='{level}' was chosen."
        )
    if preset in ("64-bit", "32-bit") and scope != "System-wide":
        raise ValueError(
            f"Invalid combination: install_dir_preset='{preset}' requires scope='System-wide', "
            f"but scope='{scope}' was chosen."
        )
    return


def is_valid_dword(value: str) -> bool:
    v = value.strip()
    if not v:
        return False
    if v.lower().startswith("0x"):
        try:
            int(v, 16)
            return True
        except ValueError:
            return False
    try:
        int(v, 10)
        return True
    except ValueError:
        return False
