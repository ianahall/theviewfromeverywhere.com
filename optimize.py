#!/usr/bin/env python3
"""
Image optimization pipeline for theviewfromeverywhere.com.

Creates web-ready WebP + JPEG derivatives from the full-resolution source images.
Output files go into web/ subdirectories so originals are untouched.

Targets:
  images/         → images/web/     (900 px wide, homepage thumbnails)
  blog/*/images/  → blog/*/images/web/ (1600 px wide, gallery images)

Usage:
    python3 optimize.py            # process everything not yet done
    python3 optimize.py --force    # reprocess all, overwriting existing derivatives

Requirements:
    pip install Pillow
    brew install webp  (provides cwebp for WebP encoding)
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from PIL import Image

# ---------- config ----------------------------------------------------------

THUMB_MAX_PX   = 900    # homepage thumbnails
GALLERY_MAX_PX = 1600   # post gallery images

JPEG_QUALITY   = 82
WEBP_QUALITY   = 85

FORCE = '--force' in sys.argv

# ---------- helpers ---------------------------------------------------------

def ensure_dir(p):
    Path(p).mkdir(parents=True, exist_ok=True)


def needs_processing(out_jpg, out_webp, force):
    if force:
        return True
    return not (Path(out_jpg).exists() and Path(out_webp).exists())


def resize_and_save(src: Path, out_jpg: Path, out_webp: Path, max_px: int):
    """Open src, resize to max_px on longest side, save JPEG + WebP."""
    try:
        with Image.open(src) as im:
            im = im.convert('RGB')
            w, h = im.size
            # Only downscale, never upscale
            if max(w, h) > max_px:
                if w >= h:
                    new_w, new_h = max_px, round(h * max_px / w)
                else:
                    new_w, new_h = round(w * max_px / h), max_px
                im = im.resize((new_w, new_h), Image.LANCZOS)

            ensure_dir(out_jpg.parent)
            im.save(out_jpg, 'JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)

        # Use cwebp for WebP (better quality than Pillow's encoder)
        result = subprocess.run(
            ['cwebp', '-q', str(WEBP_QUALITY), '-quiet', str(out_jpg), '-o', str(out_webp)],
            capture_output=True
        )
        if result.returncode != 0:
            # Fall back to Pillow if cwebp fails
            with Image.open(out_jpg) as im:
                im.save(out_webp, 'WEBP', quality=WEBP_QUALITY)

        return True
    except Exception as e:
        print(f'    ERROR {src.name}: {e}')
        return False


# ---------- main ------------------------------------------------------------

def process_dir(src_dir: Path, web_dir: Path, max_px: int, label: str):
    images = sorted(p for p in src_dir.iterdir()
                    if p.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif')
                    and p.parent.name != 'web')  # don't re-process web/ files
    if not images:
        return 0, 0

    done = skip = 0
    for src in images:
        stem    = src.stem
        out_jpg  = web_dir / f'{stem}.jpg'
        out_webp = web_dir / f'{stem}.webp'

        if not needs_processing(out_jpg, out_webp, FORCE):
            skip += 1
            continue

        ok = resize_and_save(src, out_jpg, out_webp, max_px)
        if ok:
            done += 1
            orig_kb = src.stat().st_size // 1024
            jpg_kb  = out_jpg.stat().st_size // 1024
            webp_kb = out_webp.stat().st_size // 1024
            print(f'    {stem}: {orig_kb}KB → jpg {jpg_kb}KB, webp {webp_kb}KB')
        else:
            skip += 1

    return done, skip


def main():
    base = Path(__file__).parent

    # Homepage thumbnails
    thumb_src = base / 'images'
    thumb_web = base / 'images' / 'web'
    print('Homepage thumbnails (→ images/web/):')
    done, skip = process_dir(thumb_src, thumb_web, THUMB_MAX_PX, 'thumb')
    print(f'  {done} processed, {skip} skipped\n')

    # Our-story photo
    story_src  = base / 'our-story' / 'ian-and-kellyn.jpg'
    story_webp = base / 'our-story' / 'ian-and-kellyn.webp'
    if story_src.exists() and (FORCE or not story_webp.exists()):
        print('Our Story photo:')
        tmp = base / 'our-story' / '_tmp.jpg'
        resize_and_save(story_src, tmp, story_webp, 1200)
        # Keep only WebP + move resized JPEG back to .jpg
        story_src.unlink()
        tmp.rename(story_src)
        print(f'  ian-and-kellyn: resized + webp created\n')

    # Gallery images per post
    blog_dir = base / 'blog'
    total_done = total_skip = 0
    for post_dir in sorted(blog_dir.iterdir()):
        img_dir = post_dir / 'images'
        if not img_dir.is_dir():
            continue
        web_dir = img_dir / 'web'
        print(f'{post_dir.name} gallery:')
        d, s = process_dir(img_dir, web_dir, GALLERY_MAX_PX, post_dir.name)
        total_done += d
        total_skip += s
        if d == 0 and s > 0:
            print(f'  all {s} already up to date')

    print(f'\nGallery totals: {total_done} processed, {total_skip} skipped')

    # Report size savings
    orig_bytes = sum(
        p.stat().st_size
        for p in (base / 'images').glob('*.jpg')
    ) + sum(
        p.stat().st_size
        for p in (base / 'blog').rglob('images/*.jpg')
        if p.parent.name != 'web'
    )
    web_bytes = sum(
        p.stat().st_size
        for p in (base / 'images' / 'web').glob('*')
        if p.suffix in ('.jpg', '.webp')
    ) + sum(
        p.stat().st_size
        for p in (base / 'blog').rglob('images/web/*')
        if p.suffix in ('.jpg', '.webp')
    )
    print(f'\nOriginals: {orig_bytes // (1024*1024)} MB')
    print(f'Web derivatives: {web_bytes // (1024*1024)} MB')
    if orig_bytes:
        print(f'Reduction: {100 - 100 * web_bytes // orig_bytes}%')


if __name__ == '__main__':
    main()
