<<<<<<< HEAD
// ---- toast + AJAX add-to-cart (falls back to a normal form post if JS fails)
function showToast(text) {
  const t = document.getElementById("toast");
  if (!t) return;
=======
// Add to cart without reloading the page; falls back to normal form post if JS fails.
function showToast(text) {
  const t = document.getElementById("toast");
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
  t.textContent = text;
  t.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => (t.hidden = true), 2500);
}

document.querySelectorAll(".add-form").forEach((form) => {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(form.action, {
        method: "POST",
        body: new FormData(form), // includes the CSRF token field
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const data = await res.json();
      document.getElementById("cart-count").textContent = data.count;
      showToast(data.message);
    } catch (err) {
      form.submit();
    }
  });
});
<<<<<<< HEAD

// ---- product page: choosing a variant updates price and availability
document.querySelectorAll("form[data-variants]").forEach((form) => {
  const variants = JSON.parse(form.dataset.variants);
  const select = form.querySelector("#variant");
  const price = document.getElementById("price-text");
  const stock = form.querySelector("#stock-text");
  const qty = form.querySelector("input[name=quantity]");
  select.addEventListener("change", () => {
    const v = variants.find((x) => String(x.id) === select.value);
    if (!v) return;
    price.textContent = `${form.dataset.currency} ${v.price}`;
    stock.textContent = v.stock <= 5 ? `Only ${v.stock} left` : "In stock";
    stock.classList.toggle("text-amber-700", v.stock <= 5);
    qty.max = v.stock;
    if (Number(qty.value) > v.stock) qty.value = v.stock;
  });
});

// ---- product card photo slider (landing page)
document.querySelectorAll(".slider[data-images]").forEach((slider) => {
  let images = [];
  try { images = JSON.parse(slider.dataset.images); } catch (e) { return; }
  if (images.length < 2) return;
  const img = slider.querySelector(".slide");
  const counter = slider.querySelector(".slide-count");
  let i = 0;
  const show = (n) => {
    i = (n + images.length) % images.length;
    img.src = images[i];
    counter.textContent = `${i + 1} / ${images.length}`;
  };
  slider.querySelector(".prev").addEventListener("click", () => show(i - 1));
  slider.querySelector(".next").addEventListener("click", () => show(i + 1));
  let startX = null; // swipe support
  slider.addEventListener("touchstart", (e) => (startX = e.touches[0].clientX), { passive: true });
  slider.addEventListener("touchend", (e) => {
    if (startX === null) return;
    const dx = e.changedTouches[0].clientX - startX;
    if (Math.abs(dx) > 40) show(i + (dx < 0 ? 1 : -1));
    startX = null;
  });
});

// ---- product detail gallery + lightbox
document.querySelectorAll("[data-gallery]").forEach((gallery) => {
  const main = gallery.querySelector("#main-photo");
  const thumbs = [...gallery.querySelectorAll(".thumb")];
  const urls = thumbs.length ? thumbs.map((t) => t.dataset.src) : [main.src];
  const dialog = document.getElementById("lightbox");
  const lbImg = dialog.querySelector("img");
  let current = 0;
  const select = (n) => {
    current = (n + urls.length) % urls.length;
    main.src = urls[current];
    thumbs.forEach((t, k) => {
      t.classList.toggle("ring-2", k === current);
      t.classList.toggle("ring-teal-700", k === current);
      t.classList.toggle("ring-1", k !== current);
      t.classList.toggle("ring-slate-200", k !== current);
    });
  };
  thumbs.forEach((t, k) => t.addEventListener("click", () => select(k)));
  const lb = (n) => { select(n); lbImg.src = urls[current]; };
  gallery.querySelector("[data-open-lightbox]").addEventListener("click", () => {
    lbImg.src = urls[current];
    lbImg.alt = main.alt;
    dialog.showModal();
  });
  dialog.querySelector(".lightbox-close").addEventListener("click", () => dialog.close());
  dialog.querySelectorAll("[data-lb]").forEach((b) => b.addEventListener("click", () => lb(current + Number(b.dataset.lb))));
  dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); });
  document.addEventListener("keydown", (e) => {
    if (!dialog.open) return;
    if (e.key === "ArrowRight") lb(current + 1);
    if (e.key === "ArrowLeft") lb(current - 1);
  });
});

// ---- mobile sidebar and header menu toggles (Tailwind's `hidden` class)
document.querySelectorAll(".sidebar-toggle").forEach((btn) => {
  btn.addEventListener("click", () => {
    const sidebar = document.getElementById("sidebar");
    sidebar.classList.toggle("hidden");
    btn.setAttribute("aria-expanded", String(!sidebar.classList.contains("hidden")));
  });
});
const navToggle = document.getElementById("nav-toggle");
if (navToggle) {
  navToggle.addEventListener("click", () => {
    const nav = document.getElementById("mobile-nav");
    nav.classList.toggle("hidden");
    navToggle.setAttribute("aria-expanded", String(!nav.classList.contains("hidden")));
  });
}

// ---- staff: preview newly selected photos before upload
const fileInput = document.getElementById("id_new_images");
const preview = document.getElementById("upload-preview");
if (fileInput && preview) {
  fileInput.addEventListener("change", () => {
    preview.replaceChildren();
    [...fileInput.files].forEach((f) => {
      if (!f.type.startsWith("image/")) return;
      const img = document.createElement("img");
      img.className = "aspect-square w-full rounded-lg object-cover";
      img.alt = f.name;
      img.src = URL.createObjectURL(f);
      img.onload = () => URL.revokeObjectURL(img.src);
      preview.appendChild(img);
    });
  });
}
=======
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
