/* app.js — shared behaviour for theviewfromeverywhere.com */
(function () {
  'use strict';

  /* -----------------------------------------------------------------------
     Mobile menu toggle
  ----------------------------------------------------------------------- */
  var mobileBtn = document.querySelector('.mobile-menu-btn');
  var mobileNav = document.getElementById('mobile-nav');

  if (mobileBtn && mobileNav) {
    mobileBtn.addEventListener('click', function () {
      var open = mobileNav.hasAttribute('hidden')
        ? (mobileNav.removeAttribute('hidden'), true)
        : (mobileNav.setAttribute('hidden', ''), false);
      mobileBtn.setAttribute('aria-expanded', open);
      mobileBtn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    });
  }

  /* -----------------------------------------------------------------------
     Category filtering (homepage only)
     Reads ?cat= query-param; hides non-matching cards; highlights nav link.
  ----------------------------------------------------------------------- */
  var cards = document.querySelectorAll('.blog-card[data-categories]');

  if (cards.length > 0) {
    var params = new URLSearchParams(window.location.search);
    var cat    = (params.get('cat') || 'all').toLowerCase();

    /* Highlight the matching primary-nav link */
    document.querySelectorAll('[data-filter]').forEach(function (a) {
      if (a.dataset.filter.toLowerCase() === cat) {
        a.classList.add('nav-active');
      }
    });

    /* Hide cards that don't match */
    if (cat !== 'all') {
      cards.forEach(function (card) {
        var cardCats = (card.dataset.categories || '').toLowerCase();
        if (cardCats.indexOf(cat) === -1) {
          card.hidden = true;
        }
      });
    }
  }

  /* -----------------------------------------------------------------------
     Lightbox (post pages only)
     Gallery buttons open a full-screen lightbox with prev/next/keyboard nav.
  ----------------------------------------------------------------------- */
  var galleryItems = Array.from(document.querySelectorAll('.gallery-item'));
  if (galleryItems.length === 0) return;

  var lightbox = document.getElementById('lightbox');
  var lbImg    = document.getElementById('lb-img');
  var lbCount  = document.getElementById('lb-count');
  if (!lightbox || !lbImg) return;

  /* data-src points to the full-size JPEG for lightbox display */
  var srcs = galleryItems.map(function (btn) {
    return btn.dataset.src || '';
  });

  var total   = srcs.length;
  var current = 0;

  function lbOpen(index) {
    current      = ((index % total) + total) % total;
    lbImg.src    = srcs[current];
    lbImg.alt    = galleryItems[current].getAttribute('aria-label') || '';
    lbCount.textContent = (current + 1) + ' / ' + total;
    lightbox.removeAttribute('hidden');
    lightbox.classList.add('open');
    document.body.classList.add('lb-open');
    lbImg.focus();
  }

  function lbClose() {
    lightbox.setAttribute('hidden', '');
    lightbox.classList.remove('open');
    document.body.classList.remove('lb-open');
    lbImg.src = '';
  }

  galleryItems.forEach(function (btn) {
    btn.addEventListener('click', function () {
      lbOpen(parseInt(btn.dataset.index, 10));
    });
  });

  document.getElementById('lb-close').addEventListener('click', lbClose);
  document.getElementById('lb-prev').addEventListener('click', function () { lbOpen(current - 1); });
  document.getElementById('lb-next').addEventListener('click', function () { lbOpen(current + 1); });

  lightbox.addEventListener('click', function (e) {
    if (e.target === lightbox) lbClose();
  });

  document.addEventListener('keydown', function (e) {
    if (lightbox.hasAttribute('hidden')) return;
    if (e.key === 'ArrowLeft'  || e.key === 'Left')   { lbOpen(current - 1); e.preventDefault(); }
    if (e.key === 'ArrowRight' || e.key === 'Right')   { lbOpen(current + 1); e.preventDefault(); }
    if (e.key === 'Escape')                             { lbClose(); }
  });
}());
