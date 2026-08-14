const state = {
  sessions: [],
  selectedSession: null,
  exercises: [],
  selectedExercise: null,
  sets: [],
  pendingSets: [],
};

const elements = {
  statusMessage: document.querySelector("#status-message"),
  sessionForm: document.querySelector("#session-form"),
  sessionDate: document.querySelector("#session-date"),
  sessionsList: document.querySelector("#sessions-list"),
  sessionCount: document.querySelector("#session-count"),
  refreshSessionsButton: document.querySelector("#refresh-sessions-button"),
  selectedSessionTitle: document.querySelector("#selected-session-title"),
  sessionEmptyState: document.querySelector("#session-empty-state"),
  sessionDetailContent: document.querySelector("#session-detail-content"),
  deleteSessionButton: document.querySelector("#delete-session-button"),
  exerciseForm: document.querySelector("#exercise-form"),
  exercisesList: document.querySelector("#exercises-list"),
  exerciseCount: document.querySelector("#exercise-count"),
  selectedExerciseTitle: document.querySelector("#selected-exercise-title"),
  exerciseEmptyState: document.querySelector("#exercise-empty-state"),
  exerciseDetailContent: document.querySelector("#exercise-detail-content"),
  deleteExerciseButton: document.querySelector("#delete-exercise-button"),
  pendingSetsList: document.querySelector("#pending-sets-list"),
  pendingSetCount: document.querySelector("#pending-set-count"),
  addSetRowButton: document.querySelector("#add-set-row-button"),
  savePendingSetsButton: document.querySelector("#save-pending-sets-button"),
  setsList: document.querySelector("#sets-list"),
  setCount: document.querySelector("#set-count"),
  progressForm: document.querySelector("#progress-form"),
  progressExerciseName: document.querySelector("#progress-exercise-name"),
  progressResult: document.querySelector("#progress-result"),
  sessionTemplate: document.querySelector("#session-template"),
  exerciseTemplate: document.querySelector("#exercise-template"),
};

function todayAsIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

function formatDate(dateString) {
  return new Intl.DateTimeFormat("es-ES", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(`${dateString}T12:00:00`));
}

function formatNumber(value) {
  return new Intl.NumberFormat("es-ES", {
    maximumFractionDigits: 2,
  }).format(value);
}

function emptyToNull(value) {
  const trimmedValue = value.trim();
  return trimmedValue === "" ? null : trimmedValue;
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
  state.pendingSets = [];
  elements.selectedExerciseTitle.textContent = "Selecciona un ejercicio";
  elements.exerciseEmptyState.classList.remove("hidden");
  elements.exerciseDetailContent.classList.add("hidden");
  elements.deleteExerciseButton.classList.add("hidden");
  elements.setCount.textContent = "0";
  setListEmpty(elements.setsList, "No hay series en este ejercicio.");
}

function resetSelectedSession() {
  state.selectedSession = null;
  state.exercises = [];
  elements.selectedSessionTitle.textContent = "Selecciona una sesión";
  elements.sessionEmptyState.classList.remove("hidden");
  elements.sessionDetailContent.classList.add("hidden");
  elements.deleteSessionButton.classList.add("hidden");
  elements.exerciseCount.textContent = "0";
  setListEmpty(elements.exercisesList, "No hay ejercicios en esta sesión.");
  resetSelectedExercise();
}

function renderSessions() {
  elements.sessionCount.textContent = String(state.sessions.length);
  elements.sessionsList.innerHTML = "";

  if (state.sessions.length === 0) {
    setListEmpty(elements.sessionsList, "Todavía no hay sesiones registradas.");
    return;
  }

  elements.sessionsList.className = "sessions-list";

  for (const session of state.sessions) {
    const fragment = elements.sessionTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".session-card");
    const button = fragment.querySelector(".session-select-button");

    fragment.querySelector(".session-date").textContent = formatDate(session.date);
    fragment.querySelector(".session-name").textContent = session.name;
    fragment.querySelector(".session-notes").textContent = session.notes || "Sin notas";

    if (state.selectedSession?.id === session.id) {
      card.classList.add("selected");
    }

    button.addEventListener("click", () => selectSession(session));
    elements.sessionsList.append(fragment);
  }
}

function renderExercises() {
  elements.exerciseCount.textContent = String(state.exercises.length);
  elements.exercisesList.innerHTML = "";

  if (state.exercises.length === 0) {
    setListEmpty(elements.exercisesList, "No hay ejercicios en esta sesión.");
    return;
  }

  elements.exercisesList.className = "exercise-list";

  for (const exercise of state.exercises) {
    const fragment = elements.exerciseTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".exercise-card");
    const button = fragment.querySelector(".exercise-select-button");

    fragment.querySelector(".exercise-position").textContent = exercise.position;
    fragment.querySelector(".exercise-name").textContent = exercise.name;
    fragment.querySelector(".exercise-muscle-group").textContent = exercise.muscle_group;
    fragment.querySelector(".exercise-technique-notes").textContent = exercise.technique_notes || "Sin notas técnicas";

    if (state.selectedExercise?.id === exercise.id) {
      card.classList.add("selected");
    }

    button.addEventListener("click", () => selectExercise(exercise));
    elements.exercisesList.append(fragment);
  }
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

function createPendingSet() {
  return {
    set_type: "working",
    target_rep_range: "",
    repetitions: "",
    weight_kg: "",
    rir: "",
    notes: "",
  };
}


function resetPendingSets() {
  state.pendingSets = [createPendingSet()];
  renderPendingSets();
}


function renderPendingSets() {
  elements.pendingSetsList.innerHTML = "";

  state.pendingSets.forEach((pendingSet, index) => {
    const row = document.createElement("article");
    row.className = "pending-set-row";

    row.innerHTML = `
      <span class="pending-set-number">Serie ${index + 1}</span>

      <label>
        Tipo
        <select data-field="set_type">
          <option value="warmup">Calentamiento</option>
          <option value="approximation">Aproximación</option>
          <option value="working">Trabajo</option>
          <option value="drop_set">Drop set</option>
        </select>
      </label>

      <label>
        Objetivo
        <input
          data-field="target_rep_range"
          type="text"
          maxlength="30"
          placeholder="Ej.: 8-12"
        />
      </label>

      <label>
        Reps
        <input
          data-field="repetitions"
          type="number"
          min="1"
          max="1000"
          required
        />
      </label>

      <label>
        Carga kg
        <input
          data-field="weight_kg"
          type="number"
          min="0"
          max="1000"
          step="0.5"
          required
        />
      </label>

      <label>
        RIR
        <input
          data-field="rir"
          type="number"
          min="0"
          max="10"
          step="0.5"
          placeholder="—"
        />
      </label>

      <label>
        Notas
        <input
          data-field="notes"
          type="text"
          maxlength="1000"
          placeholder="Opcional"
        />
      </label>

      <button
        class="remove-set-row-button"
        type="button"
        title="Quitar esta serie"
      >
        Quitar
      </button>
    `;

    const select = row.querySelector('[data-field="set_type"]');
    select.value = pendingSet.set_type;

    row.querySelector('[data-field="target_rep_range"]').value =
      pendingSet.target_rep_range;
    row.querySelector('[data-field="repetitions"]').value =
      pendingSet.repetitions;
    row.querySelector('[data-field="weight_kg"]').value =
      pendingSet.weight_kg;
    row.querySelector('[data-field="rir"]').value = pendingSet.rir;
    row.querySelector('[data-field="notes"]').value = pendingSet.notes;

    row.querySelectorAll("[data-field]").forEach((field) => {
      field.addEventListener("input", () => {
        state.pendingSets[index][field.dataset.field] = field.value;
      });

      field.addEventListener("change", () => {
        state.pendingSets[index][field.dataset.field] = field.value;
      });
    });

    row.querySelector(".remove-set-row-button").addEventListener("click", () => {
      if (state.pendingSets.length === 1) {
        showStatus("Debe quedar al menos una serie pendiente.", "error");
        return;
      }

      state.pendingSets.splice(index, 1);
      renderPendingSets();
    });

    elements.pendingSetsList.append(row);
  });

  const pendingCount = state.pendingSets.length;
  elements.pendingSetCount.textContent = String(pendingCount);
  elements.savePendingSetsButton.textContent =
    `Guardar ${pendingCount} ${pendingCount === 1 ? "serie" : "series"}`;
}


function addPendingSetRow() {
  const lastSet = state.pendingSets.at(-1);

  state.pendingSets.push({
    ...createPendingSet(),
    set_type: lastSet?.set_type || "working",
    target_rep_range: lastSet?.target_rep_range || "",
    weight_kg: lastSet?.weight_kg || "",
  });

  renderPendingSets();
}


function buildSetPayload(pendingSet, position) {
  const repetitions = Number(pendingSet.repetitions);
  const weightKg = Number(pendingSet.weight_kg);
  const rirValue = pendingSet.rir.trim();

  if (!Number.isInteger(repetitions) || repetitions < 1 || repetitions > 1000) {
    throw new Error(`La serie ${position} necesita un número válido de repeticiones.`);
  }

  if (!Number.isFinite(weightKg) || weightKg < 0 || weightKg > 1000) {
    throw new Error(`La serie ${position} necesita una carga válida.`);
  }

  if (
    rirValue !== "" &&
    (!Number.isFinite(Number(rirValue)) ||
        Number(rirValue) < -3 ||
        Number(rirValue) > 10)
    ) {
    throw new Error(
        `El RIR de la serie ${position} debe estar entre -3 y 10.`,
    );
    }

  return {
    set_type: pendingSet.set_type,
    position,
    target_rep_range: emptyToNull(pendingSet.target_rep_range),
    repetitions,
    weight_kg: weightKg,
    rir: rirValue === "" ? null : Number(rirValue),
    notes: emptyToNull(pendingSet.notes),
  };
}


async function handleSavePendingSets() {
  if (!state.selectedExercise) {
    return;
  }

  try {
    const payloads = state.pendingSets.map((pendingSet, index) =>
      buildSetPayload(pendingSet, state.sets.length + index + 1),
    );

    elements.savePendingSetsButton.disabled = true;
    elements.addSetRowButton.disabled = true;
    elements.savePendingSetsButton.textContent = "Guardando…";

    for (const payload of payloads) {
      await request(
        `/workout-exercises/${state.selectedExercise.id}/sets/`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
      );
    }

    showStatus(
      `${payloads.length} ${payloads.length === 1 ? "serie guardada" : "series guardadas"}.`,
    );

    await loadSets(state.selectedExercise.id);
    resetPendingSets();
  } catch (error) {
    showStatus(error.message, "error");
  } finally {
    elements.savePendingSetsButton.disabled = false;
    elements.addSetRowButton.disabled = false;
    renderPendingSets();
  }
}

function renderSets() {
  elements.setCount.textContent = String(state.sets.length);
  elements.setsList.innerHTML = "";

  if (state.sets.length === 0) {
    setListEmpty(elements.setsList, "No hay series en este ejercicio.");
    return;
  }

  elements.setsList.className = "sets-list";

  for (const set of state.sets) {
    const card = document.createElement("article");
    card.className = "set-card";

    const rirText = set.rir === null ? "RIR no registrado" : `RIR ${formatNumber(set.rir)}`;
    const targetText = set.target_rep_range ? ` · Objetivo ${set.target_rep_range}` : "";

    card.innerHTML = `
      <span class="set-type-badge ${set.set_type}">${setTypeLabel(set.set_type)}</span>
      <div class="set-main">
        <strong>Serie ${set.position}: ${set.repetitions} reps × ${formatNumber(set.weight_kg)} kg</strong>
        <span class="set-meta">${rirText}${targetText}${set.notes ? ` · ${escapeHtml(set.notes)}` : ""}</span>
      </div>
      <span class="set-volume">${formatNumber(set.volume_kg)} kg</span>
    `;

    elements.setsList.append(card);
  }
}

function escapeHtml(value) {
  const element = document.createElement("div");
  element.textContent = value;
  return element.innerHTML;
}

async function loadSessions() {
  try {
    state.sessions = await request("/workout-sessions/");
    renderSessions();
  } catch (error) {
    showStatus(error.message, "error");
    setListEmpty(elements.sessionsList, "No se pudieron cargar las sesiones.");
  }
}

async function loadExercises(sessionId) {
  const exercises = await request(`/workout-sessions/${sessionId}/exercises/`);
  state.exercises = exercises;
  renderExercises();
}

async function loadSets(exerciseId) {
  const sets = await request(`/workout-exercises/${exerciseId}/sets/`);
  state.sets = sets;
  renderSets();
}

async function selectSession(session) {
  state.selectedSession = session;
  elements.selectedSessionTitle.textContent = session.name;
  elements.sessionEmptyState.classList.add("hidden");
  elements.sessionDetailContent.classList.remove("hidden");
  elements.deleteSessionButton.classList.remove("hidden");
  elements.exerciseForm.reset();
  elements.exerciseForm.elements.position.value = "1";
  resetSelectedExercise();
  renderSessions();

  try {
    await loadExercises(session.id);
  } catch (error) {
    showStatus(error.message, "error");
  }
}

async function selectExercise(exercise) {
  state.selectedExercise = exercise;
  elements.selectedExerciseTitle.textContent = exercise.name;
  elements.exerciseEmptyState.classList.add("hidden");
  elements.exerciseDetailContent.classList.remove("hidden");
  elements.deleteExerciseButton.classList.remove("hidden");
  resetPendingSets();
  renderExercises();

  try {
    await loadSets(exercise.id);
  } catch (error) {
    showStatus(error.message, "error");
  }
}

async function handleCreateSession(event) {
  event.preventDefault();
  const formData = new FormData(elements.sessionForm);

  try {
    const session = await request("/workout-sessions/", {
      method: "POST",
      body: JSON.stringify({
        date: formData.get("date"),
        name: formData.get("name").trim(),
        notes: emptyToNull(formData.get("notes")),
      }),
    });

    elements.sessionForm.reset();
    elements.sessionDate.value = todayAsIsoDate();
    showStatus(`Sesión “${session.name}” creada.`);
    await loadSessions();
    await selectSession(session);
  } catch (error) {
    showStatus(error.message, "error");
  }
}

async function handleCreateExercise(event) {
  event.preventDefault();

  if (!state.selectedSession) {
    return;
  }

  const formData = new FormData(elements.exerciseForm);

  try {
    const exercise = await request(
      `/workout-sessions/${state.selectedSession.id}/exercises/`,
      {
        method: "POST",
        body: JSON.stringify({
          name: formData.get("name").trim(),
          muscle_group: formData.get("muscle_group").trim(),
          position: Number(formData.get("position")),
          technique_notes: emptyToNull(formData.get("technique_notes")),
        }),
      },
    );

    elements.exerciseForm.reset();
    elements.exerciseForm.elements.position.value = String(exercise.position + 1);
    showStatus(`Ejercicio “${exercise.name}” añadido.`);
    await loadExercises(state.selectedSession.id);
    await selectExercise(exercise);
  } catch (error) {
    showStatus(error.message, "error");
  }
}

async function handleDeleteSession() {
  if (!state.selectedSession) {
    return;
  }

  const confirmed = window.confirm(
    `¿Eliminar la sesión “${state.selectedSession.name}” y todo su contenido?`,
  );

  if (!confirmed) {
    return;
  }

  try {
    await request(`/workout-sessions/${state.selectedSession.id}`, {
      method: "DELETE",
    });
    showStatus("Sesión eliminada.");
    resetSelectedSession();
    await loadSessions();
  } catch (error) {
    showStatus(error.message, "error");
  }
}

async function handleDeleteExercise() {
  if (!state.selectedExercise) {
    return;
  }

  const confirmed = window.confirm(
    `¿Eliminar el ejercicio “${state.selectedExercise.name}” y todas sus series?`,
  );

  if (!confirmed) {
    return;
  }

  try {
    await request(`/workout-exercises/${state.selectedExercise.id}`, {
      method: "DELETE",
    });
    showStatus("Ejercicio eliminado.");
    resetSelectedExercise();
    await loadExercises(state.selectedSession.id);
  } catch (error) {
    showStatus(error.message, "error");
  }
}

function renderProgress(progress) {
  elements.progressResult.className = "progress-list";
  elements.progressResult.innerHTML = "";

  for (const session of progress.sessions) {
    const card = document.createElement("article");
    card.className = "progress-session";

    const sets = session.sets
      .map(
        (set) => `
          <div class="progress-set-row">
            <span>Serie ${set.position}</span>
            <span>${set.repetitions} reps × ${formatNumber(set.weight_kg)} kg · ${set.rir === null ? "RIR —" : `RIR ${formatNumber(set.rir)}`}</span>
            <span>${formatNumber(set.volume_kg)} kg</span>
          </div>
        `,
      )
      .join("");

    card.innerHTML = `
      <div class="progress-session-header">
        <div>
          <h3>${escapeHtml(session.session_name)}</h3>
          <p class="progress-meta">${formatDate(session.date)}</p>
        </div>
        <span class="total-volume">${formatNumber(session.total_volume_kg)} kg total</span>
      </div>
      ${sets}
    `;

    elements.progressResult.append(card);
  }
}

async function handleProgressSearch(event) {
  event.preventDefault();
  const exerciseName = elements.progressExerciseName.value.trim();

  try {
    const progress = await request(
      `/workouts/progress?exercise_name=${encodeURIComponent(exerciseName)}`,
    );
    renderProgress(progress);
    showStatus(`Progreso cargado para “${progress.exercise_name}”.`);
  } catch (error) {
    elements.progressResult.className = "empty-state large-empty-state";
    elements.progressResult.textContent = error.message;
    showStatus(error.message, "error");
  }
}

function configureEventListeners() {
  elements.sessionForm.addEventListener("submit", handleCreateSession);
  elements.exerciseForm.addEventListener("submit", handleCreateExercise);
  elements.addSetRowButton.addEventListener("click", addPendingSetRow);
  elements.savePendingSetsButton.addEventListener("click", handleSavePendingSets);
  elements.progressForm.addEventListener("submit", handleProgressSearch);
  elements.refreshSessionsButton.addEventListener("click", loadSessions);
  elements.deleteSessionButton.addEventListener("click", handleDeleteSession);
  elements.deleteExerciseButton.addEventListener("click", handleDeleteExercise);
}

async function initializeApp() {
  elements.sessionDate.value = todayAsIsoDate();
  configureEventListeners();
  await loadSessions();
}

initializeApp();
