from __future__ import annotations

import json
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from cover_sync import (  # noqa: E402
    check_covers,
    fetch_original_covers,
    load_stations,
    regenerate_styled_covers,
    update_xspf_image_paths,
)

app = Flask(__name__)


def _resolve_path(value: str, default: Path) -> Path:
    path = Path(value).expanduser() if value else default
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    return path


def _config_from_request() -> tuple[Path, Path, str, bool]:
    payload = request.get_json(silent=True) or request.form or {}
    xspf_path = _resolve_path(payload.get("xspf", "german_radio_stations.xspf"), ROOT / "german_radio_stations.xspf")
    covers_dir = payload.get("covers_dir", "covers")
    path_mode = payload.get("path_mode", "relative")
    force = str(payload.get("force", "")).lower() in {"1", "true", "on", "yes"}
    return xspf_path, Path(covers_dir), path_mode, force


@app.get("/")
def index():
    return render_template(
        "index.html",
        defaults={
            "xspf": str(ROOT / "german_radio_stations.xspf"),
            "covers_dir": str(ROOT / "covers"),
            "path_mode": "relative",
        },
    )


@app.get("/api/paths")
def list_paths():
    xspf = _resolve_path(request.args.get("xspf", "german_radio_stations.xspf"), ROOT / "german_radio_stations.xspf")
    covers = request.args.get("covers_dir", str(ROOT / "covers"))
    covers_path = Path(covers).expanduser()
    if not covers_path.is_absolute():
        covers_path = (xspf.parent / covers_path).resolve()
    return jsonify(
        {
            "xspf": str(xspf),
            "covers_dir": str(covers_path),
            "xspf_exists": xspf.is_file(),
            "covers_exists": covers_path.is_dir(),
        }
    )


@app.post("/api/check")
def api_check():
    xspf_path, covers_dir, _, _ = _config_from_request()
    if not xspf_path.is_file():
        return jsonify({"ok": False, "error": f"XSPF not found: {xspf_path}"}), 400
    stations = load_stations(xspf_path, covers_dir)
    return jsonify(check_covers(stations))


@app.post("/api/fetch-original")
def api_fetch_original():
    xspf_path, covers_dir, path_mode, force = _config_from_request()
    if not xspf_path.is_file():
        return jsonify({"ok": False, "error": f"XSPF not found: {xspf_path}"}), 400
    stations = load_stations(xspf_path, covers_dir)
    result = fetch_original_covers(stations, force)
    if request.form.get("update_xspf") or (request.get_json(silent=True) or {}).get("update_xspf"):
        path_result = update_xspf_image_paths(xspf_path, covers_dir, path_mode)
        result["xspf"] = path_result
    return jsonify(result)


@app.post("/api/regenerate-styled")
def api_regenerate_styled():
    xspf_path, covers_dir, path_mode, force = _config_from_request()
    if not xspf_path.is_file():
        return jsonify({"ok": False, "error": f"XSPF not found: {xspf_path}"}), 400
    stations = load_stations(xspf_path, covers_dir)
    result = regenerate_styled_covers(stations, force)
    if request.form.get("update_xspf") or (request.get_json(silent=True) or {}).get("update_xspf"):
        path_result = update_xspf_image_paths(xspf_path, covers_dir, path_mode)
        result["xspf"] = path_result
    return jsonify(result)


@app.post("/api/update-xspf")
def api_update_xspf():
    xspf_path, covers_dir, path_mode, _ = _config_from_request()
    if not xspf_path.is_file():
        return jsonify({"ok": False, "error": f"XSPF not found: {xspf_path}"}), 400
    return jsonify(update_xspf_image_paths(xspf_path, covers_dir, path_mode))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Web UI for German Radio cover sync")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
