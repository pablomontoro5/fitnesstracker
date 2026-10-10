// Registro del service worker y botón «Instalar la app».
// Se carga en todas las páginas; no hace nada si el navegador no lo admite.

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Sin service worker la aplicación sigue funcionando con normalidad.
    });
  });
}

(() => {
  const installButton = document.querySelector("#install-app-button");
  let installPrompt = null;

  if (!installButton) {
    return;
  }

  window.addEventListener("beforeinstallprompt", (event) => {
    // El navegador ofrece instalar: guardamos el evento y mostramos el botón.
    event.preventDefault();
    installPrompt = event;
    installButton.hidden = false;
  });

  installButton.addEventListener("click", async () => {
    if (!installPrompt) {
      return;
    }

    installButton.disabled = true;
    installPrompt.prompt();
    await installPrompt.userChoice;
    installPrompt = null;
    installButton.hidden = true;
    installButton.disabled = false;
  });

  window.addEventListener("appinstalled", () => {
    installPrompt = null;
    installButton.hidden = true;
  });
})();
