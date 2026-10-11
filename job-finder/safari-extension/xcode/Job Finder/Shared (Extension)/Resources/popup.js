const extensionApi = globalThis.browser ?? globalThis.chrome;
const scanButton = document.querySelector("#scan");
const fillButton = document.querySelector("#fill");
const downloadResumeButton = document.querySelector("#download-resume");
const completeButton = document.querySelector("#complete");
const status = document.querySelector("#status");
const result = document.querySelector("#result");
const fieldList = document.querySelector("#fields");
const limitations = document.querySelector("#limitations");
const apiBaseInput = document.querySelector("#api-base");
const apiTokenInput = document.querySelector("#api-token");
const settingsForm = document.querySelector("#settings");

const DEFAULT_API = "http://127.0.0.1:8473";

let currentTab = null;
let currentInventory = null;
let currentSession = null;
let currentMappings = [];

function setStatus(message, isError = false) {
  status.textContent = message;
  status.classList.toggle("error", isError);
}

function tabKeyFor(tab) {
  return `tab-${tab.id}`;
}

function pageOrigin(tab, inventory) {
  return inventory?.page?.origin || new URL(tab.url).origin;
}

async function loadSettings() {
  const stored = await extensionApi.storage.local.get(["apiBase", "apiToken"]);
  apiBaseInput.value = stored.apiBase || DEFAULT_API;
  apiTokenInput.value = stored.apiToken || "";
}

async function saveSettings(event) {
  event.preventDefault();
  await extensionApi.storage.local.set({
    apiBase: apiBaseInput.value.trim() || DEFAULT_API,
    apiToken: apiTokenInput.value.trim(),
  });
  setStatus("Conexión guardada en este Mac.");
}

async function apiRequest(path, options = {}) {
  const stored = await extensionApi.storage.local.get(["apiBase", "apiToken"]);
  const apiBase = (stored.apiBase || DEFAULT_API).replace(/\/$/, "");
  const token = stored.apiToken || "";
  if (!token) {
    throw new Error("Falta el token de la extensión. Crea uno en Job Finder y pégalo aquí.");
  }
  const {parseJson = true, ...fetchOptions} = options;
  const headers = new Headers(fetchOptions.headers ?? {});
  headers.set("Authorization", `Bearer ${token}`);
  if (fetchOptions.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${apiBase}${path}`, {...fetchOptions, headers});
  if (!response.ok) {
    let detail = `Error HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // Keep the HTTP status when the response is not JSON.
    }
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  if (response.status === 204) {
    return null;
  }
  return parseJson ? response.json() : response.blob();
}

function mappingTitle(mapping) {
  const signals = mapping.signals || {};
  const name = signals.label || signals.name || signals.id || mapping.local_id;
  const parts = [];
  if (signals.section) {
    parts.push(signals.section);
  }
  if (signals.entry) {
    parts.push(String(signals.entry));
  }
  parts.push(name);
  return parts.join(" · ");
}

function mappingPreview(mapping) {
  if (mapping.allowed_action === "never") {
    return "bloqueado";
  }
  if (mapping.value) {
    return mapping.value;
  }
  if (mapping.doc_ref?.filename) {
    return mapping.doc_ref.filename;
  }
  if (mapping.has_value || mapping.review_reason === "already_filled") {
    return "ya relleno";
  }
  if (mapping.allowed_action === "skip") {
    return mapping.explanation || "Ya rellenado en esta sesión";
  }
  return "sin valor";
}

function renderMappings(mappings, inventory) {
  fieldList.replaceChildren();
  currentMappings = mappings;
  for (const mapping of mappings) {
    const item = document.createElement("li");
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.dataset.localId = mapping.local_id;
    checkbox.checked = mapping.allowed_action === "fill" && Boolean(mapping.value);
    checkbox.disabled = mapping.allowed_action === "never" || mapping.allowed_action === "skip";
    const text = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = mappingTitle(mapping);
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `${mapping.allowed_action} · ${mappingPreview(mapping)}`;
    text.append(title, meta);
    label.append(checkbox, text);
    item.append(label);
    fieldList.append(item);
  }
  const capabilities = inventory.capabilities || {};
  const fileSupportNote =
    capabilities.data_transfer && capabilities.file_constructor
      ? "Safari expone File y DataTransfer; el PDF se adjunta a mano si el portal no acepta input.files."
      : "Este navegador no expone todas las APIs de adjuntos.";
  const blockedFrames = inventory.blocked_frames || 0;
  const skipped = mappings.filter((mapping) => mapping.already_resolved).length;
  const originNote = inventory.origin_changed
    ? " El origen de la pestaña cambió: se abre una sesión nueva y hace falta permiso del sitio."
    : "";
  limitations.textContent =
    `${fileSupportNote}${originNote}` +
    (blockedFrames > 0 ? ` ${blockedFrames} iframe(s) de otro origen no se inspeccionaron.` : "") +
    (skipped > 0 ? ` ${skipped} campo(s) ya resueltos en esta sesión.` : "");
  result.hidden = false;
  fillButton.hidden = !mappings.some((mapping) => mapping.allowed_action === "fill");
  downloadResumeButton.hidden = resumeDocRef(mappings) == null;
  completeButton.hidden = currentSession == null;
}

function resumeDocRef(mappings) {
  return mappings.find((mapping) => mapping.doc_ref?.kind === "resume" && mapping.doc_ref.id)?.doc_ref ?? null;
}

function reviewLocalIds(mappings) {
  return mappings
    .filter((mapping) => mapping.allowed_action === "review")
    .map((mapping) => mapping.local_id);
}

function originPatternFor(tab) {
  let parsed;
  try {
    parsed = new URL(tab.url);
  } catch {
    throw new Error("Esta pestaña no tiene una URL válida.");
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error("Abre el formulario del ATS en http o https e inténtalo de nuevo.");
  }
  // Match patterns reject an explicit port. http://host/* covers every port.
  const host = parsed.hostname.includes(":") ? `[${parsed.hostname}]` : parsed.hostname;
  return `${parsed.protocol}//${host}/*`;
}

async function ensureOriginPermission(tab) {
  const origin = originPatternFor(tab);
  const permissions = {origins: [origin]};
  if (typeof extensionApi.permissions?.contains === "function") {
    const already = await extensionApi.permissions.contains(permissions);
    if (already) {
      return;
    }
  }
  if (typeof extensionApi.permissions?.request !== "function") {
    return;
  }
  const granted = await extensionApi.permissions.request(permissions);
  if (!granted) {
    throw new Error(
      `Safari no tiene permiso para ${new URL(tab.url).origin}. Acepta el origen del ATS e inténtalo de nuevo.`,
    );
  }
}

async function highlightReviewFields(tab, mappings) {
  const localIds = reviewLocalIds(mappings);
  if (!tab?.id || localIds.length === 0) {
    return;
  }
  try {
    await extensionApi.tabs.sendMessage(tab.id, {
      type: "JOB_FINDER_HIGHLIGHT",
      local_ids: localIds,
    });
  } catch {
    // Highlight is assistive; a missing content script should not fail analyze/fill.
  }
}

async function activeTab() {
  const tabs = await extensionApi.tabs.query({active: true, currentWindow: true});
  if (!tabs[0]?.id) {
    throw new Error("No hay una pestaña activa.");
  }
  return tabs[0];
}

async function injectAndScan(tab) {
  await ensureOriginPermission(tab);
  await extensionApi.scripting.executeScript({
    target: {tabId: tab.id},
    files: ["form-tools.js", "content.js"],
  });
  return extensionApi.tabs.sendMessage(tab.id, {type: "JOB_FINDER_SCAN"});
}

async function ensureSession(tab, inventory) {
  const origin = pageOrigin(tab, inventory);
  const payload = {
    origin,
    tab_key: tabKeyFor(tab),
    apply_url: tab.url || `${origin}${inventory.page?.path || ""}`,
  };
  try {
    return await apiRequest("/api/v1/form-sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  } catch (error) {
    if (error.status === 409) {
      return apiRequest("/api/v1/form-sessions", {
        method: "POST",
        body: JSON.stringify({...payload, tab_key: `${tabKeyFor(tab)}-${Date.now()}`}),
      });
    }
    throw error;
  }
}

async function analyzeWithSession(session, inventory) {
  try {
    return await apiRequest(`/api/v1/form-sessions/${session.id}/analyze`, {
      method: "POST",
      body: JSON.stringify({
        schema_version: inventory.schema_version || 1,
        page: inventory.page,
        fields: inventory.fields,
        blocked_frames: inventory.blocked_frames || 0,
      }),
    });
  } catch (error) {
    if (error.status === 409 && error.message === "origin_changed") {
      const fresh = await apiRequest("/api/v1/form-sessions", {
        method: "POST",
        body: JSON.stringify({
          origin: inventory.page.origin,
          tab_key: `${tabKeyFor(currentTab)}-${Date.now()}`,
          apply_url: currentTab.url,
        }),
      });
      currentSession = fresh;
      return apiRequest(`/api/v1/form-sessions/${fresh.id}/analyze`, {
        method: "POST",
        body: JSON.stringify({
          schema_version: inventory.schema_version || 1,
          page: inventory.page,
          fields: inventory.fields,
          blocked_frames: inventory.blocked_frames || 0,
        }),
      });
    }
    throw error;
  }
}

scanButton.addEventListener("click", async () => {
  scanButton.disabled = true;
  result.hidden = true;
  fillButton.hidden = true;
  downloadResumeButton.hidden = true;
  completeButton.hidden = true;
  setStatus("Analizando la página…");
  try {
    currentTab = await activeTab();
    currentInventory = await injectAndScan(currentTab);
    currentSession = await ensureSession(currentTab, currentInventory);
    const analyzed = await analyzeWithSession(currentSession, currentInventory);
    currentSession = analyzed.session;
    renderMappings(analyzed.mappings, currentInventory);
    await highlightReviewFields(currentTab, analyzed.mappings);
    setStatus(`${analyzed.mappings.length} campos analizados. Revisa antes de rellenar.`);
  } catch (error) {
    setStatus(
      `No se pudo analizar esta página: ${error.message}. Comprueba el token, el permiso del sitio y que Job Finder esté en marcha.`,
      true,
    );
  } finally {
    scanButton.disabled = false;
  }
});

fillButton.addEventListener("click", async () => {
  if (!currentTab || !currentSession) {
    return;
  }
  fillButton.disabled = true;
  setStatus("Rellenando campos aprobados…");
  try {
    const approved = [];
    for (const mapping of currentMappings) {
      const checkbox = fieldList.querySelector(`input[data-local-id="${mapping.local_id}"]`);
      if (!checkbox?.checked || mapping.allowed_action !== "fill" || mapping.value == null) {
        continue;
      }
      approved.push({local_id: mapping.local_id, value: mapping.value});
    }
    const filled = await extensionApi.tabs.sendMessage(currentTab.id, {
      type: "JOB_FINDER_FILL",
      fields: approved,
    });
    await apiRequest(`/api/v1/form-sessions/${currentSession.id}/fill-result`, {
      method: "POST",
      body: JSON.stringify({results: filled.results || []}),
    });
    const applied = (filled.results || []).filter((item) => item.ok).length;
    await highlightReviewFields(currentTab, currentMappings);
    setStatus(`Rellenados ${applied} de ${approved.length} campos. Consentimientos y envío siguen en tus manos.`);
  } catch (error) {
    setStatus(`No se pudo rellenar: ${error.message}`, true);
  } finally {
    fillButton.disabled = false;
  }
});

downloadResumeButton.addEventListener("click", async () => {
  const ref = resumeDocRef(currentMappings);
  if (!ref) {
    return;
  }
  downloadResumeButton.disabled = true;
  try {
    const blob = await apiRequest(`/api/v1/resumes/${ref.id}/file`, {parseJson: false});
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = ref.filename || "cv.pdf";
    link.rel = "noopener";
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
    setStatus(`CV descargado (${ref.filename || "cv.pdf"}). Adjúntalo a mano en el campo de archivo.`);
  } catch (error) {
    setStatus(`No se pudo descargar el CV: ${error.message}`, true);
  } finally {
    downloadResumeButton.disabled = false;
  }
});

completeButton.addEventListener("click", async () => {
  if (!currentSession) {
    return;
  }
  completeButton.disabled = true;
  try {
    currentSession = await apiRequest(`/api/v1/form-sessions/${currentSession.id}/complete`, {
      method: "POST",
    });
    setStatus("Candidatura marcada como enviada en Job Finder. El formulario del ATS no se ha enviado.");
  } catch (error) {
    setStatus(`No se pudo marcar la candidatura: ${error.message}`, true);
  } finally {
    completeButton.disabled = false;
  }
});

settingsForm.addEventListener("submit", saveSettings);
loadSettings().catch((error) => setStatus(error.message, true));
