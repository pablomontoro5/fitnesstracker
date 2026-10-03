const state = {
  foods: [],
  templates: [],
  selectedTemplateId: null,
  editingFoodId: null,
};


const elements = {
  statusMessage: document.querySelector("#status-message"),

  foodForm: document.querySelector("#food-form"),
  foodFormTitle: document.querySelector("#food-form-title"),
  foodName: document.querySelector("#food-name"),
  foodCalories: document.querySelector("#food-calories"),
  foodProtein: document.querySelector("#food-protein"),
  foodCarbs: document.querySelector("#food-carbs"),
  foodFat: document.querySelector("#food-fat"),
  foodNotes: document.querySelector("#food-notes"),
  foodSubmitButton: document.querySelector("#food-submit-button"),
  foodCancelButton: document.querySelector("#food-cancel-button"),
  foodCount: document.querySelector("#food-count"),
  foodFilter: document.querySelector("#food-filter"),
  foodsList: document.querySelector("#foods-list"),

  templateForm: document.querySelector("#template-form"),
  templateName: document.querySelector("#template-name"),
  templateCount: document.querySelector("#template-count"),
  templatesList: document.querySelector("#templates-list"),

  templateTitle: document.querySelector("#template-title"),
  deleteTemplateButton: document.querySelector("#delete-template-button"),
  templateEmptyState: document.querySelector("#template-empty-state"),
  templateDetail: document.querySelector("#template-detail"),
  templateItemForm: document.querySelector("#template-item-form"),
  templateItemFood: document.querySelector("#template-item-food"),
  templateItemGrams: document.querySelector("#template-item-grams"),
  templateItemCount: document.querySelector("#template-item-count"),
  templateItems: document.querySelector("#template-items"),
  templateTotals: document.querySelector("#template-totals"),
};


function formatNumber(value, maximumFractionDigits = 1) {
  return new Intl.NumberFormat("es-ES", { maximumFractionDigits }).format(
    value,
  );
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


function actionButton(label, className, handler) {
  const button = createElement("button", className, label);
  button.type = "button";
  button.addEventListener("click", async () => {
    button.disabled = true;

    try {
      await handler();
    } catch (error) {
      showStatus(error.message, "error");
    } finally {
      button.disabled = false;
    }
  });

  return button;
}


/* ---------- Biblioteca de alimentos ---------- */

function macrosText(item) {
  return (
    `${formatNumber(item.calories_per_100g, 0)} kcal · `
    + `P ${formatNumber(item.protein_per_100g)} g · `
    + `C ${formatNumber(item.carbs_per_100g)} g · `
    + `G ${formatNumber(item.fat_per_100g)} g`
  );
}


function renderFoods() {
  const filter = elements.foodFilter.value.trim().toLowerCase();
  const foods = state.foods.filter((food) => (
    food.name.toLowerCase().includes(filter)
  ));

  elements.foodCount.textContent = String(state.foods.length);

  if (state.foods.length === 0) {
    elements.foodsList.className = "library-list empty-state";
    elements.foodsList.textContent = "Aún no has guardado ningún alimento.";
    return;
  }

  if (foods.length === 0) {
    elements.foodsList.className = "library-list empty-state";
    elements.foodsList.textContent = "Ningún alimento coincide con la búsqueda.";
    return;
  }

  elements.foodsList.className = "library-list";
  elements.foodsList.replaceChildren(
    ...foods.map((food) => {
      const card = createElement("article", "library-card");
      const info = createElement("div", "library-card-info");

      info.append(
        createElement("strong", "", food.name),
        createElement("small", "", `Por 100 g: ${macrosText(food)}`),
      );

      if (food.notes) {
        info.append(createElement("small", "", food.notes));
      }

      const actions = createElement("div", "library-card-actions");
      actions.append(
        actionButton("Editar", "secondary-button", async () => {
          startEditingFood(food);
        }),
        actionButton("Eliminar", "danger-button", () => deleteFood(food)),
      );

      card.append(info, actions);
      return card;
    }),
  );
}


async function loadFoods() {
  renderListLoading(elements.foodsList, "library-list", "Cargando alimentos…");

  try {
    state.foods = await request("/food-library/");
  } catch (error) {
    renderListError(
      elements.foodsList,
      "library-list",
      error.message,
      loadFoods,
    );
    return;
  }

  renderFoods();
  renderFoodOptions();
}


function startEditingFood(food) {
  state.editingFoodId = food.id;
  elements.foodFormTitle.textContent = `Editar «${food.name}»`;
  elements.foodSubmitButton.textContent = "Guardar cambios";
  elements.foodCancelButton.classList.remove("hidden");

  elements.foodName.value = food.name;
  elements.foodCalories.value = food.calories_per_100g;
  elements.foodProtein.value = food.protein_per_100g;
  elements.foodCarbs.value = food.carbs_per_100g;
  elements.foodFat.value = food.fat_per_100g;
  elements.foodNotes.value = food.notes ?? "";

  elements.foodForm.scrollIntoView({ behavior: "smooth", block: "start" });
  elements.foodName.focus();
}


function stopEditingFood() {
  state.editingFoodId = null;
  elements.foodFormTitle.textContent = "Añadir alimento";
  elements.foodSubmitButton.textContent = "Guardar alimento";
  elements.foodCancelButton.classList.add("hidden");
  elements.foodForm.reset();
}


async function handleSaveFood(event) {
  event.preventDefault();

  const notes = elements.foodNotes.value.trim();
  const payload = {
    name: elements.foodName.value.trim(),
    calories_per_100g: Number(elements.foodCalories.value),
    protein_per_100g: Number(elements.foodProtein.value),
    carbs_per_100g: Number(elements.foodCarbs.value),
    fat_per_100g: Number(elements.foodFat.value),
    notes: notes === "" ? null : notes,
  };
  const isEditing = state.editingFoodId !== null;

  try {
    await request(
      isEditing ? `/food-library/${state.editingFoodId}` : "/food-library/",
      {
        method: isEditing ? "PUT" : "POST",
        body: JSON.stringify(payload),
      },
    );

    stopEditingFood();
    showStatus(isEditing ? "Alimento actualizado." : "Alimento guardado.");
    await loadFoods();
  } catch (error) {
    showStatus(error.message, "error");
  }
}


async function deleteFood(food) {
  if (!window.confirm(
    `¿Eliminar «${food.name}» de la biblioteca? `
    + "Las plantillas que ya lo usan conservan su copia.",
  )) {
    return;
  }

  await request(`/food-library/${food.id}`, { method: "DELETE" });

  if (state.editingFoodId === food.id) {
    stopEditingFood();
  }

  showStatus("Alimento eliminado.");
  await loadFoods();
}


/* ---------- Plantillas de comida ---------- */

function totalsText(template) {
  return (
    `${formatNumber(template.calories, 0)} kcal · `
    + `P ${formatNumber(template.protein)} g · `
    + `C ${formatNumber(template.carbs)} g · `
    + `G ${formatNumber(template.fat)} g`
  );
}


function getSelectedTemplate() {
  return state.templates.find(
    (template) => template.id === state.selectedTemplateId,
  ) ?? null;
}


function renderTemplates() {
  elements.templateCount.textContent = String(state.templates.length);

  if (state.templates.length === 0) {
    elements.templatesList.className = "library-list empty-state";
    elements.templatesList.textContent = "Aún no has creado ninguna plantilla.";
    return;
  }

  elements.templatesList.className = "library-list";
  elements.templatesList.replaceChildren(
    ...state.templates.map((template) => {
      const card = createElement("article", "library-card");

      if (template.id === state.selectedTemplateId) {
        card.classList.add("selected");
      }

      const button = createElement("button", "library-select-button");
      button.type = "button";
      button.append(
        createElement("strong", "", template.name),
        createElement(
          "small",
          "",
          `${template.items.length} alimentos · ${totalsText(template)}`,
        ),
      );
      button.addEventListener("click", () => {
        state.selectedTemplateId = template.id;
        renderTemplates();
        renderTemplateDetail();
      });

      card.append(button);
      return card;
    }),
  );
}


function renderFoodOptions() {
  const options = state.foods.map(
    (food) => new Option(food.name, String(food.id)),
  );

  if (options.length === 0) {
    options.push(new Option("Primero añade alimentos a la biblioteca", ""));
  }

  elements.templateItemFood.replaceChildren(...options);
}


function renderTemplateDetail() {
  const template = getSelectedTemplate();

  if (!template) {
    elements.templateTitle.textContent = "Selecciona una plantilla";
    elements.deleteTemplateButton.classList.add("hidden");
    elements.templateEmptyState.classList.remove("hidden");
    elements.templateDetail.classList.add("hidden");
    return;
  }

  elements.templateTitle.textContent = template.name;
  elements.deleteTemplateButton.classList.remove("hidden");
  elements.templateEmptyState.classList.add("hidden");
  elements.templateDetail.classList.remove("hidden");
  elements.templateItemCount.textContent = String(template.items.length);
  elements.templateTotals.textContent = `Total: ${totalsText(template)}`;

  if (template.items.length === 0) {
    elements.templateItems.className = "library-list empty-state";
    elements.templateItems.textContent = "Esta plantilla aún no tiene alimentos.";
    return;
  }

  elements.templateItems.className = "library-list";
  elements.templateItems.replaceChildren(
    ...template.items.map((item) => buildTemplateItemCard(template, item)),
  );
}


function buildTemplateItemCard(template, item) {
  const card = createElement("article", "library-card");
  const info = createElement("div", "library-card-info");

  info.append(
    createElement("strong", "", item.name),
    createElement(
      "small",
      "",
      `${formatNumber(item.calories, 0)} kcal · P ${formatNumber(item.protein)} g`
      + ` · C ${formatNumber(item.carbs)} g · G ${formatNumber(item.fat)} g`,
    ),
  );

  const gramsInput = createElement("input", "library-grams-input");
  gramsInput.type = "number";
  gramsInput.min = "0.01";
  gramsInput.max = "100000";
  gramsInput.step = "0.01";
  gramsInput.value = item.grams;
  gramsInput.setAttribute("aria-label", `Gramos de ${item.name}`);

  const actions = createElement("div", "library-card-actions");
  actions.append(
    gramsInput,
    createElement("span", "optional", "g"),
    actionButton("Guardar", "secondary-button", async () => {
      const grams = Number(gramsInput.value);

      if (!Number.isFinite(grams) || grams <= 0) {
        throw new Error("Los gramos deben ser mayores que 0.");
      }

      replaceTemplate(
        await request(`/meal-templates/${template.id}/items/${item.id}`, {
          method: "PUT",
          body: JSON.stringify({ grams }),
        }),
      );
      showStatus("Cantidad actualizada.");
    }),
    actionButton("Quitar", "danger-button", async () => {
      await request(`/meal-templates/${template.id}/items/${item.id}`, {
        method: "DELETE",
      });
      await loadTemplates();
      showStatus("Alimento quitado de la plantilla.");
    }),
  );

  card.append(info, actions);
  return card;
}


function replaceTemplate(updated) {
  state.templates = state.templates.map(
    (template) => (template.id === updated.id ? updated : template),
  );
  renderTemplates();
  renderTemplateDetail();
}


async function loadTemplates() {
  renderListLoading(
    elements.templatesList,
    "library-list",
    "Cargando plantillas…",
  );

  try {
    state.templates = await request("/meal-templates/");
  } catch (error) {
    renderListError(
      elements.templatesList,
      "library-list",
      error.message,
      loadTemplates,
    );
    return;
  }

  if (!getSelectedTemplate()) {
    state.selectedTemplateId = null;
  }

  renderTemplates();
  renderTemplateDetail();
}


async function handleCreateTemplate(event) {
  event.preventDefault();

  try {
    const template = await request("/meal-templates/", {
      method: "POST",
      body: JSON.stringify({ name: elements.templateName.value.trim() }),
    });

    elements.templateForm.reset();
    state.selectedTemplateId = template.id;
    showStatus("Plantilla creada. Añádele alimentos.");
    await loadTemplates();
  } catch (error) {
    showStatus(error.message, "error");
  }
}


async function handleAddTemplateItem(event) {
  event.preventDefault();

  const template = getSelectedTemplate();
  const foodId = Number(elements.templateItemFood.value);

  if (!template || !foodId) {
    showStatus("Elige un alimento de la biblioteca.", "error");
    return;
  }

  try {
    replaceTemplate(
      await request(`/meal-templates/${template.id}/items`, {
        method: "POST",
        body: JSON.stringify({
          food_id: foodId,
          grams: Number(elements.templateItemGrams.value),
        }),
      }),
    );

    elements.templateItemGrams.value = "";
    showStatus("Alimento añadido a la plantilla.");
  } catch (error) {
    showStatus(error.message, "error");
  }
}


async function handleDeleteTemplate() {
  const template = getSelectedTemplate();

  if (!template || !window.confirm(`¿Eliminar la plantilla «${template.name}»?`)) {
    return;
  }

  try {
    await request(`/meal-templates/${template.id}`, { method: "DELETE" });
    state.selectedTemplateId = null;
    showStatus("Plantilla eliminada.");
    await loadTemplates();
  } catch (error) {
    showStatus(error.message, "error");
  }
}


function configureEventListeners() {
  elements.foodForm.addEventListener("submit", handleSaveFood);
  elements.foodCancelButton.addEventListener("click", stopEditingFood);
  elements.foodFilter.addEventListener("input", renderFoods);
  elements.templateForm.addEventListener("submit", handleCreateTemplate);
  elements.templateItemForm.addEventListener("submit", handleAddTemplateItem);
  elements.deleteTemplateButton.addEventListener(
    "click",
    handleDeleteTemplate,
  );
}


async function initializeApp() {
  configureEventListeners();
  await Promise.all([loadFoods(), loadTemplates()]);
}


initializeApp();
