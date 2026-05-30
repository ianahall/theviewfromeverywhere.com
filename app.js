/* app.js — shared behaviour for theviewfromeverywhere.com */
(function () {
  'use strict';

  /* -----------------------------------------------------------------------
     Pinned header — toggle .header-scrolled on scroll
  ----------------------------------------------------------------------- */
  var siteHeader = document.querySelector('.site-header');
  if (siteHeader) {
    var onHeaderScroll = function () {
      siteHeader.classList.toggle('header-scrolled', window.scrollY > 20);
    };
    window.addEventListener('scroll', onHeaderScroll, { passive: true });
    onHeaderScroll();
  }

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

    /* -------------------------------------------------------------------
       Grid layout — alternating 2/3–1/3 mosaic.
       Runs on load and on every resize/orientation-change so that:
         • Mobile (≤700px): all inline styles are cleared → CSS takes over
         • Desktop (>700px): inline styles set the 6-card repeating pattern
       Inline styles from JS beat CSS rules, so clearing them on mobile
       is the correct way to let the mobile media query win (Bug 1 fix).
    ------------------------------------------------------------------- */
    var MOBILE_BREAKPOINT = 700;

    function applyGridLayout() {
      var isMobile = window.innerWidth <= MOBILE_BREAKPOINT;
      var visibleCards = Array.from(cards).filter(function (c) { return !c.hidden; });

      visibleCards.forEach(function (card, i) {
        // Always clear first — ensures mobile gets a clean slate
        card.style.gridColumn  = '';
        card.style.gridRow     = '';
        card.style.aspectRatio = '';
        card.classList.remove('blog-card--wide');

        if (isMobile) return; // let CSS media query handle single-column layout

        var pos = i % 6;   // position within the 6-card repeating cycle

        if (pos === 0) {
          // Wide LEFT: spans cols 1-2, rows 1-2
          card.style.gridColumn  = '1 / span 2';
          card.style.gridRow     = 'span 2';
          card.style.aspectRatio = 'unset';
          card.classList.add('blog-card--wide');
        } else if (pos === 1 || pos === 2) {
          card.style.gridColumn = '3';           // Narrow RIGHT
        } else if (pos === 3 || pos === 4) {
          card.style.gridColumn = '1';           // Narrow LEFT
        } else {
          // Wide RIGHT: spans cols 2-3, rows 1-2
          card.style.gridColumn  = '2 / span 2';
          card.style.gridRow     = 'span 2';
          card.style.aspectRatio = 'unset';
          card.classList.add('blog-card--wide');
        }
      });
    }

    // Run once on load
    applyGridLayout();

    // Re-run on resize / orientation change (debounced 150ms)
    var resizeTimer;
    window.addEventListener('resize', function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(applyGridLayout, 150);
    }, { passive: true });
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
