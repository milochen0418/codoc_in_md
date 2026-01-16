(() => {
  const CLASS_NAME = "codoc-fullscreen";

  const ensurePreview = () => {
    const btn = document.querySelector('button[title="Preview Only"]');
    if (btn) btn.click();
  };

  const addClass = () => {
    document.documentElement.classList.add(CLASS_NAME);
    document.body.classList.add(CLASS_NAME);
  };

  const removeClass = () => {
    document.documentElement.classList.remove(CLASS_NAME);
    document.body.classList.remove(CLASS_NAME);
  };

  const isActive = () => document.documentElement.classList.contains(CLASS_NAME);

  const enter = () => {
    ensurePreview();
    requestAnimationFrame(addClass);
  };

  const exit = () => {
    removeClass();
  };

  const toggle = () => {
    if (isActive()) {
      exit();
    } else {
      enter();
    }
  };

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && isActive()) {
      event.preventDefault();
      exit();
    }
  });

  window.codocToggleFullscreen = toggle;
  window.codocExitFullscreen = exit;
})();
