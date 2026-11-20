/** Tailwind scans these files for class names. Add new template/JS locations here. */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./*/templates/**/*.html",
    "./store/static/store/app.js",
    "./panel/static/panel/panel.js",
    "./assistant/static/assistant/assistant.js",
    "./panel/static/panel/analytics.js",
    "./panel/templatetags/*.py",
    "./store/*.py", "./accounts/*.py", "./support/*.py",
  ].filter(Boolean),
  theme: { extend: {} },
  plugins: [require("@tailwindcss/forms")],
};
