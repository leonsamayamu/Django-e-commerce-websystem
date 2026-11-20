// Draws the analytics charts with Chart.js (vendored in panel/static/panel/vendor/, no CDN needed).
(() => {
  const el = document.getElementById("analytics-data");
  if (!el || typeof Chart === "undefined") return;
  const d = JSON.parse(el.textContent);
  const TEAL = "#0f766e", TEAL_LIGHT = "#5eead4", SLATE = "#94a3b8";
  const money = (v) => `${d.currency} ${Number(v).toLocaleString()}`;
  Chart.defaults.font.family = "ui-sans-serif, system-ui, sans-serif";
  Chart.defaults.color = "#64748b";
  Chart.defaults.maintainAspectRatio = false;

  const canvas = (name) => document.querySelector(`[data-chart="${name}"]`);
  const empty = (name, values) => {            // show a friendly note instead of a blank chart
    if (values.some((v) => v > 0)) return false;
    const c = canvas(name);
    c.parentElement.innerHTML = '<p class="grid h-full place-items-center text-sm text-slate-400">No data for this period yet.</p>';
    return true;
  };
  const grid = { color: "#e2e8f0" };

  if (!empty("revenue", [...d.revenue.revenue, ...d.revenue.orders])) {
    new Chart(canvas("revenue"), {
      data: {
        labels: d.revenue.labels,
        datasets: [
          { type: "bar", label: "Revenue", data: d.revenue.revenue, backgroundColor: TEAL_LIGHT, borderRadius: 4, yAxisID: "y" },
          { type: "line", label: "Orders", data: d.revenue.orders, borderColor: TEAL, backgroundColor: TEAL, tension: .3, pointRadius: 2, yAxisID: "y1" },
        ],
      },
      options: {
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } },
          y: { beginAtZero: true, grid, ticks: { callback: (v) => Number(v).toLocaleString() } },
          y1: { beginAtZero: true, position: "right", grid: { display: false }, ticks: { precision: 0 } },
        },
        plugins: { tooltip: { callbacks: { label: (c) => c.dataset.label === "Revenue" ? `Revenue: ${money(c.parsed.y)}` : `Orders: ${c.parsed.y}` } } },
      },
    });
  }
  if (!empty("status", d.status.values)) {
    new Chart(canvas("status"), {
      type: "doughnut",
      data: { labels: d.status.labels, datasets: [{ data: d.status.values, backgroundColor: ["#f59e0b", "#0ea5e9", "#14b8a6", "#10b981", "#dc2626"], borderWidth: 2 }] },
      options: { cutout: "62%", plugins: { legend: { position: "bottom" } } },
    });
  }
  const horizontalBar = (name, data) => {
    if (empty(name, data.values)) return;
    new Chart(canvas(name), {
      type: "bar",
      data: { labels: data.labels, datasets: [{ data: data.values, backgroundColor: TEAL, borderRadius: 4 }] },
      options: {
        indexAxis: "y",
        scales: { x: { beginAtZero: true, grid, ticks: { callback: (v) => Number(v).toLocaleString() } }, y: { grid: { display: false } } },
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => money(c.parsed.x) } } },
      },
    });
  };
  horizontalBar("products", d.products);
  horizontalBar("categories", d.categories);

  if (!empty("people", [...d.people.customers, ...d.people.subscribed, ...d.people.unsubscribed])) {
    new Chart(canvas("people"), {
      type: "bar",
      data: {
        labels: d.people.labels,
        datasets: [
          { label: "New customers", data: d.people.customers, backgroundColor: TEAL },
          { label: "Subscribed", data: d.people.subscribed, backgroundColor: TEAL_LIGHT },
          { label: "Unsubscribed", data: d.people.unsubscribed, backgroundColor: SLATE },
        ],
      },
      options: {
        scales: { x: { stacked: true, grid: { display: false }, ticks: { maxTicksLimit: 10 } }, y: { stacked: true, beginAtZero: true, grid, ticks: { precision: 0 } } },
        plugins: { legend: { position: "bottom" } },
      },
    });
  }
})();
