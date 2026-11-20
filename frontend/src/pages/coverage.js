import {state} from '../stores/session.js';import {esc} from '../utils/html.js';import {select} from '../components/common/fields.js';import {pvalue,pp,pct,time} from '../utils/format.js';import {badge} from '../components/common/status.js';
function armCard(title,a){
 return `<div class="armcard"><h3>${esc(title)}</h3>
 <p>企业 <strong>${a.enterprises}</strong> 家</p><p>归属成员 <strong>${a.members}</strong> 人</p>
 <p>曝光 <strong>${a.exposures}</strong> 人 ｜ 激活 <strong>${a.activations}</strong> 人</p>
 <p class="muted">人均激活率 ${a.exposures?pct(a.activations/a.exposures):'—'}</p></div>`}
export function render(){
 const entExps=state.experiments.filter(e=>e.unit==='enterprise');
 const cov=state.selectedCoverage;
 const done=state.decisions.filter(d=>d.state==='done');
 return `<div class="split"><section><h2>企业覆盖、分析依据与上线阻因</h2>
 <p class="notice">选择企业级实验核对整群覆盖：每臂企业数必须达到发布门禁（每组 ≥ 5 家），成员、曝光与激活按锁定组别归集；阻因来自冻结快照的真实复算，页面只读展示。</p>
 ${entExps.length===0?'<p class="notice">暂无企业级实验。</p>':
  cov?`<article class="experiment">
  <div class="eyebrow">${esc(cov.experiment.code)} · 观察期${cov.experiment.ends_at<new Date().toISOString()?'已结束':'未结束'}</div>
  <h3>${esc(cov.experiment.name)}</h3>
  <div class="armgrid">${armCard('A 组（锁定企业）',cov.arm_a)}${armCard('B 组（锁定企业）',cov.arm_b)}</div>
  <h3>首曝锁定证据（${cov.locked.length} 家）</h3>
  <div class=scroll><table><thead><tr><th>企业ID</th><th>锁定组</th><th>锁定时间(上海)</th><th>首曝事件ID</th></tr></thead>
  <tbody>${cov.locked.map(x=>`<tr><td>${esc(x.enterprise_id)}</td><td>${esc(x.group)}</td><td>${time(x.locked_at)}</td><td>${esc(x.locked_by_event??'—')}</td></tr>`).join('')}</tbody></table></div>
  </article>`:'<p class="notice">从右侧选择一个企业级实验加载覆盖。</p>'}
 <h3 style="margin-top:28px">已完成裁决的分析依据与阻因</h3>
 ${done.length?done.map(d=>{const r=d.result;const ent=r.unit==='enterprise';
  return `<article class="experiment"><div class="eyebrow">裁决 #${d.id} · ${esc(d.snapshot.experiment.code)} ${badge(d.state)} · ${ent?'企业整群随机':'个人随机'}</div>
  <p class="meta">算法版本 ${esc(r.version)} ｜ 校验和 ${esc(r.checksum.slice(0,24))}…</p>
  <p>整体人均激活提升 B−A = <strong>${pp(r.difference)}</strong>，95% 区间 [${pp(r.ci_low)}, ${pp(r.ci_high)}]；${ent?`簇稳健 t p=${pvalue(r.p_value)}，企业置换 p=${pvalue(r.perm_p_value)}，每臂企业 ${r.clusters_a}/${r.clusters_b} 家`:`双比例 z p=${pvalue(r.p_value)}`}</p>
  <p class="notice ${r.release_eligible?'good':'warning'}">${r.release_eligible?'无上线阻因，门禁全部通过（发布仍需负责人签核）。':'上线阻因：'+r.block_reasons.map(esc).join('；')}</p></article>`}).join(''):'<p class="notice">尚无完成的裁决。</p>'}
 </section>
 <aside><h2>核对企业覆盖</h2>
 <form id="coverageForm">${select('企业级实验','experiment_id',entExps.map(e=>[e.id,e.code+' · '+e.name]))}
 <button class="primary">加载覆盖视图</button></form>
 <p class="muted" style="margin-top:18px">门禁口径：未到观察期、企业级 SRM p&lt;0.01、每臂曝光企业 &lt; 5、簇间方差不可识别，任一命中即拒绝上线；个人实验继续保留双比例 z 检验，不在此页覆盖范围。</p>
 </aside></div>`}
