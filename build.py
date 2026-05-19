#!/usr/bin/env python3
"""
Static-site generator for theviewfromeverywhere.com.

Sources:
  data/posts.json   — authoritative post data (generate with data/extract.py)
  images/           — hero/thumbnail JPEGs (one per post, named {folder}.jpg)
  blog/*/images/    — full-resolution gallery images (downloaded via download_images.sh)
  blog/*/images/web/— optimized WebP + JPEG derivatives (created by optimize.py)

Outputs:
  blog/*/index.html — individual post pages
  index.html        — homepage (blog grid + category filter)
  sitemap.xml       — for search-engine discovery
  download_images.sh— shell script to re-fetch all gallery images from the CDN

Usage:
  python3 build.py            # build from data/posts.json
  python3 data/extract.py     # re-extract data/posts.json from the XML export
  python3 optimize.py         # create web-ready image derivatives
"""

import html as html_lib
import json
import os
import re

# ---------- config ----------------------------------------------------------

SITE_URL   = 'https://www.theviewfromeverywhere.com'
POSTS_JSON = 'data/posts.json'
BLOG_DIR   = 'blog'

# ---------- data ------------------------------------------------------------

def load_posts():
    with open(POSTS_JSON, encoding='utf-8') as f:
        return json.load(f)['posts']


def pick_related(post, all_posts, n=6):
    same = [p for p in all_posts
            if p['folder'] != post['folder']
            and set(p['categories']) & set(post['categories'])]
    if len(same) >= n:
        return same[:n]
    others = [p for p in all_posts
              if p['folder'] != post['folder'] and p not in same]
    return (same + others)[:n]


# ---------- image helpers ---------------------------------------------------

def web_img_path(folder, filename, ext):
    """Return relative path to an optimized derivative (web/ subdir)."""
    return f'images/web/{os.path.splitext(filename)[0]}.{ext}'


def thumb_img_tag(folder, img_filename, title, sizes='100vw', lazy=True):
    """
    <picture> element for a gallery thumbnail.
    Falls back gracefully if web/ derivatives don't exist (uses original).
    """
    stem     = os.path.splitext(img_filename)[0]
    webp_src = f'images/web/{stem}.webp'
    jpg_src  = f'images/web/{stem}.jpg'
    orig_src = f'images/{img_filename}'

    webp_exists = os.path.exists(os.path.join(BLOG_DIR, folder, webp_src))
    jpg_exists  = os.path.exists(os.path.join(BLOG_DIR, folder, jpg_src))

    title_e = html_lib.escape(title)
    lazy_attrs = ' loading="lazy" decoding="async"' if lazy else ''

    if webp_exists and jpg_exists:
        return (
            f'<picture>'
            f'<source type="image/webp" srcset="{webp_src}">'
            f'<img src="{jpg_src}" alt="{title_e}"{lazy_attrs}>'
            f'</picture>'
        )
    return f'<img src="{orig_src}" alt="{title_e}"{lazy_attrs}>'


def hero_thumb_picture(folder, title, root_to_here='../../'):
    """
    <picture> for post hero / related-card thumbnails.
    root_to_here: relative path from the HTML file to project root.
    """
    stem     = folder
    webp_src = f'{root_to_here}images/web/{stem}.webp'
    jpg_src  = f'{root_to_here}images/web/{stem}.jpg'
    orig_src = f'{root_to_here}images/{stem}.jpg'

    webp_exists = os.path.exists(f'images/web/{stem}.webp')
    jpg_exists  = os.path.exists(f'images/web/{stem}.jpg')
    title_e = html_lib.escape(title)

    if webp_exists and jpg_exists:
        return (
            f'<picture>'
            f'<source type="image/webp" srcset="{webp_src}">'
            f'<img src="{jpg_src}" alt="{title_e}" loading="eager" decoding="async">'
            f'</picture>'
        )
    return f'<img src="{orig_src}" alt="{title_e}" loading="eager" decoding="async">'


# ---------- shared HTML fragments -------------------------------------------

def header_html(root='../../', active_filter=None):
    def nav_link(href, label, filt=None):
        cls = ' class="nav-active"' if filt and filt == active_filter else ''
        df  = f' data-filter="{html_lib.escape(filt)}"' if filt else ''
        return f'<a href="{href}"{cls}{df}>{html_lib.escape(label)}</a>'

    base = root + 'index.html'
    return f"""\
  <header class="site-header">
    <nav aria-label="Primary">
      {nav_link(base + '?cat=all',           'All',    'all')}
      {nav_link(base + '?cat=United+States', 'USA',    'United States')}
      {nav_link(base + '?cat=Parks',         'Parks',  'Parks')}
      {nav_link(base + '?cat=Europe',        'Europe', 'Europe')}
      {nav_link(base + '?cat=Africa',        'Africa', 'Africa')}
      {nav_link(base + '?cat=Asia',          'Asia',   'Asia')}
    </nav>
    <div class="site-title">
      <a href="{root}index.html">The View from Everywhere</a>
    </div>
    <nav aria-label="Secondary">
      <a href="https://www.instagram.com/theviewfromeverywhere/" target="_blank" rel="noopener">Instagram</a>
      <a href="{root}our-story/index.html">About</a>
    </nav>
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
    {nav_link(base + '?cat=all',           'All')}
    {nav_link(base + '?cat=United+States', 'USA')}
    {nav_link(base + '?cat=Parks',         'Parks')}
    {nav_link(base + '?cat=Europe',        'Europe')}
    {nav_link(base + '?cat=Africa',        'Africa')}
    {nav_link(base + '?cat=Asia',          'Asia')}
    {nav_link(root + 'our-story/index.html', 'About')}
    <a href="https://www.instagram.com/theviewfromeverywhere/" target="_blank" rel="noopener">Instagram</a>
  </nav>\
"""


def footer_html(root='../../'):
    return f"""\
  <footer class="site-footer">
    <nav aria-label="Footer">
      <a href="{root}index.html">Home</a>
      <a href="{root}our-story/index.html">About</a>
      <a href="{root}contact/index.html">Contact</a>
      <a href="https://www.instagram.com/theviewfromeverywhere/" target="_blank" rel="noopener">Instagram</a>
    </nav>
    <p class="footer-quote">&ldquo;True objectivity, then, is not a position; it is an achievement. It is the view from everywhere.&rdquo;</p>
  </footer>\
"""


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
    folder    = post['folder']
    title     = post['title']
    title_e   = html_lib.escape(title)
    cat       = post['categories'][0] if post['categories'] else ''
    cat_e     = html_lib.escape(cat)
    date_e    = html_lib.escape(post['date'])
    body_e    = html_lib.escape(post['body'])
    desc_raw  = post['card_excerpt'] or post['body'][:120] or title
    desc_e    = html_lib.escape(desc_raw)

    og_image  = f'{SITE_URL}/images/{folder}.jpg'
    canonical = f'{SITE_URL}/blog/{folder}/'

    # Gallery
    gallery_items = []
    for i, img in enumerate(post['images']):
        fname   = img['filename']
        alt_e   = html_lib.escape(f'{title} — photo {i + 1}')
        lazy    = 'lazy' if i > 2 else 'eager'
        stem    = os.path.splitext(fname)[0]
        webp_p  = os.path.join(BLOG_DIR, folder, f'images/web/{stem}.webp')
        jpg_p   = os.path.join(BLOG_DIR, folder, f'images/web/{stem}.jpg')
        if os.path.exists(webp_p) and os.path.exists(jpg_p):
            inner = (f'<picture>'
                     f'<source type="image/webp" srcset="images/web/{stem}.webp">'
                     f'<img src="images/web/{stem}.jpg" alt="{alt_e}"'
                     f' loading="{lazy}" decoding="async">'
                     f'</picture>')
        else:
            inner = f'<img src="images/{fname}" alt="{alt_e}" loading="{lazy}" decoding="async">'
        gallery_items.append(
            f'    <button class="post-gallery-item" data-index="{i}" aria-label="Open photo {i + 1}">\n'
            f'      {inner}\n'
            f'    </button>'
        )
    gallery_html = '\n\n'.join(gallery_items)

    # Related posts
    related = pick_related(post, all_posts, n=6)
    related_cards = []
    for rp in related:
        rf    = rp['folder']
        rt_e  = html_lib.escape(rp['title'])
        rc_e  = html_lib.escape(rp['categories'][0] if rp['categories'] else '')
        related_cards.append(
            f'      <a class="related-card" href="../{rf}/">\n'
            f'        {hero_thumb_picture(rf, rp["title"])}\n'
            f'        <div class="related-card-overlay"></div>\n'
            f'        <div class="related-card-body">\n'
            f'          <p class="related-card-category">{rc_e}</p>\n'
            f'          <p class="related-card-title">{rt_e}</p>\n'
            f'        </div>\n'
            f'      </a>'
        )
    related_html = '\n\n'.join(related_cards)

    hero_pic = hero_thumb_picture(folder, title, root_to_here='../../')

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
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Bitter:ital,wght@0,300;0,400;1,300&family=Lora:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
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

  <div class="post-body">
    <p class="post-lede">{body_e}</p>
  </div>

  <div class="post-gallery" id="gallery">

{gallery_html}

  </div>

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
    cards = []
    for post in posts:
        folder  = post['folder']
        title_e = html_lib.escape(post['title'])
        cats    = post['categories']
        cat_e   = html_lib.escape(cats[0] if cats else '')
        exc_e   = html_lib.escape(post['card_excerpt'])
        date_e  = html_lib.escape(post['date'])
        # data-categories: space-joined for JS indexOf matching
        data_cats = html_lib.escape(' '.join(cats))

        stem     = folder
        webp_p   = f'images/web/{stem}.webp'
        jpg_p    = f'images/web/{stem}.jpg'
        orig_p   = f'images/{stem}.jpg'
        if os.path.exists(webp_p) and os.path.exists(jpg_p):
            img_html = (f'<picture>'
                        f'<source type="image/webp" srcset="{webp_p}">'
                        f'<img class="blog-card-image" src="{jpg_p}" alt="{title_e}"'
                        f' loading="lazy" decoding="async">'
                        f'</picture>')
        else:
            img_html = (f'<img class="blog-card-image" src="{orig_p}" alt="{title_e}"'
                        f' loading="lazy" decoding="async">')

        excerpt_html = f'\n        <p class="blog-card-excerpt">{exc_e}</p>' if exc_e else ''
        date_html    = f'\n        <p class="blog-card-date">{date_e}</p>'

        cards.append(
            f'    <a class="blog-card" href="blog/{folder}/" data-categories="{data_cats}">\n'
            f'      {img_html}\n'
            f'      <div class="blog-card-overlay"></div>\n'
            f'      <div class="blog-card-body">\n'
            f'        <p class="blog-card-category">{cat_e}</p>\n'
            f'        <h2 class="blog-card-title">{title_e}</h2>'
            f'{excerpt_html}'
            f'{date_html}\n'
            f'      </div>\n'
            f'    </a>'
        )

    grid_html = '\n\n'.join(cards)

    cats_json = json.dumps(
        {p['folder']: p['categories'] for p in posts}, ensure_ascii=False
    )

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
  <meta property="og:image"       content="{SITE_URL}/images/hawaii.jpg">
  <meta name="twitter:card"       content="summary_large_image">
  <meta name="twitter:image"      content="{SITE_URL}/images/hawaii.jpg">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Bitter:ital,wght@0,300;0,400;1,300&family=Lora:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
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
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    lines.append(f'  <url><loc>{SITE_URL}/</loc><priority>1.0</priority></url>')
    lines.append(f'  <url><loc>{SITE_URL}/our-story/</loc><priority>0.7</priority></url>')
    lines.append(f'  <url><loc>{SITE_URL}/contact/</loc><priority>0.5</priority></url>')
    for p in posts:
        lines.append(f'  <url><loc>{SITE_URL}/blog/{p["folder"]}/</loc><priority>0.8</priority></url>')
    lines.append('</urlset>')
    return '\n'.join(lines) + '\n'


# ---------- download script -------------------------------------------------

def write_download_script(posts):
    def img_filename_from_url(url):
        path  = url.split('?')[0]
        parts = path.rstrip('/').split('/')
        orig  = parts[-1]
        if orig.lower().startswith('image-asset'):
            ext    = orig.rsplit('.', 1)[-1] if '.' in orig else 'jpg'
            unique = parts[-2]
            return f'{unique}.{ext}'
        return orig

    lines = ['#!/usr/bin/env bash',
             '# Download all gallery images from Squarespace CDN.',
             '# Run once from the project root after a fresh clone.',
             '# Requires: curl',
             'set -euo pipefail', '']

    for post in posts:
        folder   = post['folder']
        dir_path = f'blog/{folder}/images'
        lines.append(f'mkdir -p {dir_path}')
        lines.append(f'echo "  {folder} ({len(post["images"])} images)..."')
        for img in post['images']:
            url  = img.get('src_url', '')
            if not url:
                continue
            fname = img['filename']
            out   = f'{dir_path}/{fname}'
            lines.append(f'[ -f "{out}" ] || curl -s -L -o "{out}" "{url}" &')
        lines.append('wait')
        lines.append('')

    lines.append('echo "Done."')
    with open('download_images.sh', 'w') as f:
        f.write('\n'.join(lines) + '\n')
    os.chmod('download_images.sh', 0o755)
    print('Wrote download_images.sh')


# ---------- main ------------------------------------------------------------

def main():
    posts = load_posts()
    print(f'Loaded {len(posts)} posts from {POSTS_JSON}')

    os.makedirs(BLOG_DIR, exist_ok=True)

    # Post pages
    for post in posts:
        folder  = post['folder']
        out_dir = os.path.join(BLOG_DIR, folder)
        os.makedirs(out_dir, exist_ok=True)
        os.makedirs(os.path.join(out_dir, 'images'), exist_ok=True)
        html = render_post(post, posts)
        out  = os.path.join(out_dir, 'index.html')
        with open(out, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'  {out}  ({len(post["images"])} images)')

    # Homepage
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(render_index(posts))
    print('Wrote index.html')

    # Sitemap
    with open('sitemap.xml', 'w', encoding='utf-8') as f:
        f.write(render_sitemap(posts))
    print('Wrote sitemap.xml')

    # Download script
    write_download_script(posts)


if __name__ == '__main__':
    main()
