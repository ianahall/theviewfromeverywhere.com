#!/usr/bin/env python3
"""
Generate all blog post pages from the Squarespace XML export.
Also writes download_images.sh to pull all gallery images locally.
"""

import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate

# ---------- config ----------------------------------------------------------

XML_PATH = 'Squarespace-Wordpress-Export-05-19-2026.xml'
BLOG_DIR = 'blog'
IMG_DIR  = 'images'   # thumbnail dir (relative to project root)

# Map WP post_name slugs → clean folder name (and thumbnail filename)
SLUG_MAP = {
    'capetown-south-africa':              'capetown',
    'tunis-tunisia':                      'tunisia',
    'monument-rocks-the-chalk-pyramids':  'monument-rocks',
}

# Human-readable titles for slugs that need overrides
TITLE_MAP = {
    'capetown-south-africa':              'Cape Town',
    'tunis-tunisia':                      'Tunisia',
    'monument-rocks-the-chalk-pyramids':  'Monument Rocks',
}

def img_filename(url):
    """
    Squarespace CDN URLs look like:
      .../content/v1/{site-id}/{unique-hash}/{orig-name}?format=original
    Many posts have all files named 'image-asset.jpeg', so we use the
    unique hash segment as the base filename to avoid collisions.
    """
    path = url.split('?')[0]          # strip query string
    parts = path.rstrip('/').split('/')
    orig = parts[-1]                  # e.g. image-asset.jpeg or IMG_1234.jpg
    if orig.lower().startswith('image-asset'):
        # use the unique hash segment + original extension
        ext = orig.rsplit('.', 1)[-1] if '.' in orig else 'jpg'
        unique = parts[-2]            # e.g. 1493999755287-668SFH0ILXTGO43RUZHA
        return f'{unique}.{ext}'
    return orig


NS = {
    'content':  'http://purl.org/rss/1.0/modules/content/',
    'wp':       'http://wordpress.org/export/1.2/',
    'dc':       'http://purl.org/dc/elements/1.1/',
    'excerpt':  'http://wordpress.org/export/1.2/excerpt/',
}

# ---------- parse XML -------------------------------------------------------

def parse_posts():
    tree = ET.parse(XML_PATH)
    root = tree.getroot()
    posts = []
    for item in root.findall('.//item'):
        post_type = item.find('wp:post_type', NS)
        status    = item.find('wp:status',    NS)
        if post_type is None or post_type.text != 'post':
            continue
        if status is None or status.text != 'publish':
            continue

        raw_slug  = item.find('wp:post_name', NS).text or ''
        wp_slug   = raw_slug.split('/')[-1]   # last path segment
        folder    = SLUG_MAP.get(wp_slug, wp_slug)
        title     = TITLE_MAP.get(wp_slug, item.find('title').text or folder.replace('-', ' ').title())
        pub_date  = item.find('pubDate').text or ''
        content   = item.find('content:encoded', NS).text or ''
        excerpt   = item.find('excerpt:encoded', NS).text or ''
        cats      = [c.text for c in item.findall('category') if c.get('domain') == 'category']

        # Gallery images
        img_urls = re.findall(
            r'https://images\.squarespace-cdn\.com/[^"\'<>\s]+format=original',
            content
        )
        # Deduplicate while preserving order
        seen = set()
        unique_urls = []
        for u in img_urls:
            if u not in seen:
                seen.add(u)
                unique_urls.append(u)


        # Body text (strip tags, collapse whitespace)
        paras = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
        body  = re.sub(r'<[^>]+>', '', ' '.join(paras)).strip()
        body  = re.sub(r'\s+', ' ', body)

        # Format date
        try:
            parsed = parsedate(pub_date)
            dt     = datetime(*parsed[:6])
            formatted_date = dt.strftime('%B %-d, %Y')
        except Exception:
            formatted_date = pub_date

        posts.append({
            'wp_slug':   wp_slug,
            'folder':    folder,
            'title':     title,
            'date':      formatted_date,
            'categories': cats,
            'img_urls':  unique_urls,
            'body':      body,
            'excerpt':   re.sub(r'<[^>]+>', '', excerpt).strip(),
        })

    return posts


# ---------- related posts ---------------------------------------------------

def pick_related(post, all_posts, n=6):
    same_cat = [p for p in all_posts
                if p['folder'] != post['folder']
                and set(p['categories']) & set(post['categories'])]
    if len(same_cat) >= n:
        return same_cat[:n]
    # pad with other posts
    others = [p for p in all_posts
              if p['folder'] != post['folder'] and p not in same_cat]
    return (same_cat + others)[:n]


# ---------- HTML template ---------------------------------------------------

HEADER = """\
  <!-- Desktop header -->
  <header class="site-header">
    <nav aria-label="Primary">
      <a href="../../index.html">All</a>
      <a href="../../index.html?cat=United+States">USA</a>
      <a href="../../index.html?cat=Parks">Parks</a>
      <a href="../../index.html?cat=Europe">Europe</a>
      <a href="../../index.html?cat=Africa">Africa</a>
      <a href="../../index.html?cat=Asia">Asia</a>
    </nav>
    <div class="site-title"><a href="../../index.html">The View from Everywhere</a></div>
    <nav aria-label="Secondary">
      <a href="https://www.instagram.com/theviewfromeverywhere/" target="_blank" rel="noopener">Instagram</a>
      <a href="../../our-story/index.html">About</a>
    </nav>
  </header>

  <!-- Mobile header -->
  <div class="mobile-bar">
    <button class="mobile-menu-btn" aria-label="Menu" aria-expanded="false" onclick="
      var nav = document.getElementById('mobile-nav');
      var open = nav.classList.toggle('open');
      this.setAttribute('aria-expanded', open);
    ">
      <span></span><span></span><span></span>
    </button>
    <div class="mobile-title"><a href="../../index.html">The View from Everywhere</a></div>
    <a href="https://www.instagram.com/theviewfromeverywhere/" target="_blank" rel="noopener" style="font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:#555;">IG</a>
  </div>
  <nav id="mobile-nav" class="mobile-nav">
    <a href="../../index.html">All</a>
    <a href="../../index.html?cat=United+States">USA</a>
    <a href="../../index.html?cat=Parks">Parks</a>
    <a href="../../index.html?cat=Europe">Europe</a>
    <a href="../../index.html?cat=Africa">Africa</a>
    <a href="../../index.html?cat=Asia">Asia</a>
    <a href="../../our-story/index.html">About</a>
    <a href="https://www.instagram.com/theviewfromeverywhere/" target="_blank" rel="noopener">Instagram</a>
  </nav>\
"""

LIGHTBOX_HTML = """\
  <!-- Lightbox -->
  <div id="lightbox" class="lightbox" role="dialog" aria-modal="true" aria-label="Image viewer">
    <button id="lb-close" class="lightbox-close" aria-label="Close">&times;</button>
    <button id="lb-prev"  class="lightbox-btn lightbox-prev" aria-label="Previous">&#8249;</button>
    <div class="lightbox-img-wrap">
      <img id="lb-img" src="" alt="">
    </div>
    <button id="lb-next"  class="lightbox-btn lightbox-next" aria-label="Next">&#8250;</button>
    <div id="lb-count" class="lightbox-count"></div>
  </div>\
"""

LIGHTBOX_JS = """\
  <script>
  (function () {
    var items   = Array.from(document.querySelectorAll('.post-gallery-item'));
    var srcs    = items.map(function (btn) { return btn.querySelector('img').src; });
    var total   = srcs.length;
    var current = 0;
    var lightbox = document.getElementById('lightbox');
    var lbImg    = document.getElementById('lb-img');
    var lbCount  = document.getElementById('lb-count');
    function open(index) {
      current = (index + total) % total;
      lbImg.src = srcs[current];
      lbCount.textContent = (current + 1) + ' / ' + total;
      lightbox.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
    function close() {
      lightbox.classList.remove('open');
      document.body.style.overflow = '';
      lbImg.src = '';
    }
    items.forEach(function (btn) {
      btn.addEventListener('click', function () { open(parseInt(btn.dataset.index, 10)); });
    });
    document.getElementById('lb-close').addEventListener('click', close);
    document.getElementById('lb-prev').addEventListener('click', function () { open(current - 1); });
    document.getElementById('lb-next').addEventListener('click', function () { open(current + 1); });
    lightbox.addEventListener('click', function (e) { if (e.target === lightbox) close(); });
    document.addEventListener('keydown', function (e) {
      if (!lightbox.classList.contains('open')) return;
      if (e.key === 'ArrowLeft')  { open(current - 1); e.preventDefault(); }
      if (e.key === 'ArrowRight') { open(current + 1); e.preventDefault(); }
      if (e.key === 'Escape')     { close(); }
    });
  })();
  </script>\
"""


def render_page(post, related):
    cat_display = post['categories'][0] if post['categories'] else ''
    folder      = post['folder']
    title       = post['title']
    desc        = post['excerpt'] or post['body'][:120] or title

    # Gallery items — use local paths (images downloaded alongside index.html)
    gallery_items = []
    for i, url in enumerate(post['img_urls']):
        fname = img_filename(url)
        local = f'images/{fname}'
        gallery_items.append(
            f'    <button class="post-gallery-item" data-index="{i}" aria-label="Open image {i+1}">\n'
            f'      <img src="{local}" alt="{title} {i+1}" loading="lazy">\n'
            f'    </button>'
        )
    gallery_html = '\n\n'.join(gallery_items)

    # Related cards
    related_cards = []
    for rp in related:
        r_cat   = rp['categories'][0] if rp['categories'] else ''
        related_cards.append(
            f'      <a class="related-card" href="../{rp["folder"]}/">\n'
            f'        <img src="../../images/{rp["folder"]}.jpg" alt="{rp["title"]}" loading="lazy">\n'
            f'        <div class="related-card-overlay"></div>\n'
            f'        <div class="related-card-body">\n'
            f'          <p class="related-card-title">{rp["title"]}</p>\n'
            f'        </div>\n'
            f'      </a>'
        )
    related_html = '\n\n'.join(related_cards)

    body_para = f'<p class="post-lede">{post["body"]}</p>' if post['body'] else ''

    return f"""<!DOCTYPE html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — The View from Everywhere</title>
  <meta name="description" content="{desc}">
  <meta property="og:title" content="{title} — The View from Everywhere">
  <meta property="og:type" content="article">
  <link rel="stylesheet" href="../../style.css">
</head>
<body>

{HEADER}

  <!-- Hero -->
  <div class="post-hero">
    <img src="../../images/{folder}.jpg" alt="{title}">
    <div class="post-hero-overlay"></div>
    <div class="post-hero-body">
      <p class="post-hero-category">{cat_display}</p>
      <h1 class="post-hero-title">{title}</h1>
      <p class="post-hero-date">{post['date']}</p>
    </div>
  </div>

  <!-- Body copy -->
  <div class="post-body">
    {body_para}
  </div>

  <!-- Gallery — click any image to open lightbox -->
  <div class="post-gallery" id="gallery">

{gallery_html}

  </div><!-- /.post-gallery -->

  <!-- Related posts -->
  <section class="related-posts">
    <h2 class="related-posts-heading">Related Posts</h2>
    <div class="related-posts-grid">

{related_html}

    </div>
  </section>

{LIGHTBOX_HTML}

{LIGHTBOX_JS}

  <!-- Footer -->
  <footer class="site-footer">
    <nav>
      <a href="../../index.html">All Posts</a>
      <a href="../../our-story/index.html">About</a>
      <a href="https://www.instagram.com/theviewfromeverywhere/" target="_blank" rel="noopener">Instagram</a>
    </nav>
    <p class="footer-quote">"The world is a book, and those who do not travel read only one page."</p>
  </footer>

</body>
</html>
"""


# ---------- image download script -------------------------------------------

def write_download_script(posts):
    lines = ['#!/usr/bin/env bash', 'set -euo pipefail', '']
    lines.append('# Download all post gallery images from Squarespace CDN')
    lines.append('# Run from the project root directory')
    lines.append('')

    for post in posts:
        folder = post['folder']
        dir_path = f'blog/{folder}/images'
        lines.append(f'mkdir -p {dir_path}')
        lines.append(f'echo "Downloading {folder} ({len(post["img_urls"])} images)..."')
        for url in post['img_urls']:
            fname = img_filename(url)
            out   = f'{dir_path}/{fname}'
            lines.append(f'[ -f "{out}" ] || curl -s -L -o "{out}" "{url}" &')
        lines.append('wait')
        lines.append('')

    lines.append('echo "All downloads complete."')
    script = '\n'.join(lines) + '\n'
    with open('download_images.sh', 'w') as f:
        f.write(script)
    os.chmod('download_images.sh', 0o755)
    print('Wrote download_images.sh')


# ---------- main ------------------------------------------------------------

def main():
    posts = parse_posts()
    print(f'Parsed {len(posts)} published posts')

    os.makedirs(BLOG_DIR, exist_ok=True)

    for post in posts:
        folder   = post['folder']
        out_dir  = os.path.join(BLOG_DIR, folder)
        os.makedirs(out_dir, exist_ok=True)
        os.makedirs(os.path.join(out_dir, 'images'), exist_ok=True)

        related  = pick_related(post, posts, n=6)
        html     = render_page(post, related)

        out_path = os.path.join(out_dir, 'index.html')
        with open(out_path, 'w') as f:
            f.write(html)
        print(f'  wrote {out_path}  ({len(post["img_urls"])} images)')

    write_download_script(posts)
    print('Done.')


if __name__ == '__main__':
    main()
