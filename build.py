#!/usr/bin/env python3
"""
Static-site generator for theviewfromeverywhere.com.

Sources:
  data/posts.json          — authoritative post data (regenerate with data/extract.py)
  images/web/              — optimized thumbnail derivatives (900px + 480px)
  blog/*/images/web/       — optimized gallery derivatives (1600px + 800px)
  images/web/manifest.json — {stem: {w,h}} for thumbnails
  blog/*/images/web/manifest.json — same for each post gallery

Outputs (all deterministic — running twice leaves git status clean):
  index.html           — homepage
  blog/*/index.html    — post pages
  sitemap.xml

To regenerate download_images.sh (gitignored):
  python3 build.py --with-download-script
"""

import html as html_lib
import json
import os
import re

# ---------- config ----------------------------------------------------------

SITE_URL   = 'https://www.theviewfromeverywhere.com'
POSTS_JSON = 'data/posts.json'
BLOG_DIR   = 'blog'

THUMB_FULL_W = 900
THUMB_HALF_W = 480
GAL_FULL_W   = 1600
GAL_HALF_W   = 800

# ---------- data / manifests ------------------------------------------------

def load_posts():
    with open(POSTS_JSON, encoding='utf-8') as f:
        return json.load(f)['posts']


def load_manifest(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def strip_tags(h):
    return re.sub(r'<[^>]+>', '', h or '').strip()


def pick_related(post, all_posts, n=6):
    same = [p for p in all_posts
            if p['folder'] != post['folder']
            and set(p['categories']) & set(post['categories'])]
    if len(same) >= n:
        return same[:n]
    others = [p for p in all_posts
              if p['folder'] != post['folder'] and p not in same]
    return (same + others)[:n]


# ---------- picture element helpers -----------------------------------------

def _dims(manifest, stem):
    entry = manifest.get(stem)
    if entry:
        return f' width="{entry["w"]}" height="{entry["h"]}"'
    return ''


def thumb_picture(stem, alt_e, manifest, lazy=True):
    """Homepage thumbnail — 480w + 900w srcset."""
    web_full_jpg  = f'images/web/{stem}.jpg'
    web_full_webp = f'images/web/{stem}.webp'
    web_half_jpg  = f'images/web/{stem}-sm.jpg'
    web_half_webp = f'images/web/{stem}-sm.webp'
    load = 'lazy' if lazy else 'eager'
    dims = _dims(manifest, stem)

    if all(os.path.exists(p) for p in (web_full_jpg, web_full_webp, web_half_jpg, web_half_webp)):
        return (
            f'<picture>'
            f'<source type="image/webp"'
            f' srcset="{web_half_webp} {THUMB_HALF_W}w, {web_full_webp} {THUMB_FULL_W}w"'
            f' sizes="(max-width:700px) 100vw, 50vw">'
            f'<img'
            f' srcset="{web_half_jpg} {THUMB_HALF_W}w, {web_full_jpg} {THUMB_FULL_W}w"'
            f' sizes="(max-width:700px) 100vw, 50vw"'
            f' src="{web_full_jpg}" alt="{alt_e}"{dims}'
            f' loading="{load}" decoding="async">'
            f'</picture>'
        )
    return f'<img src="images/{stem}.jpg" alt="{alt_e}"{dims} loading="{load}" decoding="async">'


def hero_picture(folder, alt_e, root='../../'):
    """Post hero and related-card image — 480w + 900w."""
    stem          = folder
    web_full_jpg  = f'{root}images/web/{stem}.jpg'
    web_full_webp = f'{root}images/web/{stem}.webp'
    web_half_jpg  = f'{root}images/web/{stem}-sm.jpg'
    web_half_webp = f'{root}images/web/{stem}-sm.webp'
    local_full    = f'images/web/{stem}.jpg'
    local_half    = f'images/web/{stem}-sm.jpg'

    if os.path.exists(local_full) and os.path.exists(local_half):
        return (
            f'<picture>'
            f'<source type="image/webp"'
            f' srcset="{web_half_webp} {THUMB_HALF_W}w, {web_full_webp} {THUMB_FULL_W}w"'
            f' sizes="100vw">'
            f'<img'
            f' srcset="{web_half_jpg} {THUMB_HALF_W}w, {web_full_jpg} {THUMB_FULL_W}w"'
            f' sizes="100vw"'
            f' src="{web_full_jpg}" alt="{alt_e}"'
            f' loading="eager" decoding="async">'
            f'</picture>'
        )
    return f'<img src="{root}images/{stem}.jpg" alt="{alt_e}" loading="eager" decoding="async">'


def gallery_picture(folder, fname, alt_e, lazy, manifest):
    """Gallery item — 800w + 1600w srcset."""
    stem          = os.path.splitext(fname)[0]
    web_full_jpg  = f'images/web/{stem}.jpg'
    web_full_webp = f'images/web/{stem}.webp'
    web_half_jpg  = f'images/web/{stem}-sm.jpg'
    web_half_webp = f'images/web/{stem}-sm.webp'
    local_full    = os.path.join(BLOG_DIR, folder, web_full_jpg)
    local_half    = os.path.join(BLOG_DIR, folder, web_half_jpg)
    load          = 'lazy' if lazy else 'eager'
    dims          = _dims(manifest, stem)

    if os.path.exists(local_full) and os.path.exists(local_half):
        return (
            f'<picture>'
            f'<source type="image/webp"'
            f' srcset="{web_half_webp} {GAL_HALF_W}w, {web_full_webp} {GAL_FULL_W}w"'
            f' sizes="(max-width:700px) 100vw, 50vw">'
            f'<img'
            f' srcset="{web_half_jpg} {GAL_HALF_W}w, {web_full_jpg} {GAL_FULL_W}w"'
            f' sizes="(max-width:700px) 100vw, 50vw"'
            f' src="{web_full_jpg}" alt="{alt_e}"{dims}'
            f' loading="{load}" decoding="async">'
            f'</picture>'
        )
    return f'<img src="images/{fname}" alt="{alt_e}"{dims} loading="{load}" decoding="async">'


# ---------- shared HTML fragments -------------------------------------------

def header_html(root='../../'):
    """Brand left | primary nav center. Secondary links live in the footer."""
    base = root + 'index.html'

    def flink(href, label, filt):
        return (f'<a href="{href}" data-filter="{html_lib.escape(filt)}">'
                f'{html_lib.escape(label)}</a>')

    return f"""\
  <header class="site-header">
    <div class="site-title">
      <a href="{root}index.html">The View from Everywhere</a>
    </div>
    <nav class="site-nav-primary" aria-label="Primary">
      {flink(base + '?cat=all',           'All',    'all')}
      {flink(base + '?cat=United+States', 'USA',    'United States')}
      {flink(base + '?cat=Parks',         'Parks',  'Parks')}
      {flink(base + '?cat=Europe',        'Europe', 'Europe')}
      {flink(base + '?cat=Africa',        'Africa', 'Africa')}
      {flink(base + '?cat=Asia',          'Asia',   'Asia')}
    </nav>
    <div></div>
  </header>

  <div class="mobile-bar">
    <button class="mobile-menu-btn" aria-label="Open menu" aria-expanded="false">
      <span></span><span></span><span></span>
    </button>
    <div class="mobile-title">
      <a href="{root}index.html">The View from Everywhere</a>
    </div>
    <a class="mobile-ig" href="https://www.instagram.com/theviewfromeverywhere/" target="_blank" rel="noopener">IG</a>
  </div>
  <nav id="mobile-nav" class="mobile-nav" hidden>
    {flink(base + '?cat=all',           'All',    'all')}
    {flink(base + '?cat=United+States', 'USA',    'United States')}
    {flink(base + '?cat=Parks',         'Parks',  'Parks')}
    {flink(base + '?cat=Europe',        'Europe', 'Europe')}
    {flink(base + '?cat=Africa',        'Africa', 'Africa')}
    {flink(base + '?cat=Asia',          'Asia',   'Asia')}
    <a href="{root}our-story/index.html">About</a>
    <a href="{root}contact/index.html">Contact</a>
    <a href="https://www.instagram.com/theviewfromeverywhere/" target="_blank" rel="noopener">Instagram</a>
  </nav>\
"""


def footer_html(root='../../'):
    return f"""\
  <footer class="site-footer">
    <nav aria-label="Footer">
      <a href="{root}index.html">All Posts</a>
      <a href="{root}our-story/index.html">About</a>
      <a href="{root}contact/index.html">Contact</a>
      <a href="https://www.instagram.com/theviewfromeverywhere/" target="_blank" rel="noopener">Instagram</a>
    </nav>
    <p class="footer-quote">&ldquo;True objectivity, then, is not a position; it is an achievement. It is the view from everywhere.&rdquo;</p>
  </footer>\
"""


FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '  <link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@'
    '0,6..72,300;0,6..72,400;1,6..72,300;1,6..72,400'
    '&family=Lora:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">'
)

LIGHTBOX_HTML = """\
  <div id="lightbox" class="lightbox" role="dialog" aria-modal="true" aria-label="Image viewer" hidden>
    <button id="lb-close" class="lightbox-close" aria-label="Close">&times;</button>
    <button id="lb-prev"  class="lightbox-btn lightbox-prev" aria-label="Previous image">&#8249;</button>
    <div class="lightbox-img-wrap">
      <img id="lb-img" src="" alt="">
    </div>
    <button id="lb-next"  class="lightbox-btn lightbox-next" aria-label="Next image">&#8250;</button>
    <p id="lb-count" class="lightbox-count"></p>
  </div>"""


# ---------- post page -------------------------------------------------------

def render_post(post, all_posts):
    folder  = post['folder']
    title   = post['title']
    title_e = html_lib.escape(title)
    cat     = post['categories'][0] if post['categories'] else ''
    cat_e   = html_lib.escape(cat)
    date_e  = html_lib.escape(post['date'])

    blocks = post.get('blocks', [])

    # Description: first paragraph text, falling back to card_excerpt
    first_para = next((b for b in blocks if b['type'] == 'paragraph'), None)
    if first_para:
        desc_raw = strip_tags(first_para['html'])[:160]
    else:
        desc_raw = post.get('card_excerpt') or title
    desc_e = html_lib.escape(desc_raw)

    canonical = f'{SITE_URL}/blog/{folder}/'
    og_image  = f'{SITE_URL}/images/web/{folder}.jpg'

    gal_manifest = load_manifest(
        os.path.join(BLOG_DIR, folder, 'images', 'web', 'manifest.json')
    )

    # Render blocks in order; assign a global lightbox index across all galleries
    content_parts = []
    global_idx    = 0
    first_para_done = False

    for block in blocks:
        if block['type'] == 'paragraph':
            cls = 'post-lede' if not first_para_done else 'post-text'
            first_para_done = True
            # HTML is already valid; output it directly (no escaping)
            content_parts.append(
                f'  <div class="{cls}">\n'
                f'    {block["html"]}\n'
                f'  </div>'
            )

        elif block['type'] == 'gallery':
            cols  = block.get('columns', 2)
            items = []
            for img in block['images']:
                fname    = img['filename']
                stem     = os.path.splitext(fname)[0]
                alt_e    = html_lib.escape(f'{title} — photo {global_idx + 1}')
                lazy     = global_idx > 2
                pic      = gallery_picture(folder, fname, alt_e, lazy, gal_manifest)
                full_src = f'images/web/{stem}.jpg'
                items.append(
                    f'    <button class="gallery-item"'
                    f' data-index="{global_idx}"'
                    f' data-src="{full_src}"'
                    f' aria-label="Open photo {global_idx + 1}">\n'
                    f'      {pic}\n'
                    f'    </button>'
                )
                global_idx += 1

            content_parts.append(
                f'  <div class="gallery-block columns-{cols}">\n'
                + '\n\n'.join(items)
                + '\n  </div>'
            )

    content_html = '\n\n'.join(content_parts)

    # Related posts
    related       = pick_related(post, all_posts, n=6)
    related_cards = []
    for rp in related:
        rf   = rp['folder']
        rt_e = html_lib.escape(rp['title'])
        rc_e = html_lib.escape(rp['categories'][0] if rp['categories'] else '')
        pic  = hero_picture(rf, rt_e)
        related_cards.append(
            f'      <a class="related-card" href="../{rf}/">\n'
            f'        {pic}\n'
            f'        <div class="related-card-overlay"></div>\n'
            f'        <div class="related-card-body">\n'
            f'          <p class="related-card-category">{rc_e}</p>\n'
            f'          <p class="related-card-title">{rt_e}</p>\n'
            f'        </div>\n'
            f'      </a>'
        )
    related_html = '\n\n'.join(related_cards)

    # Use the Squarespace featured image (gallery resolution) if available;
    # fall back to the homepage thumbnail.
    hero_fname = post.get('hero_image')
    hero_stem  = os.path.splitext(hero_fname)[0] if hero_fname else None
    hero_local = os.path.join(BLOG_DIR, folder, 'images', 'web', f'{hero_stem}.jpg') if hero_stem else None

    if hero_stem and hero_local and os.path.exists(hero_local):
        dims     = _dims(gal_manifest, hero_stem)
        hero_pic = (
            f'<picture>'
            f'<source type="image/webp"'
            f' srcset="images/web/{hero_stem}-sm.webp {GAL_HALF_W}w,'
            f' images/web/{hero_stem}.webp {GAL_FULL_W}w"'
            f' sizes="100vw">'
            f'<img'
            f' srcset="images/web/{hero_stem}-sm.jpg {GAL_HALF_W}w,'
            f' images/web/{hero_stem}.jpg {GAL_FULL_W}w"'
            f' sizes="100vw"'
            f' src="images/web/{hero_stem}.jpg" alt="{title_e}"{dims}'
            f' loading="eager" decoding="async">'
            f'</picture>'
        )
    else:
        hero_pic = hero_picture(folder, title_e, root='../../')

    return f"""<!DOCTYPE html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title_e} — The View from Everywhere</title>
  <meta name="description" content="{desc_e}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:title"       content="{title_e} — The View from Everywhere">
  <meta property="og:description" content="{desc_e}">
  <meta property="og:type"        content="article">
  <meta property="og:url"         content="{canonical}">
  <meta property="og:image"       content="{og_image}">
  <meta name="twitter:card"       content="summary_large_image">
  <meta name="twitter:image"      content="{og_image}">
  {FONT_LINK}
  <link rel="stylesheet" href="../../style.css">
</head>
<body>

{header_html()}

  <div class="post-hero">
    {hero_pic}
    <div class="post-hero-overlay"></div>
    <div class="post-hero-body">
      <p class="post-hero-category">{cat_e}</p>
      <h1 class="post-hero-title">{title_e}</h1>
      <p class="post-hero-date">{date_e}</p>
    </div>
  </div>

  <main class="post-content">

{content_html}

  </main>

  <section class="related-posts">
    <h2 class="related-posts-heading">Related Posts</h2>
    <div class="related-posts-grid">

{related_html}

    </div>
  </section>

{LIGHTBOX_HTML}

{footer_html()}

  <script src="../../app.js"></script>
</body>
</html>
"""


# ---------- homepage --------------------------------------------------------

def render_index(posts):
    thumb_manifest = load_manifest('images/web/manifest.json')

    cards = []
    for post in posts:
        folder    = post['folder']
        title_e   = html_lib.escape(post['title'])
        exc_e     = html_lib.escape(post.get('card_excerpt', ''))
        cats      = post['categories']
        data_cats = html_lib.escape(' '.join(cats))

        pic = thumb_picture(folder, title_e, thumb_manifest, lazy=True)

        tagline = f'\n        <p class="blog-card-tagline">{exc_e}</p>' if exc_e else ''

        cards.append(
            f'    <a class="blog-card" href="blog/{folder}/" data-categories="{data_cats}">\n'
            f'      {pic}\n'
            f'      <div class="blog-card-overlay"></div>\n'
            f'      <div class="blog-card-body">\n'
            f'        <h2 class="blog-card-title">{title_e}</h2>'
            f'{tagline}\n'
            f'      </div>\n'
            f'    </a>'
        )

    grid_html = '\n\n'.join(cards)

    return f"""<!DOCTYPE html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>The View from Everywhere</title>
  <meta name="description" content="A travel photography journal by Ian and Kellyn. National Parks, Europe, Asia, and Africa.">
  <link rel="canonical" href="{SITE_URL}/">
  <meta property="og:site_name"   content="The View from Everywhere">
  <meta property="og:title"       content="The View from Everywhere">
  <meta property="og:type"        content="website">
  <meta property="og:url"         content="{SITE_URL}/">
  <meta property="og:image"       content="{SITE_URL}/images/web/hawaii.jpg">
  <meta name="twitter:card"       content="summary_large_image">
  <meta name="twitter:image"      content="{SITE_URL}/images/web/hawaii.jpg">
  {FONT_LINK}
  <link rel="stylesheet" href="style.css">
</head>
<body>

{header_html(root='./')}

  <main class="blog-list" id="blog-list">

{grid_html}

  </main>

{footer_html(root='./')}

  <script src="app.js"></script>
</body>
</html>
"""


# ---------- sitemap ---------------------------------------------------------

def render_sitemap(posts):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
             f'  <url><loc>{SITE_URL}/</loc><priority>1.0</priority></url>',
             f'  <url><loc>{SITE_URL}/our-story/</loc><priority>0.7</priority></url>',
             f'  <url><loc>{SITE_URL}/contact/</loc><priority>0.5</priority></url>']
    for p in posts:
        lines.append(f'  <url><loc>{SITE_URL}/blog/{p["folder"]}/</loc><priority>0.8</priority></url>')
    lines.append('</urlset>')
    return '\n'.join(lines) + '\n'


# ---------- download script (gitignored — run with --with-download-script) --

def write_download_script(posts):
    lines = [
        '#!/usr/bin/env bash',
        '# Download full-resolution gallery images from Squarespace CDN.',
        '# Run once after a fresh clone, before python3 optimize.py.',
        'set -euo pipefail',
        '',
        'echo "Downloading gallery images..."',
        '',
    ]
    for post in posts:
        folder   = post['folder']
        dir_path = f'blog/{folder}/images'
        lines.append(f'mkdir -p {dir_path}')
        lines.append(f'echo "  {folder}..."')
        for block in post.get('blocks', []):
            if block['type'] != 'gallery':
                continue
            for img in block['images']:
                url   = img.get('src_url', '')
                fname = img['filename']
                out   = f'{dir_path}/{fname}'
                if url:
                    lines.append(f'[ -f "{out}" ] || curl -s -L -o "{out}" "{url}" &')
        lines.append('wait')
        lines.append('')
    lines.append('echo "Done."')

    with open('download_images.sh', 'w') as f:
        f.write('\n'.join(lines) + '\n')
    os.chmod('download_images.sh', 0o755)
    print('Wrote download_images.sh (gitignored)')


# ---------- main ------------------------------------------------------------

def write_if_changed(path, content):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            if f.read() == content:
                return False
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


def main():
    import sys
    with_dl = '--with-download-script' in sys.argv

    posts = load_posts()
    print(f'Loaded {len(posts)} posts')

    os.makedirs(BLOG_DIR, exist_ok=True)

    changed = 0
    for post in posts:
        folder  = post['folder']
        out_dir = os.path.join(BLOG_DIR, folder)
        os.makedirs(out_dir, exist_ok=True)
        os.makedirs(os.path.join(out_dir, 'images'), exist_ok=True)
        if write_if_changed(os.path.join(out_dir, 'index.html'), render_post(post, posts)):
            changed += 1

    if write_if_changed('index.html', render_index(posts)):
        changed += 1
    if write_if_changed('sitemap.xml', render_sitemap(posts)):
        changed += 1

    print(f'  {changed} file(s) updated')

    if with_dl:
        write_download_script(posts)


if __name__ == '__main__':
    main()
