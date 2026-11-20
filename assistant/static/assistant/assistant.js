// Chat widget. Everything shown is inserted with textContent, so replies can never inject HTML.
(() => {
  const root = document.getElementById("assistant");
  if (!root) return;
  const $ = (id) => document.getElementById(id);
  const panel = $("assistant-panel"), log = $("assistant-log"), input = $("assistant-input"), chips = $("assistant-chips");
  const csrf = root.dataset.csrf;
  let started = false, busy = false;

  const add = (text, who) => {
    const el = document.createElement("div");
    el.className = who === "user"
      ? "max-w-[85%] self-end whitespace-pre-line rounded-2xl rounded-br-sm bg-teal-700 px-3 py-2 text-white"
      : "max-w-[90%] self-start whitespace-pre-line rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-3 py-2 text-slate-800";
    el.textContent = text;
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  };

  async function start() {
    if (started) return;
    started = true;
    try {
      const res = await fetch(root.dataset.init, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!res.ok) return;
      const data = await res.json();
      add(data.greeting, "bot");
      (data.history || []).forEach((m) => add(m.content, m.role === "user" ? "user" : "bot"));
      (data.chips || []).forEach((c) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "chip";
        b.textContent = c.title;
        b.addEventListener("click", () => send("/" + c.trigger));
        chips.appendChild(b);
      });
    } catch (e) { add("Sorry, the assistant is not available right now.", "bot"); }
  }

  async function send(text) {
    text = text.trim();
    if (!text || busy) return;
    busy = true;
    add(text, "user");
    input.value = "";
    const thinking = add("...", "bot");
    try {
      const res = await fetch(root.dataset.chat, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      thinking.textContent = data.reply || "Sorry, something went wrong.";
    } catch (e) {
      thinking.textContent = "Sorry, something went wrong. Please try again.";
    }
    busy = false;
    log.scrollTop = log.scrollHeight;
    input.focus();
  }

  const open = (show) => {
    panel.classList.toggle("hidden", !show);
    panel.classList.toggle("flex", show);
    $("assistant-open").setAttribute("aria-expanded", String(show));
    if (show) { start(); input.focus(); }
  };
  $("assistant-open").addEventListener("click", () => open(panel.classList.contains("hidden")));
  $("assistant-close").addEventListener("click", () => open(false));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !panel.classList.contains("hidden")) open(false); });
  $("assistant-form").addEventListener("submit", (e) => { e.preventDefault(); send(input.value); });
  $("assistant-reset").addEventListener("click", async () => {
    try { await fetch(root.dataset.reset, { method: "POST", headers: { "X-CSRFToken": csrf } }); } catch (e) { /* ignore */ }
    log.replaceChildren();
    chips.replaceChildren();
    started = false;
    start();
  });
})();
