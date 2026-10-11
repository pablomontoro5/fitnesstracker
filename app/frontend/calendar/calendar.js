const WEEKDAYS_IN_GRID = 7;

const VIEW_STORAGE_KEY = "fitness_tracker_calendar_view";
const MAX_PLANS_SHOWN_PER_DAY = 3;


function loadSavedView() {
  try {
    return localStorage.getItem(VIEW_STORAGE_KEY) === "week" ? "week" : "month";
  } catch {
    return "month";
  }
}


const state = {
  // "month" o "week".
  view: loadSavedView(),
  // Primer día del mes que se está viendo.
  month: startOfMonth(new Date()),
  // Lunes de la semana que se está viendo (vista semanal).
  weekStart: startOfWeek(new Date()),
  selectedDate: formatDate(new Date()),
  days: new Map(),
  planSummary: null,
  templates: [],
};


const elements = {
  statusMessage: document.querySelector("#status-message"),
  monthTitle: document.querySelector("#month-title"),
  previousMonthButton: document.querySelector("#previous-month-button"),
  nextMonthButton: document.querySelector("#next-month-button"),
  todayButton: document.querySelector("#today-button"),
  calendarError: document.querySelector("#calendar-error"),
  planSummary: document.querySelector("#plan-summary"),
  calendarWeekdays: document.querySelector("#calendar-weekdays"),
  viewMonthButton: document.querySelector("#view-month-button"),
  viewWeekButton: document.querySelector("#view-week-button"),
  weekActions: document.querySelector("#week-actions"),
  copyFromPreviousButton: document.querySelector(
    "#copy-from-previous-week-button",
  ),
  copyToNextButton: document.querySelector("#copy-to-next-week-button"),
  calendarGrid: document.querySelector("#calendar-grid"),
  dayTitle: document.querySelector("#day-title"),
  daySummary: document.querySelector("#day-summary"),
  plannedList: document.querySelector("#planned-list"),
  plannedForm: document.querySelector("#planned-form"),
  plannedTemplate: document.querySelector("#planned-template"),
  plannedKind: document.querySelector("#planned-kind"),
  plannedTemplateLabel: document.querySelector("#planned-template-label"),
  plannedDistanceLabel: document.querySelector("#planned-distance-label"),
  plannedDistance: document.querySelector("#planned-distance"),
  plannedNameHint: document.querySelector("#planned-name-hint"),
  plannedName: document.querySelector("#planned-name"),
};


function startOfMonth(date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}


// Fecha local en AAAA-MM-DD. toISOString() usa UTC y desplaza el día.
function formatDate(date) {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${date.getFullYear()}-${month}-${day}`;
}


function parseDate(value) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}


// Lunes de la semana de la fecha dada (la semana empieza en lunes).
function startOfWeek(date) {
  const offset = (date.getDay() + 6) % 7;
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() - offset);
}


function addDays(date, amount) {
  return new Date(
    date.getFullYear(),
    date.getMonth(),
    date.getDate() + amount,
  );
}


function getGridRange() {
  if (state.view === "week") {
    return { start: state.weekStart, end: addDays(state.weekStart, 6) };
  }

  const start = startOfWeek(state.month);
  const lastOfMonth = new Date(
    state.month.getFullYear(),
    state.month.getMonth() + 1,
    0,
  );
  const end = addDays(startOfWeek(lastOfMonth), WEEKDAYS_IN_GRID - 1);

  return { start, end };
}


function formatNumber(value, maximumFractionDigits = 1) {
  return new Intl.NumberFormat("es-ES", { maximumFractionDigits }).format(
    value,
  );
}


function formatSleep(minutes) {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;

  return rest === 0 ? `${hours} h` : `${hours} h ${rest} min`;
}


const STATUS_LABELS = {
  planned: "Planificada",
  completed: "Completada",
  skipped: "Omitida",
};


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
  const response = await apiFetch(path, {
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


function createElement(tag, className, text) {
  const element = document.createElement(tag);

  if (className) {
    element.className = className;
  }

  if (text !== undefined) {
    element.textContent = text;
  }

  return element;
}


async function loadActivity() {
  const { start, end } = getGridRange();
  const query = new URLSearchParams({
    start_date: formatDate(start),
    end_date: formatDate(end),
    // Con la fecha local del navegador: así «vencida» no depende de la zona
    // horaria del servidor.
    today: formatDate(new Date()),
  });

  renderListLoading(
    elements.calendarError,
    "calendar-error",
    "Cargando calendario…",
  );

  try {
    const activity = await request(`/calendar/activity?${query}`);

    state.days = new Map(activity.days.map((day) => [day.date, day]));
    state.planSummary = activity.plan_summary;
    elements.calendarError.className = "empty-state hidden";
    elements.calendarError.replaceChildren();
  } catch (error) {
    state.days = new Map();
    state.planSummary = null;
    elements.calendarError.classList.remove("hidden");
    renderListError(
      elements.calendarError,
      "calendar-error",
      error.message,
      loadActivity,
    );
  }

  renderCalendar();
  renderPlanSummary();
  renderDayDetail();
}


function renderPlanSummary() {
  const summary = state.planSummary;
  const period = state.view === "week" ? "la semana" : "el mes";

  if (!summary) {
    elements.planSummary.replaceChildren();
    return;
  }

  if (summary.total === 0) {
    elements.planSummary.replaceChildren(
      createElement(
        "p",
        "plan-summary-details",
        `No hay sesiones planificadas en ${period}.`,
      ),
    );
    return;
  }

  const headline = createElement(
    "p",
    "plan-summary-text",
    `Plan de ${period}: ${summary.completed} de ${summary.total} `
      + `${summary.total === 1 ? "sesión completada" : "sesiones completadas"}`
      + (summary.completion_rate === null
        ? ""
        : ` (${formatNumber(summary.completion_rate, 0)} % de lo que ya tocaba)`),
  );

  const progress = createElement("div", "plan-progress");
  progress.setAttribute("role", "progressbar");
  progress.setAttribute("aria-valuemin", "0");
  progress.setAttribute("aria-valuemax", String(summary.total));
  progress.setAttribute("aria-valuenow", String(summary.completed));

  const bar = createElement("div", "plan-progress-bar");
  bar.style.width = `${(summary.completed / summary.total) * 100}%`;
  progress.append(bar);

  const details = createElement("p", "plan-summary-details");

  if (summary.overdue > 0) {
    details.append(
      createElement(
        "span",
        "overdue",
        `${summary.overdue} ${summary.overdue === 1 ? "vencida" : "vencidas"}`,
      ),
    );
  }

  if (summary.skipped > 0) {
    details.append(
      createElement(
        "span",
        "",
        `${summary.skipped} ${summary.skipped === 1 ? "omitida" : "omitidas"}`,
      ),
    );
  }

  if (summary.upcoming > 0) {
    details.append(
      createElement("span", "", `${summary.upcoming} por hacer`),
    );
  }

  elements.planSummary.replaceChildren(headline, progress, details);
}


async function loadTemplates() {
  try {
    state.templates = await request("/workout-templates/");
  } catch (error) {
    state.templates = [];
    showStatus(`No se cargaron las plantillas: ${error.message}`, "error");
  }

  const options = [new Option("Sin plantilla", "")];

  for (const template of state.templates) {
    options.push(new Option(template.name, String(template.id)));
  }

  elements.plannedTemplate.replaceChildren(...options);
}


function renderCalendar() {
  const { start, end } = getGridRange();
  const todayValue = formatDate(new Date());
  const cells = [];

  const isWeekView = state.view === "week";

  if (isWeekView) {
    // "5 – 11 de octubre de 2026"
    elements.monthTitle.textContent = `Semana del ${new Intl.DateTimeFormat(
      "es-ES",
      { day: "numeric", month: "long", year: "numeric" },
    ).formatRange(start, end)}`;
  } else {
    const monthName = new Intl.DateTimeFormat("es-ES", {
      month: "long",
      year: "numeric",
    }).format(state.month);

    // "octubre de 2026" -> "Octubre de 2026"
    elements.monthTitle.textContent = (
      monthName.charAt(0).toUpperCase() + monthName.slice(1)
    );
  }

  elements.calendarGrid.classList.toggle("week-view", isWeekView);
  // En la vista semanal cada día lleva su propio nombre.
  elements.calendarWeekdays.hidden = isWeekView;

  for (let day = start; day <= end; day = addDays(day, 1)) {
    const value = formatDate(day);
    const activity = state.days.get(value);
    const isOutsideMonth = (
      state.view === "month" && day.getMonth() !== state.month.getMonth()
    );

    const cell = createElement("button", "calendar-day");
    cell.type = "button";
    cell.dataset.date = value;
    cell.setAttribute("role", "gridcell");

    if (isOutsideMonth) cell.classList.add("outside-month");
    if (value === todayValue) cell.classList.add("today");
    if (value === state.selectedDate) {
      cell.classList.add("selected");
      cell.setAttribute("aria-current", "date");
    }

    if (isWeekView) {
      cell.append(
        createElement(
          "span",
          "calendar-day-weekday",
          new Intl.DateTimeFormat("es-ES", { weekday: "short" }).format(day),
        ),
      );
    }

    cell.append(createElement("span", "calendar-day-number", day.getDate()));

    if (activity) {
      const markers = createElement("span", "calendar-markers");

      if (activity.has_workout) {
        markers.append(createElement("i", "legend-dot workout"));
      }
      if (activity.running_distance_km > 0) {
        markers.append(createElement("i", "legend-dot run"));
      }
      if (activity.is_rest_day) {
        markers.append(createElement("i", "legend-dot rest"));
      }
      if (activity.planned_workouts.some(
        (item) => item.status === "planned" && !item.is_overdue,
      )) {
        markers.append(createElement("i", "legend-dot planned"));
      }
      if (activity.planned_workouts.some((item) => item.is_overdue)) {
        markers.append(createElement("i", "legend-dot overdue"));
      }

      cell.append(markers);

      if (isWeekView && activity.planned_workouts.length > 0) {
        cell.append(buildDayPlans(activity.planned_workouts));
      }

      if (activity.steps > 0) {
        cell.append(
          createElement(
            "span",
            "calendar-day-steps",
            `${formatNumber(activity.steps, 0)} pasos`,
          ),
        );
      }

      cell.setAttribute(
        "aria-label",
        describeDay(value, activity),
      );
    }

    cells.push(cell);
  }

  elements.calendarGrid.replaceChildren(...cells);
}


// «🏃 Rodaje · 10 km» para las carreras; el nombre a secas para el gimnasio.
function describePlanName(plan) {
  if (plan.kind !== "run") {
    return plan.name;
  }

  const distance = plan.target_distance_km
    ? ` · ${formatNumber(plan.target_distance_km)} km`
    : "";

  return `🏃 ${plan.name}${distance}`;
}


// Acepta «45» (minutos), «45:30» (min:seg) y «1:05:30» (h:min:seg).
function parseDuration(text) {
  const parts = text.trim().split(":");

  if (
    parts.length > 3
    || parts.some((part) => !/^\d+$/.test(part))
  ) {
    return null;
  }

  const numbers = parts.map(Number);
  const seconds = parts.length === 1
    ? numbers[0] * 60
    : numbers.reduce((total, value) => total * 60 + value, 0);

  return seconds > 0 ? seconds : null;
}


function buildDayPlans(plans) {
  const list = createElement("span", "calendar-day-plans");

  for (const plan of plans.slice(0, MAX_PLANS_SHOWN_PER_DAY)) {
    const label = plan.is_overdue
      ? "Vencida"
      : (STATUS_LABELS[plan.status] ?? plan.status);
    const item = createElement(
      "span",
      `calendar-day-plan ${plan.is_overdue ? "overdue" : plan.status}`
        + (plan.kind === "run" ? " run" : ""),
    );
    const text = describePlanName(plan);

    item.textContent = text;
    item.title = `${text} · ${label}`;
    list.append(item);
  }

  const hidden = plans.length - MAX_PLANS_SHOWN_PER_DAY;

  if (hidden > 0) {
    list.append(createElement("span", "calendar-day-more", `+${hidden} más`));
  }

  return list;
}


function describeDay(value, activity) {
  const parts = [formatLongDate(value)];

  if (activity.steps > 0) parts.push(`${activity.steps} pasos`);
  if (activity.has_workout) parts.push("entrenamiento");
  if (activity.running_distance_km > 0) parts.push("running");
  if (activity.is_rest_day) parts.push("día de descanso");
  if (activity.planned_workouts.length > 0) {
    parts.push(`${activity.planned_workouts.length} sesiones planificadas`);
  }
  if (activity.planned_workouts.some((item) => item.is_overdue)) {
    parts.push("con sesiones vencidas");
  }

  return parts.join(", ");
}


function formatLongDate(value) {
  return new Intl.DateTimeFormat("es-ES", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(parseDate(value));
}


function summaryRow(label, value, href) {
  const row = createElement("div", "day-summary-row");
  row.append(createElement("span", "day-summary-label", label));

  if (href) {
    const link = createElement("a", "day-summary-value", value);
    link.href = href;
    row.append(link);
  } else {
    row.append(createElement("strong", "day-summary-value", value));
  }

  return row;
}


function renderDayDetail() {
  const activity = state.days.get(state.selectedDate);

  elements.dayTitle.textContent = formatLongDate(state.selectedDate);

  const rows = [
    summaryRow(
      "Pasos",
      activity ? formatNumber(activity.steps, 0) : "—",
      "/static/daily-steps/",
    ),
    summaryRow(
      "Entrenamientos",
      activity ? String(activity.workout_sessions) : "—",
      "/static/workouts/history.html",
    ),
    summaryRow(
      "Running",
      activity ? `${formatNumber(activity.running_distance_km)} km` : "—",
      "/static/runs/",
    ),
    summaryRow(
      "Sueño",
      activity?.sleep_minutes != null ? formatSleep(activity.sleep_minutes) : "—",
      "/static/recovery.html",
    ),
    summaryRow(
      "Día de descanso",
      activity?.is_rest_day ? "Sí" : "No",
    ),
  ];

  elements.daySummary.replaceChildren(...rows);
  renderPlannedList();
}


async function loadPlannedDetails() {
  // El calendario solo trae id, nombre y estado; el detalle completo
  // (notas, plantilla) viene del listado de planificadas del día.
  const query = new URLSearchParams({
    start_date: state.selectedDate,
    end_date: state.selectedDate,
  });

  return request(`/planned-workouts/?${query}`);
}


async function renderPlannedList() {
  const requestedDate = state.selectedDate;

  renderListLoading(elements.plannedList, "planned-list");

  let planned;

  try {
    planned = await loadPlannedDetails();
  } catch (error) {
    renderListError(
      elements.plannedList,
      "planned-list",
      error.message,
      renderPlannedList,
    );
    return;
  }

  // Si el usuario cambió de día mientras cargaba, esta respuesta ya no vale.
  if (requestedDate !== state.selectedDate) {
    return;
  }

  if (planned.length === 0) {
    elements.plannedList.className = "planned-list empty-state";
    elements.plannedList.textContent = "No hay sesiones planificadas este día.";
    return;
  }

  elements.plannedList.className = "planned-list";
  elements.plannedList.replaceChildren(...planned.map(buildPlannedCard));
}


function isPlannedOverdue(planned) {
  const activity = state.days.get(planned.scheduled_date);

  return Boolean(
    activity?.planned_workouts.find((item) => item.id === planned.id)
      ?.is_overdue,
  );
}


function buildPlannedCard(planned) {
  const card = createElement("article", `planned-card ${planned.status}`);
  const overdue = isPlannedOverdue(planned);

  const heading = createElement("div", "planned-card-heading");
  heading.append(
    createElement("strong", "planned-card-name", describePlanName(planned)),
    createElement(
      "span",
      `planned-status ${overdue ? "overdue" : planned.status}`,
      overdue ? "Vencida" : (STATUS_LABELS[planned.status] ?? planned.status),
    ),
  );
  card.append(heading);

  if (planned.notes) {
    card.append(createElement("p", "planned-card-notes", planned.notes));
  }

  const actions = createElement("div", "planned-card-actions");

  if (planned.status === "planned") {
    actions.append(
      planned.kind === "run"
        ? actionButton("Completar", "primary-button", async () => {
          card.append(buildRunCompletionForm(planned));
          actions.remove();
        })
        : actionButton("Completar", "primary-button", () =>
          completePlanned(planned),
        ),
      actionButton("Omitir", "secondary-button", () =>
        updatePlannedStatus(planned, "skipped"),
      ),
      actionButton("Eliminar", "danger-button", () => deletePlanned(planned)),
    );
  } else if (planned.status === "skipped") {
    actions.append(
      actionButton("Volver a planificar", "secondary-button", () =>
        updatePlannedStatus(planned, "planned"),
      ),
      actionButton("Eliminar", "danger-button", () => deletePlanned(planned)),
    );
  } else {
    const isRun = planned.kind === "run";
    const link = createElement(
      "a",
      "secondary-button",
      isRun ? "Ver en running" : "Ver en entrenamientos",
    );
    link.href = isRun ? "/static/runs/" : "/static/workouts/history.html";
    actions.append(link);
  }

  card.append(actions);

  return card;
}


function buildRunCompletionForm(planned) {
  const form = createElement("form", "planned-run-form");

  const distanceLabel = createElement("label", "", "Distancia (km)");
  const distance = createElement("input");
  distance.type = "number";
  distance.min = "0.1";
  distance.max = "1000";
  distance.step = "0.1";
  distance.required = true;
  distance.value = planned.target_distance_km ?? "";
  distanceLabel.append(distance);

  const durationLabel = createElement(
    "label",
    "",
    "Duración (min, mm:ss o h:mm:ss)",
  );
  const duration = createElement("input");
  duration.type = "text";
  duration.required = true;
  duration.placeholder = "Ej.: 52:30";
  duration.autocomplete = "off";
  durationLabel.append(duration);

  const buttons = createElement("div", "planned-card-actions");
  const save = createElement("button", "primary-button", "Guardar carrera");
  save.type = "submit";
  const cancel = createElement("button", "secondary-button", "Cancelar");
  cancel.type = "button";
  cancel.addEventListener("click", renderPlannedList);
  buttons.append(save, cancel);

  form.append(distanceLabel, durationLabel, buttons);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const seconds = parseDuration(duration.value);

    if (seconds === null) {
      showStatus("Escribe la duración como 45, 45:30 o 1:05:30.", "error");
      return;
    }

    save.disabled = true;

    try {
      await completePlannedRun(planned, Number(distance.value), seconds);
    } catch (error) {
      showStatus(error.message, "error");
      save.disabled = false;
    }
  });

  return form;
}


async function completePlannedRun(planned, distanceKm, durationSeconds) {
  await request(`/planned-workouts/${planned.id}/complete`, {
    method: "POST",
    body: JSON.stringify({
      completed_date: null,
      distance_km: distanceKm,
      duration_seconds: durationSeconds,
    }),
  });

  showStatus("Carrera completada y añadida a tu running.");
  await loadActivity();
}


function actionButton(label, className, handler) {
  const button = createElement("button", className, label);
  button.type = "button";
  button.addEventListener("click", async () => {
    button.disabled = true;

    try {
      await handler();
    } catch (error) {
      showStatus(error.message, "error");
      button.disabled = false;
    }
  });

  return button;
}


async function completePlanned(planned) {
  await request(`/planned-workouts/${planned.id}/complete`, {
    method: "POST",
    body: JSON.stringify({ completed_date: null }),
  });

  showStatus("Sesión completada y añadida a tus entrenamientos.");
  await loadActivity();
}


async function updatePlannedStatus(planned, status) {
  await request(`/planned-workouts/${planned.id}`, {
    method: "PUT",
    body: JSON.stringify({
      scheduled_date: planned.scheduled_date,
      target_distance_km: planned.target_distance_km,
      workout_template_id: planned.workout_template_id,
      name: planned.name,
      notes: planned.notes,
      status,
    }),
  });

  showStatus(
    status === "skipped" ? "Sesión omitida." : "Sesión planificada de nuevo.",
  );
  await loadActivity();
}


async function deletePlanned(planned) {
  if (!window.confirm(`¿Eliminar la sesión planificada "${planned.name}"?`)) {
    return;
  }

  await request(`/planned-workouts/${planned.id}`, { method: "DELETE" });

  showStatus("Sesión planificada eliminada.");
  await loadActivity();
}


async function handleCreatePlanned(event) {
  event.preventDefault();

  const form = event.currentTarget;
  const data = new FormData(form);
  const isRun = data.get("kind") === "run";
  const templateId = isRun ? null : data.get("workout_template_id");
  const distance = String(data.get("target_distance_km") || "").trim();
  const name = String(data.get("name") || "").trim();
  const notes = String(data.get("notes") || "").trim();

  if (!isRun && !templateId && !name) {
    showStatus("Elige una plantilla o escribe un nombre.", "error");
    return;
  }

  try {
    await request("/planned-workouts/", {
      method: "POST",
      body: JSON.stringify({
        scheduled_date: state.selectedDate,
        kind: isRun ? "run" : "workout",
        target_distance_km: isRun && distance ? Number(distance) : null,
        workout_template_id: templateId ? Number(templateId) : null,
        // Con plantilla, el nombre se toma de ella salvo que se escriba otro;
        // una carrera sin nombre se llama «Carrera».
        name: name || null,
        notes: notes || null,
      }),
    });

    form.reset();
    updatePlannedKindFields();
    showStatus(isRun ? "Carrera planificada." : "Sesión planificada.");
    await loadActivity();
  } catch (error) {
    showStatus(error.message, "error");
  }
}


function updatePlannedKindFields() {
  const isRun = elements.plannedKind.value === "run";

  elements.plannedTemplateLabel.hidden = isRun;
  elements.plannedDistanceLabel.hidden = !isRun;
  elements.plannedNameHint.textContent = isRun
    ? "si no, se llamará «Carrera»"
    : "si no usas plantilla";

  if (isRun) {
    elements.plannedTemplate.value = "";
  } else {
    elements.plannedDistance.value = "";
  }
}


function changePeriod(amount) {
  if (state.view === "week") {
    state.weekStart = addDays(state.weekStart, 7 * amount);
    // El día seleccionado se mueve a la misma posición de la semana nueva.
    state.selectedDate = formatDate(
      addDays(parseDate(state.selectedDate), 7 * amount),
    );
  } else {
    state.month = new Date(
      state.month.getFullYear(),
      state.month.getMonth() + amount,
      1,
    );
  }

  loadActivity();
}


function updateViewControls() {
  const isWeekView = state.view === "week";
  const unit = isWeekView ? "Semana" : "Mes";

  elements.viewMonthButton.setAttribute("aria-pressed", String(!isWeekView));
  elements.viewWeekButton.setAttribute("aria-pressed", String(isWeekView));
  elements.weekActions.hidden = !isWeekView;

  for (const [button, direction] of [
    [elements.previousMonthButton, "anterior"],
    [elements.nextMonthButton, "siguiente"],
  ]) {
    button.title = `${unit} ${direction}`;
    button.setAttribute("aria-label", `${unit} ${direction}`);
  }
}


function setView(view) {
  if (view === state.view) {
    return;
  }

  state.view = view;

  const selected = parseDate(state.selectedDate);

  if (view === "week") {
    state.weekStart = startOfWeek(selected);
  } else {
    state.month = startOfMonth(selected);
  }

  try {
    localStorage.setItem(VIEW_STORAGE_KEY, view);
  } catch {
    // Sin almacenamiento, la vista simplemente no se recuerda.
  }

  updateViewControls();
  loadActivity();
}


async function copyWeek(sourceStart, targetStart, { goToTarget }) {
  const result = await request("/planned-workouts/copy-week", {
    method: "POST",
    body: JSON.stringify({
      source_start: formatDate(sourceStart),
      target_start: formatDate(targetStart),
    }),
  });

  if (result.copied === 0 && result.skipped === 0) {
    showStatus("No hay sesiones planificadas en esa semana para copiar.", "error");
    return;
  }

  const parts = [
    `${result.copied} ${result.copied === 1 ? "sesión copiada" : "sesiones copiadas"}`,
  ];

  if (result.skipped > 0) {
    parts.push(
      `${result.skipped} ya ${result.skipped === 1 ? "existía" : "existían"}`,
    );
  }

  showStatus(`${parts.join(", ")}.`);

  if (goToTarget) {
    const shift = Math.round((targetStart - state.weekStart) / 86400000);

    state.weekStart = targetStart;
    state.selectedDate = formatDate(
      addDays(parseDate(state.selectedDate), shift),
    );
  }

  await loadActivity();
}


function selectDate(value) {
  state.selectedDate = value;

  const selected = parseDate(value);

  // Pulsar un día de otro mes lleva a ese mes (en la vista semanal todos los
  // días visibles son de la semana actual y no hay nada que cambiar).
  if (
    state.view === "month"
    && (
      selected.getMonth() !== state.month.getMonth()
      || selected.getFullYear() !== state.month.getFullYear()
    )
  ) {
    state.month = startOfMonth(selected);
    loadActivity();
    return;
  }

  renderCalendar();
  renderDayDetail();
}


function configureEventListeners() {
  elements.previousMonthButton.addEventListener("click", () => changePeriod(-1));
  elements.nextMonthButton.addEventListener("click", () => changePeriod(1));
  elements.todayButton.addEventListener("click", () => {
    state.month = startOfMonth(new Date());
    state.weekStart = startOfWeek(new Date());
    state.selectedDate = formatDate(new Date());
    loadActivity();
  });

  elements.viewMonthButton.addEventListener("click", () => setView("month"));
  elements.viewWeekButton.addEventListener("click", () => setView("week"));

  elements.copyFromPreviousButton.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;

    try {
      await copyWeek(addDays(state.weekStart, -7), state.weekStart, {
        goToTarget: false,
      });
    } catch (error) {
      showStatus(error.message, "error");
    } finally {
      button.disabled = false;
    }
  });

  elements.copyToNextButton.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;

    try {
      await copyWeek(state.weekStart, addDays(state.weekStart, 7), {
        goToTarget: true,
      });
    } catch (error) {
      showStatus(error.message, "error");
    } finally {
      button.disabled = false;
    }
  });

  elements.calendarGrid.addEventListener("click", (event) => {
    const cell = event.target.closest(".calendar-day");

    if (cell) {
      selectDate(cell.dataset.date);
    }
  });

  elements.plannedForm.addEventListener("submit", handleCreatePlanned);
  elements.plannedKind.addEventListener("change", updatePlannedKindFields);
}


async function initializeApp() {
  configureEventListeners();
  updateViewControls();
  await Promise.all([loadTemplates(), loadActivity()]);
}


initializeApp();
