const downloadExportButton = document.querySelector(
  "#download-export-button",
);


function getExportFilename(contentDisposition) {
  const match = contentDisposition?.match(
    /filename="([^"]+)"/i,
  );

  return match?.[1] || "fitness_tracker_export.json";
}


async function downloadDataExport() {
  downloadExportButton.disabled = true;
  downloadExportButton.textContent = "Generando exportación…";

  try {
    const response = await apiFetch("/exports/fitness-tracker.json");

    if (!response.ok) {
      throw new Error(
        "No se pudo generar la exportación. Inténtalo de nuevo.",
      );
    }

    const exportBlob = await response.blob();
    const downloadUrl = URL.createObjectURL(exportBlob);
    const downloadLink = document.createElement("a");

    downloadLink.href = downloadUrl;
    downloadLink.download = getExportFilename(
      response.headers.get("content-disposition"),
    );

    document.body.appendChild(downloadLink);
    downloadLink.click();
    downloadLink.remove();

    URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    window.alert(error.message);
  } finally {
    downloadExportButton.disabled = false;
    downloadExportButton.textContent = "Descargar exportación";
  }
}


async function initializeHome() {
  if (!getAccessToken()) {
    window.location.replace("/static/login/?next=%2F");
    return;
  }

  try {
    const response = await apiFetch("/auth/me");

    if (response.status === 401) {
      // apiFetch ya limpia el token y redirige al login.
      return;
    }

    if (!response.ok) {
      throw new Error("No se pudo verificar la sesión.");
    }

    document.body.style.visibility = "visible";

    downloadExportButton.addEventListener("click", downloadDataExport);
  } catch (error) {
    // No mostramos el panel si ni siquiera pudimos comprobar la sesión.
    document.body.textContent =
      `${error.message} Comprueba la conexión y recarga la página.`;
    document.body.style.visibility = "visible";
  }
}

initializeHome();;