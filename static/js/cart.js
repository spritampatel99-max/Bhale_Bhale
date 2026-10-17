/* AJAX cart: add, change quantity, remove. Falls back to normal form posts without JS. */
(function () {
  "use strict";
  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));

  function setBadge(count) {
    $$("[data-cart-count]").forEach((el) => {
      el.textContent = count;
      el.classList.remove("bump");
      void el.offsetWidth;
      el.classList.add("bump");
    });
  }

  function applyTotals(data) {
    const map = { subtotal: data.subtotal, savings: data.savings, delivery: data.delivery, total: data.total, gap: data.free_delivery_gap };
    Object.entries(map).forEach(([k, v]) => $$('[data-sum="' + k + '"]').forEach((el) => (el.textContent = v)));
    const saveRow = $('[data-sum-row="savings"]');
    if (saveRow) saveRow.hidden = !data.has_savings;
    const ship = $("[data-free-ship]");
    if (ship) ship.hidden = data.free_delivery_gap === "\u20b90.00" || data.empty;
  }

  async function send(form, submitter) {
    const body = new FormData(form, submitter || undefined);
    const res = await fetch(form.action, {
      method: "POST",
      body,
      headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": NM.csrf(), Accept: "application/json" },
      credentials: "same-origin",
    });
    if (res.redirected && res.url.includes("/login/")) { window.location.href = res.url; return null; }
    return res.json();
  }

  document.addEventListener("submit", async (e) => {
    const form = e.target;
    const kind = form.matches("[data-cart-add]") ? "add" : form.matches("[data-cart-update]") ? "update" : form.matches("[data-cart-remove]") ? "remove" : null;
    if (!kind || !window.fetch) return;
    e.preventDefault();
    const btn = e.submitter || $('button[type="submit"]', form);
    if (btn) btn.classList.add("is-loading");
    try {
      const data = await send(form, e.submitter);
      if (!data) return;
      NM.toast(data.message, data.ok ? "ok" : "error");
      if (data.ok) {
        setBadge(data.cart_count);
        if (kind !== "add") {
          const row = form.closest("[data-cart-row]");
          if (row && (kind === "remove" || !data.item)) {
            row.classList.add("removing");
            setTimeout(() => { row.remove(); if (data.empty) window.location.reload(); }, 260);
          } else if (row && data.item) {
            $("[data-qty]", row).textContent = data.item.quantity;
            $("[data-line-total]", row).textContent = data.item.line_total;
          }
          applyTotals(data);
        }
      }
    } catch (err) {
      NM.toast("Something went wrong. Please try again.", "error");
    } finally {
      if (btn) btn.classList.remove("is-loading");
    }
  });
})();
