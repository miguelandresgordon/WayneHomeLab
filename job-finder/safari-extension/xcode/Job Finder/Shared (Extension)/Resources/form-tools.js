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

  const SECTION_TEXT_MAX = 80;

  function clipSection(text) {
    const trimmed = String(text || "").replace(/\s+/g, " ").trim();
    if (trimmed.length <= SECTION_TEXT_MAX) {
      return trimmed;
    }
    return trimmed.slice(0, SECTION_TEXT_MAX).trim();
  }

  function fieldsetLegend(field) {
    const fieldset = field.closest?.("fieldset");
    const legend = fieldset?.querySelector?.("legend");
    return legend?.textContent?.trim() || "";
  }

  function ownLabel(field) {
    const explicit = field.labels?.[0]?.textContent?.trim();
    if (explicit) {
      return explicit;
    }
    const aria = field.getAttribute?.("aria-label")?.trim();
    if (aria) {
      return aria;
    }
    return field.closest?.("label")?.textContent?.trim() || "";
  }

  function labelText(field) {
    return ownLabel(field) || fieldsetLegend(field);
  }

  function labelledByText(element) {
    const ids = element.getAttribute?.("aria-labelledby");
    const lookup = element.ownerDocument?.getElementById;
    if (!ids || typeof lookup !== "function") {
      return "";
    }
    const text = ids
      .split(/\s+/)
      .filter(Boolean)
      .map((id) => lookup.call(element.ownerDocument, id)?.textContent || "")
      .join(" ");
    return clipSection(text);
  }

  function groupSectionName(element) {
    const role = String(element.getAttribute?.("role") || "").toLowerCase();
    const tag = element.tagName?.toLowerCase?.() || "";
    if (role !== "group" && role !== "region" && tag !== "section") {
      return "";
    }
    return clipSection(element.getAttribute?.("aria-label") || "") || labelledByText(element);
  }

  function headingText(element) {
    if (!element) {
      return "";
    }
    const tag = element.tagName?.toLowerCase?.() || "";
    if (/^h[1-6]$/.test(tag)) {
      return clipSection(element.textContent);
    }
    if (typeof element.querySelector !== "function") {
      return "";
    }
    const nested = element.querySelector("h1, h2, h3, h4, h5, h6");
    return nested ? clipSection(nested.textContent) : "";
  }

  function findPreviousHeadingContext(field) {
    let node = field;
    while (node?.parentElement) {
      let sibling = node.previousElementSibling;
      while (sibling) {
        const heading = headingText(sibling);
        if (heading) {
          return {section: heading, container: node.parentElement, headingElement: sibling};
        }
        sibling = sibling.previousElementSibling;
      }
      node = node.parentElement;
    }
    return {section: "", container: null, headingElement: null};
  }

  function sectionContext(field) {
    if (ownLabel(field)) {
      const legend = clipSection(fieldsetLegend(field));
      if (legend) {
        return {section: legend, container: field.closest?.("fieldset") || null, headingElement: null};
      }
    }
    let node = field.parentElement;
    while (node) {
      const named = groupSectionName(node);
      if (named) {
        return {section: named, container: node, headingElement: null};
      }
      node = node.parentElement;
    }
    return findPreviousHeadingContext(field);
  }

  function isControlElement(element) {
    const tag = element?.tagName?.toLowerCase?.() || "";
    return tag === "input" || tag === "select" || tag === "textarea";
  }

  function nestedControlCount(element) {
    if (!element) {
      return 0;
    }
    let count = isControlElement(element) ? 1 : 0;
    for (const child of element.children || []) {
      count += nestedControlCount(child);
    }
    return count;
  }

  function entryWithin(field, context) {
    const container = context.container;
    if (!container?.children) {
      return "";
    }
    let node = field;
    while (node && node.parentElement && node.parentElement !== container) {
      node = node.parentElement;
    }
    if (!node || node.parentElement !== container) {
      return "";
    }
    let candidates = Array.from(container.children);
    if (context.headingElement) {
      const start = candidates.indexOf(context.headingElement);
      if (start >= 0) {
        const rest = candidates.slice(start + 1);
        const nextHeading = rest.findIndex((child) => headingText(child));
        candidates = nextHeading < 0 ? rest : rest.slice(0, nextHeading);
      }
    }
    const groups = candidates.filter((child) => nestedControlCount(child) > 1);
    if (groups.length < 2) {
      return "";
    }
    const index = groups.indexOf(node);
    return index < 0 ? "" : String(index + 1);
  }

  function fieldSignals(field) {
    const context = sectionContext(field);
    const label = labelText(field);
    let section = context.section || "";
    if (section && section === label) {
      section = "";
    }
    const signals = {
      label,
      name: field.name || "",
      id: field.id || "",
      autocomplete: field.autocomplete || "",
      placeholder: field.placeholder || "",
      section,
    };
    if (section) {
      const entry = entryWithin(field, context);
      if (entry) {
        signals.entry = entry;
      }
    }
    return signals;
  }

  function matchingText(signals) {
    return ["label", "name", "id", "autocomplete", "placeholder"]
      .map((key) => String(signals[key] || ""))
      .join(" ");
  }

  function neverFillReason(field, signals = fieldSignals(field)) {
    const type = normalizedType(field);
    if (SKIPPED_INPUT_TYPES.has(type)) {
      return `blocked_type:${type}`;
    }
    if (NEVER_FILL_PATTERN.test(matchingText(signals))) {
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

  function controlHasValue(field) {
    const type = normalizedType(field);
    if (type === "checkbox" || type === "radio") {
      return Boolean(field.checked);
    }
    if (type === "file") {
      return (field.files?.length || 0) > 0;
    }
    if (type === "select") {
      return Array.from(field.options || []).some(
        (option) => option.selected && String(option.value ?? "").trim() !== "",
      );
    }
    const value = String(field.value || "").trim();
    if (!value) {
      return false;
    }
    const placeholder = String(field.placeholder || "").trim();
    return !placeholder || value !== placeholder;
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
      has_value: controlHasValue(field),
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
    const signals = fieldSignals(first);
    const legend = fieldsetLegend(first);
    if (legend) {
      signals.label = legend;
    }
    if (signals.section && signals.section === signals.label) {
      signals.section = "";
      delete signals.entry;
    }
    return {
      local_id: `field-${index}`,
      element: "input",
      type: "radio-group",
      signals,
      required: fields.some((field) => field.required),
      has_value: fields.some((field) => Boolean(field.checked)),
      allowed_action: "review",
      review_reason: "manual_choice_review",
      options: fields.map((field) => ({
        value: field.value,
        label: radioOptionLabel(field),
      })),
    };
  }

  function buildIndexedDescriptors(fields) {
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
    const handles = new Map();
    let index = 0;
    for (const field of singles) {
      const descriptor = buildFieldDescriptor(field, index);
      if (!descriptor.review_reason?.startsWith("blocked_type:")) {
        descriptors.push(descriptor);
        handles.set(descriptor.local_id, {kind: "single", nodes: [field]});
      }
      index += 1;
    }
    for (const group of radioGroups.values()) {
      const descriptor = buildRadioGroupDescriptor(group, index);
      descriptors.push(descriptor);
      handles.set(descriptor.local_id, {kind: "radio-group", nodes: group});
      index += 1;
    }
    return {descriptors, handles};
  }

  let lastHandles = new Map();

  function invalidateHandles() {
    lastHandles = new Map();
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
    const indexed = buildIndexedDescriptors(visibleFields);
    lastHandles = indexed.handles;
    return {
      fields: indexed.descriptors,
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

  function fillByLocalId(localId, value) {
    const handle = lastHandles.get(localId);
    if (!handle) {
      return {ok: false, reason: "unknown_field"};
    }
    if (handle.kind !== "single") {
      return {ok: false, reason: "manual_choice_review"};
    }
    return fillField(handle.nodes[0], value);
  }

  const HIGHLIGHT_ATTR = "data-job-finder-highlight";

  function shouldHighlightNode(node) {
    const reason = neverFillReason(node);
    if (!reason) {
      return true;
    }
    return reason === "manual_file_review" || reason === "manual_choice_review";
  }

  function clearHighlights() {
    for (const handle of lastHandles.values()) {
      for (const node of handle.nodes || []) {
        if (node?.getAttribute?.(HIGHLIGHT_ATTR) === "1") {
          if (node.style) {
            node.style.outline = "";
            node.style.outlineOffset = "";
          }
          node.removeAttribute?.(HIGHLIGHT_ATTR);
        }
      }
    }
  }

  function highlightPending(localIds) {
    clearHighlights();
    let highlighted = 0;
    let firstNode = null;
    for (const localId of localIds || []) {
      const handle = lastHandles.get(localId);
      if (!handle) {
        continue;
      }
      for (const node of handle.nodes || []) {
        if (!shouldHighlightNode(node)) {
          continue;
        }
        if (node.style) {
          node.style.outline = "2px solid #1d4ed8";
          node.style.outlineOffset = "2px";
        }
        node.setAttribute?.(HIGHLIGHT_ATTR, "1");
        highlighted += 1;
        if (!firstNode) {
          firstNode = node;
        }
      }
    }
    firstNode?.scrollIntoView?.({block: "center", inline: "nearest"});
    return {highlighted};
  }

  const api = {
    buildFieldDescriptor,
    buildRadioGroupDescriptor,
    clearHighlights,
    fieldSignals,
    fillByLocalId,
    fillField,
    highlightPending,
    invalidateHandles,
    inventoryFields,
    neverFillReason,
    normalizedType,
  };

  globalScope.JobFinderFormTools = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof globalThis === "undefined" ? this : globalThis);
