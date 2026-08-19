const state = {
  sessions: [],
  detailsBySessionId: new Map(),
  loadingSessionIds: new Set(),
};

const elements = {
  historyList: document.querySelector("#history-list"),
  historySessionCount: document.querySelector("#history-session-count"),
  refreshHistoryButton: document.querySelector("#refresh-history-button"),
  sessionTemplate: document.querySelector("#history-session-template"),
  statusMessage: document.querySelector("#status-message"),
};

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

function escapeHtml(value) {
  const element = document.createElement("div");
  element.textContent = value;
  return element.innerHTML;
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

function setListEmpty(message) {
  elements.historyList.className = "sessions-list empty-state";
  elements.historyList.textContent = message;
}

function renderSessions() {
  elements.historySessionCount.textContent = String(state.sessions.length);
  elements.historyList.innerHTML = "";

  if (state.sessions.length === 0) {
    setListEmpty("Todavía no hay sesiones registradas.");
    return;
  }

  elements.historyList.className = "sessions-list";

  for (const session of state.sessions) {
    const fragment = elements.sessionTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".history-session-card");
    const toggleButton = fragment.querySelector(".history-session-toggle");
    const detail = fragment.querySelector(".history-session-detail");

    fragment.querySelector(".session-date").textContent = formatDate(session.date);
    fragment.querySelector(".session-name").textContent = session.name;
    fragment.querySelector(".session-notes").textContent =
      session.notes || "Sin notas";

    const cachedDetail = state.detailsBySessionId.get(session.id);

    if (cachedDetail) {
      renderSessionDetail(detail, session, cachedDetail);
      detail.classList.remove("hidden");
      card.classList.add("expanded");
      toggleButton.setAttribute("aria-expanded", "true");
    } else {
      fragment.querySelector(".history-exercise-count").textContent =
        "Pulsa para ver detalle";
      fragment.querySelector(".history-total-volume").textContent = "";
      toggleButton.setAttribute("aria-expanded", "false");
    }

    toggleButton.addEventListener("click", () => {
      toggleSessionDetail(session, card, detail, toggleButton);
    });

    elements.historyList.append(fragment);
  }
}

async function loadSessionDetail(sessionId) {
  const exercises = await request(
    `/workout-sessions/${sessionId}/exercises/`,
  );

  const exercisesWithSets = await Promise.all(
    exercises.map(async (exercise) => {
      const sets = await request(
        `/workout-exercises/${exercise.id}/sets/`,
      );

      return {
        ...exercise,
        sets,
        totalVolumeKg: sets.reduce(
          (total, set) => total + Number(set.volume_kg),
          0,
        ),
      };
    }),
  );

  const totalVolumeKg = exercisesWithSets.reduce(
    (total, exercise) => total + exercise.totalVolumeKg,
    0,
  );

  return {
    exercises: exercisesWithSets,
    totalVolumeKg,
  };
}

function renderSessionDetail(container, session, detail) {
  const exerciseCount = detail.exercises.length;

  const exercisesHtml =
    exerciseCount === 0
      ? `<div class="empty-state">Esta sesión no tiene ejercicios registrados.</div>`
      : detail.exercises
          .map((exercise) => {
            const setsHtml =
              exercise.sets.length === 0
                ? `<p class="history-no-sets">No hay series registradas.</p>`
                : `
                  <div class="history-sets-table-wrapper">
                    <table class="history-sets-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>Tipo</th>
                          <th>Reps</th>
                          <th>Carga</th>
                          <th>RIR</th>
                          <th>Volumen</th>
                          <th aria-label="Acciones"></th>
                        </tr>
                      </thead>
                      <tbody>
                        ${exercise.sets
                          .map(
                            (set) => `
                              <tr>
                                <td>${set.position}</td>
                                <td>${escapeHtml(setTypeLabel(set.set_type))}</td>
                                <td>${formatNumber(set.repetitions)}</td>
                                <td>${formatNumber(set.weight_kg)} kg</td>
                                <td>${set.rir === null ? "—" : formatNumber(set.rir)}</td>
                                <td>${formatNumber(set.volume_kg)} kg</td>
                                <td>
                                  <button
                                    class="history-edit-set-button secondary-button"
                                    type="button"
                                    data-set-id="${set.id}"
                                  >
                                    Editar
                                  </button>
                                </td>
                              </tr>
                              <tr class="history-set-editor-row hidden" data-editor-for="${set.id}">
                                <td colspan="7">
                                  ${renderSetEditor(set)}
                                </td>
                              </tr>
                            `,
                          )
                          .join("")}
                      </tbody>
                    </table>
                  </div>
                `;

            return `
              <article class="history-exercise-card">
                <div class="history-exercise-header">
                  <div>
                    <p class="eyebrow">Ejercicio ${exercise.position}</p>
                    <h3>${escapeHtml(exercise.name)}</h3>
                    <p class="history-muscle-group">
                      ${escapeHtml(exercise.muscle_group)}
                    </p>
                  </div>
                  <strong class="total-volume">
                    ${formatNumber(exercise.totalVolumeKg)} kg
                  </strong>
                </div>

                ${
                  exercise.technique_notes
                    ? `<p class="history-technique-notes">${escapeHtml(exercise.technique_notes)}</p>`
                    : ""
                }

                ${setsHtml}
              </article>
            `;
          })
          .join("");

  container.innerHTML = `
    <div class="history-detail-summary">
      <span>${exerciseCount} ${exerciseCount === 1 ? "ejercicio" : "ejercicios"}</span>
      <div class="history-session-actions">
        <strong class="total-volume">
          ${formatNumber(detail.totalVolumeKg)} kg total
        </strong>
        <button
          class="history-edit-session-button secondary-button"
          type="button"
        >
          Editar sesión
        </button>
      </div>
    </div>

    <form class="history-session-editor form-grid hidden">
      <label>
        Fecha
        <input name="date" type="date" value="${session.date}" required />
      </label>

      <label>
        Nombre
        <input
          name="name"
          type="text"
          maxlength="100"
          value="${escapeHtml(session.name)}"
          required
        />
      </label>

      <label class="full-width">
        Notas <span class="optional">opcional</span>
        <textarea
          name="notes"
          maxlength="1000"
          rows="2"
        >${escapeHtml(session.notes || "")}</textarea>
      </label>

      <div class="form-actions full-width">
        <button
          class="history-cancel-session-edit-button secondary-button"
          type="button"
        >
          Cancelar
        </button>
        <button class="primary-button" type="submit">
          Guardar sesión
        </button>
      </div>
    </form>

    <div class="history-exercises-list">
      ${exercisesHtml}
    </div>
  `;

  configureDetailEventListeners(container, session);
}

function renderSetEditor(set) {
  return `
    <form class="history-set-editor form-grid" data-set-id="${set.id}">
      <label>
        Tipo
        <select name="set_type">
          <option value="warmup" ${set.set_type === "warmup" ? "selected" : ""}>
            Calentamiento
          </option>
          <option value="approximation" ${set.set_type === "approximation" ? "selected" : ""}>
            Aproximación
          </option>
          <option value="working" ${set.set_type === "working" ? "selected" : ""}>
            Trabajo
          </option>
          <option value="drop_set" ${set.set_type === "drop_set" ? "selected" : ""}>
            Drop set
          </option>
        </select>
      </label>

      <label>
        Posición
        <input
          name="position"
          type="number"
          min="1"
          max="100"
          value="${set.position}"
          required
        />
      </label>

      <label>
        Objetivo
        <input
          name="target_rep_range"
          type="text"
          maxlength="30"
          value="${escapeHtml(set.target_rep_range || "")}"
          placeholder="Ej.: 8-12"
        />
      </label>

      <label>
        Repeticiones
        <input
          name="repetitions"
          type="number"
          min="1"
          max="1000"
          value="${set.repetitions}"
          required
        />
      </label>

      <label>
        Carga kg
        <input
          name="weight_kg"
          type="number"
          min="0"
          max="1000"
          step="0.5"
          value="${set.weight_kg}"
          required
        />
      </label>

      <label>
        RIR
        <input
          name="rir"
          type="number"
          min="-3"
          max="10"
          step="0.5"
          value="${set.rir ?? ""}"
          placeholder="Opcional"
        />
      </label>

      <label class="full-width">
        Notas <span class="optional">opcional</span>
        <input
          name="notes"
          type="text"
          maxlength="1000"
          value="${escapeHtml(set.notes || "")}"
        />
      </label>

      <div class="form-actions full-width">
        <button
          class="history-cancel-set-edit-button secondary-button"
          type="button"
          data-set-id="${set.id}"
        >
          Cancelar
        </button>
        <button class="primary-button" type="submit">
          Guardar serie
        </button>
      </div>
    </form>
  `;
}

function configureDetailEventListeners(container, session) {
  const sessionEditor = container.querySelector(".history-session-editor");
  const editSessionButton = container.querySelector(
    ".history-edit-session-button",
  );
  const cancelSessionEditButton = container.querySelector(
    ".history-cancel-session-edit-button",
  );

  editSessionButton.addEventListener("click", () => {
    sessionEditor.classList.remove("hidden");
    editSessionButton.classList.add("hidden");
    sessionEditor.elements.name.focus();
  });

  cancelSessionEditButton.addEventListener("click", () => {
    sessionEditor.reset();
    sessionEditor.classList.add("hidden");
    editSessionButton.classList.remove("hidden");
  });

  sessionEditor.addEventListener("submit", async (event) => {
    event.preventDefault();

    const formData = new FormData(sessionEditor);
    const saveButton = sessionEditor.querySelector('button[type="submit"]');

    try {
      saveButton.disabled = true;

      const updatedSession = await request(
        `/workout-sessions/${session.id}`,
        {
          method: "PUT",
          body: JSON.stringify({
            date: formData.get("date"),
            name: formData.get("name").trim(),
            notes: emptyToNull(formData.get("notes")),
          }),
        },
      );

      updateSessionInState(updatedSession);
      state.detailsBySessionId.delete(session.id);
      await refreshExpandedSession(updatedSession.id);
      showStatus(`Sesión “${updatedSession.name}” actualizada.`);
    } catch (error) {
      showStatus(error.message, "error");
    } finally {
      saveButton.disabled = false;
    }
  });

  container.querySelectorAll(".history-edit-set-button").forEach((button) => {
    button.addEventListener("click", () => {
      const editorRow = container.querySelector(
        `[data-editor-for="${button.dataset.setId}"]`,
      );

      editorRow.classList.remove("hidden");
      button.disabled = true;
    });
  });

  container.querySelectorAll(".history-cancel-set-edit-button").forEach(
    (button) => {
      button.addEventListener("click", () => {
        const editorRow = container.querySelector(
          `[data-editor-for="${button.dataset.setId}"]`,
        );
        const editButton = container.querySelector(
          `.history-edit-set-button[data-set-id="${button.dataset.setId}"]`,
        );

        editorRow.querySelector("form").reset();
        editorRow.classList.add("hidden");
        editButton.disabled = false;
      });
    },
  );

  container.querySelectorAll(".history-set-editor").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const formData = new FormData(form);
      const saveButton = form.querySelector('button[type="submit"]');
      const setId = form.dataset.setId;

      const position = Number(formData.get("position"));
      const repetitions = Number(formData.get("repetitions"));
      const weightKg = Number(formData.get("weight_kg"));
      const rirValue = formData.get("rir").trim();

      if (!Number.isInteger(position) || position < 1 || position > 100) {
        showStatus("La posición debe estar entre 1 y 100.", "error");
        return;
      }

      if (!Number.isInteger(repetitions) || repetitions < 1 || repetitions > 1000) {
        showStatus("Las repeticiones deben estar entre 1 y 1000.", "error");
        return;
      }

      if (!Number.isFinite(weightKg) || weightKg < 0 || weightKg > 1000) {
        showStatus("La carga debe estar entre 0 y 1000 kg.", "error");
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
        saveButton.disabled = true;

        await request(`/workout-sets/${setId}`, {
          method: "PUT",
          body: JSON.stringify({
            set_type: formData.get("set_type"),
            position,
            target_rep_range: emptyToNull(formData.get("target_rep_range")),
            repetitions,
            weight_kg: weightKg,
            rir: rirValue === "" ? null : Number(rirValue),
            notes: emptyToNull(formData.get("notes")),
          }),
        });

        state.detailsBySessionId.delete(session.id);
        await refreshExpandedSession(session.id);
        showStatus("Serie actualizada.");
      } catch (error) {
        showStatus(error.message, "error");
      } finally {
        saveButton.disabled = false;
      }
    });
  });
}

function updateSessionInState(updatedSession) {
  state.sessions = state.sessions
    .map((session) =>
      session.id === updatedSession.id ? updatedSession : session,
    )
    .sort((firstSession, secondSession) => {
      const dateComparison = secondSession.date.localeCompare(firstSession.date);

      if (dateComparison !== 0) {
        return dateComparison;
      }

      return secondSession.id - firstSession.id;
    });
}

async function refreshExpandedSession(sessionId) {
  const session = state.sessions.find((item) => item.id === sessionId);

  if (!session) {
    return;
  }

  const detail = await loadSessionDetail(sessionId);
  state.detailsBySessionId.set(sessionId, detail);
  renderSessions();
}

async function toggleSessionDetail(session, card, container, button) {
  const isExpanded = !container.classList.contains("hidden");

  if (isExpanded) {
    container.classList.add("hidden");
    card.classList.remove("expanded");
    button.setAttribute("aria-expanded", "false");
    return;
  }

  const cachedDetail = state.detailsBySessionId.get(session.id);

  if (cachedDetail) {
    renderSessionDetail(container, session, cachedDetail);
    container.classList.remove("hidden");
    card.classList.add("expanded");
    button.setAttribute("aria-expanded", "true");
    return;
  }

  if (state.loadingSessionIds.has(session.id)) {
    return;
  }

  state.loadingSessionIds.add(session.id);
  button.disabled = true;
  container.className = "history-session-detail empty-state";
  container.textContent = "Cargando detalle…";

  try {
    const detail = await loadSessionDetail(session.id);
    state.detailsBySessionId.set(session.id, detail);
    renderSessionDetail(container, session, detail);
    container.classList.remove("empty-state");
    card.classList.add("expanded");
    button.setAttribute("aria-expanded", "true");
  } catch (error) {
    container.className = "history-session-detail empty-state";
    container.textContent = error.message;
    showStatus(error.message, "error");
  } finally {
    state.loadingSessionIds.delete(session.id);
    button.disabled = false;
  }
}

async function loadHistory() {
  elements.refreshHistoryButton.disabled = true;
  elements.refreshHistoryButton.textContent = "…";

  try {
    state.sessions = await request("/workout-sessions/");
    state.detailsBySessionId.clear();
    renderSessions();
  } catch (error) {
    setListEmpty("No se pudo cargar el historial.");
    showStatus(error.message, "error");
  } finally {
    elements.refreshHistoryButton.disabled = false;
    elements.refreshHistoryButton.textContent = "↻";
  }
}

function initializeApp() {
  elements.refreshHistoryButton.addEventListener("click", loadHistory);
  loadHistory();
}

initializeApp();