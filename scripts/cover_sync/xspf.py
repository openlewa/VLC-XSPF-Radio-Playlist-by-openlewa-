from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path

from .core import NS, cover_file_path, resolve_covers_dir, slugify

PathMode = str  # "relative" | "absolute"


def _normalize_xml_declaration(xspf_path: Path) -> None:
    text = xspf_path.read_text(encoding="utf-8")
    if text.startswith("<?xml version='1.0' encoding='UTF-8'?>"):
        text = '<?xml version="1.0" encoding="UTF-8"?>' + text[39:]
        xspf_path.write_text(text, encoding="utf-8")


def image_path_for_vlc(
    cover_file: Path,
    xspf_path: Path,
    mode: PathMode = "relative",
) -> str:
    resolved = cover_file.resolve()
    if mode == "absolute":
        return resolved.as_uri()

    relative = os.path.relpath(resolved, xspf_path.parent.resolve())
    return relative.replace(os.sep, "/")


def update_xspf_image_paths(
    xspf_path: Path,
    covers_dir: str | Path,
    mode: PathMode = "relative",
) -> dict:
    xspf_path = xspf_path.resolve()
    resolved_covers = resolve_covers_dir(covers_dir, xspf_path)
    tree = ET.parse(xspf_path)
    root = tree.getroot()
    updated = 0
    results = []

    for track in root.findall(".//x:track", NS):
        title = track.findtext("x:title", default="", namespaces=NS).strip()
        slug = slugify(title)
        cover_file = cover_file_path(resolved_covers, slug)
        image_element = track.find("x:image", NS)
        if image_element is None:
            image_element = ET.SubElement(track, f"{{{NS['x']}}}image")

        existing = image_element.text.strip() if image_element.text else ""
        if existing:
            existing_path = Path(existing).expanduser()
            if not existing_path.is_absolute():
                existing_path = (xspf_path.parent / existing_path).resolve()
            if existing_path.is_file():
                cover_file = existing_path

        new_path = image_path_for_vlc(cover_file, xspf_path, mode)
        old_path = image_element.text or ""
        image_element.text = new_path
        exists = cover_file.is_file()
        if old_path != new_path:
            updated += 1
        results.append(
            {
                "title": title,
                "path": new_path,
                "exists": exists,
                "status": "ok" if exists else "missing",
            }
        )

    tree.write(xspf_path, encoding="UTF-8", xml_declaration=True)
    _normalize_xml_declaration(xspf_path)
    return {
        "ok": all(item["exists"] for item in results),
        "updated": updated,
        "mode": mode,
        "covers_dir": str(resolved_covers),
        "results": results,
    }
