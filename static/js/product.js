/* Product detail: image gallery + quantity stepper. */
(function () {
  "use strict";
  const stage = document.querySelector("[data-stage]");
  const thumbs = Array.from(document.querySelectorAll("[data-thumb]"));
  thumbs.forEach((btn) => {
    btn.addEventListener("click", () => {
      stage.src = btn.dataset.thumb;
      stage.alt = btn.dataset.alt;
      thumbs.forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
    });
  });

  const wrap = document.querySelector("[data-stepper]");
  if (wrap) {
    const input = wrap.querySelector("input");
    const max = parseInt(input.max, 10) || 1;
    const clamp = (n) => Math.max(1, Math.min(max, isNaN(n) ? 1 : n));
    wrap.querySelector("[data-step-down]").addEventListener("click", () => (input.value = clamp(parseInt(input.value, 10) - 1)));
    wrap.querySelector("[data-step-up]").addEventListener("click", () => (input.value = clamp(parseInt(input.value, 10) + 1)));
    input.addEventListener("change", () => (input.value = clamp(parseInt(input.value, 10))));
  }
})();
