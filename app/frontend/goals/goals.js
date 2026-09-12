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

  const current = progress?.current_value ?? 0;
  const percentage = progress?.progress_percentage ?? 0;
  const isCompleted = progress?.is_completed ?? false;
  const currentFormatted = getDisplayValue(current, config);
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
      fetch("/goals/"),
      fetch("/goals/progress"),
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
    const response = await fetch(`/goals/${goalType}`, {
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
    const response = await fetch(`/goals/${goalType}`, {
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

configureEventListeners();
loadGoals();