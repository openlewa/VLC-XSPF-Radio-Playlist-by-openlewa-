#!/usr/bin/env python3
"""
Optional cover utilities for german_radio_stations.xspf.

Bundled PNG thumbnails in covers/ are used by default (offline, no download).
Use --fetch-original only if downloading station artwork is legal where you are.
Use --regenerate-styled only when maintaining the bundled thumbnail set.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cover_sync import (
    check_covers,
    fetch_original_covers,
    load_stations,
    regenerate_styled_covers,
    update_xspf_image_paths,
)


def print_check(result: dict) -> int:
    for item in result["results"]:
        print(f"{item['status']:7} {item['title']} -> {item['path']}")
    if result["missing"]:
        print(f"\n{result['missing']} bundled cover(s) missing.", file=sys.stderr)
        return 1
    print(f"\nAll {result['total']} bundled covers are present.")
    return 0


def print_operation(result: dict, success_message: str) -> int:
    for item in result["results"]:
        print(f"{item['status']:7} {item['title']} -> {item['path']}")
        if item.get("message"):
            print(f"        {item['message']}")
    if result.get("failed"):
        print(f"\n{result['failed']} cover(s) could not be processed.", file=sys.stderr)
        return 1
    print(f"\n{success_message}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xspf", default="german_radio_stations.xspf")
    parser.add_argument("--covers-dir", default="covers")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify bundled cover files referenced by the playlist exist",
    )
    parser.add_argument(
        "--fetch-original",
        action="store_true",
        help="Download original station artwork from image-remote URLs (use only where legal)",
    )
    parser.add_argument(
        "--regenerate-styled",
        action="store_true",
        help="Regenerate bundled styled thumbnails (maintainer workflow)",
    )
    parser.add_argument(
        "--update-xspf",
        action="store_true",
        help="Rewrite <image> paths in the XSPF for VLC (use with --path-mode)",
    )
    parser.add_argument(
        "--path-mode",
        choices=("relative", "absolute"),
        default="relative",
        help="How to write cover paths into the XSPF (default: relative to playlist file)",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing cover files")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output")
    args = parser.parse_args()

    xspf_path = Path(args.xspf)
    if not xspf_path.exists():
        print(f"XSPF not found: {xspf_path}", file=sys.stderr)
        return 1

    stations = load_stations(xspf_path, args.covers_dir)

    if args.update_xspf:
        result = update_xspf_image_paths(xspf_path, args.covers_dir, args.path_mode)
        if args.json:
            print(json.dumps(result, indent=2))
            return 0 if result["ok"] else 1
        for item in result["results"]:
            status = item["status"]
            print(f"{status:7} {item['title']} -> {item['path']}")
        print(f"\nUpdated {result['updated']} image path(s) using {result['mode']} mode.")
        return 0 if result["ok"] else 1

    if args.fetch_original:
        result = fetch_original_covers(stations, args.force)
        if args.json:
            print(json.dumps(result, indent=2))
            return 0 if result["ok"] else 1
        return print_operation(result, "Fetched original artwork.")

    if args.regenerate_styled:
        result = regenerate_styled_covers(stations, args.force)
        if args.json:
            print(json.dumps(result, indent=2))
            return 0 if result["ok"] else 1
        return print_operation(result, "Regenerated styled thumbnails.")

    result = check_covers(stations)
    if args.json:
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    return print_check(result)


if __name__ == "__main__":
    raise SystemExit(main())
