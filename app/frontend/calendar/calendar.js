const WEEKDAYS_IN_GRID = 7;

const state = {
  // Primer día del mes que se está viendo.
  month: startOfMonth(new Date()),
  selectedDate: formatDate(new Date()),
  days: new Map(),
  templates: [],
};


const elements = {
  statusMessage: document.querySelector("#status-message"),
  monthTitle: document.querySelector("#month-title"),
  previousMonthButton: document.querySelector("#previous-month-button"),
  nextMonthButton: document.querySelector("#next-month-button"),
  todayButton: document.querySelector("#today-button"),
  calendarError: document.querySelector("#calendar-error"),
  calendarGrid: document.querySelector("#calendar-grid"),
  dayTitle: document.querySelector("#day-title"),
  daySummary: document.querySelector("#day-summary"),
  plannedList: document.querySelector("#planned-list"),
  plannedForm: document.querySelector("#planned-form"),
  plannedTemplate: document.querySelector("#planned-template"),
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
  });

  renderListLoading(
    elements.calendarError,
    "calendar-error",
    "Cargando calendario…",
  );

  try {
    const activity = await request(`/calendar/activity?${query}`);

    state.days = new Map(activity.days.map((day) => [day.date, day]));
    elements.calendarError.className = "empty-state hidden";
    elements.calendarError.replaceChildren();
  } catch (error) {
    state.days = new Map();
    elements.calendarError.classList.remove("hidden");
    renderListError(
      elements.calendarError,
      "calendar-error",
      error.message,
      loadActivity,
    );
  }

  renderCalendar();
  renderDayDetail();
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

  const monthName = new Intl.DateTimeFormat("es-ES", {
    month: "long",
    year: "numeric",
  }).format(state.month);

  // "octubre de 2026" -> "Octubre de 2026"
  elements.monthTitle.textContent = (
    monthName.charAt(0).toUpperCase() + monthName.slice(1)
  );

  for (let day = start; day <= end; day = addDays(day, 1)) {
    const value = formatDate(day);
    const activity = state.days.get(value);
    const isOutsideMonth = day.getMonth() !== state.month.getMonth();

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
      if (activity.planned_workouts.some((item) => item.status === "planned")) {
        markers.append(createElement("i", "legend-dot planned"));
      }

      cell.append(markers);

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


function describeDay(value, activity) {
  const parts = [formatLongDate(value)];

  if (activity.steps > 0) parts.push(`${activity.steps} pasos`);
  if (activity.has_workout) parts.push("entrenamiento");
  if (activity.running_distance_km > 0) parts.push("running");
  if (activity.is_rest_day) parts.push("día de descanso");
  if (activity.planned_workouts.length > 0) {
    parts.push(`${activity.planned_workouts.length} sesiones planificadas`);
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


function buildPlannedCard(planned) {
  const card = createElement("article", `planned-card ${planned.status}`);

  const heading = createElement("div", "planned-card-heading");
  heading.append(
    createElement("strong", "planned-card-name", planned.name),
    createElement(
      "span",
      `planned-status ${planned.status}`,
      STATUS_LABELS[planned.status] ?? planned.status,
    ),
  );
  card.append(heading);

  if (planned.notes) {
    card.append(createElement("p", "planned-card-notes", planned.notes));
  }

  const actions = createElement("div", "planned-card-actions");

  if (planned.status === "planned") {
    actions.append(
      actionButton("Completar", "primary-button", () =>
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
    const link = createElement(
      "a",
      "secondary-button",
      "Ver en entrenamientos",
    );
    link.href = "/static/workouts/history.html";
    actions.append(link);
  }

  card.append(actions);

  return card;
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
  const templateId = data.get("workout_template_id");
  const name = String(data.get("name") || "").trim();
  const notes = String(data.get("notes") || "").trim();

  if (!templateId && !name) {
    showStatus("Elige una plantilla o escribe un nombre.", "error");
    return;
  }

  try {
    await request("/planned-workouts/", {
      method: "POST",
      body: JSON.stringify({
        scheduled_date: state.selectedDate,
        workout_template_id: templateId ? Number(templateId) : null,
        // Con plantilla, el nombre se toma de ella salvo que se escriba otro.
        name: name || null,
        notes: notes || null,
      }),
    });

    form.reset();
    showStatus("Sesión planificada.");
    await loadActivity();
  } catch (error) {
    showStatus(error.message, "error");
  }
}


function changeMonth(amount) {
  state.month = new Date(
    state.month.getFullYear(),
    state.month.getMonth() + amount,
    1,
  );

  loadActivity();
}


function selectDate(value) {
  state.selectedDate = value;

  const selected = parseDate(value);

  // Pulsar un día de otro mes lleva a ese mes.
  if (
    selected.getMonth() !== state.month.getMonth()
    || selected.getFullYear() !== state.month.getFullYear()
  ) {
    state.month = startOfMonth(selected);
    loadActivity();
    return;
  }

  renderCalendar();
  renderDayDetail();
}


function configureEventListeners() {
  elements.previousMonthButton.addEventListener("click", () => changeMonth(-1));
  elements.nextMonthButton.addEventListener("click", () => changeMonth(1));
  elements.todayButton.addEventListener("click", () => {
    state.month = startOfMonth(new Date());
    state.selectedDate = formatDate(new Date());
    loadActivity();
  });

  elements.calendarGrid.addEventListener("click", (event) => {
    const cell = event.target.closest(".calendar-day");

    if (cell) {
      selectDate(cell.dataset.date);
    }
  });

  elements.plannedForm.addEventListener("submit", handleCreatePlanned);
}


async function initializeApp() {
  configureEventListeners();
  await Promise.all([loadTemplates(), loadActivity()]);
}


initializeApp();
