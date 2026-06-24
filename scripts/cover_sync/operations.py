from __future__ import annotations

from pathlib import Path

from .core import download_image, render_original_cover, render_styled_cover


def _station_path(station: dict) -> Path:
    return Path(station["local"])


def check_covers(stations: list[dict]) -> dict:
    results = []
    missing_count = 0
    for station in stations:
        output_path = _station_path(station)
        exists = output_path.is_file()
        if not exists:
            missing_count += 1
        results.append(
            {
                "title": station["title"],
                "path": str(output_path),
                "status": "ok" if exists else "missing",
            }
        )
    return {
        "ok": missing_count == 0,
        "total": len(stations),
        "missing": missing_count,
        "results": results,
    }


def fetch_original_covers(stations: list[dict], force: bool = False) -> dict:
    results = []
    failed = 0
    for station in stations:
        output_path = _station_path(station)
        if output_path.exists() and not force:
            results.append(
                {
                    "title": station["title"],
                    "status": "skipped",
                    "path": str(output_path),
                    "message": "already exists",
                }
            )
            continue
        if not station["remote"]:
            failed += 1
            results.append(
                {
                    "title": station["title"],
                    "status": "error",
                    "path": str(output_path),
                    "message": "no image-remote URL",
                }
            )
            continue

        icon, error = download_image(station["remote"])
        if icon is None:
            failed += 1
            results.append(
                {
                    "title": station["title"],
                    "status": "error",
                    "path": str(output_path),
                    "message": error or "download failed",
                }
            )
            continue

        output_path.parent.mkdir(parents=True, exist_ok=True)
        render_original_cover(icon).save(output_path, format="PNG", optimize=True)
        results.append(
            {
                "title": station["title"],
                "status": "ok",
                "path": str(output_path),
                "message": "fetched original artwork",
            }
        )

    return {
        "ok": failed == 0,
        "failed": failed,
        "results": results,
    }


def regenerate_styled_covers(stations: list[dict], force: bool = False) -> dict:
    results = []
    failed = 0
    for station in stations:
        output_path = _station_path(station)
        if output_path.exists() and not force:
            results.append(
                {
                    "title": station["title"],
                    "status": "skipped",
                    "path": str(output_path),
                    "message": "already exists",
                }
            )
            continue

        icon = None
        error = None
        if station["remote"]:
            icon, error = download_image(station["remote"])
            if icon is None:
                failed += 1

        output_path.parent.mkdir(parents=True, exist_ok=True)
        render_styled_cover(station["title"], icon).save(output_path, format="PNG", optimize=True)
        results.append(
            {
                "title": station["title"],
                "status": "error" if error else "ok",
                "path": str(output_path),
                "message": error or "regenerated styled thumbnail",
            }
        )

    return {
        "ok": failed == 0,
        "failed": failed,
        "results": results,
    }
