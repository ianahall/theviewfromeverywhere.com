#!/usr/bin/env python3
"""
Extract post data from the Squarespace WordPress export XML and write data/posts.json.

The content:encoded field is parsed into ordered blocks that preserve the original
paragraph / gallery sequence, so the static site can render them in the right order.

Usage:
    python3 data/extract.py [path/to/export.xml]
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate

# ---------- slug / title overrides -----------------------------------------

SLUG_MAP = {
    'capetown-south-africa':             'capetown',
    'tunis-tunisia':                     'tunisia',
    'monument-rocks-the-chalk-pyramids': 'monument-rocks',
}

TITLE_MAP = {
    'capetown-south-africa':             'Cape Town',
    'tunis-tunisia':                     'Tunisia',
    'monument-rocks-the-chalk-pyramids': 'Monument Rocks',
}

# Hand-written card taglines shown on the homepage grid.
EXCERPT_OVERRIDE = {
    'hawaii':          'Oh what a Hawaii!',
    'budapest':        'When I say “Buda” you say “Pest”!',
    'vienna':          'Oh what a wiener.',
    'prague':          'Prague gone it!',
    'berlin':          'Berlin, my friend.',
    'copenhagen':      'Copenhagen 4 Life…',
    'osaka':           'Here in Osaka!',
    'nara':            'Deer God!',
    'kyoto':           'Kyoto, ya know.',
    'tokyo':           'Tokyoooo!',
    'hong-kong':       'Oh, duck it.',
    'monument-rocks':  'The Chalk Pyramids',
    'joshua-tree':     'Joshua Tree, yeah you know me!',
    'barcelona':       'A New Favorite City',
    'rome':            'Rome if you want to.',
    'naples':          'Come for the pizza, stay for the volcano.',
    'florence':        'The David and Butter Chicken',
    'cinque-terre':    'Five lands, sweet wine and biscuits.',
    'venice':          'A lot of boats, a lot of moats.',
    'milan':           'Northern Italy',
    'iceland':         'Iceland is a game-changer.',
    'capetown':        'See you next time, Cape Town.',
    'tunisia':         'From Tunis to La Marsa to Carthage',
    'london':          "You have to love ol’ London town.",
}

NS = {
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'wp':      'http://wordpress.org/export/1.2/',
    'dc':      'http://purl.org/dc/elements/1.1/',
    'excerpt': 'http://wordpress.org/export/1.2/excerpt/',
}

# ---------- helpers ---------------------------------------------------------

def img_filename(url):
    """Derive a collision-safe local filename from a Squarespace CDN URL."""
    path  = url.split('?')[0]
    parts = path.rstrip('/').split('/')
    orig  = parts[-1]
    if orig.lower().startswith('image-asset'):
        ext    = orig.rsplit('.', 1)[-1] if '.' in orig else 'jpg'
        unique = parts[-2]
        return f'{unique}.{ext}'
    return orig


def fmt_date(pub_date):
    try:
        parsed = parsedate(pub_date)
        dt     = datetime(*parsed[:6])
        return dt.strftime('%B %-d, %Y')
    except Exception:
        return pub_date


def strip_tags(html):
    return re.sub(r'<[^>]+>', '', html or '').strip()


def is_blank_para(p_html):
    """True if a <p> contains only whitespace or &nbsp;."""
    text = re.sub(r'<[^>]+>', '', p_html)
    return not text.replace('\xa0', '').replace('&nbsp;', '').strip()


# ---------- block parser ----------------------------------------------------

CDN_IMG_RE = re.compile(
    r'https://images\.squarespace-cdn\.com/[^\s"\'<>]+format=original'
)

# Splits on the two known block-level div types; capturing group keeps matches
# in the result so we can detect them by content, not by index.
BLOCK_SPLIT_RE = re.compile(
    r'(<div\b[^>]*(?:sqs-html-content|image-gallery-wrapper)[^>]*>[\s\S]*?</div>)',
    re.DOTALL
)


def _gallery_from_urls(url_list):
    """Deduplicate a URL list and build image dicts; returns [] if empty."""
    seen = set()
    images = []
    for u in url_list:
        if u not in seen:
            seen.add(u)
            images.append({'filename': img_filename(u), 'src_url': u})
    return images


def parse_blocks(content):
    """
    Parse Squarespace content:encoded into ordered blocks.

    Handles two gallery formats:
      - <div class="image-gallery-wrapper"> wrapping <img> tags (most posts)
      - Standalone <img> tags between text blocks (Paris, some others)

    Returns a list of:
      { "type": "paragraph", "html": "<p>...</p>\\n..." }
      { "type": "gallery",   "columns": 2, "images": [{filename, src_url}, ...] }
    """
    blocks = []

    # Split on the known div block types; non-matching chunks may hold standalone imgs.
    chunks = BLOCK_SPLIT_RE.split(content)

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        if 'sqs-html-content' in chunk and chunk.startswith('<div'):
            # Extract inner content (strip outer <div ...> and </div>)
            inner = re.sub(r'^<div[^>]*>', '', chunk, count=1, flags=re.DOTALL)
            inner = re.sub(r'</div>\s*$', '', inner, flags=re.DOTALL)
            paras = re.findall(r'<p(?:\s[^>]*)?>[\s\S]*?</p>', inner, re.DOTALL)
            paras = [p.strip() for p in paras if not is_blank_para(p)]
            if paras:
                blocks.append({'type': 'paragraph', 'html': '\n'.join(paras)})

        elif 'image-gallery-wrapper' in chunk and chunk.startswith('<div'):
            images = _gallery_from_urls(CDN_IMG_RE.findall(chunk))
            if images:
                blocks.append({
                    'type':    'gallery',
                    'columns': 1 if len(images) == 1 else 2,
                    'images':  images,
                })

        else:
            # In-between content: collect standalone CDN <img> src attributes
            urls = re.findall(
                r'<img\b[^>]*\bsrc="(' + CDN_IMG_RE.pattern + r')"',
                chunk
            )
            images = _gallery_from_urls(urls)
            if images:
                blocks.append({
                    'type':    'gallery',
                    'columns': 1 if len(images) == 1 else 2,
                    'images':  images,
                })

    return blocks


# ---------- main ------------------------------------------------------------

def extract(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    posts = []

    for item in root.findall('.//item'):
        post_type = item.find('wp:post_type', NS)
        status    = item.find('wp:status',    NS)
        if post_type is None or post_type.text != 'post':
            continue
        if status is None or status.text != 'publish':
            continue

        raw_slug = item.find('wp:post_name', NS).text or ''
        wp_slug  = raw_slug.split('/')[-1]
        folder   = SLUG_MAP.get(wp_slug, wp_slug)
        title    = TITLE_MAP.get(wp_slug,
                       item.find('title').text or folder.replace('-', ' ').title())
        pub_date = item.find('pubDate').text or ''
        content  = item.find('content:encoded', NS).text or ''
        excerpt  = item.find('excerpt:encoded', NS).text or ''
        cats     = [c.text for c in item.findall('category')
                    if c.get('domain') == 'category']

        blocks       = parse_blocks(content)
        card_excerpt = EXCERPT_OVERRIDE.get(folder) or strip_tags(excerpt) or ''

        posts.append({
            'folder':       folder,
            'title':        title,
            'date':         fmt_date(pub_date),
            'categories':   cats,
            'card_excerpt': card_excerpt,
            'blocks':       blocks,
        })

    return posts


if __name__ == '__main__':
    xml_path = sys.argv[1] if len(sys.argv) > 1 else 'Squarespace-Wordpress-Export-05-19-2026.xml'
    if not os.path.exists(xml_path):
        print(f'ERROR: {xml_path} not found. Provide the export XML as the first argument.')
        sys.exit(1)

    posts = extract(xml_path)
    print(f'Extracted {len(posts)} published posts')

    # Report block counts
    for p in posts:
        n_gal  = sum(1 for b in p['blocks'] if b['type'] == 'gallery')
        n_para = sum(1 for b in p['blocks'] if b['type'] == 'paragraph')
        n_imgs = sum(len(b['images']) for b in p['blocks'] if b['type'] == 'gallery')
        print(f"  {p['folder']}: {n_para} paragraphs, {n_gal} galleries, {n_imgs} images")

    out = os.path.join(os.path.dirname(__file__), 'posts.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'posts': posts}, f, ensure_ascii=False, indent=2)
    print(f'\nWrote {out}')
