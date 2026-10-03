const authStatus = document.querySelector("#auth-status");
const loginForm = document.querySelector("#login-form");
const registerForm = document.querySelector("#register-form");
const loginSubmitButton = document.querySelector("#login-submit-button");
const registerSubmitButton = document.querySelector(
  "#register-submit-button",
);

const resetSection = document.querySelector("#reset-section");
const resetForm = document.querySelector("#reset-form");
const resetSubmitButton = document.querySelector("#reset-submit-button");
const showResetButton = document.querySelector("#show-reset-button");

function showAuthStatus(message, type) {
  authStatus.textContent = message;
  authStatus.className = `status-message ${type}`;
}

function clearAuthStatus() {
  authStatus.textContent = "";
  authStatus.className = "status-message";
}

async function readAuthErrorMessage(response) {
  try {
    const payload = await response.json();
    return payload.detail || "No se pudo completar la operación.";
  } catch {
    return "No se pudo completar la operación.";
  }
}

function getNextPath() {
  const nextPath = new URLSearchParams(window.location.search).get("next");

  if (!nextPath || !nextPath.startsWith("/") || nextPath.startsWith("//")) {
    return "/";
  }

  return nextPath;
}

function redirectAfterAuthentication() {
  window.location.href = getNextPath();
}

async function login(email, password) {
  const response = await fetch("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email,
      password,
    }),
  });

  if (!response.ok) {
    throw new Error(await readAuthErrorMessage(response));
  }

  const payload = await response.json();
  saveAccessToken(payload.access_token);
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearAuthStatus();

  const email = document.querySelector("#login-email").value.trim();
  const password = document.querySelector("#login-password").value;

  loginSubmitButton.disabled = true;

  try {
    await login(email, password);
    showAuthStatus("Sesión iniciada. Redirigiendo…", "success");
    redirectAfterAuthentication();
  } catch (error) {
    showAuthStatus(error.message, "error");
  } finally {
    loginSubmitButton.disabled = false;
  }
});

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearAuthStatus();

  const displayName = document
    .querySelector("#register-display-name")
    .value
    .trim();
  const email = document.querySelector("#register-email").value.trim();
  const password = document.querySelector("#register-password").value;
  const inviteCode = document
    .querySelector("#register-invite-code")
    .value
    .trim();

  registerSubmitButton.disabled = true;

  try {
    const registerResponse = await fetch("/auth/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email,
        display_name: displayName,
        password,
        invite_code: inviteCode || null,
      }),
    });

    if (!registerResponse.ok) {
      throw new Error(await readAuthErrorMessage(registerResponse));
    }

    await login(email, password);
    showAuthStatus("Cuenta creada. Redirigiendo…", "success");
    redirectAfterAuthentication();
  } catch (error) {
    showAuthStatus(error.message, "error");
  } finally {
    registerSubmitButton.disabled = false;
  }
});

showResetButton.addEventListener("click", () => {
  const willShow = resetSection.hidden;

  resetSection.hidden = !willShow;
  showResetButton.setAttribute("aria-expanded", String(willShow));

  if (willShow) {
    document.querySelector("#reset-email").value =
      document.querySelector("#login-email").value.trim();
    resetSection.scrollIntoView({ behavior: "smooth", block: "start" });
    document.querySelector("#reset-email").focus();
  }
});

resetForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearAuthStatus();

  const email = document.querySelector("#reset-email").value.trim();
  const code = document.querySelector("#reset-code").value.trim();
  const newPassword = document.querySelector("#reset-password").value;

  resetSubmitButton.disabled = true;

  try {
    const response = await fetch("/auth/reset-password", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email,
        code,
        new_password: newPassword,
      }),
    });

    if (!response.ok) {
      throw new Error(await readAuthErrorMessage(response));
    }

    resetForm.reset();
    resetSection.hidden = true;
    showResetButton.setAttribute("aria-expanded", "false");
    document.querySelector("#login-email").value = email;
    document.querySelector("#login-password").focus();
    window.scrollTo({ top: 0, behavior: "smooth" });
    showAuthStatus(
      "Contraseña actualizada. Ya puedes iniciar sesión con la nueva.",
      "success",
    );
  } catch (error) {
    showAuthStatus(error.message, "error");
  } finally {
    resetSubmitButton.disabled = false;
  }
});

if (new URLSearchParams(window.location.search).has("deleted")) {
  showAuthStatus(
    "Tu cuenta y tus datos se han borrado.",
    "success",
  );
}
