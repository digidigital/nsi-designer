from __future__ import annotations
from dataclasses import dataclass, field, fields, asdict
from typing import List, Dict, Any, Optional
import json
import os


REG_ROOT_OPTIONS = ["HKLM", "HKCU"]
ENV_MODE_OPTIONS = ["set", "append"]

# Available NSIS languages (European and American) mapped to NSIS macro codes
AVAILABLE_LANGUAGES = [
    "English", "German", "French", "Spanish", "Italian", "Portuguese",
    "Dutch", "Danish", "Swedish", "Norwegian", "Finnish", "Polish", "Czech",
    "Hungarian", "Romanian", "Ukrainian"
]

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

ICON_PATH = os.path.join(current_dir, 'images', 'generic.ico')
BMP_PATH = os.path.join(current_dir, 'images', 'generic.png')

@dataclass
class RegistryRow:
    """Represents a single registry entry to be written by the installer."""
    root: str = "HKLM"  # e.g., HKLM
    key: str = ""       # e.g., Software\\MyApp
    value: str = ""     # e.g., Install_Dir
    data: str = ""      # e.g., $INSTDIR
    reg_type: str = "string"  # "string" or "dword"


@dataclass
class EnvRow:
    """Represents a single environment variable change."""
    name: str = ""      # e.g., PATH
    value: str = ""     # e.g., ;$INSTDIR\bin (if append) or exact value (if set)
    mode: str = "set"   # "set" or "append"


@dataclass
class ProjectModel:
    """
    Stores all fields required by the application and generator.
    """
    # Metadata
    app_name: str = "MyApp"
    company_name: str = "MyCompany"
    version: str = "0.1.0"
    caption: str = "Installation Wizard"
    about_url: str = ""
    help_url: str = ""
    branding_text: str = "A John Doe project"
    exe_path: str = ""  # Selected .exe path
    estimated_size: int = 0
    update_url: str = ""
    comments: str = "" 
    contact: str = "" 

    # Presets
    install_dir_preset: str = "64-bit"  # "64-bit", "32-bit", "Per-user"
    exec_level: str = "admin"           # "admin", "user"
    scope: str = "System-wide"          # "System-wide", "Per-user"

    # Assets (store selected path and preferred format)
    install_icon_path: str = f"{ICON_PATH}"
    install_icon_format: str = "ico"  # ico, png, jpg
    uninstall_icon_path: str = f"{ICON_PATH}"
    uninstall_icon_format: str = "ico"
    welcome_bitmap_path: str = f"{BMP_PATH}"
    welcome_bitmap_format: str = "bmp"  # bmp, png, jpg
    license_file_path: str = ""         # RTF only

    # Languages
    languages: List[str] = field(default_factory=lambda: ["English"])

    # Registry and environment
    registry_rows: List[RegistryRow] = field(default_factory=list)
    env_rows: List[EnvRow] = field(default_factory=list)

    # Compression and export
    compression: str = "lzma"
    encoding: str = "ANSI"  # "UTF-8" or "ANSI"
    export_dir: str = ""

    # NSIS integration
    nsis_path: str = ""  # path to makensis.exe

    def to_json(self) -> str:
        """Serialize the project to JSON string."""
        return json.dumps(asdict(self), indent=2)

    @staticmethod
    def from_json(data: str) -> "ProjectModel":
        obj = json.loads(data)

        reg_rows = [RegistryRow(**row) for row in obj.get("registry_rows", [])]
        env_rows = [EnvRow(**row) for row in obj.get("env_rows", [])]

        # Only keep keys that match ProjectModel fields
        valid_field_names = {f.name for f in fields(ProjectModel)}
        filtered_obj = {k: v for k, v in obj.items() if k in valid_field_names and k not in ("registry_rows", "env_rows")}

        return ProjectModel(
            registry_rows=reg_rows,
            env_rows=env_rows,
            **filtered_obj
        )

    def is_per_user(self) -> bool:
        """Return True if scope or preset implies per-user context."""
        return self.scope == "Per-user" or self.install_dir_preset == "Per-user"

    def install_dir_base(self) -> str:
        """Return InstallDir base path depending on preset."""
        if self.install_dir_preset == "64-bit":
            return r"$PROGRAMFILES64\${APPNAME}"
        elif self.install_dir_preset == "32-bit":
            return r"$PROGRAMFILES32\${APPNAME}"
        else:
            # Per-user (use LocalAppData by default)
            return r"$LOCALAPPDATA\${APPNAME}"

    def reg_view_bits(self) -> int:
        """Return 64 or 32 depending on preset."""
        if self.install_dir_preset == "64-bit":
            return 64
        elif self.install_dir_preset == "32-bit":
            return 32
        else:
            # Per-user: reg view can follow OS bitness; default to 64 for modern Windows
            return 64

    def execution_level_macro(self) -> str:
        """Return NSIS RequestExecutionLevel."""
        return "admin" if self.exec_level == "admin" else "user"

    def encoding_codec(self) -> str:
        """Return Python codec name based on encoding selection."""
        return "utf-8" if self.encoding == "UTF-8" else "mbcs"
