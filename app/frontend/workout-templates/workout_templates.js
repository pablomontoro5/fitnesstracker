const state = {
  templates: [],
  selectedTemplate: null,
  exercises: [],
  selectedExercise: null,
  sets: [],
};


const elements = {
  statusMessage: document.querySelector("#status-message"),

  refreshTemplatesButton: document.querySelector(
    "#refresh-templates-button",
  ),
  templatesList: document.querySelector("#templates-list"),
  templateCount: document.querySelector("#template-count"),
  templateCardTemplate: document.querySelector(
    "#template-card-template",
  ),

  selectedTemplateTitle: document.querySelector(
    "#selected-template-title",
  ),
  deleteTemplateButton: document.querySelector(
    "#delete-template-button",
  ),
  templateEmptyState: document.querySelector("#template-empty-state"),
  templateDetailContent: document.querySelector(
    "#template-detail-content",
  ),
  templateExerciseForm: document.querySelector(
    "#template-exercise-form",
  ),
  templateExercisesList: document.querySelector(
    "#template-exercises-list",
  ),
  templateExerciseCount: document.querySelector(
    "#template-exercise-count",
  ),
  templateExerciseTemplate: document.querySelector(
    "#template-exercise-template",
  ),

  selectedTemplateExerciseTitle: document.querySelector(
    "#selected-template-exercise-title",
  ),
  deleteTemplateExerciseButton: document.querySelector(
    "#delete-template-exercise-button",
  ),
  templateExerciseEmptyState: document.querySelector(
    "#template-exercise-empty-state",
  ),
  templateExerciseDetailContent: document.querySelector(
    "#template-exercise-detail-content",
  ),
  templateSetForm: document.querySelector("#template-set-form"),
  templateSetsList: document.querySelector("#template-sets-list"),
  templateSetCount: document.querySelector("#template-set-count"),
};


function emptyToNull(value) {
  const trimmedValue = value.trim();
  return trimmedValue === "" ? null : trimmedValue;
}


function formatNumber(value) {
  return new Intl.NumberFormat("es-ES", {
    maximumFractionDigits: 2,
  }).format(value);
}


function setTypeLabel(setType) {
  const labels = {
    warmup: "Calentamiento",
    approximation: "Aproximación",
    working: "Trabajo",
    drop_set: "Drop set",
  };

  return labels[setType] || setType;
}


function escapeHtml(value) {
  const element = document.createElement("div");
  element.textContent = value;
  return element.innerHTML;
}


function showStatus(message, type = "success") {
  elements.statusMessage.textContent = message;
  elements.statusMessage.className = `status-message ${type}`;

  window.clearTimeout(showStatus.timeoutId);
  showStatus.timeoutId = window.setTimeout(() => {
    elements.statusMessage.textContent = "";
    elements.statusMessage.className = "status-message";
  }, 5000);
}


async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (response.status === 204) {
    return null;
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((error) => error.msg).join(". ")
      : body?.detail;

    throw new Error(detail || "No se pudo completar la operación.");
  }

  return body;
}


function setListEmpty(container, message) {
  container.className = "empty-state";
  container.textContent = message;
}


function resetSelectedExercise() {
  state.selectedExercise = null;
  state.sets = [];

  elements.selectedTemplateExerciseTitle.textContent =
    "Selecciona un ejercicio";
  elements.templateExerciseEmptyState.classList.remove("hidden");
  elements.templateExerciseDetailContent.classList.add("hidden");
  elements.deleteTemplateExerciseButton.classList.add("hidden");
  elements.templateSetCount.textContent = "0";

  setListEmpty(
    elements.templateSetsList,
    "No hay series en este ejercicio.",
  );
}


function resetSelectedTemplate() {
  state.selectedTemplate = null;
  state.exercises = [];

  elements.selectedTemplateTitle.textContent =
    "Selecciona una plantilla";
  elements.templateEmptyState.classList.remove("hidden");
  elements.templateDetailContent.classList.add("hidden");
  elements.deleteTemplateButton.classList.add("hidden");
  elements.templateExerciseCount.textContent = "0";

  setListEmpty(
    elements.templateExercisesList,
    "No hay ejercicios en esta plantilla.",
  );

  resetSelectedExercise();
}


function renderTemplates() {
  elements.templateCount.textContent = String(state.templates.length);
  elements.templatesList.innerHTML = "";

  if (state.templates.length === 0) {
    setListEmpty(
      elements.templatesList,
      "Todavía no hay plantillas guardadas.",
    );
    return;
  }

  elements.templatesList.className = "templates-list";

  for (const workoutTemplate of state.templates) {
    const fragment = elements.templateCardTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".template-card");
    const button = fragment.querySelector(".template-select-button");

    fragment.querySelector(".template-name").textContent =
      workoutTemplate.name;
    fragment.querySelector(".template-notes").textContent =
      workoutTemplate.notes || "Sin notas";

    if (state.selectedTemplate?.id === workoutTemplate.id) {
      card.classList.add("selected");
    }

    button.addEventListener("click", () => {
      selectTemplate(workoutTemplate);
    });

    elements.templatesList.append(fragment);
  }
}


function renderExercises() {
  elements.templateExerciseCount.textContent = String(
    state.exercises.length,
  );
  elements.templateExercisesList.innerHTML = "";

  if (state.exercises.length === 0) {
    setListEmpty(
      elements.templateExercisesList,
      "No hay ejercicios en esta plantilla.",
    );
    return;
  }

  elements.templateExercisesList.className = "exercise-list";

  for (const exercise of state.exercises) {
    const fragment = elements.templateExerciseTemplate.content.cloneNode(
      true,
    );
    const card = fragment.querySelector(".exercise-card");
    const button = fragment.querySelector(".exercise-select-button");

    fragment.querySelector(".exercise-position").textContent =
      exercise.position;
    fragment.querySelector(".exercise-name").textContent = exercise.name;
    fragment.querySelector(".exercise-muscle-group").textContent =
      exercise.muscle_group;
    fragment.querySelector(".exercise-technique-notes").textContent =
      exercise.technique_notes || "Sin notas técnicas";

    if (state.selectedExercise?.id === exercise.id) {
      card.classList.add("selected");
    }

    button.addEventListener("click", () => {
      selectExercise(exercise);
    });

    elements.templateExercisesList.append(fragment);
  }
}


function renderSets() {
  elements.templateSetCount.textContent = String(state.sets.length);
  elements.templateSetsList.innerHTML = "";

  if (state.sets.length === 0) {
    setListEmpty(
      elements.templateSetsList,
      "No hay series en este ejercicio.",
    );
    return;
  }

  elements.templateSetsList.className = "sets-list";

  for (const set of state.sets) {
    const card = document.createElement("article");
    card.className = "set-card";

    const rirText = set.rir === null
      ? "RIR no registrado"
      : `RIR ${formatNumber(set.rir)}`;
    const targetText = set.target_rep_range
      ? ` · Objetivo ${set.target_rep_range}`
      : "";

    card.innerHTML = `
      <span class="set-type-badge ${set.set_type}">
        ${setTypeLabel(set.set_type)}
      </span>
      <div class="set-main">
        <strong>
          Serie ${set.position}: ${set.repetitions} reps ×
          ${formatNumber(set.weight_kg)} kg
        </strong>
        <span class="set-meta">
          ${rirText}${targetText}${set.notes ? ` · ${escapeHtml(set.notes)}` : ""}
        </span>
      </div>
      <span class="set-volume">${formatNumber(set.volume_kg)} kg</span>
    `;

    elements.templateSetsList.append(card);
  }
}


async function loadTemplates() {
  try {
    state.templates = await request("/workout-templates/");
    renderTemplates();
  } catch (error) {
    showStatus(error.message, "error");
    setListEmpty(
      elements.templatesList,
      "No se pudieron cargar las plantillas.",
    );
  }
}


async function loadExercises(templateId) {
  state.exercises = await request(
    `/workout-templates/${templateId}/exercises/`,
  );
  renderExercises();
}


async function loadSets(exerciseId) {
  state.sets = await request(
    `/workout-templates/exercises/${exerciseId}/sets/`,
  );
  renderSets();
}


async function selectTemplate(workoutTemplate) {
  state.selectedTemplate = workoutTemplate;

  elements.selectedTemplateTitle.textContent = workoutTemplate.name;
  elements.templateEmptyState.classList.add("hidden");
  elements.templateDetailContent.classList.remove("hidden");
  elements.deleteTemplateButton.classList.remove("hidden");

  elements.templateExerciseForm.reset();
  elements.templateExerciseForm.elements.position.value = "1";

  resetSelectedExercise();
  renderTemplates();

  try {
    await loadExercises(workoutTemplate.id);
  } catch (error) {
    showStatus(error.message, "error");
  }
}


async function selectExercise(exercise) {
  state.selectedExercise = exercise;

  elements.selectedTemplateExerciseTitle.textContent = exercise.name;
  elements.templateExerciseEmptyState.classList.add("hidden");
  elements.templateExerciseDetailContent.classList.remove("hidden");
  elements.deleteTemplateExerciseButton.classList.remove("hidden");

  elements.templateSetForm.reset();
  elements.templateSetForm.elements.set_type.value = "working";
  elements.templateSetForm.elements.position.value = "1";

  renderExercises();

  try {
    await loadSets(exercise.id);
  } catch (error) {
    showStatus(error.message, "error");
  }
}


async function handleCreateTemplateExercise(event) {
  event.preventDefault();

  if (!state.selectedTemplate) {
    return;
  }

  const formData = new FormData(elements.templateExerciseForm);

  try {
    const exercise = await request(
      `/workout-templates/${state.selectedTemplate.id}/exercises/`,
      {
        method: "POST",
        body: JSON.stringify({
          name: formData.get("name").trim(),
          muscle_group: formData.get("muscle_group").trim(),
          position: Number(formData.get("position")),
          technique_notes: emptyToNull(
            formData.get("technique_notes"),
          ),
        }),
      },
    );

    elements.templateExerciseForm.reset();
    elements.templateExerciseForm.elements.position.value = String(
      exercise.position + 1,
    );

    showStatus(`Ejercicio “${exercise.name}” añadido a la plantilla.`);
    await loadExercises(state.selectedTemplate.id);
    await selectExercise(exercise);
  } catch (error) {
    showStatus(error.message, "error");
  }
}


async function handleCreateTemplateSet(event) {
  event.preventDefault();

  if (!state.selectedExercise) {
    return;
  }

  const formData = new FormData(elements.templateSetForm);
  const repetitions = Number(formData.get("repetitions"));
  const weightKg = Number(formData.get("weight_kg"));
  const rirValue = formData.get("rir").trim();

  if (!Number.isInteger(repetitions) || repetitions < 1) {
    showStatus("Indica un número válido de repeticiones.", "error");
    return;
  }

  if (!Number.isFinite(weightKg) || weightKg < 0) {
    showStatus("Indica una carga válida.", "error");
    return;
  }

  if (
    rirValue !== ""
    && (!Number.isFinite(Number(rirValue))
      || Number(rirValue) < -3
      || Number(rirValue) > 10)
  ) {
    showStatus("El RIR debe estar entre -3 y 10.", "error");
    return;
  }

  try {
    const workoutTemplateSet = await request(
      `/workout-templates/exercises/${state.selectedExercise.id}/sets/`,
      {
        method: "POST",
        body: JSON.stringify({
          set_type: formData.get("set_type"),
          position: Number(formData.get("position")),
          target_rep_range: emptyToNull(
            formData.get("target_rep_range"),
          ),
          repetitions,
          weight_kg: weightKg,
          rir: rirValue === "" ? null : Number(rirValue),
          notes: emptyToNull(formData.get("notes")),
        }),
      },
    );

    elements.templateSetForm.reset();
    elements.templateSetForm.elements.set_type.value = "working";
    elements.templateSetForm.elements.position.value = String(
      workoutTemplateSet.position + 1,
    );

    showStatus("Serie añadida a la plantilla.");
    await loadSets(state.selectedExercise.id);
  } catch (error) {
    showStatus(error.message, "error");
  }
}


async function handleDeleteTemplate() {
  if (!state.selectedTemplate) {
    return;
  }

  const confirmed = window.confirm(
    `¿Eliminar la plantilla “${state.selectedTemplate.name}” y todo su contenido?`,
  );

  if (!confirmed) {
    return;
  }

  try {
    await request(
      `/workout-templates/${state.selectedTemplate.id}`,
      {
        method: "DELETE",
      },
    );

    showStatus("Plantilla eliminada.");
    resetSelectedTemplate();
    await loadTemplates();
  } catch (error) {
    showStatus(error.message, "error");
  }
}


async function handleDeleteTemplateExercise() {
  if (!state.selectedExercise || !state.selectedTemplate) {
    return;
  }

  const confirmed = window.confirm(
    `¿Eliminar el ejercicio “${state.selectedExercise.name}” y sus series?`,
  );

  if (!confirmed) {
    return;
  }

  try {
    await request(
      `/workout-templates/exercises/${state.selectedExercise.id}`,
      {
        method: "DELETE",
      },
    );

    showStatus("Ejercicio de plantilla eliminado.");
    resetSelectedExercise();
    await loadExercises(state.selectedTemplate.id);
  } catch (error) {
    showStatus(error.message, "error");
  }
}


function configureEventListeners() {
  elements.refreshTemplatesButton.addEventListener(
    "click",
    loadTemplates,
  );
  elements.templateExerciseForm.addEventListener(
    "submit",
    handleCreateTemplateExercise,
  );
  elements.templateSetForm.addEventListener(
    "submit",
    handleCreateTemplateSet,
  );
  elements.deleteTemplateButton.addEventListener(
    "click",
    handleDeleteTemplate,
  );
  elements.deleteTemplateExerciseButton.addEventListener(
    "click",
    handleDeleteTemplateExercise,
  );
}


async function initializeApp() {
  configureEventListeners();
  await loadTemplates();
}


initializeApp();