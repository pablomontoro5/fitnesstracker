const state = {
  dailyLogs: [],
  selectedDailyLog: null,
};

const elements = {
  statusMessage: document.querySelector("#status-message"),
  dailyLogForm: document.querySelector("#daily-log-form"),
  dailyLogDate: document.querySelector("#daily-log-date"),
  dailyLogSteps: document.querySelector("#daily-log-steps"),
  dailyLogNotes: document.querySelector("#daily-log-notes"),
  saveDailyLogButton: document.querySelector("#save-daily-log-button"),
  cancelDailyLogEditButton: document.querySelector(
    "#cancel-daily-log-edit-button",
  ),
  dailyLogMode: document.querySelector("#daily-log-mode"),
  dailyLogCount: document.querySelector("#daily-log-count"),
  dailyLogsList: document.querySelector("#daily-logs-list"),
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
  return new Intl.NumberFormat("es-ES").format(value);
}

function emptyToNull(value) {
  const trimmedValue = value.trim();
  return trimmedValue === "" ? null : trimmedValue;
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

function resetDailyLogForm() {
  state.selectedDailyLog = null;
  elements.dailyLogForm.reset();
  elements.dailyLogDate.value = todayAsIsoDate();
  elements.dailyLogMode.textContent = "Nuevo registro";
  elements.saveDailyLogButton.textContent = "Guardar pasos";
  elements.cancelDailyLogEditButton.classList.add("hidden");
  renderDailyLogs();
}

function renderDailyLogs() {
  elements.dailyLogCount.textContent = String(state.dailyLogs.length);
  elements.dailyLogsList.innerHTML = "";

  if (state.dailyLogs.length === 0) {
    setListEmpty(
      elements.dailyLogsList,
      "Todavía no hay registros de pasos.",
    );
    return;
  }

  elements.dailyLogsList.className = "daily-logs-list";

  for (const dailyLog of state.dailyLogs) {
    const card = document.createElement("article");
    card.className = "daily-log-card";

    if (state.selectedDailyLog?.id === dailyLog.id) {
      card.classList.add("selected");
    }

    card.innerHTML = `
      <button class="daily-log-select-button" type="button">
        <span class="daily-log-date">${formatDate(dailyLog.date)}</span>
        <strong class="daily-log-steps">${formatNumber(dailyLog.steps)} pasos</strong>
        <span class="daily-log-notes">${escapeHtml(dailyLog.notes || "Sin notas")}</span>
      </button>
      <button class="secondary-button edit-daily-log-button" type="button">
        Editar
      </button>
    `;

    card.querySelector(".daily-log-select-button").addEventListener(
      "click",
      () => selectDailyLog(dailyLog),
    );

    card.querySelector(".edit-daily-log-button").addEventListener(
      "click",
      () => selectDailyLog(dailyLog),
    );

    elements.dailyLogsList.append(card);
  }
}

async function loadDailyLogs() {
  try {
    state.dailyLogs = await request("/daily-logs/");
    renderDailyLogs();
  } catch (error) {
    showStatus(error.message, "error");
    setListEmpty(
      elements.dailyLogsList,
      "No se pudieron cargar los registros diarios.",
    );
  }
}

function selectDailyLog(dailyLog) {
  state.selectedDailyLog = dailyLog;

  elements.dailyLogDate.value = dailyLog.date;
  elements.dailyLogSteps.value = dailyLog.steps;
  elements.dailyLogNotes.value = dailyLog.notes || "";
  elements.dailyLogMode.textContent = "Editando registro";
  elements.saveDailyLogButton.textContent = "Guardar cambios";
  elements.cancelDailyLogEditButton.classList.remove("hidden");

  renderDailyLogs();
  elements.dailyLogSteps.focus();
}

async function handleSaveDailyLog(event) {
  event.preventDefault();

  const date = elements.dailyLogDate.value;
  const steps = Number(elements.dailyLogSteps.value);
  const notes = emptyToNull(elements.dailyLogNotes.value);

  if (!Number.isInteger(steps) || steps < 0 || steps > 100000) {
    showStatus(
      "Los pasos deben ser un número entero entre 0 y 100000.",
      "error",
    );
    return;
  }

  try {
    const isEditing = state.selectedDailyLog !== null;

    const dailyLog = await request(
      isEditing
        ? `/daily-logs/${state.selectedDailyLog.date}`
        : "/daily-logs/",
      {
        method: isEditing ? "PUT" : "POST",
        body: JSON.stringify(
          isEditing
            ? { steps, notes }
            : { date, steps, notes },
        ),
      },
    );

    showStatus(
      isEditing
        ? `Registro de ${formatDate(dailyLog.date)} actualizado.`
        : `Pasos de ${formatDate(dailyLog.date)} guardados.`,
    );

    await loadDailyLogs();
    resetDailyLogForm();
  } catch (error) {
    showStatus(error.message, "error");
  }
}

function initializeApp() {
  elements.dailyLogDate.value = todayAsIsoDate();

  elements.dailyLogForm.addEventListener(
    "submit",
    handleSaveDailyLog,
  );

  elements.cancelDailyLogEditButton.addEventListener(
    "click",
    resetDailyLogForm,
  );

  loadDailyLogs();
}

document.addEventListener("DOMContentLoaded", () => {
  initializeApp();
});