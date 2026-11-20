// Polls the order's payment status every 3 seconds (the server asks PayHero) until it is paid or failed.
(() => {
  const root = document.getElementById("pay-wait");
  if (!root) return;
  const $ = (id) => document.getElementById(id);
  const finish = (ok, data) => {
    $("pay-spinner").classList.add("hidden");
    $("pay-title").textContent = ok ? "Payment received. Thank you!" : "Payment not completed";
    $("pay-message").textContent = ok ? (data.receipt ? `M-Pesa receipt ${data.receipt}` : "Your order is being prepared.") : (data.message || "You can try again from your order page.");
    const actions = $("pay-actions");
    actions.classList.remove("hidden");
    actions.classList.add("flex");
  };
  let tries = 0;
  const tick = async () => {
    tries += 1;
    try {
      const res = await fetch(root.dataset.statusUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      const data = await res.json();
      if (data.status === "success") return finish(true, data);
      if (data.status === "failed") return finish(false, data);
      $("pay-message").textContent = data.message || "Waiting for your confirmation...";
    } catch (e) { /* network hiccup: keep trying */ }
    if (tries < 60) setTimeout(tick, 3000);
    else finish(false, { message: "We have not received a confirmation yet. If money left your account it will be matched automatically; check your order page shortly." });
  };
  if (root.dataset.initial === "failed") { $("pay-spinner").classList.add("hidden"); $("pay-title").textContent = "Payment not completed"; $("pay-actions").classList.remove("hidden"); $("pay-actions").classList.add("flex"); }
  else if (root.dataset.initial === "success") finish(true, {});
  else setTimeout(tick, 2000);
})();
