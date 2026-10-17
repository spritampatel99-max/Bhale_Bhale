/* NovaMart shared behaviour. JavaScript only enhances; the server is the source of truth. */
(function () {
  "use strict";
  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));

  window.NM = window.NM || {};
  NM.csrf = () => (document.querySelector('meta[name="csrf-token"]') || {}).content || "";

  NM.toast = function (text, type) {
    const region = $("#toast-region");
    if (!region) return;
    const el = document.createElement("div");
    el.className = "toast" + (type === "error" ? " error" : "");
    el.setAttribute("role", type === "error" ? "alert" : "status");
    el.textContent = text;
    region.appendChild(el);
    setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 300); }, 3600);
  };

  // Dropdown menus (account menu)
  $$("[data-dropdown]").forEach((dd) => {
    const btn = $("[data-dropdown-toggle]", dd);
    const setOpen = (open) => { dd.classList.toggle("open", open); btn.setAttribute("aria-expanded", String(open)); };
    btn.addEventListener("click", (e) => { e.stopPropagation(); setOpen(!dd.classList.contains("open")); });
    document.addEventListener("click", (e) => { if (!dd.contains(e.target)) setOpen(false); });
    dd.addEventListener("keydown", (e) => { if (e.key === "Escape") { setOpen(false); btn.focus(); } });
  });

  // Generic toggles: <button data-toggle="#target" data-toggle-class="open">
  $$("[data-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = $(btn.dataset.toggle);
      if (!target) return;
      const open = target.classList.toggle(btn.dataset.toggleClass || "open");
      btn.setAttribute("aria-expanded", String(open));
    });
  });

  // Show/hide password
  $$("[data-password-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = $("input", btn.parentElement);
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
      btn.setAttribute("aria-pressed", String(show));
      $("use", btn).setAttribute("href", "#" + (show ? "i-eye-off" : "i-eye"));
    });
  });

  // Dismissable messages
  $$(".message .close").forEach((b) => b.addEventListener("click", () => b.closest(".message").remove()));
  $$(".message.success").forEach((m) => setTimeout(() => m.remove(), 6000));

  // Prevent double submits on regular forms
  $$("form[data-once]").forEach((form) => {
    form.addEventListener("submit", () => {
      const b = $('button[type="submit"]', form);
      if (b) { setTimeout(() => { b.classList.add("is-loading"); b.disabled = true; }, 0); }
    });
  });

  // Confirm dialogs for destructive actions
  $$("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (e) => { if (!window.confirm(form.dataset.confirm)) e.preventDefault(); });
  });

  // Fill checkout address from a saved address
  $$("[data-fill-address]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const data = JSON.parse(btn.dataset.fillAddress);
      Object.entries(data).forEach(([name, value]) => {
        const field = document.querySelector('[name="' + name + '"]');
        if (field) field.value = value;
      });
      NM.toast("Address filled in.");
    });
  });
})();
