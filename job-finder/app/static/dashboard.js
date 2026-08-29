const csrfToken = document.querySelector("#csrf-token")?.value ?? "";
const pageMessage = document.querySelector("#page-message");

function showMessage(message, isError = false) {
  pageMessage.textContent = message;
  pageMessage.classList.toggle("status-error", isError);
}

async function apiRequest(url, options = {}) {
  const headers = new Headers(options.headers ?? {});
  if (options.method && options.method !== "GET") {
    headers.set("X-CSRF-Token", csrfToken);
  }
  const response = await fetch(url, {...options, headers});
  if (!response.ok) {
    let detail = `Error HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // Keep the HTTP status when the response is not JSON.
    }
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

function nullableFormValue(formData, key) {
  const value = formData.get(key)?.toString().trim() ?? "";
  return value || null;
}

function commaSeparatedValues(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

async function loadProfile() {
  const profile = await apiRequest("/api/v1/profile");
  for (const [key, value] of Object.entries(profile)) {
    const field = document.querySelector(`[name="${key}"]`);
    if (field) {
      field.value = value ?? "";
    }
  }
}

document.querySelector("#profile-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);
  const payload = {
    full_name: formData.get("full_name")?.toString().trim(),
    phone: nullableFormValue(formData, "phone"),
    location: nullableFormValue(formData, "location"),
    linkedin_url: nullableFormValue(formData, "linkedin_url"),
    portfolio_url: nullableFormValue(formData, "portfolio_url"),
    summary: nullableFormValue(formData, "summary"),
  };

  try {
    await apiRequest("/api/v1/profile", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    showMessage("Perfil guardado.");
  } catch (error) {
    showMessage(`No se pudo guardar el perfil: ${error.message}`, true);
  }
});

loadProfile().catch((error) => {
  showMessage(`No se pudo cargar el perfil: ${error.message}`, true);
});

const searchProfileForm = document.querySelector("#search-profile-form");
const searchProfileList = document.querySelector("#search-profile-list");
const searchProfileEmpty = document.querySelector("#search-profile-empty");
const cancelSearchProfile = document.querySelector("#cancel-search-profile");
const resumeSearchProfile = document.querySelector("#resume-search-profile");

function resetSearchProfileForm() {
  searchProfileForm.reset();
  searchProfileForm.elements.is_active.checked = true;
  searchProfileForm.elements.salary_currency.value = "EUR";
  document.querySelector("#search-profile-id").value = "";
  cancelSearchProfile.hidden = true;
}

function searchProfilePayload(formData) {
  return {
    name: formData.get("name")?.toString().trim(),
    is_default: formData.get("is_default") === "on",
    is_active: formData.get("is_active") === "on",
  };
}

function preferencesPayload(formData) {
  const salaryMin = nullableFormValue(formData, "salary_min");
  return {
    desired_roles: commaSeparatedValues(formData.get("desired_roles")?.toString() ?? ""),
    locations: commaSeparatedValues(formData.get("locations")?.toString() ?? ""),
    seniority_level: nullableFormValue(formData, "seniority_level"),
    work_mode: nullableFormValue(formData, "work_mode"),
    employment_type: nullableFormValue(formData, "employment_type"),
    salary_min: salaryMin === null ? null : Number(salaryMin),
    salary_currency: nullableFormValue(formData, "salary_currency"),
  };
}

function fillSearchProfileForm(profile) {
  const preferences = profile.preferences ?? {};
  document.querySelector("#search-profile-id").value = profile.id;
  searchProfileForm.elements.name.value = profile.name;
  searchProfileForm.elements.is_default.checked = profile.is_default;
  searchProfileForm.elements.is_active.checked = profile.is_active;
  searchProfileForm.elements.desired_roles.value = (preferences.desired_roles ?? []).join(", ");
  searchProfileForm.elements.locations.value = (preferences.locations ?? []).join(", ");
  searchProfileForm.elements.seniority_level.value = preferences.seniority_level ?? "";
  searchProfileForm.elements.work_mode.value = preferences.work_mode ?? "";
  searchProfileForm.elements.employment_type.value = preferences.employment_type ?? "";
  searchProfileForm.elements.salary_min.value = preferences.salary_min ?? "";
  searchProfileForm.elements.salary_currency.value = preferences.salary_currency ?? "EUR";
  cancelSearchProfile.hidden = false;
  searchProfileForm.scrollIntoView({behavior: "smooth", block: "start"});
}

function renderSearchProfile(profile) {
  const preferences = profile.preferences ?? {};
  const card = document.createElement("article");
  card.className = "resource-card";

  const titleRow = document.createElement("div");
  titleRow.className = "resource-title";
  const title = document.createElement("h3");
  title.textContent = profile.name;
  titleRow.append(title);
  if (profile.is_default) {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = "Predeterminado";
    titleRow.append(badge);
  }

  const details = document.createElement("p");
  details.className = "resource-details";
  const roles = preferences.desired_roles?.join(", ") || "Sin puestos";
  const locations = preferences.locations?.join(", ") || "Sin ubicaciones";
  details.textContent = `${roles} · ${locations}`;

  const actions = document.createElement("div");
  actions.className = "resource-actions";

  const editButton = document.createElement("button");
  editButton.type = "button";
  editButton.className = "button-secondary";
  editButton.textContent = "Editar";
  editButton.addEventListener("click", () => fillSearchProfileForm(profile));
  actions.append(editButton);

  if (!profile.is_default) {
    const defaultButton = document.createElement("button");
    defaultButton.type = "button";
    defaultButton.className = "button-secondary";
    defaultButton.textContent = "Predeterminado";
    defaultButton.addEventListener("click", async () => {
      try {
        await apiRequest(`/api/v1/search-profiles/${profile.id}`, {
          method: "PUT",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            name: profile.name,
            is_default: true,
            is_active: profile.is_active,
          }),
        });
        await loadSearchProfiles();
        showMessage("Perfil predeterminado actualizado.");
      } catch (error) {
        showMessage(`No se pudo actualizar el perfil: ${error.message}`, true);
      }
    });
    actions.append(defaultButton);
  }

  const deleteButton = document.createElement("button");
  deleteButton.type = "button";
  deleteButton.className = "button-danger";
  deleteButton.textContent = "Eliminar";
  deleteButton.addEventListener("click", async () => {
    if (!window.confirm(`¿Eliminar el perfil “${profile.name}”?`)) {
      return;
    }
    try {
      await apiRequest(`/api/v1/search-profiles/${profile.id}`, {method: "DELETE"});
      await loadSearchProfiles();
      showMessage("Perfil de búsqueda eliminado.");
    } catch (error) {
      showMessage(`No se pudo eliminar el perfil: ${error.message}`, true);
    }
  });
  actions.append(deleteButton);

  card.append(titleRow, details, actions);
  return card;
}

async function loadSearchProfiles() {
  const summaries = await apiRequest("/api/v1/search-profiles");
  const profiles = await Promise.all(
    summaries.map((profile) => apiRequest(`/api/v1/search-profiles/${profile.id}`)),
  );
  searchProfileList.replaceChildren(...profiles.map(renderSearchProfile));
  searchProfileEmpty.hidden = profiles.length > 0;
  const currentResumeProfile = resumeSearchProfile.value;
  const options = profiles.map((profile) => {
    const option = document.createElement("option");
    option.value = profile.id;
    option.textContent = profile.name;
    return option;
  });
  resumeSearchProfile.replaceChildren(new Option("Sin asociar", ""), ...options);
  resumeSearchProfile.value = currentResumeProfile;
}

searchProfileForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const editingId = document.querySelector("#search-profile-id").value;
  const url = editingId
    ? `/api/v1/search-profiles/${editingId}`
    : "/api/v1/search-profiles";

  try {
    const profile = await apiRequest(url, {
      method: editingId ? "PUT" : "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(searchProfilePayload(formData)),
    });
    await apiRequest(`/api/v1/search-profiles/${profile.id}/preferences`, {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(preferencesPayload(formData)),
    });
    resetSearchProfileForm();
    await loadSearchProfiles();
    showMessage(editingId ? "Perfil de búsqueda actualizado." : "Perfil de búsqueda creado.");
  } catch (error) {
    showMessage(`No se pudo guardar el perfil de búsqueda: ${error.message}`, true);
  }
});

cancelSearchProfile?.addEventListener("click", resetSearchProfileForm);

loadSearchProfiles().catch((error) => {
  showMessage(`No se pudieron cargar los perfiles de búsqueda: ${error.message}`, true);
});

const resumeForm = document.querySelector("#resume-form");
const resumeList = document.querySelector("#resume-list");
const resumeEmpty = document.querySelector("#resume-empty");

function formatFileSize(sizeBytes) {
  return `${(sizeBytes / 1024).toFixed(1)} KiB`;
}

function renderResume(resume) {
  const card = document.createElement("article");
  card.className = "resource-card";

  const titleRow = document.createElement("div");
  titleRow.className = "resource-title";
  const title = document.createElement("h3");
  title.textContent = resume.original_filename;
  titleRow.append(title);
  if (resume.is_default) {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = "Predeterminado";
    titleRow.append(badge);
  }

  const details = document.createElement("p");
  details.className = "resource-details";
  details.textContent = formatFileSize(resume.size_bytes);

  const actions = document.createElement("div");
  actions.className = "resource-actions";

  const download = document.createElement("a");
  download.className = "button-link";
  download.href = `/api/v1/resumes/${resume.id}/file`;
  download.textContent = "Descargar";
  actions.append(download);

  if (!resume.is_default) {
    const defaultButton = document.createElement("button");
    defaultButton.type = "button";
    defaultButton.className = "button-secondary";
    defaultButton.textContent = "Predeterminado";
    defaultButton.addEventListener("click", async () => {
      try {
        await apiRequest(`/api/v1/resumes/${resume.id}/default`, {method: "POST"});
        await loadResumes();
        showMessage("Currículum predeterminado actualizado.");
      } catch (error) {
        showMessage(`No se pudo actualizar el currículum: ${error.message}`, true);
      }
    });
    actions.append(defaultButton);
  }

  const deleteButton = document.createElement("button");
  deleteButton.type = "button";
  deleteButton.className = "button-danger";
  deleteButton.textContent = "Eliminar";
  deleteButton.addEventListener("click", async () => {
    if (!window.confirm(`¿Eliminar el currículum “${resume.original_filename}”?`)) {
      return;
    }
    try {
      await apiRequest(`/api/v1/resumes/${resume.id}`, {method: "DELETE"});
      await loadResumes();
      showMessage("Currículum eliminado.");
    } catch (error) {
      showMessage(`No se pudo eliminar el currículum: ${error.message}`, true);
    }
  });
  actions.append(deleteButton);

  card.append(titleRow, details, actions);
  return card;
}

async function loadResumes() {
  const resumes = await apiRequest("/api/v1/resumes");
  resumeList.replaceChildren(...resumes.map(renderResume));
  resumeEmpty.hidden = resumes.length > 0;
}

resumeForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0) {
    showMessage("Selecciona un archivo PDF.", true);
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    showMessage("El currículum supera el límite de 5 MiB.", true);
    return;
  }
  formData.set("csrf_token", csrfToken);

  try {
    await apiRequest("/api/v1/resumes", {method: "POST", body: formData});
    resumeForm.reset();
    await loadResumes();
    showMessage("Currículum subido.");
  } catch (error) {
    showMessage(`No se pudo subir el currículum: ${error.message}`, true);
  }
});

loadResumes().catch((error) => {
  showMessage(`No se pudieron cargar los currículums: ${error.message}`, true);
});

const answerForm = document.querySelector("#answer-form");
const answerList = document.querySelector("#answer-list");
const answerEmpty = document.querySelector("#answer-empty");
const cancelAnswer = document.querySelector("#cancel-answer");

function resetAnswerForm() {
  answerForm.reset();
  document.querySelector("#answer-id").value = "";
  cancelAnswer.hidden = true;
}

function fillAnswerForm(answer) {
  document.querySelector("#answer-id").value = answer.id;
  answerForm.elements.key.value = answer.key;
  answerForm.elements.locale.value = answer.locale;
  answerForm.elements.text.value = answer.text;
  cancelAnswer.hidden = false;
  answerForm.scrollIntoView({behavior: "smooth", block: "start"});
}

function renderAnswer(answer) {
  const card = document.createElement("article");
  card.className = "resource-card";

  const titleRow = document.createElement("div");
  titleRow.className = "resource-title";
  const title = document.createElement("h3");
  title.textContent = answer.key;
  const badge = document.createElement("span");
  badge.className = "badge badge-neutral";
  badge.textContent = answer.locale.toUpperCase();
  titleRow.append(title, badge);

  const text = document.createElement("p");
  text.className = "answer-preview";
  text.textContent = answer.text;

  const actions = document.createElement("div");
  actions.className = "resource-actions";
  const editButton = document.createElement("button");
  editButton.type = "button";
  editButton.className = "button-secondary";
  editButton.textContent = "Editar";
  editButton.addEventListener("click", () => fillAnswerForm(answer));

  const deleteButton = document.createElement("button");
  deleteButton.type = "button";
  deleteButton.className = "button-danger";
  deleteButton.textContent = "Eliminar";
  deleteButton.addEventListener("click", async () => {
    if (!window.confirm(`¿Eliminar la respuesta “${answer.key}”?`)) {
      return;
    }
    try {
      await apiRequest(`/api/v1/reusable-answers/${answer.id}`, {method: "DELETE"});
      await loadAnswers();
      showMessage("Respuesta eliminada.");
    } catch (error) {
      showMessage(`No se pudo eliminar la respuesta: ${error.message}`, true);
    }
  });

  actions.append(editButton, deleteButton);
  card.append(titleRow, text, actions);
  return card;
}

async function loadAnswers() {
  const answers = await apiRequest("/api/v1/reusable-answers");
  answerList.replaceChildren(...answers.map(renderAnswer));
  answerEmpty.hidden = answers.length > 0;
}

answerForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const editingId = document.querySelector("#answer-id").value;
  const url = editingId
    ? `/api/v1/reusable-answers/${editingId}`
    : "/api/v1/reusable-answers";
  const payload = {
    key: formData.get("key")?.toString().trim(),
    locale: formData.get("locale")?.toString(),
    text: formData.get("text")?.toString().trim(),
  };

  try {
    await apiRequest(url, {
      method: editingId ? "PUT" : "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    resetAnswerForm();
    await loadAnswers();
    showMessage(editingId ? "Respuesta actualizada." : "Respuesta guardada.");
  } catch (error) {
    showMessage(`No se pudo guardar la respuesta: ${error.message}`, true);
  }
});

cancelAnswer?.addEventListener("click", resetAnswerForm);

loadAnswers().catch((error) => {
  showMessage(`No se pudieron cargar las respuestas: ${error.message}`, true);
});
