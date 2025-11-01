# NSI Designer 

## Features

- A PySide6 desktop application for creating NSIS installer scripts (.nsi):
- Just point to .exe all other files in the exe-location will be added to the installer package  
- Live script preview
- Asset pickers and format conversion (icons to .ico, welcome bitmap to .bmp)
- Set Registry values and environment variables 
- Language selection dialog
- Presets for install location, execution level, and scope
- Export with encoding selection (UTF-8 or ANSI cp1252) 
- Optional flags /S (silent), /NOICONS (do not create shortcuts), /LOG=[path] (logging) and /D=[path (always without "!)]
- Makensis integration to compile the script directly from within the app

## What is NSI Designer?

NSI Designer is a **free Windows installer creator** and **NSIS GUI tool** that helps developers build professional setup packages without writing scripts by hand.  
It acts as a **setup maker / installer builder** for your applications, generating `.nsi` scripts and compiling them into `.exe` installers using NSIS.  

With NSI Designer you can:
- Quickly create **Windows setup wizards** for your apps
- Use a graphical interface instead of editing NSIS scripts manually
- Package executables, assets, registry keys, and environment variables
- Export ready‑to‑use installers with uninstaller support
- Create **Nullsoft Scriptable Install System** boilerplates for your applications

Whether you call it an **installer maker, setup creator, or installer generator**, NSI Designer gives you a modern, PySide6‑based desktop app to streamline the process.

## Install via pypi

Install via pypi and run from command line:

`nsi_designer`

or 

`python -m nsi_designer`

## Notes
- Asset conversions happen on export using Pillow.
- Makensis path is stored in QSettings after first selection if not found.
- The uninstaller reverses all installer actions, including registry and environment changes (safe append removal).
- Always manually check the script and test the installer prior to production use!
- If you mess with the registry things can go terribly wrong on uninstall if you do not take care that everithing is set up correctly. 
- NEVER use set-Mode with existing environment variables (like Path)