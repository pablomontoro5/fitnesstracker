const downloadBackupButton = document.querySelector("#download-backup-button");
const restoreForm = document.querySelector("#restore-form");
const restoreFileInput = document.querySelector("#restore-file");
const restoreButton = document.querySelector("#restore-button");
const statusMessage = document.querySelector("#backup-status");

function showStatus(message, type) {
  statusMessage.textContent = message;
  statusMessage.className = `status-message ${type}`;
}

function clearStatus() {
  statusMessage.textContent = "";
  statusMessage.className = "status-message";
}

async function readErrorMessage(response) {
  try {
    const payload = await response.json();
    return payload.detail || "No se pudo completar la operación.";
  } catch {
    return "No se pudo completar la operación.";
  }
}

async function downloadDatabaseBackup() {
  clearStatus();
  downloadBackupButton.disabled = true;

  try {
    const response = await fetch("/backups/database", {
      method: "POST",
    });

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    const backup = await response.blob();
    const contentDisposition = response.headers.get("content-disposition") || "";
    const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
    const filename = filenameMatch?.[1] || "fitness_tracker_backup.db";
    const downloadUrl = URL.createObjectURL(backup);
    const link = document.createElement("a");

    link.href = downloadUrl;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(downloadUrl);

    showStatus("Copia de seguridad descargada correctamente.", "success");
  } catch (error) {
    showStatus(error.message, "error");
  } finally {
    downloadBackupButton.disabled = false;
  }
}

async function restoreDatabase(event) {
  event.preventDefault();
  clearStatus();

  const file = restoreFileInput.files[0];

  if (!file) {
    showStatus("Selecciona una copia de seguridad .db.", "error");
    return;
  }

  if (!file.name.toLowerCase().endsWith(".db")) {
    showStatus("Debes seleccionar un archivo con extensión .db.", "error");
    return;
  }

  const confirmed = window.confirm(
    "Vas a reemplazar todos los datos actuales por los datos de esta copia. " +
      "Antes se creará una copia de seguridad automática. ¿Quieres continuar?"
  );

  if (!confirmed) {
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  restoreButton.disabled = true;

  try {
    const response = await fetch("/restores/database", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    const result = await response.json();
    restoreForm.reset();
    showStatus(
      `${result.message} Copia de protección creada: ${result.safety_backup_filename}.`,
      "success"
    );
  } catch (error) {
    showStatus(error.message, "error");
  } finally {
    restoreButton.disabled = false;
  }
}

downloadBackupButton.addEventListener("click", downloadDatabaseBackup);
restoreForm.addEventListener("submit", restoreDatabase);