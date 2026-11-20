import {state} from '../stores/session.js';import {esc} from '../utils/html.js';import {field,select} from '../components/common/fields.js';import {UNITS} from '../constants/enums.js';
export function render(){
 const enterpriseExps=state.experiments.filter(e=>e.unit==='enterprise');
 return `<div class="split"><section><h2>企业归属与整群随机依据</h2>
 <p class="notice">成员唯一归属一家企业，采集沿用该归属；企业组别在<strong>首次曝光</strong>时按 sha256(实验盐+企业键) 锁定，跨组事件服务端拒收。共登记 ${state.enterprises.length} 家企业。</p>
 ${table2(['企业键','企业名称','成员数'],state.enterprises.map(e=>[e.key,e.name,e.members]))}
 <h3>企业级实验协议</h3>
 ${enterpriseExps.length?table2(['实验编号','名称','观察期结束(上海)','A 占比','已锁定企业'],
   enterpriseExps.map(e=>[e.code,e.name,new Date(e.ends_at).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}),
     (e.a_ratio*100).toFixed(0)+'%',e.enterprise_count??0]))
   :'<p class="notice">尚无企业级实验。右侧新建时随机化单位请选「企业整群随机」。</p>'}
 </section>
 <aside><h2>登记企业</h2>
 <form id="enterprise">${field('企业唯一键','key','text','required maxlength=80')}${field('企业名称','name','text','required minlength="2"')}
 <button class="primary">登记企业</button></form>
 <h2 style="margin-top:26px">成员归属企业</h2>
 <form id="member">${select('企业','enterprise_key',state.enterprises.map(e=>[e.key,e.name+' ('+e.key+')']))}
 ${field('成员唯一键','user_key','text','required maxlength=80')}<button class="primary">冻结成员归属</button></form>
 <h2 style="margin-top:26px">新建企业级实验</h2>
 <form id="experiment">${field('实验编号','code','text','required')}${field('实验名称','name','text','required minlength="2"')}
 ${field('开始时间 · 上海','starts_at','datetime-local','required')}${field('结束时间 · 上海','ends_at','datetime-local','required')}
 ${field('A 组预期企业占比','a_ratio','number','required min="0.1" max="0.9" step="0.01" value="0.5"')}
 <label>随机化单位<select name="unit">${Object.entries(UNITS).map(([v,t])=>`<option value="${v}"${v==='enterprise'?' selected':''}>${esc(t)}</option>`).join('')}</select></label>
 <label>预先假设<textarea name="hypothesis" required minlength="5" rows="3"></textarea></label>
 <button class="primary">保存企业实验协议</button></form>
 </aside></div>`}
function table2(headers,rows){return `<div class=scroll><table><thead><tr>${headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead>
 <tbody>${rows.map(r=>`<tr>${r.map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')||'<tr><td>暂无记录。</td></tr>'}</tbody></table></div>`}
