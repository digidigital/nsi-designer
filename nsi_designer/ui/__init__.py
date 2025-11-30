"""
__init__.py
-----------
This file marks the `ui` directory as a Python package and provides a clear overview
of the modularized UI components for the NSI Script Designer.

Contents:
- Exposes the main UI classes and widgets so they can be imported directly from `ui`.
- Documents the structure of the package for maintainers and Copilot.

Modules:
- main_window.py   → MainWindow (central application window)
- dialogs.py       → LanguageDialog (modal dialog for language selection)
- forms_metadata.py→ MetadataForm (application metadata fields + executable row)
- forms_presets.py → PresetsForm (install location, execution level, scope)
- forms_assets.py  → AssetsForm (installer assets: icons, bitmaps, license file)
- tables_registry.py→ RegistryTable (registry entries table)
- tables_env.py    → EnvTable (environment variables table)
- helpers.py       → AutoLabel, calc_estimated_size_kb, choose_asset (shared utilities)
"""

from .main_window import MainWindow
from .dialogs import LanguageDialog
from .forms_metadata import MetadataForm
from .forms_presets import PresetsForm
from .forms_assets import AssetsForm
from .tables_registry import RegistryTable
from .tables_env import EnvTable
from .helpers import AutoLabel, calc_estimated_size_kb, choose_asset

__all__ = [
    "MainWindow",
    "LanguageDialog",
    "MetadataForm",
    "PresetsForm",
    "AssetsForm",
    "RegistryTable",
    "EnvTable",
    "AutoLabel",
    "calc_estimated_size_kb",
    "choose_asset",
]
