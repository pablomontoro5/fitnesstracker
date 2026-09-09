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
  stepsChart: document.querySelector("#steps-chart"),
  weightChart: document.querySelector("#weight-chart"),
  runningChart: document.querySelector("#running-chart"),
  exerciseProgressForm: document.querySelector("#exercise-progress-form"),
  exerciseProgressName: document.querySelector("#exercise-progress-name"),
  exerciseNames: document.querySelector("#exercise-names"),
  exerciseProgressStatus: document.querySelector("#exercise-progress-status"),
  exerciseProgressContent: document.querySelector(
    "#exercise-progress-content",
  ),
  exerciseProgressSessions: document.querySelector(
    "#exercise-progress-sessions",
  ),
  exerciseProgressLatestVolume: document.querySelector(
    "#exercise-progress-latest-volume",
  ),
  exerciseProgressMaxWeight: document.querySelector(
    "#exercise-progress-max-weight",
  ),
  exerciseProgressMaxSetVolume: document.querySelector(
    "#exercise-progress-max-set-volume",
  ),
  exerciseProgressHistoryBody: document.querySelector(
    "#exercise-progress-history-body",
  ),
  exerciseVolumeChart: document.querySelector("#exercise-volume-chart"),
  exerciseWeightChart: document.querySelector("#exercise-weight-chart"),
};

const charts = {
  steps: null,
  weight: null,
  running: null,
  exerciseVolume: null,
  exerciseWeight: null,
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

async function requestCharts(startDate, endDate) {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  });

  const response = await fetch(`/statistics/charts?${params}`);
  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((error) => error.msg).join(". ")
      : body?.detail;

    throw new Error(detail || "No se pudieron cargar las gráficas.");
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

function formatChartDate(dateString) {
  return new Intl.DateTimeFormat("es-ES", {
    day: "2-digit",
    month: "short",
  }).format(new Date(`${dateString}T12:00:00`));
}


function destroyChart(chartName) {
  if (charts[chartName]) {
    charts[chartName].destroy();
    charts[chartName] = null;
  }
}


function renderLineChart({
  chartName,
  canvas,
  points,
  valueKey,
  label,
  color,
}) {
  destroyChart(chartName);

  if (!points.length) {
    return;
  }

  charts[chartName] = new Chart(canvas, {
    type: "line",
    data: {
      labels: points.map((point) => formatChartDate(point.date)),
      datasets: [
        {
          label,
          data: points.map((point) => point[valueKey]),
          borderColor: color,
          backgroundColor: `${color}22`,
          borderWidth: 3,
          pointRadius: 4,
          pointHoverRadius: 6,
          tension: 0.3,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
      },
      scales: {
        y: {
          beginAtZero: chartName !== "weight",
          ticks: {
            callback(value) {
              if (chartName === "steps") {
                return `${formatNumber(value, 0)} pasos`;
              }

              if (chartName === "weight") {
                return `${formatNumber(value)} kg`;
              }

              return `${formatNumber(value)} km`;
            },
          },
        },
      },
    },
  });
}


function renderCharts(chartData) {
  renderLineChart({
    chartName: "steps",
    canvas: elements.stepsChart,
    points: chartData.steps,
    valueKey: "steps",
    label: "Pasos",
    color: "#176b48",
  });

  renderLineChart({
    chartName: "weight",
    canvas: elements.weightChart,
    points: chartData.weight,
    valueKey: "weight_kg",
    label: "Peso corporal",
    color: "#4f46e5",
  });

  renderLineChart({
    chartName: "running",
    canvas: elements.runningChart,
    points: chartData.running,
    valueKey: "distance_km",
    label: "Distancia",
    color: "#e58c12",
  });
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
    const [summary, chartData] = await Promise.all([
      requestStatistics(startDate, endDate),
      requestCharts(startDate, endDate),
    ]);

    renderStatistics(summary);
    renderCharts(chartData);
  } catch (error) {
    showStatus(error.message, "error");
  }
}
function showExerciseProgressStatus(message, type = "success") {
  elements.exerciseProgressStatus.textContent = message;
  elements.exerciseProgressStatus.className =
    `status-message ${type}`;
}

async function requestExerciseNames() {
  const response = await fetch("/workouts/exercise-names");
  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((error) => error.msg).join(". ")
      : body?.detail;

    throw new Error(
      detail || "No se pudieron cargar los ejercicios.",
    );
  }

  return body;
}

async function requestExerciseProgress(exerciseName) {
  const params = new URLSearchParams({
    exercise_name: exerciseName,
  });
  const response = await fetch(`/workouts/progress?${params}`);
  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((error) => error.msg).join(". ")
      : body?.detail;

    throw new Error(
      detail || "No se pudo cargar el progreso del ejercicio.",
    );
  }

  return body;
}

function renderExerciseNames(names) {
  elements.exerciseNames.innerHTML = "";

  for (const name of names) {
    const option = document.createElement("option");
    option.value = name;
    elements.exerciseNames.append(option);
  }
}

function renderExerciseProgressSummary(progress) {
  const sessions = progress.sessions;
  const latestSession = sessions.at(-1);
  const maxWeight = Math.max(
    ...sessions.map((session) => session.max_weight_kg),
  );
  const maxSetVolume = Math.max(
    ...sessions.map((session) => session.max_volume_set_kg),
  );

  elements.exerciseProgressSessions.textContent =
    `${sessions.length} sesión(es)`;
  elements.exerciseProgressLatestVolume.textContent =
    `${formatNumber(latestSession.total_volume_kg)} kg`;
  elements.exerciseProgressMaxWeight.textContent =
    `${formatNumber(maxWeight)} kg`;
  elements.exerciseProgressMaxSetVolume.textContent =
    `${formatNumber(maxSetVolume)} kg`;
}

function renderExerciseProgressCharts(progress) {
  const sessions = progress.sessions;
  const labels = sessions.map((session) => formatChartDate(session.date));

  destroyChart("exerciseVolume");
  charts.exerciseVolume = new Chart(elements.exerciseVolumeChart, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Volumen total",
          data: sessions.map((session) => session.total_volume_kg),
          borderColor: "#176b48",
          backgroundColor: "#176b4822",
          borderWidth: 3,
          pointRadius: 4,
          pointHoverRadius: 6,
          tension: 0.3,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback(value) {
              return `${formatNumber(value)} kg`;
            },
          },
        },
      },
    },
  });

  destroyChart("exerciseWeight");
  charts.exerciseWeight = new Chart(elements.exerciseWeightChart, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Carga máxima",
          data: sessions.map((session) => session.max_weight_kg),
          borderColor: "#4f46e5",
          backgroundColor: "#4f46e522",
          borderWidth: 3,
          pointRadius: 4,
          pointHoverRadius: 6,
          tension: 0.3,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
      },
      scales: {
        y: {
          beginAtZero: false,
          ticks: {
            callback(value) {
              return `${formatNumber(value)} kg`;
            },
          },
        },
      },
    },
  });
}

function renderExerciseProgressHistory(progress) {
  elements.exerciseProgressHistoryBody.innerHTML = "";

  for (const session of progress.sessions.slice().reverse()) {
    const row = document.createElement("tr");

    row.innerHTML = `
      <td>${formatDate(session.date)}</td>
      <td>${session.session_name}</td>
      <td>${session.working_sets}</td>
      <td>${session.total_repetitions}</td>
      <td>${formatNumber(session.total_volume_kg)} kg</td>
      <td>${formatNumber(session.max_weight_kg)} kg</td>
    `;

    elements.exerciseProgressHistoryBody.append(row);
  }
}

async function loadExerciseNames() {
  try {
    const names = await requestExerciseNames();
    renderExerciseNames(names);
  } catch (error) {
    showExerciseProgressStatus(error.message, "error");
  }
}

async function handleExerciseProgressSearch(event) {
  event.preventDefault();

  const exerciseName = elements.exerciseProgressName.value.trim();

  if (!exerciseName) {
    showExerciseProgressStatus(
      "Introduce o selecciona un ejercicio.",
      "error",
    );
    return;
  }

  showExerciseProgressStatus("Cargando progreso…");
  elements.exerciseProgressContent.classList.add("hidden");

  try {
    const progress = await requestExerciseProgress(exerciseName);

    renderExerciseProgressSummary(progress);
    renderExerciseProgressCharts(progress);
    renderExerciseProgressHistory(progress);

    elements.exerciseProgressContent.classList.remove("hidden");
    showExerciseProgressStatus(
      `Progreso cargado para “${progress.exercise_name}”.`,
    );
  } catch (error) {
    destroyChart("exerciseVolume");
    destroyChart("exerciseWeight");
    showExerciseProgressStatus(error.message, "error");
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

  elements.downloadBackupButton.addEventListener("click", async () => {
    await downloadDatabaseBackup();
  });

  elements.exerciseProgressForm.addEventListener(
    "submit",
    handleExerciseProgressSearch,
  );
}

async function initializeApp() {
  setPeriod("this-month");
  configureEventListeners();

  await Promise.all([
    loadStatistics(),
    loadExerciseNames(),
  ]);
}

initializeApp();