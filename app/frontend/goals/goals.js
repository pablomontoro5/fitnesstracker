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
  const currentFormatted = formatValue(
    current,
    config.decimalPlaces
  );
  const targetFormatted = formatValue(
    goal.target_value,
    config.decimalPlaces
  );

  input.value = goal.target_value;
  currentValue.textContent = `${currentFormatted}${config.currentSuffix}`;
  targetLabel.textContent = (
    `${config.targetPrefix}${targetFormatted}${config.targetSuffix}`
  );
  progressTrack.setAttribute("aria-valuenow", String(percentage));
  progressBar.style.width = `${percentage}%`;
  progressText.textContent = `${formatValue(
    percentage,
    1
  )}% completado`;
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
  const targetValue = Number(input.value);

  if (!Number.isFinite(targetValue) || targetValue <= 0) {
    showStatus("Introduce un objetivo mayor que cero.", "error");
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