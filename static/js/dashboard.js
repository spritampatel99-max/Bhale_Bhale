/* Dashboard: sidebar toggle + Chart.js charts built from server-rendered JSON. */
(function () {
  "use strict";
  const toggle = document.querySelector("[data-side-toggle]");
  const side = document.querySelector(".sidebar");
  if (toggle && side) {
    toggle.addEventListener("click", () => side.classList.toggle("open"));
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") side.classList.remove("open"); });
    side.addEventListener("click", (e) => { if (e.target === side) side.classList.remove("open"); });
  }

  const read = (id) => { const el = document.getElementById(id); return el ? JSON.parse(el.textContent) : null; };
  const make = (id, config) => {
    const canvas = document.getElementById(id);
    if (!canvas || !window.Chart) return null;
    return new Chart(canvas, config);
  };
  const markEmpty = (id, empty) => { const box = document.getElementById(id); if (box) box.parentElement.classList.toggle("no-data", empty); };

  const INK = "#0b1b33", SUN = "#ffb81c", SKY = "#2f6bff", MINT = "#12875a", ROSE = "#e5484d", VIOLET = "#6d4ae0", TEAL = "#0e8a9a";
  const PALETTE = [SKY, SUN, MINT, VIOLET, ROSE, TEAL, "#b07a3e", "#3a4a63"];
  if (window.Chart) {
    Chart.defaults.font.family = '"DM Sans", "Segoe UI", system-ui, sans-serif';
    Chart.defaults.color = "#56667e";
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
  }
  const money = (cur) => (v) => cur + Number(v).toLocaleString("en-IN", { maximumFractionDigits: 0 });
  const moneyFull = (cur) => (v) => cur + Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  // ---- overview: last 14 days
  const act = read("activity-data");
  if (act) {
    const cur = act.currency || "\u20b9";
    markEmpty("activityChart", !act.revenue.some((v) => v > 0));
    make("activityChart", {
      type: "bar",
      data: { labels: act.labels, datasets: [{ label: "Revenue", data: act.revenue, backgroundColor: SKY, borderRadius: 6, maxBarThickness: 28 }] },
      options: { plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => " " + moneyFull(cur)(c.parsed.y) } } },
                 scales: { y: { beginAtZero: true, ticks: { callback: money(cur) }, grid: { color: "#eef1f6" } }, x: { grid: { display: false } } } },
    });
  }

  // ---- analytics
  const d = read("analytics-data");
  if (d) {
    const cur = d.currency;
    let period = "daily";
    const series = () => d.series[period];
    const hasSales = Object.values(d.series).some((s) => s.revenue.some((v) => v > 0));
    ["revenueChart", "ordersChart", "productsChart", "categoryChart", "statusChart"].forEach((id) => markEmpty(id, !hasSales));

    const revenue = make("revenueChart", {
      type: "line",
      data: { labels: series().labels, datasets: [{ label: "Revenue", data: series().revenue, borderColor: SKY, backgroundColor: "rgba(47,107,255,.12)", fill: true, tension: .3, pointRadius: 2, pointHoverRadius: 5, borderWidth: 2.5 }] },
      options: { interaction: { mode: "index", intersect: false },
                 plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => " Revenue: " + moneyFull(cur)(c.parsed.y) } } },
                 scales: { y: { beginAtZero: true, ticks: { callback: money(cur) }, grid: { color: "#eef1f6" } }, x: { grid: { display: false }, ticks: { maxTicksLimit: 12, autoSkip: true } } } },
    });
    const orders = make("ordersChart", {
      type: "bar",
      data: { labels: series().labels, datasets: [{ label: "Orders", data: series().orders, backgroundColor: SUN, borderRadius: 5 }] },
      options: { plugins: { legend: { display: false } },
                 scales: { y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#eef1f6" } }, x: { grid: { display: false }, ticks: { maxTicksLimit: 12, autoSkip: true } } } },
    });
    document.querySelectorAll("[data-period]").forEach((btn) => {
      btn.addEventListener("click", () => {
        period = btn.dataset.period;
        document.querySelectorAll("[data-period]").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
        if (revenue) { revenue.data.labels = series().labels; revenue.data.datasets[0].data = series().revenue; revenue.update(); }
        if (orders) { orders.data.labels = series().labels; orders.data.datasets[0].data = series().orders; orders.update(); }
      });
    });
    make("productsChart", {
      type: "bar",
      data: { labels: d.products.labels, datasets: [{ label: "Units sold", data: d.products.units, backgroundColor: MINT, borderRadius: 5 }] },
      options: { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#eef1f6" } }, y: { grid: { display: false } } } },
    });
    make("categoryChart", {
      type: "doughnut",
      data: { labels: d.categories.labels, datasets: [{ data: d.categories.revenue, backgroundColor: PALETTE, borderWidth: 2, borderColor: "#fff" }] },
      options: { cutout: "62%", plugins: { legend: { position: "bottom" }, tooltip: { callbacks: { label: (c) => " " + c.label + ": " + moneyFull(cur)(c.parsed) } } } },
    });
    make("statusChart", {
      type: "doughnut",
      data: { labels: d.statuses.labels, datasets: [{ data: d.statuses.counts, backgroundColor: [SUN, SKY, TEAL, VIOLET, MINT, ROSE], borderWidth: 2, borderColor: "#fff" }] },
      options: { cutout: "62%", plugins: { legend: { position: "bottom" } } },
    });
  }
})();
