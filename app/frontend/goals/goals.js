const GOAL_CONFIG = {
  daily_steps: {
    currentSuffix: " pasos",
    targetSuffix: " pasos",
    targetPrefix: "Objetivo: ",
    decimalPlaces: 0,
  },
  weekly_workouts: {
    currentSuffix: " sesiones",
    targetSuffix: " sesiones",
    targetPrefix: "Objetivo semanal: ",
    decimalPlaces: 0,
  },
  weekly_running_km: {
    currentSuffix: " km",
    targetSuffix: " km",
    targetPrefix: "Objetivo semanal: ",
    decimalPlaces: 1,
  },
  daily_calories: {
    currentSuffix: " kcal",
    targetSuffix: " kcal",
    targetPrefix: "Objetivo diario: ",
    decimalPlaces: 0,
  },
  daily_protein_g: {
    currentSuffix: " g",
    targetSuffix: " g",
    targetPrefix: "Objetivo diario: ",
    decimalPlaces: 1,
  },
  daily_carbs_g: {
    currentSuffix: " g",
    targetSuffix: " g",
    targetPrefix: "Objetivo diario: ",
    decimalPlaces: 1,
  },
  daily_fat_g: {
    currentSuffix: " g",
    targetSuffix: " g",
    targetPrefix: "Objetivo diario: ",
    decimalPlaces: 1,
  },

  daily_sleep_minutes: {
    currentSuffix: "",
    targetSuffix: "",
    targetPrefix: "Objetivo diario: ",
    decimalPlaces: 0,
    valueType: "sleep",
  },
  weekly_rest_days: {
    currentSuffix: " días",
    targetSuffix: " días",
    targetPrefix: "Objetivo semanal: ",
    decimalPlaces: 0,
  },
};

const BODY_GOAL_CONFIG = {
  weight_kg: {
    label: "Peso",
    unit: "kg",
    decimalPlaces: 1,
    icon: "⚖️",
    max: 500,
  },
  body_fat_percentage: {
    label: "Porcentaje graso",
    unit: "%",
    decimalPlaces: 1,
    icon: "📊",
    max: 99.99,
  },
  waist_cm: {
    label: "Cintura",
    unit: "cm",
    decimalPlaces: 1,
    icon: "📏",
    max: 300,
  },
  hip_cm: {
    label: "Cadera",
    unit: "cm",
    decimalPlaces: 1,
    icon: "📏",
    max: 300,
  },
  chest_cm: {
    label: "Pecho",
    unit: "cm",
    decimalPlaces: 1,
    icon: "📏",
    max: 300,
  },
  arm_cm: {
    label: "Brazo",
    unit: "cm",
    decimalPlaces: 1,
    icon: "💪",
    max: 200,
  },
  thigh_cm: {
    label: "Muslo",
    unit: "cm",
    decimalPlaces: 1,
    icon: "🦵",
    max: 300,
  },
};

const statusMessage = document.querySelector("#goals-status");
const goalCards = [...document.querySelectorAll("[data-goal-type]")];

function showStatus(message, type) {
  statusMessage.textContent = message;
  statusMessage.className = `status-message ${type}`;
}

function clearStatus() {
  statusMessage.textContent = "";
  statusMessage.className = "status-message";
}

function formatValue(value, decimalPlaces) {
  return new Intl.NumberFormat("es-ES", {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimalPlaces,
  }).format(value);
}

function formatSleepMinutes(value) {
  const totalMinutes = Math.round(value);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours === 0) {
    return `${minutes} min`;
  }

  if (minutes === 0) {
    return `${hours} h`;
  }

  return `${hours} h ${minutes} min`;
}


function minutesToHoursInputValue(minutes) {
  return (minutes / 60).toFixed(2).replace(/\.?0+$/, "");
}


function getDisplayValue(value, config) {
  if (config.valueType === "sleep") {
    return formatSleepMinutes(value);
  }

  return `${formatValue(value, config.decimalPlaces)}${config.currentSuffix}`;
}


function getTargetLabelValue(value, config) {
  if (config.valueType === "sleep") {
    return formatSleepMinutes(value);
  }

  return `${formatValue(value, config.decimalPlaces)}${config.targetSuffix}`;
}

async function readErrorMessage(response) {
  try {
    const payload = await response.json();
    return payload.detail || "No se pudo completar la operación.";
  } catch {
    return "No se pudo completar la operación.";
  }
}

function getGoalCard(goalType) {
  return document.querySelector(
    `[data-goal-type="${goalType}"]`
  );
}

function renderGoal(goalType, goal, progress) {
  const card = getGoalCard(goalType);
  const config = GOAL_CONFIG[goalType];
  const input = card.querySelector("[data-target-input]");
  const currentValue = card.querySelector("[data-current-value]");
  const targetLabel = card.querySelector("[data-target-label]");
  const progressTrack = card.querySelector("[role='progressbar']");
  const progressBar = card.querySelector("[data-progress-bar]");
  const progressText = card.querySelector("[data-progress-text]");
  const completedMessage = card.querySelector("[data-completed-message]");
  const deleteButton = card.querySelector("[data-delete-button]");

  if (!goal) {
    input.value = "";
    currentValue.textContent = "Sin objetivo";
    targetLabel.textContent = "";
    progressTrack.setAttribute("aria-valuenow", "0");
    progressBar.style.width = "0%";
    progressText.textContent = "Configura un objetivo para empezar.";
    completedMessage.classList.add("hidden");
    deleteButton.classList.add("hidden");
    card.classList.remove("completed");

    return;
  }

  const hasProgress = Boolean(progress);
  const isNutritionGoal = goalType.startsWith("daily_")
    && [
      "daily_calories",
      "daily_protein_g",
      "daily_carbs_g",
      "daily_fat_g",
    ].includes(goalType);
  const current = progress?.current_value ?? 0;
  const percentage = progress?.progress_percentage ?? 0;
  const isCompleted = progress?.is_completed ?? false;
  const currentFormatted = isNutritionGoal && !hasProgress
    ? "Consulta Nutrición"
    : getDisplayValue(current, config);
  const targetFormatted = getTargetLabelValue(
    goal.target_value,
    config,
  );

  input.value = config.valueType === "sleep"
    ? minutesToHoursInputValue(goal.target_value)
    : goal.target_value;

  currentValue.textContent = currentFormatted;
  targetLabel.textContent = `${config.targetPrefix}${targetFormatted}`;
  progressTrack.setAttribute("aria-valuenow", String(percentage));
  progressBar.style.width = `${percentage}%`;
  progressText.textContent = progress
    ? `${formatValue(percentage, 1)}% completado`
    : "Consulta el progreso en la pantalla de Nutrición.";
  completedMessage.classList.toggle("hidden", !isCompleted);
  deleteButton.classList.remove("hidden");
  card.classList.toggle("completed", isCompleted);
}

async function loadGoals() {
  clearStatus();

  try {
    const [goalsResponse, progressResponse] = await Promise.all([
      apiFetch("/goals/"),
      apiFetch("/goals/progress"),
    ]);

    if (!goalsResponse.ok) {
      throw new Error(await readErrorMessage(goalsResponse));
    }

    if (!progressResponse.ok) {
      throw new Error(await readErrorMessage(progressResponse));
    }

    const goals = await goalsResponse.json();
    const progressItems = await progressResponse.json();
    const goalsByType = new Map(
      goals.map((goal) => [goal.goal_type, goal])
    );
    const progressByType = new Map(
      progressItems.map((progress) => [progress.goal_type, progress])
    );

    for (const goalType of Object.keys(GOAL_CONFIG)) {
      renderGoal(
        goalType,
        goalsByType.get(goalType),
        progressByType.get(goalType)
      );
    }
  } catch (error) {
    showStatus(error.message, "error");
  }
}

async function saveGoal(event) {
  event.preventDefault();
  clearStatus();

  const form = event.currentTarget;
  const card = form.closest("[data-goal-type]");
  const goalType = card.dataset.goalType;
  const input = card.querySelector("[data-target-input]");
  const saveButton = card.querySelector("[data-save-button]");
  const inputValue = Number(input.value);
  const config = GOAL_CONFIG[goalType];
  const targetValue = config.valueType === "sleep"
    ? Math.round(inputValue * 60)
    : inputValue;

  if (!Number.isFinite(inputValue) || inputValue <= 0) {
    showStatus("Introduce un objetivo mayor que cero.", "error");
    input.focus();
    return;
  }

  if (goalType === "daily_sleep_minutes" && inputValue > 24) {
    showStatus(
      "El objetivo de sueño no puede superar 24 horas.",
      "error",
    );
    input.focus();
    return;
  }

  if (
    goalType === "weekly_rest_days" &&
    (!Number.isInteger(inputValue) || inputValue > 7)
  ) {
    showStatus(
      "El objetivo de días de descanso debe ser un número entero entre 1 y 7.",
      "error",
    );
    input.focus();
    return;
  }

  saveButton.disabled = true;

  try {
    const response = await apiFetch(`/goals/${goalType}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        target_value: targetValue,
      }),
    });

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    showStatus("Objetivo guardado correctamente.", "success");
    await loadGoals();
  } catch (error) {
    showStatus(error.message, "error");
  } finally {
    saveButton.disabled = false;
  }
}

async function deleteGoal(event) {
  const button = event.currentTarget;
  const card = button.closest("[data-goal-type]");
  const goalType = card.dataset.goalType;

  const confirmed = window.confirm(
    "¿Quieres eliminar este objetivo? Se conservarán tus registros de actividad."
  );

  if (!confirmed) {
    return;
  }

  clearStatus();
  button.disabled = true;

  try {
    const response = await apiFetch(`/goals/${goalType}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    showStatus("Objetivo eliminado correctamente.", "success");
    await loadGoals();
  } catch (error) {
    showStatus(error.message, "error");
  } finally {
    button.disabled = false;
  }
}

function configureEventListeners() {
  for (const card of goalCards) {
    card
      .querySelector("[data-goal-form]")
      .addEventListener("submit", saveGoal);

    card
      .querySelector("[data-delete-button]")
      .addEventListener("click", deleteGoal);
  }
}
function formatBodyGoalValue(metricType, value) {
  const config = BODY_GOAL_CONFIG[metricType];

  return `${formatValue(value, config.decimalPlaces)} ${config.unit}`;
}

function getBodyGoalDirectionLabel(direction) {
  const labels = {
    decrease: "Reducir",
    increase: "Aumentar",
    maintain: "Mantener",
  };

  return labels[direction];
}

function createBodyGoalCard(goal, progress) {
  const config = BODY_GOAL_CONFIG[goal.metric_type];
  const card = document.createElement("article");

  card.className = "panel goal-card";
  card.dataset.bodyGoalMetricType = goal.metric_type;

  const heading = document.createElement("div");
  heading.className = "goal-card-heading";

  const headingText = document.createElement("div");
  const eyebrow = document.createElement("p");
  eyebrow.className = "eyebrow";
  eyebrow.textContent = getBodyGoalDirectionLabel(goal.direction);

  const title = document.createElement("h2");
  title.textContent = config.label;

  headingText.append(eyebrow, title);

  const icon = document.createElement("span");
  icon.className = "goal-icon";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = config.icon;

  heading.append(headingText, icon);

  const description = document.createElement("p");
  description.className = "goal-description";
  description.textContent = `Objetivo: ${formatBodyGoalValue(
    goal.metric_type,
    goal.target_value,
  )}.`;

  const summary = document.createElement("div");
  summary.className = "goal-progress-summary";

  const current = document.createElement("strong");
  const target = document.createElement("span");

  if (progress.current_value === null) {
    current.textContent = "Sin medición";
    target.textContent = `Objetivo: ${formatBodyGoalValue(
      goal.metric_type,
      goal.target_value,
    )}`;
  } else {
    current.textContent = formatBodyGoalValue(
      goal.metric_type,
      progress.current_value,
    );
    target.textContent = `Objetivo: ${formatBodyGoalValue(
      goal.metric_type,
      goal.target_value,
    )}`;
  }

  summary.append(current, target);

  const track = document.createElement("div");
  track.className = "goal-progress-track";
  track.setAttribute("role", "progressbar");
  track.setAttribute("aria-valuemin", "0");
  track.setAttribute("aria-valuemax", "100");

  const percentage = progress.progress_percentage ?? 0;
  track.setAttribute("aria-valuenow", String(percentage));

  const bar = document.createElement("span");
  bar.className = "goal-progress-bar";
  bar.style.width = `${percentage}%`;
  track.append(bar);

  const progressText = document.createElement("p");
  progressText.className = "goal-progress-text";

if (progress.current_value === null) {
  progressText.textContent = (
    "Registra una medición corporal para calcular tu progreso."
  );
} else if (progress.is_completed) {
  progressText.textContent = "Has alcanzado este objetivo.";
} else if (progress.progress_percentage === null) {
  progressText.textContent = (
    `Distancia al objetivo: ${formatBodyGoalValue(
      goal.metric_type,
      progress.remaining_value,
    )}.`
  );
} else {
  progressText.textContent = `${formatValue(
    progress.progress_percentage,
    1,
  )}% completado · faltan ${formatBodyGoalValue(
    goal.metric_type,
    progress.remaining_value,
  )}.`;
}

  const completed = document.createElement("p");
  completed.className = "goal-completed-message";
  completed.textContent = "✓ Objetivo completado";
  completed.classList.toggle("hidden", !progress.is_completed);

  const baseline = document.createElement("p");
  baseline.className = "goal-baseline-help";
  baseline.textContent = goal.start_value === null
    ? "Aún no hay una línea base disponible."
    : `Inicio: ${formatBodyGoalValue(
      goal.metric_type,
      goal.start_value,
    )}.`;

  const actions = document.createElement("div");
  actions.className = "goal-actions";

  const deleteButton = document.createElement("button");
  deleteButton.className = "danger-button";
  deleteButton.type = "button";
  deleteButton.textContent = "Eliminar";
  deleteButton.addEventListener("click", () => {
    deleteBodyCompositionGoal(goal.metric_type, deleteButton);
  });

  actions.append(deleteButton);

  card.classList.toggle("completed", progress.is_completed);
  card.append(
    heading,
    description,
    summary,
    track,
    progressText,
    completed,
    baseline,
    actions,
  );

  return card;
}

const bodyGoalForm = document.querySelector("#body-goal-form");
const bodyGoalMetricTypeInput = document.querySelector(
  "#body-goal-metric-type",
);
const bodyGoalDirectionInput = document.querySelector(
  "#body-goal-direction",
);
const bodyGoalTargetValueInput = document.querySelector(
  "#body-goal-target-value",
);
const bodyGoalStartValueInput = document.querySelector(
  "#body-goal-start-value",
);
const bodyGoalSaveButton = document.querySelector(
  "#body-goal-save-button",
);
const bodyGoalsGrid = document.querySelector(
  "#body-composition-goals-grid",
);
const bodyGoalsEmptyState = document.querySelector(
  "#body-composition-goals-empty",
);

async function loadBodyCompositionGoals() {
  const [goalsResponse, progressResponse] = await Promise.all([
    apiFetch("/goals/body-composition"),
    apiFetch("/goals/body-composition/progress"),
  ]);

  if (!goalsResponse.ok) {
    throw new Error(await readErrorMessage(goalsResponse));
  }

  if (!progressResponse.ok) {
    throw new Error(await readErrorMessage(progressResponse));
  }

  const goals = await goalsResponse.json();
  const progressItems = await progressResponse.json();
  const progressByMetric = new Map(
    progressItems.map((item) => [item.metric_type, item]),
  );

  bodyGoalsGrid.replaceChildren();

  for (const goal of goals) {
    const progress = progressByMetric.get(goal.metric_type);

    if (progress) {
      bodyGoalsGrid.append(createBodyGoalCard(goal, progress));
    }
  }

  bodyGoalsEmptyState.classList.toggle("hidden", goals.length > 0);
  bodyGoalsGrid.classList.toggle("hidden", goals.length === 0);
}

async function saveBodyCompositionGoal(event) {
  event.preventDefault();
  clearStatus();

  const metricType = bodyGoalMetricTypeInput.value;
  const direction = bodyGoalDirectionInput.value;
  const targetValue = Number(bodyGoalTargetValueInput.value);
  const startValueText = bodyGoalStartValueInput.value.trim();
  const startValue = startValueText === "" ? null : Number(startValueText);
  const metricConfig = BODY_GOAL_CONFIG[metricType];

  if (!Number.isFinite(targetValue) || targetValue <= 0) {
    showStatus("Introduce un objetivo corporal mayor que cero.", "error");
    bodyGoalTargetValueInput.focus();
    return;
  }

  if (targetValue > metricConfig.max) {
    showStatus(
      `El objetivo de ${metricConfig.label.toLowerCase()} no puede superar ${metricConfig.max}.`,
      "error",
    );
    bodyGoalTargetValueInput.focus();
    return;
  }

  if (
    startValue !== null
    && (!Number.isFinite(startValue) || startValue <= 0)
  ) {
    if (startValue !== null && startValue > metricConfig.max) {
      showStatus(
        `El valor inicial de ${metricConfig.label.toLowerCase()} no puede superar ${metricConfig.max}.`,
        "error",
      );
      bodyGoalStartValueInput.focus();
      return;
    }
        showStatus(
      "El valor inicial debe ser un número mayor que cero.",
      "error",
    );
    bodyGoalStartValueInput.focus();
    return;
  }

  bodyGoalSaveButton.disabled = true;

  try {
    const response = await apiFetch(
      `/goals/body-composition/${metricType}`,
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          target_value: targetValue,
          direction,
          start_value: startValue,
        }),
      },
    );

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    bodyGoalForm.reset();
    showStatus("Objetivo corporal guardado correctamente.", "success");
    await loadBodyCompositionGoals();
  } catch (error) {
    showStatus(error.message, "error");
  } finally {
    bodyGoalSaveButton.disabled = false;
  }
}

async function deleteBodyCompositionGoal(metricType, button) {
  const config = BODY_GOAL_CONFIG[metricType];
  const confirmed = window.confirm(
    `¿Quieres eliminar tu objetivo de ${config.label.toLowerCase()}? Tus mediciones se conservarán.`,
  );

  if (!confirmed) {
    return;
  }

  clearStatus();
  button.disabled = true;

  try {
    const response = await apiFetch(
      `/goals/body-composition/${metricType}`,
      { method: "DELETE" },
    );

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    showStatus("Objetivo corporal eliminado correctamente.", "success");
    await loadBodyCompositionGoals();
  } catch (error) {
    showStatus(error.message, "error");
  } finally {
    button.disabled = false;
  }
}

configureEventListeners();

bodyGoalForm.addEventListener("submit", saveBodyCompositionGoal);

Promise.all([
  loadGoals(),
  loadBodyCompositionGoals(),
]).catch((error) => {
  showStatus(error.message, "error");
});