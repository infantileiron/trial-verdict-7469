export function values(form){const node=form?.target??form;return Object.fromEntries(new window.FormData(node))}export function feedback(text){document.querySelector('#error').textContent=text}
