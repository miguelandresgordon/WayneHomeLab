const extensionApi = globalThis.browser ?? globalThis.chrome;
const scanButton = document.querySelector("#scan");
const status = document.querySelector("#status");
const result = document.querySelector("#result");
const fieldList = document.querySelector("#fields");
const limitations = document.querySelector("#limitations");

function setStatus(message, isError = false) {
  status.textContent = message;
  status.classList.toggle("error", isError);
}

function renderInventory(inventory) {
  fieldList.replaceChildren();
  for (const field of inventory.fields) {
    const item = document.createElement("li");
    const name =
      field.signals.label ||
      field.signals.name ||
      field.signals.id ||
      `${field.element} ${field.type}`;
    item.textContent = `${name} — ${field.allowed_action === "fill" ? "rellenable" : "revisión manual"}`;
    fieldList.append(item);
  }
  const capabilities = inventory.capabilities;
  const fileSupportNote =
    capabilities.data_transfer && capabilities.file_constructor
      ? "Safari expone File y DataTransfer; la asignación real de PDF sigue pendiente de prueba manual."
      : "Este navegador no expone todas las APIs necesarias para probar adjuntos automáticos.";
  const blockedFrames = inventory.blocked_frames || 0;
  limitations.textContent =
    blockedFrames > 0
      ? `${fileSupportNote} ${blockedFrames} iframe(s) de otro origen no se pudieron inspeccionar.`
      : fileSupportNote;
  result.hidden = false;
  setStatus(`${inventory.fields.length} campos visibles detectados.`);
}

async function activeTab() {
  const tabs = await extensionApi.tabs.query({active: true, currentWindow: true});
  if (!tabs[0]?.id) {
    throw new Error("No hay una pestaña activa.");
  }
  return tabs[0];
}

scanButton.addEventListener("click", async () => {
  scanButton.disabled = true;
  result.hidden = true;
  setStatus("Analizando la página…");
  try {
    const tab = await activeTab();
    await extensionApi.scripting.executeScript({
      target: {tabId: tab.id},
      files: ["form-tools.js", "content.js"],
    });
    const inventory = await extensionApi.tabs.sendMessage(tab.id, {
      type: "JOB_FINDER_SCAN",
    });
    renderInventory(inventory);
  } catch (error) {
    setStatus(
      `No se pudo analizar esta página: ${error.message}. Comprueba el permiso del sitio.`,
      true,
    );
  } finally {
    scanButton.disabled = false;
  }
});
