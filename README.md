# German Radio Stations (VLC XSPF Playlist)

Curated XSPF playlist of ~30 popular German radio stations for [VLC](https://www.videolan.org/). Stream URLs are based on the [IPRD](https://iprd-org.github.io/iprd/) catalog (MIT license).

## Quick start

1. Clone or download this repository.
2. Open `german_radio_stations.xspf` in VLC (**Media → Open File**).
3. Cover images load from the bundled `covers/` folder — no internet required.

## Cover images

Each station has a **sender-style thumbnail** in `covers/` (gradient background, station icon colors, full station name). These ship with the repo and work offline.

The playlist also stores an optional remote source per station:

```xml
<image>covers/1live.png</image>
<meta rel="image-remote">https://www1.wdr.de/resources/img/favicon/apple-touch-icon.png</meta>
```

VLC uses the local `<image>` path. The `image-remote` URL is **not** fetched automatically; it is only a hint for the optional sync script below.

### Cover sync (CLI or web app)

If covers are stored outside the default `covers/` folder, or VLC does not show artwork, use the cover sync tools to write the correct paths into the XSPF.

**Web app (recommended):**

```bash
pip install -r requirements.txt
python3 webapp/app.py
```

Open http://127.0.0.1:8765 in your browser. Choose the XSPF file, pick a cover storage folder, then either check covers or update the playlist paths for VLC. Use **relative** paths when the playlist and covers stay together; use **absolute `file://` URLs** when covers live elsewhere.

**CLI:**

```bash
python3 scripts/sync_covers.py --check
python3 scripts/sync_covers.py --update-xspf --covers-dir /path/to/covers
python3 scripts/sync_covers.py --update-xspf --path-mode absolute --covers-dir /path/to/covers
```

### Optional: fetch original station artwork

If downloading station logos is legal where you are, you can replace bundled thumbnails with originals from the official websites:

```bash
python3 scripts/sync_covers.py --fetch-original --covers-dir covers
```

Use `--force` to overwrite existing files. This is entirely optional — the playlist works out of the box with bundled covers.

### Maintainer: verify or regenerate covers

```bash
python3 scripts/sync_covers.py --check              # verify all bundled covers exist
python3 scripts/sync_covers.py --regenerate-styled  # rebuild styled thumbnails from image-remote URLs
```

## Attribution

- Stream metadata: [IPRD](https://iprd-org.github.io/iprd/) (MIT)
- Station names, logos and trademarks belong to their respective broadcasters
- Playlist and styled thumbnails: WTFPL (see `LICENSE.txt`)

## Genres

Public broadcasters (ARD, NDR, WDR, BR, SWR, rbb, hr, MDR, Deutschlandradio), rock/metal (ROCK ANTENNE, RADIO BOB!), decades channels, schlager, trance and dance.
