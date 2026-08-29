(function exposeFormTools(globalScope) {
  const SKIPPED_INPUT_TYPES = new Set([
    "button",
    "hidden",
    "image",
    "password",
    "reset",
    "submit",
  ]);
  const NEVER_FILL_PATTERN =
    /(captcha|csrf|xsrf|authenticity|password|passwd|secret|token|consent|terms|privacy|legal|gdpr|acepto|condiciones)/i;

  function normalizedType(field) {
    if (field.tagName?.toLowerCase() === "textarea") {
      return "textarea";
    }
    if (field.tagName?.toLowerCase() === "select") {
      return "select";
    }
    return (field.type || "text").toLowerCase();
  }

  function fieldsetLegend(field) {
    const fieldset = field.closest?.("fieldset");
    const legend = fieldset?.querySelector?.("legend");
    return legend?.textContent?.trim() || "";
  }

  function labelText(field) {
    const explicit = field.labels?.[0]?.textContent?.trim();
    if (explicit) {
      return explicit;
    }
    const aria = field.getAttribute?.("aria-label")?.trim();
    if (aria) {
      return aria;
    }
    const wrapping = field.closest?.("label")?.textContent?.trim();
    if (wrapping) {
      return wrapping;
    }
    return fieldsetLegend(field);
  }

  function fieldSignals(field) {
    return {
      label: labelText(field),
      name: field.name || "",
      id: field.id || "",
      autocomplete: field.autocomplete || "",
      placeholder: field.placeholder || "",
    };
  }

  function neverFillReason(field, signals = fieldSignals(field)) {
    const type = normalizedType(field);
    if (SKIPPED_INPUT_TYPES.has(type)) {
      return `blocked_type:${type}`;
    }
    const combinedSignals = Object.values(signals).join(" ");
    if (NEVER_FILL_PATTERN.test(combinedSignals)) {
      return "sensitive_or_legal";
    }
    if (type === "file") {
      return "manual_file_review";
    }
    if (type === "checkbox" || type === "radio") {
      return "manual_choice_review";
    }
    return null;
  }

  function isVisible(field) {
    if (field.hidden || field.disabled) {
      return false;
    }
    const style = globalScope.getComputedStyle?.(field);
    if (style?.display === "none" || style?.visibility === "hidden") {
      return false;
    }
    const rect = field.getBoundingClientRect?.();
    return !rect || (rect.width > 0 && rect.height > 0);
  }

  function buildFieldDescriptor(field, index) {
    const signals = fieldSignals(field);
    const type = normalizedType(field);
    const isMultiSelect = type === "select" && Boolean(field.multiple);
    const reason = neverFillReason(field, signals) ?? (isMultiSelect ? "multi_select_review" : null);
    const descriptor = {
      local_id: `field-${index}`,
      element: field.tagName?.toLowerCase() || "input",
      type,
      signals,
      required: Boolean(field.required),
      allowed_action: reason ? "review" : "fill",
      review_reason: reason,
    };
    if (type === "select") {
      descriptor.options = Array.from(field.options || [], (option) => ({
        value: option.value,
        label: option.textContent?.trim() || "",
      }));
      if (isMultiSelect) {
        descriptor.multiple = true;
      }
    }
    return descriptor;
  }

  function radioOptionLabel(field) {
    return labelText(field) || field.value || "";
  }

  function buildRadioGroupDescriptor(fields, index) {
    const first = fields[0];
    return {
      local_id: `field-${index}`,
      element: "input",
      type: "radio-group",
      signals: {
        label: fieldsetLegend(first),
        name: first.name || "",
        id: "",
        autocomplete: "",
        placeholder: "",
      },
      required: fields.some((field) => field.required),
      allowed_action: "review",
      review_reason: "manual_choice_review",
      options: fields.map((field) => ({
        value: field.value,
        label: radioOptionLabel(field),
      })),
    };
  }

  function buildDescriptors(fields) {
    const radioGroups = new Map();
    const singles = [];
    for (const field of fields) {
      if (normalizedType(field) === "radio" && field.name) {
        const key = `radio:${field.name}`;
        if (!radioGroups.has(key)) {
          radioGroups.set(key, []);
        }
        radioGroups.get(key).push(field);
      } else {
        singles.push(field);
      }
    }
    const descriptors = [];
    let index = 0;
    for (const field of singles) {
      descriptors.push(buildFieldDescriptor(field, index));
      index += 1;
    }
    for (const group of radioGroups.values()) {
      descriptors.push(buildRadioGroupDescriptor(group, index));
      index += 1;
    }
    return descriptors.filter((field) => !field.review_reason?.startsWith("blocked_type:"));
  }

  function queryAll(root, selector) {
    return root?.querySelectorAll ? Array.from(root.querySelectorAll(selector)) : [];
  }

  function directShadowRoots(root) {
    return queryAll(root, "*")
      .filter((element) => element.shadowRoot)
      .map((element) => element.shadowRoot);
  }

  function directFrameDocuments(root, blockedCounter) {
    const docs = [];
    for (const frame of queryAll(root, "iframe")) {
      if (frame.tagName?.toLowerCase() !== "iframe") {
        continue;
      }
      let frameDocument = null;
      try {
        frameDocument = frame.contentDocument || null;
      } catch {
        frameDocument = null;
      }
      if (frameDocument) {
        docs.push(frameDocument);
      } else {
        blockedCounter.count += 1;
      }
    }
    return docs;
  }

  // Same-origin iframes and open shadow roots are traversed so the inventory
  // covers embedded ATS widgets; cross-origin frames and closed shadow roots
  // cannot be inspected and are only counted (never guessed at).
  function collectScanRoots(root) {
    const blockedCounter = {count: 0};
    const roots = [root];
    const queue = [root];
    while (queue.length > 0) {
      const current = queue.shift();
      for (const shadowRoot of directShadowRoots(current)) {
        roots.push(shadowRoot);
        queue.push(shadowRoot);
      }
      for (const frameDocument of directFrameDocuments(current, blockedCounter)) {
        roots.push(frameDocument);
        queue.push(frameDocument);
      }
    }
    return {roots, blockedFrames: blockedCounter.count};
  }

  function inventoryFields(root = globalScope.document) {
    const {roots, blockedFrames} = collectScanRoots(root);
    const rawFields = roots.flatMap((scanRoot) => queryAll(scanRoot, "input, select, textarea"));
    const visibleFields = rawFields.filter(isVisible);
    return {
      fields: buildDescriptors(visibleFields),
      blocked_frames: blockedFrames,
    };
  }

  function dispatchFieldEvents(field) {
    for (const name of ["input", "change", "blur"]) {
      field.dispatchEvent(new Event(name, {bubbles: true}));
    }
  }

  function fillField(field, value) {
    const reason = neverFillReason(field);
    if (reason) {
      return {ok: false, reason};
    }
    let expectedValue = String(value);
    if (normalizedType(field) === "select") {
      const matchingOption = Array.from(field.options || []).find(
        (option) => option.value === value || option.textContent?.trim() === value,
      );
      if (!matchingOption) {
        return {ok: false, reason: "option_not_found"};
      }
      field.value = matchingOption.value;
      expectedValue = matchingOption.value;
    } else {
      field.value = value;
    }
    dispatchFieldEvents(field);
    return {ok: field.value === expectedValue, reason: null};
  }

  const api = {
    buildFieldDescriptor,
    buildRadioGroupDescriptor,
    fieldSignals,
    fillField,
    inventoryFields,
    neverFillReason,
    normalizedType,
  };

  globalScope.JobFinderFormTools = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof globalThis === "undefined" ? this : globalThis);
