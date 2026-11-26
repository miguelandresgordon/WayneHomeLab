// wayne-fonts.js — @font-face for the wayne_default theme, served by HA from
// /config/www/wayne (=/local/wayne). No external requests.
// Registered globally via frontend.extra_module_url (configuration.haos.yaml).
const FACES = [
  ["Inter", 400, "/local/wayne/fonts/inter-latin-400-normal.woff2"],
  ["Inter", 600, "/local/wayne/fonts/inter-latin-600-normal.woff2"],
  ["Inter", 800, "/local/wayne/fonts/inter-latin-800-normal.woff2"],
  ["JetBrains Mono", 400, "/local/wayne/fonts/jetbrains-mono-latin-400-normal.woff2"],
  ["JetBrains Mono", 700, "/local/wayne/fonts/jetbrains-mono-latin-700-normal.woff2"],
];

if (!document.getElementById("wayne-fonts")) {
  const css = FACES.map(
    ([family, weight, url]) =>
      `@font-face{font-family:"${family}";font-style:normal;font-weight:${weight};font-display:swap;src:url("${url}") format("woff2");}`
  ).join("\n");
  const style = document.createElement("style");
  style.id = "wayne-fonts";
  style.textContent = css;
  document.head.appendChild(style);
}
