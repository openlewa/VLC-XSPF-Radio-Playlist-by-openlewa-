from __future__ import annotations

import io
import re
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


def download_image(url: str, timeout: int = 20) -> tuple[Image.Image | None, str | None]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read()
        image = Image.open(io.BytesIO(data))
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA")
        return image, None
    except (URLError, OSError, Image.UnidentifiedImageError) as error:
        return None, str(error)


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


def resolve_covers_dir(covers_dir: str | Path, xspf_path: Path) -> Path:
    path = Path(covers_dir).expanduser()
    if not path.is_absolute():
        path = (xspf_path.parent / path).resolve()
    return path


def cover_file_path(covers_dir: Path, slug: str) -> Path:
    return covers_dir / f"{slug}.png"


def load_stations(xspf_path: Path, covers_dir: str | Path) -> list[dict[str, str | Path]]:
    root = ET.parse(xspf_path).getroot()
    resolved_covers = resolve_covers_dir(covers_dir, xspf_path)
    stations: list[dict[str, str | Path]] = []

    for track in root.findall(".//x:track", NS):
        title = track.findtext("x:title", default="", namespaces=NS).strip()
        slug = slugify(title)
        remote = find_meta(track, "image-remote") or ""
        image_element = track.find("x:image", NS)
        if image_element is not None and image_element.text:
            image_ref = image_element.text.strip()
            image_path = Path(image_ref).expanduser()
            if not image_path.is_absolute():
                image_path = (xspf_path.parent / image_path).resolve()
            local = image_path
        else:
            local = cover_file_path(resolved_covers, slug)
        stations.append(
            {
                "title": title,
                "slug": slug,
                "local": local,
                "remote": remote,
            }
        )

    return stations
