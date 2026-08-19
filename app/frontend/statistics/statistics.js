const elements = {
  form: document.querySelector("#statistics-form"),
  startDate: document.querySelector("#start-date"),
  endDate: document.querySelector("#end-date"),
  quickActions: document.querySelector(".statistics-quick-actions"),
  statusMessage: document.querySelector("#status-message"),

  stepsTotal: document.querySelector("#steps-total"),
  stepsDetail: document.querySelector("#steps-detail"),

  workoutsSessions: document.querySelector("#workouts-sessions"),
  workoutsDetail: document.querySelector("#workouts-detail"),

  runningDistance: document.querySelector("#running-distance"),
  runningDetail: document.querySelector("#running-detail"),

  bodyWeight: document.querySelector("#body-weight"),
  bodyDetail: document.querySelector("#body-detail"),
};


function formatNumber(value, maximumFractionDigits = 2) {
  return new Intl.NumberFormat("es-ES", {
    maximumFractionDigits,
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


function formatDate(dateString) {
  return new Intl.DateTimeFormat("es-ES", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(`${dateString}T12:00:00`));
}


function toIsoDate(localDate) {
  const year = localDate.getFullYear();
  const month = String(localDate.getMonth() + 1).padStart(2, "0");
  const day = String(localDate.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
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


async function requestStatistics(startDate, endDate) {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  });

  const response = await fetch(`/statistics/summary?${params}`);

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((error) => error.msg).join(". ")
      : body?.detail;

    throw new Error(detail || "No se pudieron cargar las estadísticas.");
  }

  return body;
}


function setLoadingState() {
  elements.stepsTotal.textContent = "…";
  elements.stepsDetail.textContent = "Cargando datos…";

  elements.workoutsSessions.textContent = "…";
  elements.workoutsDetail.textContent = "Cargando datos…";

  elements.runningDistance.textContent = "…";
  elements.runningDetail.textContent = "Cargando datos…";

  elements.bodyWeight.textContent = "…";
  elements.bodyDetail.textContent = "Cargando datos…";
}


function renderStatistics(summary) {
  elements.stepsTotal.textContent =
    `${formatNumber(summary.steps.total, 0)} pasos`;
  elements.stepsDetail.textContent =
    `${summary.steps.days_logged} día(s) registrado(s) · ` +
    `Media: ${formatNumber(summary.steps.average_per_logged_day, 0)} pasos/día`;

  elements.workoutsSessions.textContent =
    `${summary.workouts.sessions} sesión(es)`;
  elements.workoutsDetail.textContent =
    `${summary.workouts.exercises} ejercicio(s) · ` +
    `${summary.workouts.working_sets} serie(s) de trabajo · ` +
    `${formatNumber(summary.workouts.volume_kg)} kg de volumen`;

  elements.runningDistance.textContent =
    `${formatNumber(summary.running.distance_km)} km`;
  elements.runningDetail.textContent =
    `${summary.running.runs} carrera(s) · ` +
    `${formatDuration(summary.running.duration_seconds)} · ` +
    `Ritmo: ${formatPace(summary.running.average_pace_seconds_km)}`;

  const latestMetric = summary.body_metrics.latest;

  if (!latestMetric) {
    elements.bodyWeight.textContent = "Sin registros";
    elements.bodyDetail.textContent =
      "No hay mediciones corporales en este periodo.";
    return;
  }

  const weightChange = summary.body_metrics.weight_change_kg;
  const changeText = weightChange === null
    ? "Sin comparación"
    : weightChange === 0
      ? "Sin cambio de peso"
      : `${weightChange > 0 ? "+" : ""}${formatNumber(weightChange)} kg`;

  elements.bodyWeight.textContent =
    `${formatNumber(latestMetric.weight_kg)} kg`;

  elements.bodyDetail.textContent =
    `${formatDate(latestMetric.date)} · BMI ${formatNumber(latestMetric.bmi)} · ` +
    `${changeText}`;
}


function setPeriod(period) {
  const today = new Date();
  const endDate = new Date(
    today.getFullYear(),
    today.getMonth(),
    today.getDate(),
  );
  let startDate;

  if (period === "7-days") {
    startDate = new Date(endDate);
    startDate.setDate(endDate.getDate() - 6);
  }

  if (period === "30-days") {
    startDate = new Date(endDate);
    startDate.setDate(endDate.getDate() - 29);
  }

  if (period === "this-month") {
    startDate = new Date(endDate.getFullYear(), endDate.getMonth(), 1);
  }

  elements.startDate.value = toIsoDate(startDate);
  elements.endDate.value = toIsoDate(endDate);
}


async function loadStatistics() {
  const startDate = elements.startDate.value;
  const endDate = elements.endDate.value;

  if (!startDate || !endDate) {
    showStatus("Selecciona una fecha de inicio y otra de fin.", "error");
    return;
  }

  if (startDate > endDate) {
    showStatus(
      "La fecha de inicio no puede ser posterior a la fecha de fin.",
      "error",
    );
    return;
  }

  setLoadingState();

  try {
    const summary = await requestStatistics(startDate, endDate);
    renderStatistics(summary);
  } catch (error) {
    showStatus(error.message, "error");
  }
}


function configureEventListeners() {
  elements.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await loadStatistics();
  });

  elements.quickActions.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-period]");

    if (!button) {
      return;
    }

    setPeriod(button.dataset.period);
    await loadStatistics();
  });
}


async function initializeApp() {
  setPeriod("this-month");
  configureEventListeners();
  await loadStatistics();
}


initializeApp();