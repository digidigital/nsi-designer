from __future__ import annotations
import os
import shutil
from typing import Optional
from PIL import Image


def ensure_dir(path: str) -> None:
    """Create directory if it does not exist."""
    os.makedirs(path, exist_ok=True)


def copy_or_convert_icon(src_path: str, export_icons_dir: str) -> Optional[str]:
    """
    Copy or convert the selected icon to .ico under export_icons_dir.
    Returns the destination path or None if src_path is empty.
    File type is determined from src_path extension.
    """
    if not src_path:
        return None
    ensure_dir(export_icons_dir)
    basename = os.path.splitext(os.path.basename(src_path))[0]
    dst_path = os.path.join(export_icons_dir, f"{basename}.ico")

    ext = os.path.splitext(src_path)[1].lower()
    if ext == ".ico":
        shutil.copy2(src_path, dst_path)
        return dst_path

    # Convert from png/jpg to ico (simple single-size icon)
    with Image.open(src_path) as im:
        im = im.convert("RGBA")

        # Check size and resize if necessary
        if im.size != (256, 256):
            im = im.resize((256, 256), Image.LANCZOS)

        # Save as ICO with a single 256x256 size
        im.save(dst_path, format="ICO", sizes=[(256, 256)])
    return dst_path


def copy_or_convert_bitmap(src_path: str, export_bitmaps_dir: str) -> Optional[str]:
    """
    Copy or convert the selected bitmap to .bmp under export_bitmaps_dir.
    Returns the destination path or None if src_path is empty.
    File type is determined from src_path extension.
    """
    if not src_path:
        return None
    ensure_dir(export_bitmaps_dir)
    basename = os.path.splitext(os.path.basename(src_path))[0]
    dst_path = os.path.join(export_bitmaps_dir, f"{basename}.bmp")

    # Always convert the bmp for bettercompatibility 
    '''
    ext = os.path.splitext(src_path)[1].lower()
    if ext == ".bmp":
        shutil.copy2(src_path, dst_path)
        return dst_path
    '''
    with Image.open(src_path) as im:
        rgb = im.convert("RGB")
        # Check size and resize if necessary
        if rgb.size != (164, 314):
            rgb = rgb.resize((164, 314), Image.LANCZOS)
        rgb.save(dst_path, format="BMP")
    return dst_path


def copy_license(src_path: str, export_docs_dir: str) -> Optional[str]:
    """
    Copy license RTF file to export_docs_dir.
    Returns the destination path or None if src_path is empty or not .rtf.
    """
    if not src_path:
        return None
    if not src_path.lower().endswith(".rtf"):
        return None
    ensure_dir(export_docs_dir)
    basename = os.path.basename(src_path)
    dst_path = os.path.join(export_docs_dir, basename)
    shutil.copy2(src_path, dst_path)
    return dst_path


def copy_executable(src_path: str, export_root_dir: str) -> Optional[str]:
    """
    Copy the selected application executable into export_root_dir.
    Returns destination path or None if src_path empty.
    """
    if not src_path:
        return None
    ensure_dir(export_root_dir)
    dst = os.path.join(export_root_dir, os.path.basename(src_path))
    shutil.copy2(src_path, dst)
    return dst


def copy_app_payload_recursive(exe_path: str, payload_target_dir: str) -> Optional[str]:
    """
    Copy the entire directory that contains the selected exe to payload_target_dir, recursively.
    Returns the root payload folder path, or None if exe_path is empty.
    """
    if not exe_path:
        return None
    app_dir = os.path.dirname(exe_path)
    if not os.path.isdir(app_dir):
        return None
    ensure_dir(payload_target_dir)
    # Copy everything under the app_dir into payload_target_dir/<app_dir_name>
    app_dir_name = os.path.basename(app_dir)
    dest_root = os.path.join(payload_target_dir, app_dir_name)
    if os.path.exists(dest_root):
        shutil.rmtree(dest_root)
    shutil.copytree(app_dir, dest_root)
    return dest_root
