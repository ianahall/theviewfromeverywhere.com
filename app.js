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

    document.querySelectorAll('[data-filter]').forEach(function (a) {
      if (a.dataset.filter.toLowerCase() === cat) {
        a.classList.add('nav-active');
      }
    });

    if (cat !== 'all') {
      cards.forEach(function (card) {
        var cardCats = (card.dataset.categories || '').toLowerCase();
        if (cardCats.indexOf(cat) === -1) {
          card.hidden = true;
        }
      });
    }

    // Apply the alternating 2/3–1/3 grid layout based on each card's
    // VISIBLE position. CSS nth-child counts DOM position and breaks when
    // cards are hidden, so we apply inline styles keyed to visible index.
    // This runs for both 'all' and filtered views.
    var visibleCards = Array.from(cards).filter(function (c) { return !c.hidden; });

    visibleCards.forEach(function (card, i) {
      var pos = i % 6;        // position within the 6-card repeating cycle
      var isWide = (pos === 0 || pos === 5);

      // Reset previous inline styles
      card.style.gridColumn = '';
      card.style.gridRow    = '';
      card.style.aspectRatio = '';
      card.classList.remove('blog-card--wide');

      if (pos === 0) {
        // Wide LEFT: spans cols 1-2, rows 1-2 of each group
        card.style.gridColumn  = '1 / span 2';
        card.style.gridRow     = 'span 2';
        card.style.aspectRatio = 'unset';
        card.classList.add('blog-card--wide');
      } else if (pos === 1 || pos === 2) {
        // Narrow RIGHT
        card.style.gridColumn = '3';
      } else if (pos === 3 || pos === 4) {
        // Narrow LEFT
        card.style.gridColumn = '1';
      } else {
        // Wide RIGHT: spans cols 2-3, rows 1-2 of each group
        card.style.gridColumn  = '2 / span 2';
        card.style.gridRow     = 'span 2';
        card.style.aspectRatio = 'unset';
        card.classList.add('blog-card--wide');
      }
    });
  }

  /* -----------------------------------------------------------------------
     Back-to-top button
     Shows after scrolling 400px; smooth-scrolls to top on click.
  ----------------------------------------------------------------------- */
  var btt = document.getElementById('back-to-top');
  if (btt) {
    btt.removeAttribute('hidden');   // JS available — show the button element
    window.addEventListener('scroll', function () {
      if (window.scrollY > 400) {
        btt.classList.add('visible');
      } else {
        btt.classList.remove('visible');
      }
    }, { passive: true });

    btt.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /* -----------------------------------------------------------------------
     Lightbox (post pages only)
     Gallery buttons open a full-screen lightbox with prev/next/keyboard nav
     and a proper focus trap so keyboard users can't escape to the page behind.
  ----------------------------------------------------------------------- */
  var galleryItems = Array.from(document.querySelectorAll('.gallery-item'));
  if (galleryItems.length === 0) return;

  var lightbox    = document.getElementById('lightbox');
  var lbImg       = document.getElementById('lb-img');
  var lbCount     = document.getElementById('lb-count');
  var lbClose     = document.getElementById('lb-close');
  var lbPrev      = document.getElementById('lb-prev');
  var lbNext      = document.getElementById('lb-next');
  if (!lightbox || !lbImg) return;

  var srcs    = galleryItems.map(function (btn) { return btn.dataset.src || ''; });
  var total   = srcs.length;
  var current = 0;
  var triggerEl = null;   // element that opened the lightbox (restore focus on close)

  // Focusable elements inside the lightbox (for the focus trap)
  var focusableInLb = [lbClose, lbPrev, lbNext].filter(Boolean);

  function lbOpen(index, opener) {
    current      = ((index % total) + total) % total;
    lbImg.src    = srcs[current];
    lbImg.alt    = galleryItems[current].getAttribute('aria-label') || '';
    lbCount.textContent = (current + 1) + ' / ' + total;
    lightbox.removeAttribute('hidden');
    lightbox.classList.add('open');
    document.body.classList.add('lb-open');
    triggerEl = opener || document.activeElement;
    // Move focus to close button
    if (lbClose) lbClose.focus();
  }

  function lbClose_() {
    lightbox.setAttribute('hidden', '');
    lightbox.classList.remove('open');
    document.body.classList.remove('lb-open');
    lbImg.src = '';
    // Return focus to the element that opened the lightbox
    if (triggerEl && typeof triggerEl.focus === 'function') {
      triggerEl.focus();
    }
    triggerEl = null;
  }

  galleryItems.forEach(function (btn) {
    btn.addEventListener('click', function () {
      lbOpen(parseInt(btn.dataset.index, 10), btn);
    });
  });

  if (lbClose) lbClose.addEventListener('click', lbClose_);
  if (lbPrev)  lbPrev.addEventListener('click',  function () { lbOpen(current - 1); });
  if (lbNext)  lbNext.addEventListener('click',  function () { lbOpen(current + 1); });

  lightbox.addEventListener('click', function (e) {
    if (e.target === lightbox) lbClose_();
  });

  document.addEventListener('keydown', function (e) {
    if (lightbox.hasAttribute('hidden')) return;

    if (e.key === 'ArrowLeft'  || e.key === 'Left')  { lbOpen(current - 1); e.preventDefault(); return; }
    if (e.key === 'ArrowRight' || e.key === 'Right') { lbOpen(current + 1); e.preventDefault(); return; }
    if (e.key === 'Escape')                           { lbClose_(); return; }

    // Focus trap: Tab / Shift+Tab cycles only within the lightbox
    if (e.key === 'Tab') {
      var first = focusableInLb[0];
      var last  = focusableInLb[focusableInLb.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
  });
}());
