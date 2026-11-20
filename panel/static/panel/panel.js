// Admin panel behaviour: off-canvas sidebar, pop-up (modal) forms, auto-dismissing alerts.
(() => {
  const AJAX = { "X-Requested-With": "XMLHttpRequest" };
  const dialog = document.getElementById("modal");
  const box = document.getElementById("modal-content");
  let opener = null;

  // ---- sidebar (mobile)
  const sidebar = document.getElementById("panel-sidebar");
  const overlay = document.getElementById("panel-overlay");
  const toggle = document.getElementById("panel-toggle");
  const setSidebar = (open) => {
    sidebar.classList.toggle("-translate-x-full", !open);
    overlay.classList.toggle("hidden", !open);
    toggle.setAttribute("aria-expanded", String(open));
  };
  if (toggle) {
    toggle.addEventListener("click", () => setSidebar(sidebar.classList.contains("-translate-x-full")));
    overlay.addEventListener("click", () => setSidebar(false));
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") setSidebar(false); });
  }

  // ---- alerts fade away
  document.querySelectorAll("[data-autodismiss]").forEach((el) => {
    setTimeout(() => { el.classList.add("opacity-0", "transition-opacity"); setTimeout(() => el.remove(), 400); }, 6000);
  });

  // ---- modal helpers
  const message = (text) =>
    `<div class="p-8 text-center"><p class="text-sm text-slate-700">${text}</p>` +
    `<button type="button" data-modal-close class="btn btn-outline mt-5">Close</button></div>`;
  const focusFirst = () => box.querySelector("input:not([type=hidden]):not([disabled]), select, textarea")?.focus();
  const sessionExpired = (res) => res.redirected && /\/accounts\/login/.test(res.url);

  async function openModal(url) {
    box.innerHTML = '<div class="p-10 text-center text-sm text-slate-500">Loading&hellip;</div>';
    if (!dialog.open) dialog.showModal();
    try {
      const res = await fetch(url, { headers: AJAX });
      if (sessionExpired(res)) { location.href = res.url; return; }
      if (res.status === 403) { box.innerHTML = message("You do not have permission to do that."); return; }
      if (!res.ok) throw new Error(res.status);
      box.innerHTML = await res.text();
      focusFirst();
    } catch (err) {
      box.innerHTML = message("Something went wrong loading this form. Please try again.");
    }
  }

  document.addEventListener("click", (e) => {
    const trigger = e.target.closest("[data-modal]");
    if (trigger) {
      e.preventDefault();
      opener = trigger;
      openModal(trigger.dataset.modal || trigger.getAttribute("href"));
      return;
    }
    if (e.target.closest("[data-modal-close]")) dialog.close();
  });
  dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); }); // click on backdrop
  dialog.addEventListener("close", () => { box.innerHTML = ""; if (opener && document.contains(opener)) opener.focus(); });

  // ---- submit the pop-up form with fetch; errors re-render inside the pop-up, success reloads the page
  document.addEventListener("submit", async (e) => {
    const form = e.target.closest("[data-modal-form]");
    if (!form) return;
    e.preventDefault();
    const btn = form.querySelector("[type=submit]");
    const label = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Saving\u2026";
    try {
      const res = await fetch(form.action, { method: "POST", body: new FormData(form), headers: AJAX });
      if (sessionExpired(res)) { location.href = res.url; return; }
      if (res.status === 403) { box.innerHTML = message("You do not have permission to do that."); return; }
      if ((res.headers.get("content-type") || "").includes("application/json")) {
        const data = await res.json();
        if (data.ok) { dialog.close(); location.reload(); return; }
      }
      box.innerHTML = await res.text();      // validation errors
      focusFirst();
      box.querySelector(".text-red-600, .alert-error")?.scrollIntoView({ block: "center" });
    } catch (err) {
      btn.disabled = false;
      btn.textContent = label;
      box.insertAdjacentHTML("afterbegin", '<div class="alert alert-error m-4">Network error. Please try again.</div>');
    }
  });

  // ---- product options: add a row by cloning the empty-form template
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-add-variant]");
    if (!btn) return;
    const box = btn.closest("[data-variants-box]");
    const total = box.querySelector("input[name$='-TOTAL_FORMS']");
    const html = box.querySelector("[data-variant-template]").innerHTML.replaceAll("__prefix__", total.value);
    box.querySelector("[data-variant-rows]").insertAdjacentHTML("beforeend", html);
    total.value = Number(total.value) + 1;
    box.querySelector("[data-variant-row]:last-child input[type=text]")?.focus();
  });

  // ---- preview newly chosen product photos (works inside the injected form)
  document.addEventListener("change", (e) => {
    if (e.target.id !== "id_new_images") return;
    const preview = document.getElementById("upload-preview");
    if (!preview) return;
    preview.replaceChildren();
    [...e.target.files].forEach((f) => {
      if (!f.type.startsWith("image/")) return;
      const img = document.createElement("img");
      img.className = "aspect-square w-full rounded-lg object-cover";
      img.alt = f.name;
      img.src = URL.createObjectURL(f);
      img.onload = () => URL.revokeObjectURL(img.src);
      preview.appendChild(img);
    });
  });
})();
