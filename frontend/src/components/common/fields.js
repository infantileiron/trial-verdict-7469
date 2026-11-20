import {esc} from '../../utils/html.js';
export const field=(label,name,type='text',extra='')=>`<label>${label}<input name=${name} type=${type} ${extra}></label>`;export const select=(label,name,options)=>`<label>${label}<select name=${name}>${options.map(([v,t])=>`<option value="${esc(v)}">${esc(t)}</option>`).join('')}</select></label>`;
