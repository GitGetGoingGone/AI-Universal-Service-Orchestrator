/**
 * Partner Portal - Theme & Layout Switcher
 * Persists preferences in localStorage. Supports:
 * - Themes: light | dark | ocean | forest | slate
 * - Layouts: centered | sidebar | top-nav | compact
 */

const STORAGE_KEY = "partner_portal_prefs";
const DEFAULT_THEME = "light";
const DEFAULT_LAYOUT = "centered";

const THEMES = ["light", "dark", "ocean", "forest", "slate"];
const LAYOUTS = ["centered", "sidebar", "top-nav", "compact"];

function getServerDefaults() {
  const html = document.documentElement;
  const theme = html.getAttribute("data-default-theme");
  const layout = html.getAttribute("data-default-layout");
  return {
    theme: theme && THEMES.includes(theme) ? theme : DEFAULT_THEME,
    layout: layout && LAYOUTS.includes(layout) ? layout : DEFAULT_LAYOUT,
  };
}

function getPrefs() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const p = JSON.parse(raw);
      return {
        theme: THEMES.includes(p.theme) ? p.theme : DEFAULT_THEME,
        layout: LAYOUTS.includes(p.layout) ? p.layout : DEFAULT_LAYOUT,
      };
    }
  } catch (_) {}
  return getServerDefaults();
}

function savePrefs(prefs) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch (_) {}
}

function applyPrefs(prefs) {
  const root = document.documentElement;
  root.setAttribute("data-theme", prefs.theme);
  root.setAttribute("data-layout", prefs.layout);
}

/**
 * Initialize theme/layout from localStorage and apply.
 * Call on DOMContentLoaded.
 */
function initTheme() {
  const prefs = getPrefs();
  applyPrefs(prefs);
  return prefs;
}

/**
 * Set theme and persist.
 */
function setTheme(theme) {
  if (!THEMES.includes(theme)) return;
  const prefs = getPrefs();
  prefs.theme = theme;
  savePrefs(prefs);
  applyPrefs(prefs);
}

/**
 * Set layout and persist.
 */
function setLayout(layout) {
  if (!LAYOUTS.includes(layout)) return;
  const prefs = getPrefs();
  prefs.layout = layout;
  savePrefs(prefs);
  applyPrefs(prefs);
}

/**
 * Render theme/layout switcher UI. Call after DOM ready.
 * @param {HTMLElement} container - Where to render
 */
function renderSwitcher(container) {
  if (!container) return;
  const prefs = getPrefs();

  container.innerHTML = `
    <div class="theme-switcher">
      <label for="theme-select" style="font-size:0.75rem;margin:0;">Theme</label>
      <select id="theme-select" aria-label="Theme">
        ${THEMES.map((t) => `<option value="${t}" ${prefs.theme === t ? "selected" : ""}>${t}</option>`).join("")}
      </select>
    </div>
    <div class="layout-switcher" style="margin-left:var(--spacing-sm,0.5rem);">
      <label for="layout-select" style="font-size:0.75rem;margin:0;">Layout</label>
      <select id="layout-select" aria-label="Layout">
        ${LAYOUTS.map((l) => `<option value="${l}" ${prefs.layout === l ? "selected" : ""}>${l}</option>`).join("")}
      </select>
    </div>
  `;

  container.querySelector("#theme-select").addEventListener("change", (e) => {
    setTheme(e.target.value);
  });
  container.querySelector("#layout-select").addEventListener("change", (e) => {
    setLayout(e.target.value);
  });
}

// Auto-init when script loads
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initTheme);
} else {
  initTheme();
}
