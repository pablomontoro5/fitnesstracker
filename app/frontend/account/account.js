const accountStatus = document.querySelector("#account-status");
const changePasswordForm = document.querySelector("#change-password-form");
const changePasswordButton = document.querySelector("#change-password-button");
const deleteAccountForm = document.querySelector("#delete-account-form");
const deleteAccountButton = document.querySelector("#delete-account-button");


function showAccountStatus(message, type) {
  accountStatus.textContent = message;
  accountStatus.className = `status-message ${type}`;
}


function clearAccountStatus() {
  accountStatus.textContent = "";
  accountStatus.className = "status-message";
}


async function readErrorMessage(response) {
  try {
    const payload = await response.json();

    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    // Se usa el mensaje genérico.
  }

  return "No se pudo completar la operación.";
}


function formatMemberSince(createdAt) {
  const date = new Date(createdAt.replace(" ", "T") + "Z");

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleDateString("es-ES", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}


async function loadAccount() {
  const response = await apiFetch("/auth/me");

  if (response.status === 401) {
    // apiFetch ya limpia el token y redirige al login.
    return false;
  }

  if (!response.ok) {
    throw new Error("No se pudo verificar la sesión.");
  }

  const user = await response.json();
  const since = formatMemberSince(user.created_at);

  document.querySelector("#account-name").textContent = user.display_name;
  document.querySelector("#account-details").textContent = since
    ? `${user.email} · Cuenta creada el ${since}`
    : user.email;

  return true;
}


changePasswordForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearAccountStatus();

  const currentPassword = document.querySelector("#current-password").value;
  const newPassword = document.querySelector("#new-password").value;
  const repeatPassword = document.querySelector("#repeat-password").value;

  if (newPassword !== repeatPassword) {
    showAccountStatus("Las contraseñas nuevas no coinciden.", "error");
    return;
  }

  changePasswordButton.disabled = true;

  try {
    const response = await apiFetch("/auth/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    // Las demás sesiones se cierran; esta sigue con el token nuevo.
    const payload = await response.json();
    saveAccessToken(payload.access_token);

    changePasswordForm.reset();
    showAccountStatus(
      "Contraseña cambiada. Se han cerrado las demás sesiones.",
      "success",
    );
  } catch (error) {
    showAccountStatus(error.message, "error");
  } finally {
    changePasswordButton.disabled = false;
  }
});


deleteAccountForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearAccountStatus();

  const password = document.querySelector("#delete-password").value;

  deleteAccountButton.disabled = true;

  try {
    const response = await apiFetch("/auth/me", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    clearAccessToken();
    window.location.replace("/static/login/?deleted=1");
  } catch (error) {
    showAccountStatus(error.message, "error");
    deleteAccountButton.disabled = false;
  }
});


const restoreAccountForm = document.querySelector("#restore-account-form");
const restoreAccountButton = document.querySelector("#restore-account-button");

restoreAccountForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearAccountStatus();

  const formData = new FormData();
  formData.append(
    "file",
    document.querySelector("#restore-account-file").files[0],
  );
  formData.append(
    "password",
    document.querySelector("#restore-account-password").value,
  );

  restoreAccountButton.disabled = true;

  try {
    // Sin Content-Type: el navegador añade el límite del multipart.
    const response = await apiFetch("/restores/account", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    restoreAccountForm.reset();
    showAccountStatus(
      "Datos restaurados correctamente. Ya puedes consultarlos en la aplicación.",
      "success",
    );
  } catch (error) {
    showAccountStatus(error.message, "error");
  } finally {
    restoreAccountButton.disabled = false;
  }
});


const importWorkoutsForm = document.querySelector("#import-workouts-form");
const importWorkoutsFile = document.querySelector("#import-workouts-file");
const importWorkoutsSummary = document.querySelector("#import-workouts-summary");
const importWorkoutsPreviewButton = document.querySelector(
  "#import-workouts-preview-button",
);
const importWorkoutsConfirmButton = document.querySelector(
  "#import-workouts-confirm-button",
);


function resetWorkoutsImport() {
  importWorkoutsSummary.hidden = true;
  importWorkoutsSummary.replaceChildren();
  importWorkoutsConfirmButton.hidden = true;
}


function plural(count, singular, pluralForm) {
  return `${count} ${count === 1 ? singular : pluralForm}`;
}


function renderImportSummary(result) {
  importWorkoutsSummary.replaceChildren();

  const lines = [
    result.dry_run
      ? `Se importarían ${plural(result.sessions, "sesión", "sesiones")}, `
        + `${plural(result.exercises, "ejercicio", "ejercicios")} y `
        + `${plural(result.sets, "serie", "series")}.`
      : `Importadas ${plural(result.sessions, "sesión", "sesiones")}, `
        + `${plural(result.exercises, "ejercicio", "ejercicios")} y `
        + `${plural(result.sets, "serie", "series")}.`,
  ];

  if (result.skipped_sessions > 0) {
    lines.push(
      `${plural(result.skipped_sessions, "sesión ya existía", "sesiones ya existían")} `
      + "y se omite.",
    );
  }

  if (result.omitted_sets > 0) {
    lines.push(
      `${plural(result.omitted_sets, "serie omitida", "series omitidas")} `
      + "(sin repeticiones o con datos no válidos).",
    );
  }

  for (const line of lines) {
    const paragraph = document.createElement("p");
    paragraph.textContent = line;
    importWorkoutsSummary.append(paragraph);
  }

  if (result.warnings.length > 0) {
    const list = document.createElement("ul");

    for (const warning of result.warnings) {
      const item = document.createElement("li");
      item.textContent = warning;
      list.append(item);
    }

    importWorkoutsSummary.append(list);
  }

  importWorkoutsSummary.hidden = false;
}


const importWorkoutsSource = document.querySelector("#import-workouts-source");
const importWorkoutsUnitLabel = document.querySelector(
  "#import-workouts-unit-label",
);
const importWorkoutsUnit = document.querySelector("#import-workouts-unit");


importWorkoutsSource.addEventListener("change", () => {
  // Solo el CSV de Strong necesita que se indique la unidad del peso.
  importWorkoutsUnitLabel.hidden = importWorkoutsSource.value !== "strong";
  resetWorkoutsImport();
});

importWorkoutsUnit.addEventListener("change", resetWorkoutsImport);


async function sendImportFile(dryRun) {
  const source = importWorkoutsSource.value;
  const formData = new FormData();
  formData.append("file", importWorkoutsFile.files[0]);
  formData.append("dry_run", dryRun ? "true" : "false");

  if (source === "strong") {
    formData.append("weight_unit", importWorkoutsUnit.value);
  }

  const response = await apiFetch(`/imports/${source}`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}


importWorkoutsFile.addEventListener("change", resetWorkoutsImport);

importWorkoutsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearAccountStatus();
  resetWorkoutsImport();
  importWorkoutsPreviewButton.disabled = true;

  try {
    const result = await sendImportFile(true);

    renderImportSummary(result);
    importWorkoutsConfirmButton.hidden = result.sessions === 0;

    if (result.sessions === 0) {
      showAccountStatus("No hay sesiones nuevas que importar.", "success");
    }
  } catch (error) {
    showAccountStatus(error.message, "error");
  } finally {
    importWorkoutsPreviewButton.disabled = false;
  }
});

importWorkoutsConfirmButton.addEventListener("click", async () => {
  clearAccountStatus();
  importWorkoutsConfirmButton.disabled = true;
  importWorkoutsPreviewButton.disabled = true;

  try {
    const result = await sendImportFile(false);

    importWorkoutsConfirmButton.hidden = true;
    renderImportSummary(result);
    importWorkoutsForm.reset();
    showAccountStatus(
      "Entrenamientos importados. Ya puedes verlos en tu historial.",
      "success",
    );
  } catch (error) {
    showAccountStatus(error.message, "error");
  } finally {
    importWorkoutsConfirmButton.disabled = false;
    importWorkoutsPreviewButton.disabled = false;
  }
});


async function initializeAccount() {
  if (!getAccessToken()) {
    window.location.replace("/static/login/?next=%2Fstatic%2Faccount%2F");
    return;
  }

  try {
    if (!(await loadAccount())) {
      return;
    }

    document.body.style.visibility = "visible";
    document.querySelector("#logout-button").addEventListener("click", logout);
  } catch (error) {
    document.body.textContent =
      `${error.message} Comprueba la conexión y recarga la página.`;
    document.body.style.visibility = "visible";
  }
}


initializeAccount();
