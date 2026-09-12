const state = {
  recoveryLogs: [],
  selectedRecoveryLog: null,
};


const elements = {
  status: document.querySelector("#recovery-status"),
  form: document.querySelector("#recovery-form"),
  formTitle: document.querySelector("#recovery-form-title"),
  mode: document.querySelector("#recovery-mode"),
  date: document.querySelector("#recovery-date"),
  sleepHours: document.querySelector("#sleep-hours"),
  sleepQuality: document.querySelector("#sleep-quality"),
  isRestDay: document.querySelector("#is-rest-day"),
  notes: document.querySelector("#recovery-notes"),
  sleepPreview: document.querySelector("#sleep-preview"),
  restDayPreview: document.querySelector("#rest-day-preview"),
  saveButton: document.querySelector("#save-recovery-button"),
  cancelEditButton: document.querySelector(
    "#cancel-recovery-edit-button",
  ),
  count: document.querySelector("#recovery-count"),
  list: document.querySelector("#recovery-list"),
};


function todayAsIsoDate() {
  const now = new Date();
  const timezoneOffset = now.getTimezoneOffset() * 60_000;

  return new Date(now.getTime() - timezoneOffset)
    .toISOString()
    .slice(0, 10);
}


function formatDate(dateString) {
  return new Intl.DateTimeFormat("es-ES", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(`${dateString}T12:00:00`));
}


function formatNumber(value, maximumFractionDigits = 2) {
  return new Intl.NumberFormat("es-ES", {
    maximumFractionDigits,
  }).format(value);
}


function escapeHtml(value) {
  const element = document.createElement("div");
  element.textContent = value;
  return element.innerHTML;
}


function emptyToNull(value) {
  const trimmedValue = value.trim();
  return trimmedValue === "" ? null : trimmedValue;
}


function showStatus(message, type = "success") {
  elements.status.textContent = message;
  elements.status.className = `status-message ${type}`;

  window.clearTimeout(showStatus.timeoutId);
  showStatus.timeoutId = window.setTimeout(() => {
    elements.status.textContent = "";
    elements.status.className = "status-message";
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


function sleepMinutesToHours(sleepMinutes) {
  if (sleepMinutes === null || sleepMinutes === undefined) {
    return null;
  }

  return sleepMinutes / 60;
}


function formatSleepDuration(sleepMinutes) {
  if (sleepMinutes === null || sleepMinutes === undefined) {
    return "Sin dato";
  }

  const hours = Math.floor(sleepMinutes / 60);
  const minutes = sleepMinutes % 60;

  if (hours === 0) {
    return `${minutes} min`;
  }

  if (minutes === 0) {
    return `${hours} h`;
  }

  return `${hours} h ${minutes} min`;
}


function getSleepMinutesFromInput() {
  const value = elements.sleepHours.value.trim();

  if (!value) {
    return null;
  }

  const sleepHours = Number(value);

  if (!Number.isFinite(sleepHours) || sleepHours < 0 || sleepHours > 24) {
    throw new Error(
      "El sueño debe estar entre 0 y 24 horas.",
    );
  }

  return Math.round(sleepHours * 60);
}


function getSleepQualityFromInput() {
  const value = elements.sleepQuality.value;

  if (!value) {
    return null;
  }

  const sleepQuality = Number(value);

  if (
    !Number.isInteger(sleepQuality) ||
    sleepQuality < 1 ||
    sleepQuality > 5
  ) {
    throw new Error(
      "La calidad del sueño debe estar entre 1 y 5.",
    );
  }

  return sleepQuality;
}


function renderPreview() {
  try {
    const sleepMinutes = getSleepMinutesFromInput();

    elements.sleepPreview.textContent = formatSleepDuration(sleepMinutes);
  } catch {
    elements.sleepPreview.textContent = "Valor no válido";
  }

  elements.restDayPreview.textContent = elements.isRestDay.checked
    ? "Día de descanso"
    : "Día activo";
}


function setListEmpty(message) {
  elements.list.className = "recovery-list";
  elements.list.innerHTML = `
    <div class="empty-state large-empty-state">
      ${escapeHtml(message)}
    </div>
  `;
}


function resetRecoveryForm() {
  state.selectedRecoveryLog = null;

  elements.form.reset();
  elements.date.value = todayAsIsoDate();
  elements.formTitle.textContent = "Registrar recuperación";
  elements.mode.textContent = "Nuevo registro";
  elements.saveButton.textContent = "Guardar recuperación";
  elements.cancelEditButton.classList.add("hidden");

  renderPreview();
  renderRecoveryLogs();
}


function startEditing(recoveryLog) {
  state.selectedRecoveryLog = recoveryLog;

  elements.date.value = recoveryLog.date;
  elements.sleepHours.value = recoveryLog.sleep_minutes === null
    ? ""
    : formatNumber(
        sleepMinutesToHours(recoveryLog.sleep_minutes),
        2,
      ).replace(",", ".");
  elements.sleepQuality.value = recoveryLog.sleep_quality ?? "";
  elements.isRestDay.checked = recoveryLog.is_rest_day;
  elements.notes.value = recoveryLog.notes ?? "";

  elements.formTitle.textContent = "Editar recuperación";
  elements.mode.textContent = "Editando registro";
  elements.saveButton.textContent = "Guardar cambios";
  elements.cancelEditButton.classList.remove("hidden");

  renderPreview();
  renderRecoveryLogs();

  elements.form.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
}


function formatSleepQuality(sleepQuality) {
  if (sleepQuality === null || sleepQuality === undefined) {
    return "Calidad no registrada";
  }

  const labels = {
    1: "Muy mala",
    2: "Mala",
    3: "Normal",
    4: "Buena",
    5: "Excelente",
  };

  return `${sleepQuality}/5 · ${labels[sleepQuality]}`;
}


function renderRecoveryLogs() {
  elements.count.textContent = String(state.recoveryLogs.length);
  elements.list.innerHTML = "";

  if (state.recoveryLogs.length === 0) {
    setListEmpty("Todavía no hay registros de recuperación.");
    return;
  }

  elements.list.className = "recovery-list";

  for (const recoveryLog of state.recoveryLogs) {
    const card = document.createElement("article");
    card.className = "recovery-card";

    if (state.selectedRecoveryLog?.id === recoveryLog.id) {
      card.classList.add("selected");
    }

    const restDayText = recoveryLog.is_rest_day
      ? "Día de descanso"
      : "Día activo";

    card.innerHTML = `
      <div class="recovery-card-main">
        <span class="recovery-date">${formatDate(recoveryLog.date)}</span>
        <strong>${formatSleepDuration(recoveryLog.sleep_minutes)}</strong>
        <span class="recovery-meta">
          ${formatSleepQuality(recoveryLog.sleep_quality)} · ${restDayText}
        </span>
        ${
          recoveryLog.notes
            ? `<span class="recovery-notes">${escapeHtml(
                recoveryLog.notes,
              )}</span>`
            : ""
        }
      </div>

      <div class="recovery-actions">
        <button
          class="secondary-button recovery-edit-button"
          type="button"
        >
          Editar
        </button>

        <button
          class="danger-button recovery-delete-button"
          type="button"
        >
          Eliminar
        </button>
      </div>
    `;

    card.querySelector(".recovery-edit-button").addEventListener(
      "click",
      () => startEditing(recoveryLog),
    );

    card.querySelector(".recovery-delete-button").addEventListener(
      "click",
      () => deleteRecoveryLog(recoveryLog),
    );

    elements.list.append(card);
  }
}


async function loadRecoveryLogs() {
  try {
    state.recoveryLogs = await request("/recovery-logs/");
    renderRecoveryLogs();
  } catch (error) {
    setListEmpty("No se pudieron cargar los registros de recuperación.");
    showStatus(error.message, "error");
  }
}


function buildRecoveryPayload() {
  return {
    date: elements.date.value,
    sleep_minutes: getSleepMinutesFromInput(),
    sleep_quality: getSleepQualityFromInput(),
    is_rest_day: elements.isRestDay.checked,
    notes: emptyToNull(elements.notes.value),
  };
}


async function handleSaveRecoveryLog(event) {
  event.preventDefault();

  let payload;

  try {
    payload = buildRecoveryPayload();
  } catch (error) {
    showStatus(error.message, "error");
    return;
  }

  if (!payload.date) {
    showStatus("Selecciona una fecha.", "error");
    return;
  }

  const isEditing = state.selectedRecoveryLog !== null;

  elements.saveButton.disabled = true;
  elements.saveButton.textContent = isEditing
    ? "Guardando cambios…"
    : "Guardando…";

  try {
    if (isEditing) {
      await request(
        `/recovery-logs/${state.selectedRecoveryLog.date}`,
        {
          method: "PUT",
          body: JSON.stringify({
            sleep_minutes: payload.sleep_minutes,
            sleep_quality: payload.sleep_quality,
            is_rest_day: payload.is_rest_day,
            notes: payload.notes,
          }),
        },
      );

      showStatus("Registro de recuperación actualizado.");
    } else {
      await request("/recovery-logs/", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      showStatus("Registro de recuperación guardado.");
    }

    await loadRecoveryLogs();
    resetRecoveryForm();
  } catch (error) {
    showStatus(error.message, "error");
  } finally {
    elements.saveButton.disabled = false;

    if (state.selectedRecoveryLog === null) {
      elements.saveButton.textContent = "Guardar recuperación";
    } else {
      elements.saveButton.textContent = "Guardar cambios";
    }
  }
}


async function deleteRecoveryLog(recoveryLog) {
  const confirmed = window.confirm(
    `¿Eliminar el registro de recuperación del ${formatDate(
      recoveryLog.date,
    )}?`,
  );

  if (!confirmed) {
    return;
  }

  try {
    await request(`/recovery-logs/${recoveryLog.date}`, {
      method: "DELETE",
    });

    if (state.selectedRecoveryLog?.id === recoveryLog.id) {
      resetRecoveryForm();
    }

    showStatus("Registro de recuperación eliminado.");
    await loadRecoveryLogs();
  } catch (error) {
    showStatus(error.message, "error");
  }
}


function configureEventListeners() {
  elements.form.addEventListener("submit", handleSaveRecoveryLog);
  elements.cancelEditButton.addEventListener("click", resetRecoveryForm);

  elements.sleepHours.addEventListener("input", renderPreview);
  elements.isRestDay.addEventListener("change", renderPreview);
}


async function initializeApp() {
  resetRecoveryForm();
  configureEventListeners();
  await loadRecoveryLogs();
}


initializeApp();