const state = {
  runs: [],
  selectedRun: null,
};


const elements = {
  runForm: document.querySelector("#run-form"),
  runDate: document.querySelector("#run-date"),
  runDistanceKm: document.querySelector("#run-distance-km"),
  runHours: document.querySelector("#run-hours"),
  runMinutes: document.querySelector("#run-minutes"),
  runSeconds: document.querySelector("#run-seconds"),
  runNotes: document.querySelector("#run-notes"),
  pacePreview: document.querySelector("#pace-preview"),

  refreshRunsButton: document.querySelector("#refresh-runs-button"),
  runsList: document.querySelector("#runs-list"),
  runCount: document.querySelector("#run-count"),
  runTemplate: document.querySelector("#run-template"),

  statusMessage: document.querySelector("#status-message"),
  selectedRunTitle: document.querySelector("#selected-run-title"),
  runEmptyState: document.querySelector("#run-empty-state"),
  editRunForm: document.querySelector("#edit-run-form"),
  deleteRunButton: document.querySelector("#delete-run-button"),
  cancelEditRunButton: document.querySelector("#cancel-edit-run-button"),

  editRunDate: document.querySelector("#edit-run-date"),
  editRunDistanceKm: document.querySelector("#edit-run-distance-km"),
  editRunHours: document.querySelector("#edit-run-hours"),
  editRunMinutes: document.querySelector("#edit-run-minutes"),
  editRunSeconds: document.querySelector("#edit-run-seconds"),
  editRunNotes: document.querySelector("#edit-run-notes"),
  editPacePreview: document.querySelector("#edit-pace-preview"),
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


function formatDuration(durationSeconds) {
  const totalSeconds = Math.round(durationSeconds);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(
      seconds,
    ).padStart(2, "0")}`;
  }

  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}


function formatPace(paceSecondsPerKm) {
  if (!Number.isFinite(paceSecondsPerKm) || paceSecondsPerKm <= 0) {
    return "—";
  }

  const totalSeconds = Math.round(paceSecondsPerKm);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  return `${minutes}:${String(seconds).padStart(2, "0")} min/km`;
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


function setListEmpty(message) {
  elements.runsList.className = "runs-list empty-state";
  elements.runsList.textContent = message;
}


function getDurationSeconds(hoursInput, minutesInput, secondsInput) {
  const hours = Number(hoursInput.value);
  const minutes = Number(minutesInput.value);
  const seconds = Number(secondsInput.value);

  if (
    !Number.isInteger(hours) ||
    !Number.isInteger(minutes) ||
    !Number.isInteger(seconds) ||
    hours < 0 ||
    minutes < 0 ||
    minutes > 59 ||
    seconds < 0 ||
    seconds > 59
  ) {
    throw new Error("Introduce una duración válida.");
  }

  const durationSeconds = hours * 3600 + minutes * 60 + seconds;

  if (durationSeconds <= 0) {
    throw new Error("La duración debe ser mayor que cero.");
  }

  return durationSeconds;
}


function updatePacePreview(
  distanceInput,
  hoursInput,
  minutesInput,
  secondsInput,
  previewElement,
) {
  const distanceKm = Number(distanceInput.value);

  try {
    const durationSeconds = getDurationSeconds(
      hoursInput,
      minutesInput,
      secondsInput,
    );

    if (!Number.isFinite(distanceKm) || distanceKm <= 0) {
      previewElement.textContent = "—";
      return;
    }

    previewElement.textContent = formatPace(durationSeconds / distanceKm);
  } catch {
    previewElement.textContent = "—";
  }
}


function updateCreatePacePreview() {
  updatePacePreview(
    elements.runDistanceKm,
    elements.runHours,
    elements.runMinutes,
    elements.runSeconds,
    elements.pacePreview,
  );
}


function updateEditPacePreview() {
  updatePacePreview(
    elements.editRunDistanceKm,
    elements.editRunHours,
    elements.editRunMinutes,
    elements.editRunSeconds,
    elements.editPacePreview,
  );
}


function splitDuration(durationSeconds) {
  const totalSeconds = Math.round(durationSeconds);

  return {
    hours: Math.floor(totalSeconds / 3600),
    minutes: Math.floor((totalSeconds % 3600) / 60),
    seconds: totalSeconds % 60,
  };
}


function resetSelectedRun() {
  state.selectedRun = null;
  elements.selectedRunTitle.textContent = "Selecciona una carrera";
  elements.runEmptyState.classList.remove("hidden");
  elements.editRunForm.classList.add("hidden");
  elements.deleteRunButton.classList.add("hidden");
}


function renderRuns() {
  elements.runCount.textContent = String(state.runs.length);
  elements.runsList.innerHTML = "";

  if (state.runs.length === 0) {
    setListEmpty("Todavía no hay carreras registradas.");
    return;
  }

  elements.runsList.className = "runs-list";

  for (const run of state.runs) {
    const fragment = elements.runTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".run-card");
    const button = fragment.querySelector(".run-select-button");

    fragment.querySelector(".run-date").textContent = formatDate(run.date);
    fragment.querySelector(".run-distance").textContent =
      `${formatNumber(run.distance_km)} km`;
    fragment.querySelector(".run-notes").textContent =
      run.notes || "Sin notas";
    fragment.querySelector(".run-pace").textContent = formatPace(
      run.average_pace_seconds_km,
    );
    fragment.querySelector(".run-duration").textContent = formatDuration(
      run.duration_seconds,
    );

    if (state.selectedRun?.id === run.id) {
      card.classList.add("selected");
    }

    button.addEventListener("click", () => selectRun(run));
    elements.runsList.append(fragment);
  }
}


function populateEditForm(run) {
  const duration = splitDuration(run.duration_seconds);

  elements.editRunDate.value = run.date;
  elements.editRunDistanceKm.value = run.distance_km;
  elements.editRunHours.value = duration.hours;
  elements.editRunMinutes.value = duration.minutes;
  elements.editRunSeconds.value = duration.seconds;
  elements.editRunNotes.value = run.notes || "";

  updateEditPacePreview();
}


function selectRun(run) {
  state.selectedRun = run;
  elements.selectedRunTitle.textContent =
    `${formatNumber(run.distance_km)} km · ${formatDate(run.date)}`;
  elements.runEmptyState.classList.add("hidden");
  elements.editRunForm.classList.remove("hidden");
  elements.deleteRunButton.classList.remove("hidden");

  populateEditForm(run);
  renderRuns();
}


async function loadRuns() {
  elements.refreshRunsButton.disabled = true;
  elements.refreshRunsButton.textContent = "…";

  try {
    state.runs = await request("/runs/");
    renderRuns();
  } catch (error) {
    setListEmpty("No se pudieron cargar las carreras.");
    showStatus(error.message, "error");
  } finally {
    elements.refreshRunsButton.disabled = false;
    elements.refreshRunsButton.textContent = "↻";
  }
}


function buildRunPayload(
  dateInput,
  distanceInput,
  hoursInput,
  minutesInput,
  secondsInput,
  notesInput,
) {
  const distanceKm = Number(distanceInput.value);

  if (!Number.isFinite(distanceKm) || distanceKm <= 0 || distanceKm > 1000) {
    throw new Error("La distancia debe estar entre 0 y 1000 km.");
  }

  return {
    date: dateInput.value,
    distance_km: distanceKm,
    duration_seconds: getDurationSeconds(
      hoursInput,
      minutesInput,
      secondsInput,
    ),
    notes: emptyToNull(notesInput.value),
  };
}


async function handleCreateRun(event) {
  event.preventDefault();

  try {
    const payload = buildRunPayload(
      elements.runDate,
      elements.runDistanceKm,
      elements.runHours,
      elements.runMinutes,
      elements.runSeconds,
      elements.runNotes,
    );

    const run = await request("/runs/", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    elements.runForm.reset();
    elements.runDate.value = todayAsIsoDate();
    elements.runHours.value = "0";
    elements.runMinutes.value = "0";
    elements.runSeconds.value = "0";
    elements.pacePreview.textContent = "—";

    showStatus(`Carrera de ${formatNumber(run.distance_km)} km guardada.`);
    await loadRuns();
    selectRun(run);
  } catch (error) {
    showStatus(error.message, "error");
  }
}


async function handleUpdateRun(event) {
  event.preventDefault();

  if (!state.selectedRun) {
    return;
  }

  try {
    const payload = buildRunPayload(
      elements.editRunDate,
      elements.editRunDistanceKm,
      elements.editRunHours,
      elements.editRunMinutes,
      elements.editRunSeconds,
      elements.editRunNotes,
    );

    const updatedRun = await request(`/runs/${state.selectedRun.id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });

    state.selectedRun = updatedRun;
    showStatus("Carrera actualizada.");
    await loadRuns();
    selectRun(updatedRun);
  } catch (error) {
    showStatus(error.message, "error");
  }
}


async function handleDeleteRun() {
  if (!state.selectedRun) {
    return;
  }

  const confirmed = window.confirm(
    `¿Eliminar la carrera de ${formatNumber(
      state.selectedRun.distance_km,
    )} km del ${formatDate(state.selectedRun.date)}?`,
  );

  if (!confirmed) {
    return;
  }

  try {
    await request(`/runs/${state.selectedRun.id}`, {
      method: "DELETE",
    });

    showStatus("Carrera eliminada.");
    resetSelectedRun();
    await loadRuns();
  } catch (error) {
    showStatus(error.message, "error");
  }
}


function configurePaceListeners() {
  [
    elements.runDistanceKm,
    elements.runHours,
    elements.runMinutes,
    elements.runSeconds,
  ].forEach((input) => {
    input.addEventListener("input", updateCreatePacePreview);
  });

  [
    elements.editRunDistanceKm,
    elements.editRunHours,
    elements.editRunMinutes,
    elements.editRunSeconds,
  ].forEach((input) => {
    input.addEventListener("input", updateEditPacePreview);
  });
}


function configureEventListeners() {
  elements.runForm.addEventListener("submit", handleCreateRun);
  elements.editRunForm.addEventListener("submit", handleUpdateRun);
  elements.refreshRunsButton.addEventListener("click", loadRuns);
  elements.deleteRunButton.addEventListener("click", handleDeleteRun);

  elements.cancelEditRunButton.addEventListener("click", () => {
    if (state.selectedRun) {
      populateEditForm(state.selectedRun);
    }
  });

  configurePaceListeners();
}


async function initializeApp() {
  elements.runDate.value = todayAsIsoDate();
  configureEventListeners();
  await loadRuns();
}


initializeApp();