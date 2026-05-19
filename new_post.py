#!/usr/bin/env python3
"""
Scaffold a new post for theviewfromeverywhere.com.

Usage:
    python3 new_post.py <slug>

    slug — URL-safe identifier, lowercase with hyphens (e.g. "new-zealand")

What this script does:
  1. Creates posts/<slug>.md with a template you fill in.
  2. Creates blog/<slug>/images/ directory for your full-resolution photos.
  3. Prepends the slug to posts/_index.json so the post appears first on the homepage.
  4. Prints the next steps.

After running this script:
  1. Fill in posts/<slug>.md (title, date, categories, gallery blocks).
  2. Copy your full-resolution photos into blog/<slug>/images/.
  3. Run: python3 optimize.py blog/<slug>/images
  4. Run: python3 build.py
  5. Commit and push.
"""

import json
import os
import re
import sys
from datetime import date

POSTS_DIR = 'posts'
BLOG_DIR  = 'blog'


def slugify_check(slug):
    if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', slug):
        print(f'ERROR: "{slug}" is not a valid slug.')
        print('Use lowercase letters, numbers, and hyphens only. Example: new-zealand')
        sys.exit(1)


def create_md(slug):
    path = os.path.join(POSTS_DIR, f'{slug}.md')
    if os.path.exists(path):
        print(f'  posts/{slug}.md already exists — skipping.')
        return

    today = date.today().strftime('%B %-d, %Y')
    title = slug.replace('-', ' ').title()

    template = f"""\
title: {title}
date: {today}
categories:
  - Europe
hero_image: DSC_0001.jpg
card_excerpt: Write a short tagline here.
---

Write your first paragraph here. Tell the story of the trip.
Multiple lines are fine — they'll be joined into one paragraph.

Add more paragraphs by leaving a blank line between them.

[gallery]
DSC_0001.jpg
DSC_0002.jpg
DSC_0003.jpg
[/gallery]

Text between gallery blocks becomes its own paragraph section.
You can have as many [gallery] blocks as you like, interleaved with text.

[gallery]
DSC_0004.jpg
DSC_0005.jpg
[/gallery]
"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(template)
    print(f'  Created posts/{slug}.md')


def create_images_dir(slug):
    path = os.path.join(BLOG_DIR, slug, 'images')
    os.makedirs(path, exist_ok=True)
    print(f'  Created blog/{slug}/images/')


def prepend_to_index(slug):
    index_path = os.path.join(POSTS_DIR, '_index.json')
    if os.path.exists(index_path):
        with open(index_path) as f:
            slugs = json.load(f)
        if slug in slugs:
            print(f'  {slug} already in _index.json — not adding again.')
            return
        slugs.insert(0, slug)
    else:
        slugs = [slug]

    with open(index_path, 'w') as f:
        json.dump(slugs, f, indent=2)
    print(f'  Prepended "{slug}" to posts/_index.json (will appear first on homepage)')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    slug = sys.argv[1].lower().strip()
    slugify_check(slug)

    print(f'\nScaffolding new post: {slug}\n')
    create_md(slug)
    create_images_dir(slug)
    prepend_to_index(slug)

    print(f"""
Next steps:
  1. Edit posts/{slug}.md
       — Set title, date, categories, hero_image, card_excerpt
       — Write your paragraphs and [gallery] blocks
       — List image filenames exactly as they appear in blog/{slug}/images/

  2. Copy full-resolution photos into:
       blog/{slug}/images/

  3. Optimize images (creates web derivatives):
       python3 optimize.py blog/{slug}/images

  4. Build the site:
       python3 build.py

  5. Preview locally, then commit and push:
       git add posts/{slug}.md blog/{slug}/ posts/_index.json
       git commit -m "Add {slug} post"
       git push

Categories available: Europe, Asia, Africa, United States, Parks
""")


if __name__ == '__main__':
    main()
