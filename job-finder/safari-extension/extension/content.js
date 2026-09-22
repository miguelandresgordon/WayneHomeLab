(function registerJobFinderContentScript() {
  if (globalThis.__jobFinderContentScriptRegistered) {
    return;
  }
  globalThis.__jobFinderContentScriptRegistered = true;

  const extensionApi = globalThis.browser ?? globalThis.chrome;
  const sessionOrigin = location.origin;
  let debounceTimer = null;

  function ensureObserver() {
    if (globalThis.__jobFinderObserver) {
      return;
    }
    const observer = new MutationObserver(() => {
      globalThis.__jobFinderDomDirty = true;
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        globalThis.JobFinderFormTools?.invalidateHandles?.();
      }, 400);
    });
    observer.observe(document.documentElement, {childList: true, subtree: true, attributes: false});
    globalThis.__jobFinderObserver = observer;
  }

  ensureObserver();

  extensionApi.runtime.onMessage.addListener((message) => {
    if (message?.type === "JOB_FINDER_SCAN") {
      ensureObserver();
      const inventory = globalThis.JobFinderFormTools.inventoryFields(document);
      globalThis.__jobFinderDomDirty = false;
      return Promise.resolve({
        schema_version: 1,
        page: {
          origin: sessionOrigin,
          path: location.pathname,
          title: document.title,
        },
        fields: inventory.fields,
        blocked_frames: inventory.blocked_frames,
        capabilities: {
          data_transfer: typeof DataTransfer !== "undefined",
          file_constructor: typeof File !== "undefined",
        },
        origin_changed: location.origin !== sessionOrigin,
        dom_dirty: Boolean(globalThis.__jobFinderDomDirty),
      });
    }
    if (message?.type === "JOB_FINDER_FILL") {
      const results = [];
      for (const item of message.fields || []) {
        const result = globalThis.JobFinderFormTools.fillByLocalId(item.local_id, item.value);
        results.push({
          local_id: item.local_id,
          ok: Boolean(result.ok),
          reason: result.reason,
        });
      }
      return Promise.resolve({results});
    }
    return undefined;
  });
})();
