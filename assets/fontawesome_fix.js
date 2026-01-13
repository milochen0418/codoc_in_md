// Restore Font Awesome icon classes from sanitized markdown.
//
// Some markdown renderers strip the `class` attribute from raw HTML like:
//   <i class="fa fa-github"></i>
// The backend preprocessor preserves it in `data-fa-class`, and this script
// re-applies the class on the client.

(function () {
  function apply(root) {
    if (!root || !root.querySelectorAll) return;

    const nodes = root.querySelectorAll('[data-codoc-fa-class], [data-fa-class]');
    for (const el of nodes) {
      const wanted = el.getAttribute('data-codoc-fa-class') || el.getAttribute('data-fa-class');
      if (!wanted) continue;

      // If the sanitizer kept the class, don't clobber it.
      if (el.classList && el.classList.contains('fa')) continue;

      el.setAttribute('class', wanted);
    }
  }

  function init() {
    const root = document.getElementById('preview-pane') || document;

    // Initial pass.
    apply(root);

    // Re-apply on live preview updates.
    let scheduled = false;
    const obs = new MutationObserver(() => {
      if (scheduled) return;
      scheduled = true;
      requestAnimationFrame(() => {
        scheduled = false;
        apply(root);
      });
    });

    obs.observe(root, { subtree: true, childList: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
