// Helpers compartidos para estados de carga y error en listas.

function renderListLoading(element, className, message = "Cargando…") {
  element.className = `${className} empty-state`;
  element.textContent = message;
}


function renderListError(element, className, message, retry) {
  element.className = `${className} empty-state`;
  element.replaceChildren();

  const content = document.createElement("div");
  content.className = "list-error-action";

  const text = document.createElement("p");
  text.textContent = message;

  const button = document.createElement("button");
  button.type = "button";
  button.className = "secondary-button";
  button.textContent = "Reintentar";
  button.addEventListener("click", retry);

  content.append(text, button);
  element.append(content);
}
