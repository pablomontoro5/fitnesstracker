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
