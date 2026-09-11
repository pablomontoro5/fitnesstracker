const elements = {
  form: document.querySelector("#body-metric-form"),
  formTitle: document.querySelector("#body-metric-form-title"),
  modeBadge: document.querySelector("#body-metric-mode"),
  submitButton: document.querySelector("#body-metric-submit-button"),
  cancelEditButton: document.querySelector("#cancel-edit-button"),
  statusMessage: document.querySelector("#status-message"),
  metricsList: document.querySelector("#body-metrics-list"),
  metricsCount: document.querySelector("#body-metrics-count"),

  date: document.querySelector("#metric-date"),
  weightKg: document.querySelector("#weight-kg"),
  heightCm: document.querySelector("#height-cm"),
  bodyFatPercentage: document.querySelector("#body-fat-percentage"),
  waistCm: document.querySelector("#waist-cm"),
  hipCm: document.querySelector("#hip-cm"),
  chestCm: document.querySelector("#chest-cm"),
  armCm: document.querySelector("#arm-cm"),
  thighCm: document.querySelector("#thigh-cm"),
  notes: document.querySelector("#metric-notes"),

  bmiPreview: document.querySelector("#bmi-preview"),
  fatMassPreview: document.querySelector("#fat-mass-preview"),
  leanMassPreview: document.querySelector("#lean-mass-preview"),
};


let editingMetricId = null;


function formatNumber(value, maximumFractionDigits = 2) {
  return new Intl.NumberFormat("es-ES", {
    maximumFractionDigits,
  }).format(value);
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


function parseOptionalNumber(input) {
  const value = input.value.trim();

  if (!value) {
    return null;
  }

  const parsedValue = Number(value);
  return Number.isFinite(parsedValue) ? parsedValue : null;
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


function renderPreview() {
  const weightKg = parseOptionalNumber(elements.weightKg);
  const heightCm = parseOptionalNumber(elements.heightCm);
  const bodyFatPercentage = parseOptionalNumber(
    elements.bodyFatPercentage,
  );

  if (!weightKg || !heightCm) {
    elements.bmiPreview.textContent = "—";
    elements.fatMassPreview.textContent = "—";
    elements.leanMassPreview.textContent = "—";
    return;
  }

  const heightM = heightCm / 100;
  const bmi = weightKg / (heightM ** 2);

  elements.bmiPreview.textContent = formatNumber(bmi);

  if (bodyFatPercentage === null) {
    elements.fatMassPreview.textContent = "—";
    elements.leanMassPreview.textContent = "—";
    return;
  }

  const fatMassKg = weightKg * bodyFatPercentage / 100;
  const leanMassKg = weightKg - fatMassKg;

  elements.fatMassPreview.textContent = `${formatNumber(fatMassKg)} kg`;
  elements.leanMassPreview.textContent =
    `${formatNumber(leanMassKg)} kg`;
}


async function requestBodyMetrics() {
  const response = await fetch("/body-metrics/");
  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((error) => error.msg).join(". ")
      : body?.detail;

    throw new Error(detail || "No se pudieron cargar las mediciones.");
  }

  return body;
}


async function createBodyMetric(payload) {
  const response = await fetch("/body-metrics/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((error) => error.msg).join(". ")
      : body?.detail;

    throw new Error(detail || "No se pudo guardar la medición.");
  }

  return body;
}


async function updateBodyMetric(metricId, payload) {
  const response = await fetch(`/body-metrics/${metricId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((error) => error.msg).join(". ")
      : body?.detail;

    throw new Error(detail || "No se pudo actualizar la medición.");
  }

  return body;
}


async function deleteBodyMetric(metricId) {
  const response = await fetch(`/body-metrics/${metricId}`, {
    method: "DELETE",
  });

  if (response.status === 204) {
    return;
  }

  const body = await response.json().catch(() => null);
  const detail = Array.isArray(body?.detail)
    ? body.detail.map((error) => error.msg).join(". ")
    : body?.detail;

  throw new Error(detail || "No se pudo eliminar la medición.");
}


function renderBodyMetrics(metrics) {
  elements.metricsList.innerHTML = "";
  elements.metricsCount.textContent = metrics.length;

  if (!metrics.length) {
    elements.metricsList.innerHTML = `
      <div class="empty-state large-empty-state">
        Aún no hay mediciones. Registra peso y altura para comenzar tu historial.
      </div>
    `;
    return;
  }

  for (const metric of metrics) {
    const card = document.createElement("article");
    card.className = "body-metric-card";

    const bodyFatText = metric.body_fat_percentage === null
      ? "Sin dato de grasa corporal"
      : `${formatNumber(metric.body_fat_percentage)} % grasa · ` +
        `${formatNumber(metric.lean_mass_kg)} kg masa libre`;

    const measurements = [
      ["Cintura", metric.waist_cm],
      ["Cadera", metric.hip_cm],
      ["Pecho", metric.chest_cm],
      ["Brazo", metric.arm_cm],
      ["Muslo", metric.thigh_cm],
    ].filter(([, value]) => value !== null);

    const measurementsText = measurements.length
      ? measurements
          .map(([name, value]) => `${name}: ${formatNumber(value)} cm`)
          .join(" · ")
      : "Sin perímetros registrados";

    card.innerHTML = `
      <div class="body-metric-card-main">
        <span class="body-metric-date">${formatDate(metric.date)}</span>
        <strong>${formatNumber(metric.weight_kg)} kg</strong>
        <span class="body-metric-bmi">IMC ${formatNumber(metric.bmi)}</span>
        <span class="body-metric-composition">${bodyFatText}</span>
        <span class="body-metric-measurements">${measurementsText}</span>
        ${
          metric.notes
            ? `<span class="body-metric-notes">${metric.notes}</span>`
            : ""
        }
      </div>

      <div class="body-metric-actions">
        <button
          class="secondary-button body-metric-edit-button"
          type="button"
          data-metric-id="${metric.id}"
        >
          Editar
        </button>

        <button
          class="danger-button body-metric-delete-button"
          type="button"
          data-metric-id="${metric.id}"
        >
          Eliminar
        </button>
      </div>
    `;

    elements.metricsList.append(card);
  }
}


async function loadBodyMetrics() {
  try {
    const metrics = await requestBodyMetrics();
    renderBodyMetrics(metrics);
  } catch (error) {
    elements.metricsList.innerHTML = `
      <div class="empty-state large-empty-state">
        No se pudo cargar el historial de mediciones.
      </div>
    `;
    showStatus(error.message, "error");
  }
}


function getFormPayload() {
  return {
    date: elements.date.value,
    weight_kg: parseOptionalNumber(elements.weightKg),
    height_cm: parseOptionalNumber(elements.heightCm),
    body_fat_percentage: parseOptionalNumber(
      elements.bodyFatPercentage,
    ),
    waist_cm: parseOptionalNumber(elements.waistCm),
    hip_cm: parseOptionalNumber(elements.hipCm),
    chest_cm: parseOptionalNumber(elements.chestCm),
    arm_cm: parseOptionalNumber(elements.armCm),
    thigh_cm: parseOptionalNumber(elements.thighCm),
    notes: elements.notes.value.trim() || null,
  };
}


function resetForm() {
  editingMetricId = null;
  elements.form.reset();
  elements.date.value = toIsoDate(new Date());
  elements.formTitle.textContent = "Registrar medida";
  elements.modeBadge.textContent = "Creación";
  elements.submitButton.textContent = "Guardar medición";
  elements.cancelEditButton.classList.add("hidden");
  renderPreview();
}


function startEditing(metric) {
  editingMetricId = metric.id;

  elements.date.value = metric.date;
  elements.weightKg.value = metric.weight_kg;
  elements.heightCm.value = metric.height_cm;
  elements.bodyFatPercentage.value = metric.body_fat_percentage ?? "";
  elements.waistCm.value = metric.waist_cm ?? "";
  elements.hipCm.value = metric.hip_cm ?? "";
  elements.chestCm.value = metric.chest_cm ?? "";
  elements.armCm.value = metric.arm_cm ?? "";
  elements.thighCm.value = metric.thigh_cm ?? "";
  elements.notes.value = metric.notes ?? "";

  elements.formTitle.textContent = "Editar medida";
  elements.modeBadge.textContent = "Edición";
  elements.submitButton.textContent = "Guardar cambios";
  elements.cancelEditButton.classList.remove("hidden");

  renderPreview();
  elements.form.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
}


async function handleSubmit(event) {
  event.preventDefault();

  const payload = getFormPayload();

  if (!payload.date || !payload.weight_kg || !payload.height_cm) {
    showStatus(
      "Completa fecha, peso y altura antes de guardar.",
      "error",
    );
    return;
  }

  elements.submitButton.disabled = true;
  elements.submitButton.textContent = editingMetricId
    ? "Guardando cambios…"
    : "Guardando…";

  try {
    if (editingMetricId === null) {
      await createBodyMetric(payload);
      showStatus("Medición corporal guardada.");
    } else {
      await updateBodyMetric(editingMetricId, payload);
      showStatus("Medición corporal actualizada.");
    }

    resetForm();
    await loadBodyMetrics();
  } catch (error) {
    showStatus(error.message, "error");
  } finally {
    elements.submitButton.disabled = false;

    if (editingMetricId === null) {
      elements.submitButton.textContent = "Guardar medición";
    } else {
      elements.submitButton.textContent = "Guardar cambios";
    }
  }
}


async function handleMetricListClick(event) {
  const editButton = event.target.closest(".body-metric-edit-button");
  const deleteButton = event.target.closest(".body-metric-delete-button");

  if (editButton) {
    const metricId = Number(editButton.dataset.metricId);
    const metrics = await requestBodyMetrics();
    const metric = metrics.find((item) => item.id === metricId);

    if (metric) {
      startEditing(metric);
    }

    return;
  }

  if (!deleteButton) {
    return;
  }

  const metricId = Number(deleteButton.dataset.metricId);

  const confirmed = window.confirm(
    "¿Quieres eliminar esta medición corporal? Esta acción no se puede deshacer.",
  );

  if (!confirmed) {
    return;
  }

  deleteButton.disabled = true;
  deleteButton.textContent = "Eliminando…";

  try {
    await deleteBodyMetric(metricId);

    if (editingMetricId === metricId) {
      resetForm();
    }

    showStatus("Medición corporal eliminada.");
    await loadBodyMetrics();
  } catch (error) {
    showStatus(error.message, "error");
    deleteButton.disabled = false;
    deleteButton.textContent = "Eliminar";
  }
}


function configureEventListeners() {
  elements.form.addEventListener("submit", handleSubmit);
  elements.cancelEditButton.addEventListener("click", resetForm);
  elements.metricsList.addEventListener("click", handleMetricListClick);

  for (const input of [
    elements.weightKg,
    elements.heightCm,
    elements.bodyFatPercentage,
  ]) {
    input.addEventListener("input", renderPreview);
  }
}


async function initializeApp() {
  resetForm();
  configureEventListeners();
  await loadBodyMetrics();
}


initializeApp();