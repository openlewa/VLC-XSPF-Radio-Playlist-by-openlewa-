#!/usr/bin/env python3
"""
Optional cover utilities for german_radio_stations.xspf.

Bundled PNG thumbnails in covers/ are used by default (offline, no download).
Use --fetch-original only if downloading station artwork is legal where you are.
Use --regenerate-styled only when maintaining the bundled thumbnail set.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont

NS = {"x": "http://xspf.org/ns/0/"}
ET.register_namespace("", "http://xspf.org/ns/0/")
USER_AGENT = "Mozilla/5.0 (compatible; GermanRadioCoverSync/1.0)"
SIZE = 256
ICON_SIZE = 88
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
)


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())
    return slug.strip("-")


def find_meta(track: ET.Element, rel: str) -> str | None:
    for meta in track.findall("x:meta", NS):
        if meta.get("rel") == rel and meta.text:
            return meta.text.strip()
    return None


def download_image(url: str, timeout: int = 20) -> Image.Image | None:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read()
        image = Image.open(io.BytesIO(data))
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA")
        return image
    except (URLError, OSError, Image.UnidentifiedImageError) as error:
        print(f"  download failed: {error}", file=sys.stderr)
        return None


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def rgba_to_rgb(image: Image.Image, background: tuple[int, int, int]) -> Image.Image:
    if image.mode == "RGBA":
        base = Image.new("RGB", image.size, background)
        base.paste(image, mask=image.split()[3])
        return base
    return image.convert("RGB")


def average_color(image: Image.Image) -> tuple[int, int, int]:
    sample = image.copy()
    sample.thumbnail((64, 64))
    sample = rgba_to_rgb(sample, (240, 240, 240))
    pixels = list(sample.getdata())
    red = sum(color[0] for color in pixels) // len(pixels)
    green = sum(color[1] for color in pixels) // len(pixels)
    blue = sum(color[2] for color in pixels) // len(pixels)
    return red, green, blue


def luminance(color: tuple[int, int, int]) -> float:
    red, green, blue = color
    return 0.299 * red + 0.587 * green + 0.114 * blue


def adjust_color(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(channel * factor))) for channel in color)


def contrast_text_color(background: tuple[int, int, int]) -> tuple[int, int, int]:
    return (255, 255, 255) if luminance(background) < 145 else (24, 24, 32)


def wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [text]

    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines[:3]


def fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int) -> ImageFont.ImageFont:
    for size in range(30, 14, -2):
        font = load_font(size)
        lines = wrap_lines(draw, text, font, max_width)
        heights = [draw.textbbox((0, 0), line, font=font)[3] for line in lines]
        if len(lines) <= 3 and max(heights) <= 42:
            return font
    return load_font(16)


def render_styled_cover(title: str, icon: Image.Image | None) -> Image.Image:
    if icon is not None:
        base_color = average_color(icon)
    else:
        seed = sum(ord(char) for char in title)
        base_color = ((seed * 3) % 156 + 60, (seed * 5) % 156 + 60, (seed * 7) % 156 + 60)

    top_color = adjust_color(base_color, 1.08)
    bottom_color = adjust_color(base_color, 0.62)
    canvas = Image.new("RGB", (SIZE, SIZE), top_color)
    draw = ImageDraw.Draw(canvas)

    for y in range(SIZE):
        ratio = y / (SIZE - 1)
        color = tuple(
            int(top_color[index] * (1 - ratio) + bottom_color[index] * ratio)
            for index in range(3)
        )
        draw.line([(0, y), (SIZE, y)], fill=color)

    if icon is not None:
        icon_copy = icon.copy()
        icon_copy.thumbnail((ICON_SIZE, ICON_SIZE), Image.Resampling.LANCZOS)
        x = (SIZE - icon_copy.width) // 2
        y = 28
        if icon_copy.mode == "RGBA":
            canvas.paste(icon_copy, (x, y), icon_copy)
        else:
            canvas.paste(icon_copy, (x, y))

    text_color = contrast_text_color(bottom_color)
    font = fit_font(draw, title, SIZE - 28)
    lines = wrap_lines(draw, title, font, SIZE - 28)
    line_height = draw.textbbox((0, 0), "Ay", font=font)[3] + 4
    block_height = line_height * len(lines)
    start_y = SIZE - block_height - 22
    for index, line in enumerate(lines):
        width = draw.textlength(line, font=font)
        x = (SIZE - width) // 2
        y = start_y + index * line_height
        draw.text((x, y), line, fill=text_color, font=font)

    return canvas


def render_original_cover(icon: Image.Image) -> Image.Image:
    canvas = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 255))
    icon_copy = icon.copy()
    icon_copy.thumbnail((SIZE - 24, SIZE - 24), Image.Resampling.LANCZOS)
    x = (SIZE - icon_copy.width) // 2
    y = (SIZE - icon_copy.height) // 2
    if icon_copy.mode == "RGBA":
        canvas.paste(icon_copy, (x, y), icon_copy)
    else:
        canvas.paste(icon_copy, (x, y))
    return canvas.convert("RGB")


def load_stations(xspf_path: Path, covers_dir: str) -> list[dict[str, str]]:
    root = ET.parse(xspf_path).getroot()
    stations: list[dict[str, str]] = []

    for track in root.findall(".//x:track", NS):
        title = track.findtext("x:title", default="", namespaces=NS).strip()
        slug = slugify(title)
        remote = find_meta(track, "image-remote") or ""
        image_element = track.find("x:image", NS)
        local = image_element.text.strip() if image_element is not None and image_element.text else f"{covers_dir}/{slug}.png"
        stations.append(
            {
                "title": title,
                "slug": slug,
                "local": local,
                "remote": remote,
            }
        )

    return stations


def check_covers(stations: list[dict[str, str]]) -> int:
    missing = [station for station in stations if not Path(station["local"]).is_file()]
    for station in stations:
        status = "ok" if Path(station["local"]).is_file() else "missing"
        print(f"{status:7} {station['title']} -> {station['local']}")
    if missing:
        print(f"\n{len(missing)} bundled cover(s) missing.", file=sys.stderr)
        return 1
    print(f"\nAll {len(stations)} bundled covers are present.")
    return 0


def fetch_original_covers(stations: list[dict[str, str]], force: bool) -> int:
    failed = 0
    for station in stations:
        output_path = Path(station["local"])
        if output_path.exists() and not force:
            print(f"skip {station['title']} ({output_path})")
            continue
        if not station["remote"]:
            print(f"skip {station['title']} (no image-remote URL)", file=sys.stderr)
            failed += 1
            continue

        print(f"fetch {station['title']} <- {station['remote']}")
        icon = download_image(station["remote"])
        if icon is None:
            failed += 1
            continue
        output_path.parent.mkdir(parents=True, exist_ok=True)
        render_original_cover(icon).save(output_path, format="PNG", optimize=True)

    if failed:
        print(f"\n{failed} cover(s) could not be fetched.", file=sys.stderr)
        return 1
    print(f"\nFetched original artwork for {len(stations) - failed} station(s).")
    return 0


def regenerate_styled_covers(stations: list[dict[str, str]], force: bool) -> int:
    failed = 0
    for station in stations:
        output_path = Path(station["local"])
        if output_path.exists() and not force:
            print(f"skip {station['title']} ({output_path})")
            continue

        print(f"style {station['title']}")
        icon = download_image(station["remote"]) if station["remote"] else None
        if station["remote"] and icon is None:
            failed += 1
        output_path.parent.mkdir(parents=True, exist_ok=True)
        render_styled_cover(station["title"], icon).save(output_path, format="PNG", optimize=True)

    if failed:
        print(f"\n{failed} remote icon(s) could not be downloaded.", file=sys.stderr)
        return 1
    print(f"\nRegenerated styled thumbnails.")
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
    parser.add_argument("--force", action="store_true", help="Overwrite existing cover files")
    args = parser.parse_args()

    xspf_path = Path(args.xspf)
    if not xspf_path.exists():
        print(f"XSPF not found: {xspf_path}", file=sys.stderr)
        return 1

    stations = load_stations(xspf_path, args.covers_dir)

    if args.fetch_original:
        return fetch_original_covers(stations, args.force)
    if args.regenerate_styled:
        return regenerate_styled_covers(stations, args.force)

    return check_covers(stations)


if __name__ == "__main__":
    raise SystemExit(main())
