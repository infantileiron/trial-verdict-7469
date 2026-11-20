import {api,post} from './api/client.js';import {state} from './stores/session.js';import {routes,page} from './router/index.js';import {values,feedback} from './hooks/form.js';import * as experiments from './pages/experiments.js';import * as enterprises from './pages/enterprises.js';import * as events from './pages/events.js';import * as decisions from './pages/decisions.js';import * as releases from './pages/releases.js';import * as coverage from './pages/coverage.js';
const pages=[experiments,enterprises,events,decisions,releases,coverage];
const root=document.querySelector('#app');
async function load(){
 [state.experiments,state.events,state.decisions,state.enterprises]=await Promise.all(['/experiments','/events','/decisions','/enterprises'].map(x=>api(x)));
 const entExp=state.experiments.filter(e=>e.unit==='enterprise');
 state.coverage=await Promise.all(entExp.map(e=>api('/experiments/'+e.id+'/coverage')));
 state.selected=state.decisions.find(d=>d.id===state.selected?.id)||state.decisions[0]||null;
 if(!state.selectedCoverage||!state.coverage.some(c=>c.experiment?.id===state.selectedCoverage.experiment?.id)){
  state.selectedCoverage=state.coverage[0]||null;
 }
}
function login(){root.innerHTML=`<div class="login"><section class="cover"><div class="eyebrow">PRISM / EXPERIMENT CONTROL ROOM</div><h1>一次激活，<br>值得怎样的<br><em>发布决定。</em></h1><p>棱镜协作软件 · 增长实验室<br>个人随机与企业整群随机并存。<br>从试用事件走到有依据的产品裁决。</p><div class="ruler">A ━━━━━━ B / 企业为独立单位</div></section><section><div class="eyebrow">TRIAL VERDICT / 2026</div><h2>进入实验裁决室</h2><form id="login"><label>工作邮箱<input name="email" type="email" value="analyst@demo.local" required></label><label>密码<input name="password" type="password" value="Demo123!" required></label><button class="primary">打开实验工作簿</button></form><p id="error" class="error"></p><p>演示账号：角色@demo.local<br>admin / analyst / viewer · Demo123!</p></section></div>`;document.querySelector('form').onsubmit=e=>{e.preventDefault();run(async()=>{let d=await post('/auth/login',values(e));localStorage.setItem('token',d.token);state.user=d.user;await load();render()})}}
function render(){let n=Math.min(pages.length-1,Math.max(0,page()));root.innerHTML=`<header><div class="brand">棱镜 / 实验裁决室 <span class="eyebrow">TRIAL VERDICT</span></div><div>${state.user.email} · ${state.user.role} <button id="logout" ${pending?'disabled':''}>退出</button></div></header><div class="layout"><nav>${routes.map((r,i)=>`<button data-nav="${i}" class="${i===n?'active':''}"><span>0${i+1}</span> ${r}</button>`).join('')}<p class="eyebrow">EVIDENCE BEFORE RELEASE<br>02 / CLUSTER TRIAL</p></nav><main><div class="intro"><div class="eyebrow">GROWTH RESEARCH / 0${n+1}</div><h1>${routes[n]}</h1><p>把采集、检验和发布连成一条可复核的证据链。</p></div><p id="error" class="error"></p>${pages[n].render()}</main></div>`;bind();const protocol=document.querySelector('#decision [name=experiment_id]');if(protocol&&state.selected)protocol.value=String(state.selected.experiment_id);window.scrollTo(0,0);if(state.user.role==='viewer')document.querySelectorAll('form button').forEach(b=>{b.disabled=true;b.textContent='观察员只读'})}
let pending=0;async function run(fn){pending++;document.querySelector('#logout')?.setAttribute('disabled','');try{await fn()}catch(e){feedback(e.message)}finally{pending--;if(!pending)document.querySelector('#logout')?.removeAttribute('disabled')}}
const stamp=s=>new Date(s+'+08:00').toISOString();
// 每个表单独立闭包绑定，避免共享变量在重渲染后被后续表单覆盖
function bindForm(id,handler){const form=document.querySelector('#'+id);if(form)form.onsubmit=e=>{e.preventDefault();run(()=>handler(values(e),form))};}
function bind(){
 document.querySelectorAll('[data-nav]').forEach(b=>b.onclick=()=>location.hash=b.dataset.nav);
 document.querySelector('#logout').onclick=()=>{localStorage.removeItem('token');state.user=null;login()};
 bindForm('experiment',d=>{d.a_ratio=Number(d.a_ratio);d.starts_at=stamp(d.starts_at);d.ends_at=stamp(d.ends_at);return post('/experiments',d).then(load).then(render);});
 bindForm('enterprise',d=>post('/enterprises',d).then(load).then(render));
 bindForm('member',d=>post('/enterprises/members',d).then(load).then(render));
 bindForm('event',d=>{d.experiment_id=Number(d.experiment_id);if(!d.group)delete d.group;d.occurred_at=stamp(d.occurred_at);return post('/events',d).then(load).then(render);});
 bindForm('decision',d=>post('/decisions',{experiment_id:Number(d.experiment_id)}).then(created=>{state.selected=created;}).then(load).then(render));
 bindForm('rationale',d=>api('/decisions/'+d.decision_id+'/rationale',{method:'PUT',body:JSON.stringify({rationale:d.rationale})}).then(load).then(render));
 bindForm('coverageForm',d=>api('/experiments/'+Number(d.experiment_id)+'/coverage').then(cov=>{state.selectedCoverage=cov;}).then(render));
 document.querySelectorAll('[data-decision]').forEach(b=>b.onclick=()=>run(async()=>{state.selected=await api('/decisions/'+b.dataset.decision);render()}));
 document.querySelectorAll('[data-release]').forEach(b=>b.onclick=()=>run(async()=>{await post('/decisions/'+b.dataset.release+'/publish',{action:b.dataset.action});await load();render()}));
 let refresh=document.querySelector('#refresh');if(refresh)refresh.onclick=()=>run(async()=>{await load();render()});
 let retry=document.querySelector('#retry');if(retry)retry.onclick=()=>run(async()=>{let id=state.selected.id;state.selected=await api('/decisions/'+id+'/retry',{method:'POST'});await load();render()});
 let download=document.querySelector('#download');if(download)download.onclick=()=>run(async()=>{let d=await api('/decisions/'+state.selected.id+'/export');let u=URL.createObjectURL(new Blob([JSON.stringify(d,null,2)],{type:'application/json'}));let a=document.createElement('a');a.href=u;a.download='trial-verdict-'+d.id+'.json';a.click();URL.revokeObjectURL(u)});
}
window.onhashchange=()=>{if(state.user)render()};if(localStorage.getItem('token'))run(async()=>{try{state.user=await api('/me');await load();render()}catch(e){localStorage.removeItem('token');login();feedback(e.message)}});else login();
