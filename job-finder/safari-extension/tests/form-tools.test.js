const test = require("node:test");
const assert = require("node:assert/strict");

global.Event = class Event {
  constructor(type, options = {}) {
    this.type = type;
    this.bubbles = Boolean(options.bubbles);
  }
};

const {
  buildFieldDescriptor,
  fillField,
  inventoryFields,
  neverFillReason,
} = require("../extension/form-tools.js");

function fakeField(overrides = {}) {
  const attributes = overrides.attributes ?? {};
  return {
    tagName: "INPUT",
    type: "text",
    name: "",
    id: "",
    autocomplete: "",
    placeholder: "",
    required: false,
    hidden: false,
    disabled: false,
    value: "",
    labels: [],
    getAttribute(name) {
      return attributes[name] ?? null;
    },
    closest() {
      return null;
    },
    getBoundingClientRect() {
      return {width: 100, height: 20};
    },
    dispatchEvent() {},
    ...overrides,
  };
}

// Minimal fake DOM root: distinguishes the three selectors form-tools.js
// actually issues ("*" for shadow hosts, "iframe" for frames, the field
// tag list for form controls) without pulling in a real DOM implementation.
function fakeRoot(elements) {
  return {
    querySelectorAll(selector) {
      if (selector === "*") {
        return elements;
      }
      if (selector === "iframe") {
        return elements.filter((el) => el.tagName?.toLowerCase() === "iframe");
      }
      return elements.filter((el) =>
        ["input", "select", "textarea"].includes(el.tagName?.toLowerCase()),
      );
    },
  };
}

function fakeFieldset(legendText) {
  return {
    querySelector(selector) {
      return selector === "legend" ? {textContent: legendText} : null;
    },
  };
}

function fakeRadio(name, value, label, fieldsetLegendText) {
  return fakeField({
    type: "radio",
    name,
    value,
    labels: label ? [{textContent: label}] : [],
    closest(selector) {
      return selector === "fieldset" && fieldsetLegendText
        ? fakeFieldset(fieldsetLegendText)
        : null;
    },
  });
}

test("descriptor includes signals but never the current value", () => {
  const field = fakeField({
    name: "email",
    value: "persona@example.test",
    labels: [{textContent: "Correo electrónico"}],
  });

  const descriptor = buildFieldDescriptor(field, 0);

  assert.equal(descriptor.signals.label, "Correo electrónico");
  assert.equal(descriptor.signals.name, "email");
  assert.equal("value" in descriptor, false);
  assert.equal(JSON.stringify(descriptor).includes("persona@example.test"), false);
});

test("inventory excludes hidden and password inputs", () => {
  const visible = fakeField({name: "full_name"});
  const hidden = fakeField({name: "internal", hidden: true});
  const password = fakeField({name: "password", type: "password"});

  const inventory = inventoryFields(fakeRoot([visible, hidden, password]));

  assert.equal(inventory.fields.length, 1);
  assert.equal(inventory.fields[0].signals.name, "full_name");
  assert.equal(inventory.blocked_frames, 0);
});

test("legal checkboxes and file inputs require manual review", () => {
  const consent = fakeField({name: "accept_terms", type: "checkbox"});
  const file = fakeField({name: "resume", type: "file"});

  assert.equal(neverFillReason(consent), "sensitive_or_legal");
  assert.equal(neverFillReason(file), "manual_file_review");
});

test("fill dispatches expected events and verifies the accepted value", () => {
  const events = [];
  const field = fakeField({
    name: "city",
    dispatchEvent(event) {
      events.push(event.type);
    },
  });

  const result = fillField(field, "Madrid");

  assert.deepEqual(result, {ok: true, reason: null});
  assert.equal(field.value, "Madrid");
  assert.deepEqual(events, ["input", "change", "blur"]);
});

test("fill refuses sensitive fields", () => {
  const field = fakeField({name: "csrf_token"});

  assert.deepEqual(fillField(field, "secret"), {
    ok: false,
    reason: "sensitive_or_legal",
  });
  assert.equal(field.value, "");
});

test("select fill accepts either option value or label", () => {
  const events = [];
  const field = fakeField({
    tagName: "SELECT",
    type: "select-one",
    options: [
      {value: "remote", textContent: "Remoto"},
      {value: "hybrid", textContent: "Híbrido"},
    ],
    dispatchEvent(event) {
      events.push(event.type);
    },
  });

  const result = fillField(field, "Remoto");

  assert.equal(result.ok, true);
  assert.equal(field.value, "remote");
  assert.deepEqual(events, ["input", "change", "blur"]);
});

test("radio buttons sharing a name are grouped into one reviewable descriptor", () => {
  const remote = fakeRadio("work_mode", "remote", "Remoto", "Modalidad");
  const hybrid = fakeRadio("work_mode", "hybrid", "Híbrido", "Modalidad");

  const inventory = inventoryFields(fakeRoot([remote, hybrid]));

  assert.equal(inventory.fields.length, 1);
  const [group] = inventory.fields;
  assert.equal(group.type, "radio-group");
  assert.equal(group.signals.name, "work_mode");
  assert.equal(group.signals.label, "Modalidad");
  assert.equal(group.allowed_action, "review");
  assert.equal(group.review_reason, "manual_choice_review");
  assert.deepEqual(group.options, [
    {value: "remote", label: "Remoto"},
    {value: "hybrid", label: "Híbrido"},
  ]);
});

test("fieldset legend is used as a label fallback", () => {
  const field = fakeField({
    name: "note",
    closest(selector) {
      return selector === "fieldset" ? fakeFieldset("Notas adicionales") : null;
    },
  });

  const descriptor = buildFieldDescriptor(field, 0);

  assert.equal(descriptor.signals.label, "Notas adicionales");
});

test("multi-select options are flagged for manual review", () => {
  const field = fakeField({
    tagName: "SELECT",
    type: "select-multiple",
    multiple: true,
    options: [
      {value: "js", textContent: "JavaScript"},
      {value: "py", textContent: "Python"},
    ],
  });

  const descriptor = buildFieldDescriptor(field, 0);

  assert.equal(descriptor.multiple, true);
  assert.equal(descriptor.allowed_action, "review");
  assert.equal(descriptor.review_reason, "multi_select_review");
});

test("inputs inside an open shadow root are inventoried", () => {
  const shadowField = fakeField({name: "shadow_input"});
  const host = {tagName: "DIV", shadowRoot: fakeRoot([shadowField])};
  const root = fakeRoot([host]);

  const inventory = inventoryFields(root);

  assert.equal(inventory.fields.length, 1);
  assert.equal(inventory.fields[0].signals.name, "shadow_input");
});

test("same-origin iframes are scanned and cross-origin iframes are counted as blocked", () => {
  const frameField = fakeField({name: "frame_input"});
  const sameOriginFrame = {
    tagName: "IFRAME",
    contentDocument: fakeRoot([frameField]),
  };
  const crossOriginFrame = {
    tagName: "IFRAME",
    get contentDocument() {
      throw new Error("blocked by same-origin policy");
    },
  };
  const root = fakeRoot([sameOriginFrame, crossOriginFrame]);

  const inventory = inventoryFields(root);

  assert.equal(inventory.fields.length, 1);
  assert.equal(inventory.fields[0].signals.name, "frame_input");
  assert.equal(inventory.blocked_frames, 1);
});
