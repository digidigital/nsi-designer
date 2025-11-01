from __future__ import annotations
from typing import List
from .model import ProjectModel
import platform

GENERATOR_VERSION ='0.1.0'

def build_script(model: ProjectModel, exported_paths: dict[str, str]) -> str:
    # Resolve model values with safe fallbacks
    appname = model.app_name or "MyApp"
    version = model.version or "0.1.0"
    company = model.company_name or ""
    about = model.about_url or ""
    caption = model.caption or "Installation Wizard"
    branding = model.branding_text or ""
    compressor = model.compression or "lzma"
    install_dir = model.install_dir_base()
    reg_view_bits = model.reg_view_bits()
    exec_level = model.execution_level_macro()

    exe_path = exported_paths.get("exe_path", "")
    exe_dir = exported_paths.get("exe_dir", "").replace('/', '\\')
    exe_basename = exe_path.split("\\")[-1].split("/")[-1] if exe_path else ""

    # Detect architecture based on system and install_dir
    machine = platform.machine().lower()
    if "arm" in machine:
        arch = "ARM32" if "32" in str(reg_view_bits) else "ARM64"
    else:
        arch = "x86" if "32" in str(reg_view_bits) else "x86_64"

    out_file = f"{appname}-{version}-{arch}.exe"

    install_icon = exported_paths.get("install_icon_path")
    uninstall_icon = exported_paths.get("uninstall_icon_path")
    welcome_bmp = exported_paths.get("welcome_bitmap_path")
    license_rtf = exported_paths.get("license_file_path")

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
        "; https://github.com/digidigital/nsi-designer - Bjoern Seipel - 11.2025 ",
        ";=============================================================================",
        "",
        f'!define APPNAME "{appname}"',
        f'!define COMPANYNAME "{company}"',
        f'!define VERSION "{version}"',
        f'!define EXEFILE "{exe_basename}"',
        f'!define ABOUTURL "{about}"',
        f'OutFile "{out_file}"',
        "",
        f'Name "${{APPNAME}} ${{VERSION}}"',
        f'Caption "{caption}"',
        "",
        f'SetCompressor /SOLID {compressor}',
        f'RequestExecutionLevel {exec_level}',
        "",
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
        f'InstallDirRegKey {install_dir_reg_root} "Software\\${{APPNAME}}" "Install_Dir"',
        "",
        "Var NOICONS",
        "Var LOGFILE",
        "Var LOGHANDLE",
        "",
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
    has_env = bool(model.env_rows)
    has_env_append = any(env.mode != "set" for env in model.env_rows)

    if has_env and has_env_append:
        lines += [
            ";=============================================================================",
            ";--- Remove an element from a semicolon-separated list ---",
            "; Removes element ($1) from list ($0), cleans double/edge semicolons",
            "${Using:StrFunc} StrRep",
            "Function RemoveFromSemicolonList",
            "  Exch $1        ; Element to remove",
            "  Exch",
            "  Exch $0        ; Original list",
            "",
            "  ; Case 1: element in middle or at beginning with semicolon after",
            '  ${StrRep} $0 $0 "$1;" ""',
            "",
            "  ; Case 2: element at end with semicolon before",
            '  ${StrRep} $0 $0 ";$1" ""',
            "",
            "  ; Case 3: element alone without semicolons",
            '  ${StrRep} $0 $0 "$1" ""',
            "",
            "  ; Clean double semicolons",
            '  ${StrRep} $0 $0 ";;" ";"',
            "",
            "  ; Remove leading semicolon if present",
            "  StrCpy $2 $0 1",
            '  StrCmp $2 ";" 0 +2',
            '    StrCpy $0 $0 "" 1',
            "",
            "  ; Remove trailing semicolon if present",
            "  StrLen $3 $0",
            "  IntOp $3 $3 - 1",
            "  StrCpy $2 $0 1 $3",
            '  StrCmp $2 ";" 0 +2',
            "    StrCpy $0 $0 $3",
            "",
            "  Push $0",
            "FunctionEnd",
            "",
            ";=============================================================================",
            ";--- Remove an element from a semicolon-separated list (Uninstall variant) ---",
            "${Using:StrFunc} UnStrRep",
            "Function un.RemoveFromSemicolonList",
            "  Exch $1        ; Element to remove",
            "  Exch",
            "  Exch $0        ; Original list",
            "",
            "  ; Case 1: element in middle or at beginning with semicolon after",
            '  ${UnStrRep} $0 $0 "$1;" ""',
            "",
            "  ; Case 2: element at end with semicolon before",
            '  ${UnStrRep} $0 $0 ";$1" ""',
            "",
            "  ; Case 3: element alone without semicolons",
            '  ${UnStrRep} $0 $0 "$1" ""',
            "",
            "  ; Clean double semicolons",
            '  ${UnStrRep} $0 $0 ";;" ";"',
            "",
            "  ; Remove leading semicolon if present",
            "  StrCpy $2 $0 1",
            '  StrCmp $2 ";" 0 +2',
            '    StrCpy $0 $0 "" 1',
            "",
            "  ; Remove trailing semicolon if present",
            "  StrLen $3 $0",
            "  IntOp $3 $3 - 1",
            "  StrCpy $2 $0 1 $3",
            '  StrCmp $2 ";" 0 +2',
            "    StrCpy $0 $0 $3",
            "",
            "  Push $0",
            "FunctionEnd",
            "",
            ";=============================================================================",
            ";--- Add an element to a semicolon-separated list (no duplicates) ---",
            "Function AddToSemicolonList",
            "  Exch $1        ; Element to add",
            "  Exch",
            "  Exch $0        ; Original list",
            "",
            "  ; Remove existing occurrence to avoid duplicates",
            "  Push $0",
            "  Push $1",
            "  Call RemoveFromSemicolonList",
            "  Pop $2",
            "",
            " ; If the list changed, element was present and removed -> use updated list ($2)",
            "  StrCmp $0 $2 0 +2",
            "    StrCpy $0 $2",
            "",
            " ; Append or set depending on emptiness",
            ' StrCmp $0 "" 0 +3',
            '  StrCpy $0 "$1"',
            "  Goto doneAdd",
            ' StrCpy $0 "$0;$1"',
            "",
            " doneAdd:",
            "  Push $0",
            "FunctionEnd",
            "",
        ]

    # Install Section
    lines += [
        ";=============================================================================",
        'Section "Install"',
        f"  SetRegView {reg_view_bits}",
        f"  SetShellVarContext {'current' if model.is_per_user() else 'all'}",
        "",
        '  Push "Installation started"',
        "  Call WriteLog",
        "",
        '  SetOutPath "$INSTDIR"',
    ]
    if exe_dir:
        lines += [
            '  ; Copy application files (recursively) from exported exe directory',
            f'  File /r "{exe_dir}\\*.*"',
        ]

    # Registry rows (install)
    if model.registry_rows:
        lines.append("")
        lines.append("  ; Write custom registry entries")
        lines.append('  Push "Writing custom registry entries"')
        lines.append("  Call WriteLog")
        for row in model.registry_rows:
            root = row.root or ("HKCU" if model.is_per_user() else "HKLM")
            key = (row.key or "").replace("\\", "\\\\")
            value = row.value or ""
            data = row.data or ""
            if getattr(row, "reg_type", "string") == "dword":
                lines.append(f'  WriteRegDWORD {root} "{key}" "{value}" {data}')
                lines.append(f'  Push "WriteRegDWORD {root} {key} {value}={data}"')
                lines.append("  Call WriteLog")
            else:
                lines.append(f'  WriteRegStr {root} "{key}" "{value}" "{data}"')
                lines.append(f'  Push "WriteRegStr {root} {key} {value}={data}"')
                lines.append("  Call WriteLog")
        # Notify system (potential changes to shell once after env updates
        lines += [
            "  ; Notify system about ptential shell changes",
            '  Push "Trigger ShellChangeNotify"',
            "  Call WriteLog",
            "  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0x0000, p 0, p 0)'",
        ]

    # Environment variables (install)
    if has_env:
        lines += [
            "",
            "  ; Environment variables (switch to system-wide)",
            "  SetRegView 64",
            "  ; Environment variables: set or append to existing semicolon-separated lists",

        ]
        for env in model.env_rows:
            name = env.name or ""
            val = env.value or ""
            root, env_key = ("HKCU", r"Environment") if model.is_per_user() else (
                "HKLM", r"SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment")

            if env.mode == "set":
                lines.append(f'  ; Set {name} to provided value (overwrites existing)')
                lines.append(f'  Push "Setting environment variable {name}={val}"')
                lines.append("  Call WriteLog")
                lines.append(f'  WriteRegExpandStr {root} "{env_key}" "{name}" "{val}"')
            else:
                # Append mode: add to existing list robustly
                lines += [
                    f'  ; Append value to {name} without duplicates',
                    f'  Push "Appending to environment variable {name}: {val}"',
                    "  Call WriteLog",
                    f'  ReadRegStr $0 {root} "{env_key}" "{name}"',
                    '  Push "$0"',
                    f'  Push "{val}"',
                    '  Call AddToSemicolonList',
                    '  Pop $1',
                    f'  WriteRegExpandStr {root} "{env_key}" "{name}" "$1"',
                ]

        # Notify system once after env updates
        lines += [
            "  ; Notify system about environment variable changes",
            '  Push "Broadcasting WM_SETTINGCHANGE for Environment"',
            "  Call WriteLog",
            "  System::Call 'User32::SendMessageTimeoutW(i 0xffff, i ${WM_SETTINGCHANGE}, i 0, w \"Environment\", i 0, i 5000, *i .r0)'",
        ]

    lines += [
        "",
        "  ; Uninstall registration (Add/Remove Programs)",
        "  SetRegView 64",
        '  Push "Registering uninstaller in Add/Remove Programs"',
        "  Call WriteLog",
        f'  WriteRegStr {uninstall_root} "Software\\${{APPNAME}}" "Install_Dir" "$INSTDIR"',
        f'  WriteRegStr {uninstall_root} "Software\\${{APPNAME}}" "Publisher" "${{COMPANYNAME}}"',
        f'  WriteRegStr {uninstall_root} "Software\\${{APPNAME}}" "Version" "${{VERSION}}"',
        f'  WriteRegStr {uninstall_root} "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "DisplayName" "${{APPNAME}} ${{VERSION}}"',
        f'  WriteRegStr {uninstall_root} "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "DisplayVersion" "${{VERSION}}"',
        f'  WriteRegStr {uninstall_root} "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "UninstallString" \'"$INSTDIR\\Uninstall.exe"\'',
        f'  WriteRegStr {uninstall_root} "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "QuietUninstallString" \'"$INSTDIR\\Uninstall.exe" /S\'',
        f'  WriteRegStr {uninstall_root} "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "DisplayIcon" "$INSTDIR\\{exe_basename}"',
        f'  WriteRegStr {uninstall_root} "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "Publisher" "${{COMPANYNAME}}"',
        f'  WriteRegExpandStr {uninstall_root} "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "InstallLocation" "$INSTDIR"',
        '  WriteUninstaller "$INSTDIR\\Uninstall.exe"',
        "",
        "  ; Shortcuts",
        '  StrCmp $NOICONS "1" skipShortcuts',
        '    Push "Creating shortcuts"',
        "    Call WriteLog",
        f'    CreateDirectory "$SMPROGRAMS\\${{APPNAME}}"',
        f'    CreateShortCut "$SMPROGRAMS\\${{APPNAME}}\\${{APPNAME}}.lnk" "$INSTDIR\\{exe_basename}"',
        f'    CreateShortCut "$DESKTOP\\${{APPNAME}}.lnk" "$INSTDIR\\{exe_basename}"',
        "  skipShortcuts:",
        "",
        '  Push "Installation finished successfully"',
        "  Call WriteLog",
        "SectionEnd",
        "",
    ]
    # Uninstall Section
    lines += [
        ";=============================================================================",
        'Section "Uninstall"',
        f"  SetRegView {reg_view_bits}",
        f"  SetShellVarContext {'current' if model.is_per_user() else 'all'}",
        "",
        "  ; Remove shortcuts",
        f'  Delete "$SMPROGRAMS\\${{APPNAME}}\\${{APPNAME}}.lnk"',
        f'  RMDir "$SMPROGRAMS\\${{APPNAME}}"',
        f'  Delete "$DESKTOP\\${{APPNAME}}.lnk"',
    ]

    # Registry rows removal (mirror of install writes)
    if model.registry_rows:
        lines += [
            "",
            "  ; Remove custom registry entries (mirrors install writes)",
        ]
        for row in model.registry_rows:
            root = row.root or ("HKCU" if model.is_per_user() else "HKLM")
            key = (row.key or "").replace("\\", "\\\\")
            value = row.value or ""
            lines.append(f'  DeleteRegValue {root} "{key}" "{value}"')
            lines.append(f'  DeleteRegKey /ifempty {root} "{key}"')
        
        # Notify system (potential changes to shell once after env updates
        lines += [
            "  ; Notify system about ptential shell changes",
            "  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0x0000, p 0, p 0)'",
        ]   

    # Always remove uninstall keys
    lines += [
        "",
        "  ; Remove uninstall registry keys",
        "  SetRegView 64",
        f'  DeleteRegKey {uninstall_root} "Software\\${{APPNAME}}"',
        f'  DeleteRegKey {uninstall_root} "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}"',
    ]

    # Environment variable removals (uninstall)
    if has_env:
        lines += [
            " ; Environment variables (system-wide)",
            " SetRegView 64",
            "",
            "  ; Remove or update environment variables",
        ]
        for env in model.env_rows:
            name = env.name or ""
            val = env.value or ""
            root, env_key = ("HKCU", r"Environment") if model.is_per_user() else (
                "HKLM", r"SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment")

            if env.mode == "set":
                lines.append(f'  ; Delete variable {name} (was set by installer)')
                lines.append(f'  DeleteRegValue {root} "{env_key}" "{name}"')
            else:
                # Append-mode uninstall: remove appended fragment robustly
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

    script = "\n".join(lines)
    return script