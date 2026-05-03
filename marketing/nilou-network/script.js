/* Nilou Network — landing page client script
 * Vanilla JS, no framework, no tracking, no third-party calls.
 * AGPL-3.0, original work.
 *
 * Responsibilities:
 *   1. Scroll-triggered reveal for [.scroll-reveal] elements
 *   2. Topbar elevation when scrolled past hero
 *   3. Mobile drawer toggle (< 880px)
 */

(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // 1. Scroll reveal
  if (!reduceMotion && 'IntersectionObserver' in window) {
    var revealTargets = document.querySelectorAll('.scroll-reveal');
    if (revealTargets.length) {
      var revealObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            revealObserver.unobserve(entry.target);
          }
        });
      }, { rootMargin: '0px 0px -8% 0px', threshold: 0.15 });
      revealTargets.forEach(function (el) { revealObserver.observe(el); });
    }
  } else {
    document.querySelectorAll('.scroll-reveal').forEach(function (el) {
      el.classList.add('is-visible');
    });
  }

  // 2. Topbar elevation
  var sentinel = document.querySelector('.topbar-sentinel');
  var topbar = document.querySelector('.topbar');
  if (sentinel && topbar && 'IntersectionObserver' in window) {
    var topbarObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        topbar.classList.toggle('is-scrolled', !entry.isIntersecting);
      });
    });
    topbarObserver.observe(sentinel);
  }

  // 3. Mobile drawer
  var hamburger = document.querySelector('.hamburger');
  var drawer = document.querySelector('.mobile-drawer');
  if (hamburger && drawer) {
    hamburger.addEventListener('click', function () {
      var isOpen = drawer.classList.toggle('is-open');
      hamburger.setAttribute('aria-expanded', String(isOpen));
      document.body.style.overflow = isOpen ? 'hidden' : '';
    });
    drawer.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') {
        drawer.classList.remove('is-open');
        hamburger.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
      }
    });
  }
})();
