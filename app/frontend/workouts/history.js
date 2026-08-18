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
      renderSessionDetail(detail, cachedDetail);
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
      toggleSessionDetail(session.id, card, detail, toggleButton);
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

function renderSessionDetail(container, detail) {
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
      <strong class="total-volume">
        ${formatNumber(detail.totalVolumeKg)} kg total
      </strong>
    </div>
    <div class="history-exercises-list">
      ${exercisesHtml}
    </div>
  `;
}

async function toggleSessionDetail(sessionId, card, container, button) {
  const isExpanded = !container.classList.contains("hidden");

  if (isExpanded) {
    container.classList.add("hidden");
    card.classList.remove("expanded");
    button.setAttribute("aria-expanded", "false");
    return;
  }

  const cachedDetail = state.detailsBySessionId.get(sessionId);

  if (cachedDetail) {
    renderSessionDetail(container, cachedDetail);
    container.classList.remove("hidden");
    card.classList.add("expanded");
    button.setAttribute("aria-expanded", "true");
    return;
  }

  if (state.loadingSessionIds.has(sessionId)) {
    return;
  }

  state.loadingSessionIds.add(sessionId);
  button.disabled = true;
  container.classList.remove("hidden");
  container.className = "history-session-detail empty-state";
  container.textContent = "Cargando detalle…";

  try {
    const detail = await loadSessionDetail(sessionId);
    state.detailsBySessionId.set(sessionId, detail);
    renderSessionDetail(container, detail);
    container.classList.remove("empty-state");
    card.classList.add("expanded");
    button.setAttribute("aria-expanded", "true");
  } catch (error) {
    container.className = "history-session-detail empty-state";
    container.textContent = error.message;
    showStatus(error.message, "error");
  } finally {
    state.loadingSessionIds.delete(sessionId);
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