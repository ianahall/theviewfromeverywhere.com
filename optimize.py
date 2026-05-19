#!/usr/bin/env python3
"""
Image optimization pipeline for theviewfromeverywhere.com.

For each source image, produces a web/ subdirectory containing:
  {stem}.jpg / {stem}.webp          — full-size derivative (900px thumbs, 1600px gallery)
  {stem}-sm.jpg / {stem}-sm.webp   — half-size derivative (480px thumbs, 800px gallery)
  manifest.json                     — {filename: {w, h}} for the full-size derivatives

Usage:
    python3 optimize.py            # skip files that already exist
    python3 optimize.py --force    # reprocess everything

Requirements:
    pip install Pillow
    brew install webp              # macOS; Linux: apt install webp
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from PIL import Image

# ---------- config ----------------------------------------------------------

THUMB_FULL   = 900     # homepage thumbnail, full width
THUMB_HALF   = 480     # homepage thumbnail, small/half width
GALLERY_FULL = 1600    # gallery image, full width
GALLERY_HALF = 800     # gallery image, small/half width

JPEG_QUALITY = 82
WEBP_QUALITY = 85

FORCE = '--force' in sys.argv


# ---------- helpers ---------------------------------------------------------

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def needs_work(*paths, force=False):
    return force or not all(Path(p).exists() for p in paths)


def resize_jpeg(src: Path, out: Path, max_px: int) -> tuple[int, int]:
    """Resize src to max_px longest side, save as progressive JPEG. Returns (w, h)."""
    with Image.open(src) as im:
        im = im.convert('RGB')
        w, h = im.size
        if max(w, h) > max_px:
            if w >= h:
                w, h = max_px, round(h * max_px / w)
            else:
                w, h = round(w * max_px / h), max_px
            im = im.resize((w, h), Image.LANCZOS)
        ensure_dir(out.parent)
        im.save(out, 'JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)
    return w, h


def jpeg_to_webp(jpg: Path, webp: Path):
    """Convert a JPEG to WebP using cwebp; fall back to Pillow."""
    result = subprocess.run(
        ['cwebp', '-q', str(WEBP_QUALITY), '-quiet', str(jpg), '-o', str(webp)],
        capture_output=True
    )
    if result.returncode != 0:
        with Image.open(jpg) as im:
            im.save(webp, 'WEBP', quality=WEBP_QUALITY)


def process_image(src: Path, web_dir: Path, full_px: int, half_px: int, force=False):
    """
    Produce four derivatives from src in web_dir:
      {stem}.jpg, {stem}.webp, {stem}-sm.jpg, {stem}-sm.webp
    Returns (stem, full_width, full_height) or None if skipped.
    """
    stem = src.stem
    full_jpg  = web_dir / f'{stem}.jpg'
    full_webp = web_dir / f'{stem}.webp'
    half_jpg  = web_dir / f'{stem}-sm.jpg'
    half_webp = web_dir / f'{stem}-sm.webp'

    if not needs_work(full_jpg, full_webp, half_jpg, half_webp, force=force):
        return None  # already up-to-date

    ensure_dir(web_dir)

    # Full size
    fw, fh = resize_jpeg(src, full_jpg, full_px)
    jpeg_to_webp(full_jpg, full_webp)

    # Half size
    resize_jpeg(src, half_jpg, half_px)
    jpeg_to_webp(half_jpg, half_webp)

    orig_kb = src.stat().st_size // 1024
    full_kb = full_jpg.stat().st_size // 1024
    half_kb = half_jpg.stat().st_size // 1024
    print(f'    {stem}: {orig_kb}KB → {full_px}px/{full_kb}KB + {half_px}px/{half_kb}KB')
    return stem, fw, fh


def process_dir(src_dir: Path, web_dir: Path, full_px: int, half_px: int):
    """Process all images in src_dir (not the web/ subdir itself)."""
    sources = sorted(
        p for p in src_dir.iterdir()
        if p.suffix.lower() in ('.jpg', '.jpeg', '.png')
        and p.parent.name != 'web'
    )
    if not sources:
        return {}

    manifest = {}
    # Load existing manifest so skipped files still appear
    manifest_path = web_dir / 'manifest.json'
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)

    processed = skipped = 0
    for src in sources:
        result = process_image(src, web_dir, full_px, half_px, force=FORCE)
        if result is None:
            skipped += 1
            # Ensure existing entries stay in manifest (already loaded above)
        else:
            stem, fw, fh = result
            manifest[stem] = {'w': fw, 'h': fh}
            processed += 1

    with open(manifest_path, 'w') as f:
        json.dump(manifest, f)

    return manifest, processed, skipped


# ---------- main ------------------------------------------------------------

def main():
    base = Path(__file__).parent

    # Homepage thumbnails
    thumb_src = base / 'images'
    thumb_web = base / 'images' / 'web'
    print('Homepage thumbnails:')
    result = process_dir(thumb_src, thumb_web, THUMB_FULL, THUMB_HALF)
    if result:
        _, done, skip = result
        print(f'  {done} processed, {skip} skipped\n')
    else:
        print('  nothing to do\n')

    # Our Story photo
    story_src  = base / 'our-story' / 'ian-and-kellyn.jpg'
    story_out  = base / 'our-story' / 'ian-and-kellyn.webp'
    if story_src.exists() and needs_work(story_out, force=FORCE):
        print('Our Story photo:')
        # Resize source in-place (max 1200px) then make WebP
        fw, fh = resize_jpeg(story_src, story_src, 1200)
        jpeg_to_webp(story_src, story_out)
        print(f'  resized to {fw}×{fh}, webp created\n')

    # Gallery images per post
    blog_dir = base / 'blog'
    total_done = total_skip = 0
    for post_dir in sorted(blog_dir.iterdir()):
        img_dir = post_dir / 'images'
        if not img_dir.is_dir():
            continue
        web_dir = img_dir / 'web'
        result = process_dir(img_dir, web_dir, GALLERY_FULL, GALLERY_HALF)
        if result:
            _, d, s = result
            total_done += d
            total_skip += s
            if d:
                print(f'  {post_dir.name}: {d} processed, {s} skipped')
            else:
                print(f'  {post_dir.name}: all {s} up to date')

    print(f'\nGallery totals: {total_done} processed, {total_skip} skipped')

    # Size summary
    orig = sum(p.stat().st_size for p in base.rglob('images/*.jpg')
               if 'web' not in p.parts)
    web  = sum(p.stat().st_size for p in base.rglob('images/web/*')
               if p.suffix in ('.jpg', '.webp'))
    if orig:
        print(f'\nOriginals: {orig // (1024*1024)} MB  →  Web: {web // (1024*1024)} MB  ({100 - 100*web//orig}% reduction)')


if __name__ == '__main__':
    main()
