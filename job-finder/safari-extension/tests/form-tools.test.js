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
  fillByLocalId,
  fillField,
  highlightPending,
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
    parentElement: null,
    closest(selector) {
      const matches = (node) => {
        const tag = node.tagName?.toLowerCase?.() || "";
        if (selector === "fieldset") {
          return tag === "fieldset";
        }
        if (selector === "label") {
          return tag === "label";
        }
        return tag === selector;
      };
      let node = this.parentElement;
      while (node) {
        if (matches(node)) {
          return node;
        }
        node = node.parentElement;
      }
      return null;
    },
    getBoundingClientRect() {
      return {width: 100, height: 20};
    },
    dispatchEvent() {},
    style: {},
    attributes: {...attributes},
    setAttribute(name, value) {
      this.attributes[name] = String(value);
    },
    getAttribute(name) {
      return this.attributes[name] ?? attributes[name] ?? null;
    },
    removeAttribute(name) {
      delete this.attributes[name];
    },
    scrollIntoView() {
      this.scrolledIntoView = true;
    },
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

test("fillByLocalId uses the last inventory handles and still refuses never-fill fields", () => {
  const name = fakeField({name: "full_name", autocomplete: "name"});
  const csrf = fakeField({name: "csrf_token", type: "hidden"});
  inventoryFields(fakeRoot([name, csrf]));

  assert.deepEqual(fillByLocalId("field-0", "Ana"), {ok: true, reason: null});
  assert.equal(name.value, "Ana");
  assert.deepEqual(fillByLocalId("missing", "x"), {ok: false, reason: "unknown_field"});
});

test("fillByLocalId refuses radio groups even if asked to fill", () => {
  const remote = fakeRadio("work_mode", "remote", "Remoto", "Modalidad");
  const hybrid = fakeRadio("work_mode", "hybrid", "Híbrido", "Modalidad");
  const inventory = inventoryFields(fakeRoot([remote, hybrid]));

  const result = fillByLocalId(inventory.fields[0].local_id, "remote");
  assert.deepEqual(result, {ok: false, reason: "manual_choice_review"});
});

test("highlightPending outlines review and file fields, never legales or passwords", () => {
  const name = fakeField({name: "full_name"});
  const file = fakeField({name: "resume", type: "file"});
  const legal = fakeField({name: "accept_terms", type: "checkbox"});
  const password = fakeField({name: "password", type: "password"});
  const inventory = inventoryFields(fakeRoot([name, file, legal, password]));
  const fileId = inventory.fields.find((field) => field.signals.name === "resume").local_id;
  const legalId = inventory.fields.find((field) => field.signals.name === "accept_terms").local_id;

  const result = highlightPending([fileId, legalId, "field-missing"]);

  assert.equal(name.style.outline, undefined);
  assert.equal(file.style.outline, "2px solid #1d4ed8");
  assert.equal(file.getAttribute("data-job-finder-highlight"), "1");
  assert.equal(file.scrolledIntoView, true);
  assert.equal(legal.style.outline, undefined);
  assert.equal(legal.getAttribute("data-job-finder-highlight"), null);
  assert.equal(password.style.outline, undefined);
  assert.equal(result.highlighted, 1);
});

function linkChildren(parent, children) {
  parent.children = children;
  children.forEach((child, index) => {
    child.parentElement = parent;
    child.previousElementSibling = index > 0 ? children[index - 1] : null;
  });
  return parent;
}

function sectionNode(tag, text, children = []) {
  const node = {
    tagName: tag.toUpperCase(),
    textContent: text,
    children,
    parentElement: null,
    previousElementSibling: null,
    querySelector(selector) {
      const tags = selector.split(",").map((part) => part.trim().toLowerCase());
      const walk = (current) => {
        for (const child of current.children || []) {
          if (tags.includes(child.tagName?.toLowerCase())) {
            return child;
          }
          const found = walk(child);
          if (found) {
            return found;
          }
        }
        return null;
      };
      return walk(this);
    },
  };
  return linkChildren(node, children);
}

test("repeated labels keep their section and entry, without leaking the current value", () => {
  const filled = "Licenciatura en datos";
  const educationOne = fakeField({
    tagName: "TEXTAREA",
    name: "description",
    value: filled,
    labels: [{textContent: "Description"}],
  });
  const educationOneSchool = fakeField({
    name: "school",
    value: "Universidad",
    labels: [{textContent: "School"}],
  });
  const educationTwo = fakeField({
    tagName: "TEXTAREA",
    name: "description",
    value: "",
    placeholder: "Description",
    labels: [{textContent: "Description"}],
  });
  const educationTwoSchool = fakeField({
    name: "school",
    labels: [{textContent: "School"}],
  });
  const work = fakeField({
    tagName: "TEXTAREA",
    name: "description",
    value: "Pipelines on-prem",
    labels: [{textContent: "Description"}],
  });
  const employer = fakeField({
    name: "employer",
    value: "AMD",
    labels: [{textContent: "Employer"}],
  });
  const educationEntryOne = sectionNode("div", "", [educationOneSchool, educationOne]);
  const educationEntryTwo = sectionNode("div", "", [educationTwoSchool, educationTwo]);
  const workEntry = sectionNode("div", "", [employer, work]);
  sectionNode("div", "", [
    sectionNode("h2", "Education"),
    educationEntryOne,
    educationEntryTwo,
    sectionNode("h2", "Work Experience"),
    workEntry,
  ]);

  const first = buildFieldDescriptor(educationOne, 0);
  const second = buildFieldDescriptor(educationTwo, 1);
  const experience = buildFieldDescriptor(work, 2);

  assert.equal(first.signals.label, "Description");
  assert.equal(first.signals.section, "Education");
  assert.equal(first.signals.entry, "1");
  assert.equal(first.has_value, true);
  assert.equal(second.signals.section, "Education");
  assert.equal(second.signals.entry, "2");
  assert.equal(second.has_value, false);
  assert.equal(experience.signals.section, "Work Experience");
  assert.equal(experience.signals.entry, undefined);
  assert.equal(experience.has_value, true);
  assert.equal(JSON.stringify(first).includes(filled), false);
  assert.equal("value" in first, false);
});

test("fieldset legend stays a section when the control already has a label", () => {
  const field = fakeField({
    name: "description",
    value: "",
    labels: [{textContent: "Description"}],
    closest(selector) {
      return selector === "fieldset" ? fakeFieldset("Education") : null;
    },
  });

  const descriptor = buildFieldDescriptor(field, 0);

  assert.equal(descriptor.signals.label, "Description");
  assert.equal(descriptor.signals.section, "Education");
  assert.equal(descriptor.has_value, false);
});
