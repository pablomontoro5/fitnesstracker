const state = {
  nutritionDays: [],
  selectedDay: null,
  meals: [],
  selectedMeal: null,
  foods: [],
};

const nutritionGoalConfig = {
  calories: {
    suffix: " kcal",
    decimals: 0,
  },
  protein_g: {
    suffix: " g",
    decimals: 1,
  },
  carbs_g: {
    suffix: " g",
    decimals: 1,
  },
  fat_g: {
    suffix: " g",
    decimals: 1,
  },
};

const elements = {
  statusMessage: document.querySelector("#status-message"),

  nutritionDayForm: document.querySelector("#nutrition-day-form"),
  nutritionDayDate: document.querySelector("#nutrition-day-date"),
  nutritionDayNotes: document.querySelector("#nutrition-day-notes"),
  refreshNutritionDaysButton: document.querySelector(
    "#refresh-nutrition-days-button",
  ),
  nutritionDayCount: document.querySelector("#nutrition-day-count"),
  nutritionDaysList: document.querySelector("#nutrition-days-list"),
  nutritionDayTemplate: document.querySelector("#nutrition-day-template"),

  nutritionContent: document.querySelector("#nutrition-content"),
  selectedDayTitle: document.querySelector("#selected-day-title"),

  totalCalories: document.querySelector("#total-calories"),
  totalProtein: document.querySelector("#total-protein"),
  totalCarbs: document.querySelector("#total-carbs"),
  totalFat: document.querySelector("#total-fat"),

  nutritionGoalCards: [
    ...document.querySelectorAll("[data-nutrition-goal]"),
  ],

  nutritionMealForm: document.querySelector("#nutrition-meal-form"),
  nutritionMealName: document.querySelector("#nutrition-meal-name"),
  nutritionMealPosition: document.querySelector("#nutrition-meal-position"),
  nutritionMealsList: document.querySelector("#nutrition-meals-list"),
  nutritionMealTemplate: document.querySelector("#nutrition-meal-template"),

  selectedMealTitle: document.querySelector("#selected-meal-title"),
  deleteMealButton: document.querySelector("#delete-meal-button"),
  nutritionFoodEmptyState: document.querySelector(
    "#nutrition-food-empty-state",
  ),
  nutritionFoodContent: document.querySelector("#nutrition-food-content"),

  nutritionFoodForm: document.querySelector("#nutrition-food-form"),
  nutritionFoodName: document.querySelector("#nutrition-food-name"),
  nutritionFoodQuantity: document.querySelector("#nutrition-food-quantity"),
  nutritionFoodCalories: document.querySelector("#nutrition-food-calories"),
  nutritionFoodProtein: document.querySelector("#nutrition-food-protein"),
  nutritionFoodCarbs: document.querySelector("#nutrition-food-carbs"),
  nutritionFoodFat: document.querySelector("#nutrition-food-fat"),
  nutritionFoodPosition: document.querySelector("#nutrition-food-position"),
  nutritionFoodNotes: document.querySelector("#nutrition-food-notes"),
  nutritionFoodCount: document.querySelector("#nutrition-food-count"),
  nutritionFoodsList: document.querySelector("#nutrition-foods-list"),
  nutritionFoodTemplate: document.querySelector("#nutrition-food-template"),
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


function formatNumber(value, maximumFractionDigits = 2) {
  return new Intl.NumberFormat("es-ES", {
    maximumFractionDigits,
  }).format(value);
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


function setListEmpty(element, className, message) {
  element.className = `${className} empty-state`;
  element.textContent = message;
}


function calculateTotals(foods) {
  return foods.reduce(
    (totals, food) => ({
      calories: totals.calories + food.calories,
      protein_g: totals.protein_g + food.protein_g,
      carbs_g: totals.carbs_g + food.carbs_g,
      fat_g: totals.fat_g + food.fat_g,
    }),
    {
      calories: 0,
      protein_g: 0,
      carbs_g: 0,
      fat_g: 0,
    },
  );
}


function renderTotals() {
  const totals = calculateTotals(state.foods);

  elements.totalCalories.textContent =
    `${formatNumber(totals.calories)} kcal`;
  elements.totalProtein.textContent =
    `${formatNumber(totals.protein_g)} g`;
  elements.totalCarbs.textContent =
    `${formatNumber(totals.carbs_g)} g`;
  elements.totalFat.textContent =
    `${formatNumber(totals.fat_g)} g`;
}

function getNutritionGoalCard(goalKey) {
  return elements.nutritionGoalCards.find(
    (card) => card.dataset.nutritionGoal === goalKey,
  );
}


function renderNutritionGoalProgress(progress) {
  for (const [goalKey, config] of Object.entries(nutritionGoalConfig)) {
    const card = getNutritionGoalCard(goalKey);
    const item = progress[goalKey];
    const currentElement = card.querySelector("[data-nutrition-current]");
    const progressTrack = card.querySelector("[role='progressbar']");
    const progressBar = card.querySelector(
      "[data-nutrition-progress-bar]",
    );
    const progressText = card.querySelector(
      "[data-nutrition-progress-text]",
    );

    currentElement.textContent =
      `${formatNumber(item.current_value, config.decimals)}${config.suffix}`;

    if (item.target_value === null) {
      progressTrack.setAttribute("aria-valuenow", "0");
      progressBar.style.width = "0%";
      progressText.textContent =
        "Configura un objetivo en la pantalla de Objetivos.";
      card.classList.remove("completed", "exceeded");
      continue;
    }

    const displayPercentage = Math.min(
      item.progress_percentage,
      100,
    );

    progressTrack.setAttribute(
      "aria-valuenow",
      String(item.progress_percentage),
    );
    progressBar.style.width = `${displayPercentage}%`;

    const targetText =
      `${formatNumber(item.current_value, config.decimals)}${config.suffix} ` +
      `de ${formatNumber(item.target_value, config.decimals)}${config.suffix}`;

    if (item.is_completed) {
      const exceededValue = Math.abs(item.remaining_value);

      progressText.textContent = exceededValue === 0
        ? `Objetivo alcanzado · ${targetText}`
        : `Objetivo superado por ${formatNumber(
            exceededValue,
            config.decimals,
          )}${config.suffix} · ${targetText}`;
    } else {
      progressText.textContent =
        `Faltan ${formatNumber(
          item.remaining_value,
          config.decimals,
        )}${config.suffix} · ${targetText}`;
    }

    card.classList.toggle("completed", item.is_completed);
    card.classList.toggle(
      "exceeded",
      item.is_completed && item.remaining_value < 0,
    );
  }
}


async function loadNutritionGoalProgress(targetDate) {
  try {
    const progress = await request(
      `/goals/nutrition-progress?target_date=${encodeURIComponent(
        targetDate,
      )}`,
    );

    renderNutritionGoalProgress(progress);
  } catch (error) {
    showStatus(error.message, "error");
  }
}

function resetSelectedMeal() {
  state.selectedMeal = null;
  state.foods = [];

  elements.selectedMealTitle.textContent = "Selecciona una comida";
  elements.deleteMealButton.classList.add("hidden");
  elements.nutritionFoodEmptyState.classList.remove("hidden");
  elements.nutritionFoodContent.classList.add("hidden");
  elements.nutritionFoodCount.textContent = "0";

  renderTotals();
}


function resetSelectedDay() {
  state.selectedDay = null;
  state.meals = [];
  resetSelectedMeal();

  elements.nutritionContent.classList.add("hidden");
  elements.selectedDayTitle.textContent = "Día seleccionado";
}


function renderNutritionDays() {
  elements.nutritionDayCount.textContent = String(state.nutritionDays.length);
  elements.nutritionDaysList.innerHTML = "";

  if (state.nutritionDays.length === 0) {
    setListEmpty(
      elements.nutritionDaysList,
      "nutrition-days-list",
      "Todavía no hay días nutricionales registrados.",
    );
    return;
  }

  elements.nutritionDaysList.className = "nutrition-days-list";

  for (const nutritionDay of state.nutritionDays) {
    const fragment = elements.nutritionDayTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".nutrition-day-card");
    const button = fragment.querySelector(".nutrition-day-select-button");

    fragment.querySelector(".nutrition-day-date").textContent = formatDate(
      nutritionDay.date,
    );
    fragment.querySelector(".nutrition-day-notes").textContent =
      nutritionDay.notes || "Sin notas";

    if (state.selectedDay?.id === nutritionDay.id) {
      card.classList.add("selected");
    }

    button.addEventListener("click", () => selectNutritionDay(nutritionDay));
    elements.nutritionDaysList.append(fragment);
  }
}


function renderMeals() {
  elements.nutritionMealsList.innerHTML = "";

  if (state.meals.length === 0) {
    setListEmpty(
      elements.nutritionMealsList,
      "nutrition-meals-list",
      "Todavía no hay comidas en este día.",
    );
    return;
  }

  elements.nutritionMealsList.className = "nutrition-meals-list";

  for (const meal of state.meals) {
    const fragment = elements.nutritionMealTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".nutrition-meal-card");
    const button = fragment.querySelector(".nutrition-meal-select-button");

    fragment.querySelector(".nutrition-meal-position").textContent =
      String(meal.position);
    fragment.querySelector(".nutrition-meal-name").textContent = meal.name;
    fragment.querySelector(".nutrition-meal-summary").textContent =
      "Seleccionar para añadir alimentos";

    if (state.selectedMeal?.id === meal.id) {
      card.classList.add("selected");
    }

    button.addEventListener("click", () => selectNutritionMeal(meal));
    elements.nutritionMealsList.append(fragment);
  }
}


function renderFoods() {
  elements.nutritionFoodCount.textContent = String(state.foods.length);
  elements.nutritionFoodsList.innerHTML = "";

  if (state.foods.length === 0) {
    setListEmpty(
      elements.nutritionFoodsList,
      "nutrition-foods-list",
      "Todavía no hay alimentos en esta comida.",
    );
    renderTotals();
    return;
  }

  elements.nutritionFoodsList.className = "nutrition-foods-list";

  for (const food of state.foods) {
    const fragment = elements.nutritionFoodTemplate.content.cloneNode(true);

    fragment.querySelector(".nutrition-food-name").textContent = food.name;
    fragment.querySelector(".nutrition-food-meta").textContent =
      `${formatNumber(food.quantity_g)} g`;
    fragment.querySelector(".nutrition-food-notes").textContent =
      food.notes || "Sin notas";

    fragment.querySelector(".nutrition-food-calories").textContent =
      `${formatNumber(food.calories)} kcal`;
    fragment.querySelector(".nutrition-food-protein").textContent =
      `P: ${formatNumber(food.protein_g)} g`;
    fragment.querySelector(".nutrition-food-carbs").textContent =
      `C: ${formatNumber(food.carbs_g)} g`;
    fragment.querySelector(".nutrition-food-fat").textContent =
      `G: ${formatNumber(food.fat_g)} g`;

    fragment
      .querySelector(".nutrition-food-delete-button")
      .addEventListener("click", () => deleteNutritionFood(food));

    elements.nutritionFoodsList.append(fragment);
  }

  renderTotals();
}


async function loadNutritionDays() {
  elements.refreshNutritionDaysButton.disabled = true;
  elements.refreshNutritionDaysButton.textContent = "…";

  try {
    state.nutritionDays = await request("/nutrition-days/");
    renderNutritionDays();
  } catch (error) {
    setListEmpty(
      elements.nutritionDaysList,
      "nutrition-days-list",
      "No se pudieron cargar los días nutricionales.",
    );
    showStatus(error.message, "error");
  } finally {
    elements.refreshNutritionDaysButton.disabled = false;
    elements.refreshNutritionDaysButton.textContent = "↻";
  }
}


async function loadNutritionMeals(dayId) {
  state.meals = await request(`/nutrition-days/${dayId}/meals/`);
  renderMeals();
}


async function loadNutritionFoods(mealId) {
  state.foods = await request(`/nutrition-meals/${mealId}/foods/`);
  renderFoods();

  if (state.selectedDay) {
    await loadNutritionGoalProgress(state.selectedDay.date);
  }
}


async function selectNutritionDay(nutritionDay) {
  state.selectedDay = nutritionDay;
  elements.selectedDayTitle.textContent =
    `Comidas de ${formatDate(nutritionDay.date)}`;
  elements.nutritionContent.classList.remove("hidden");

  resetSelectedMeal();

  try {
    await Promise.all([
      loadNutritionMeals(nutritionDay.id),
      loadNutritionGoalProgress(nutritionDay.date),
    ]);
    renderNutritionDays();
  } catch (error) {
    showStatus(error.message, "error");
  }
}


async function selectNutritionMeal(meal) {
  state.selectedMeal = meal;
  elements.selectedMealTitle.textContent = meal.name;
  elements.deleteMealButton.classList.remove("hidden");
  elements.nutritionFoodEmptyState.classList.add("hidden");
  elements.nutritionFoodContent.classList.remove("hidden");

  try {
    await loadNutritionFoods(meal.id);
    renderMeals();
  } catch (error) {
    showStatus(error.message, "error");
  }
}


function getNumberValue(input, label, minimum = 0) {
  const value = Number(input.value);

  if (!Number.isFinite(value) || value < minimum) {
    throw new Error(`${label} no es válido.`);
  }

  return value;
}


function nextMealPosition() {
  if (state.meals.length === 0) {
    return 1;
  }

  return Math.max(...state.meals.map((meal) => meal.position)) + 1;
}


function nextFoodPosition() {
  if (state.foods.length === 0) {
    return 1;
  }

  return Math.max(...state.foods.map((food) => food.position)) + 1;
}


async function handleCreateNutritionDay(event) {
  event.preventDefault();

  try {
    const nutritionDay = await request("/nutrition-days/", {
      method: "POST",
      body: JSON.stringify({
        date: elements.nutritionDayDate.value,
        notes: emptyToNull(elements.nutritionDayNotes.value),
      }),
    });

    elements.nutritionDayForm.reset();
    elements.nutritionDayDate.value = todayAsIsoDate();

    showStatus("Día nutricional creado.");
    await loadNutritionDays();
    await selectNutritionDay(nutritionDay);
  } catch (error) {
    showStatus(error.message, "error");
  }
}


async function handleCreateNutritionMeal(event) {
  event.preventDefault();

  if (!state.selectedDay) {
    return;
  }

  try {
    const meal = await request(
      `/nutrition-days/${state.selectedDay.id}/meals/`,
      {
        method: "POST",
        body: JSON.stringify({
          name: elements.nutritionMealName.value.trim(),
          position: getNumberValue(
            elements.nutritionMealPosition,
            "La posición",
            1,
          ),
        }),
      },
    );

    elements.nutritionMealForm.reset();
    elements.nutritionMealPosition.value = String(nextMealPosition());

    showStatus(`Comida "${meal.name}" añadida.`);
    await loadNutritionMeals(state.selectedDay.id);
    await selectNutritionMeal(meal);
  } catch (error) {
    showStatus(error.message, "error");
  }
}


async function handleCreateNutritionFood(event) {
  event.preventDefault();

  if (!state.selectedMeal) {
    return;
  }

  try {
    const food = await request(
      `/nutrition-meals/${state.selectedMeal.id}/foods/`,
      {
        method: "POST",
        body: JSON.stringify({
          name: elements.nutritionFoodName.value.trim(),
          quantity_g: getNumberValue(
            elements.nutritionFoodQuantity,
            "La cantidad",
            0.01,
          ),
          calories: getNumberValue(
            elements.nutritionFoodCalories,
            "Las calorías",
          ),
          protein_g: getNumberValue(
            elements.nutritionFoodProtein,
            "La proteína",
          ),
          carbs_g: getNumberValue(
            elements.nutritionFoodCarbs,
            "Los carbohidratos",
          ),
          fat_g: getNumberValue(
            elements.nutritionFoodFat,
            "Las grasas",
          ),
          position: getNumberValue(
            elements.nutritionFoodPosition,
            "La posición",
            1,
          ),
          notes: emptyToNull(elements.nutritionFoodNotes.value),
        }),
      },
    );

    elements.nutritionFoodForm.reset();
    elements.nutritionFoodPosition.value = String(nextFoodPosition());

    showStatus(`Alimento "${food.name}" añadido.`);
    await loadNutritionFoods(state.selectedMeal.id);
  } catch (error) {
    showStatus(error.message, "error");
  }
}


async function deleteNutritionFood(food) {
  const confirmed = window.confirm(`¿Eliminar "${food.name}"?`);

  if (!confirmed) {
    return;
  }

  try {
    await request(`/nutrition-foods/${food.id}`, {
      method: "DELETE",
    });

    showStatus(`Alimento "${food.name}" eliminado.`);
    await loadNutritionFoods(state.selectedMeal.id);
  } catch (error) {
    showStatus(error.message, "error");
  }
}


async function deleteSelectedMeal() {
  if (!state.selectedMeal) {
    return;
  }

  const confirmed = window.confirm(
    `¿Eliminar la comida "${state.selectedMeal.name}" y todos sus alimentos?`,
  );

  if (!confirmed) {
    return;
  }

  try {
    await request(`/nutrition-meals/${state.selectedMeal.id}`, {
      method: "DELETE",
    });

    showStatus(`Comida "${state.selectedMeal.name}" eliminada.`);
    resetSelectedMeal();
    await loadNutritionMeals(state.selectedDay.id);
  } catch (error) {
    showStatus(error.message, "error");
  }
}


function configureEventListeners() {
  elements.nutritionDayForm.addEventListener(
    "submit",
    handleCreateNutritionDay,
  );

  elements.nutritionMealForm.addEventListener(
    "submit",
    handleCreateNutritionMeal,
  );

  elements.nutritionFoodForm.addEventListener(
    "submit",
    handleCreateNutritionFood,
  );

  elements.refreshNutritionDaysButton.addEventListener(
    "click",
    loadNutritionDays,
  );

  elements.deleteMealButton.addEventListener(
    "click",
    deleteSelectedMeal,
  );
}


async function initializeApp() {
  elements.nutritionDayDate.value = todayAsIsoDate();
  configureEventListeners();
  await loadNutritionDays();
}


initializeApp();