(function registerJobFinderContentScript() {
  if (globalThis.__jobFinderContentScriptRegistered) {
    return;
  }
  globalThis.__jobFinderContentScriptRegistered = true;

  const extensionApi = globalThis.browser ?? globalThis.chrome;

  extensionApi.runtime.onMessage.addListener((message) => {
    if (message?.type !== "JOB_FINDER_SCAN") {
      return undefined;
    }
    const inventory = globalThis.JobFinderFormTools.inventoryFields(document);
    return Promise.resolve({
      schema_version: 1,
      page: {
        origin: location.origin,
        path: location.pathname,
        title: document.title,
      },
      fields: inventory.fields,
      blocked_frames: inventory.blocked_frames,
      capabilities: {
        data_transfer: typeof DataTransfer !== "undefined",
        file_constructor: typeof File !== "undefined",
      },
    });
  });
})();
