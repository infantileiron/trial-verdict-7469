export function values(form){return Object.fromEntries(new FormData(form))}export function feedback(text){document.querySelector('#error').textContent=text}
