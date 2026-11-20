import {state} from '../stores/session.js';import {esc} from '../utils/html.js';import {badge} from '../components/common/status.js';import {select} from '../components/common/fields.js';import {pct,pp,pvalue,num3} from '../utils/format.js';
function clusterPanel(r){
 return `<div class="comparison"><div><span>原方案 A · ${r.clusters_a} 家企业 / ${r.members_a} 人</span><strong>${pct(r.rate_a)}</strong><small>激活 ${r.activated_a} 人</small></div>
 <div class="delta"><span>整体人均激活提升 B − A</span><strong>${pp(r.difference)}</strong><small>95% t 区间 [${pp(r.ci_low)}, ${pp(r.ci_high)}]</small></div>
 <div><span>新方案 B · ${r.clusters_b} 家企业 / ${r.members_b} 人</span><strong>${pct(r.rate_b)}</strong><small>激活 ${r.activated_b} 人</small></div></div>
 <svg viewBox="0 0 700 170" role="img" aria-label="企业簇稳健检验结果">
 <text x="0" y="35">A</text><rect x="35" y="12" width="${r.rate_a*600}" height="32" fill="var(--muted)"/>
 <text x="0" y="105">B</text><rect x="35" y="82" width="${r.rate_b*600}" height="32" fill="var(--accent)"/>
 <text x="350" y="38">t=${num3(r.t_stat)} (df=${num3(r.welch_df)}) / 双侧 p=${pvalue(r.p_value)}</text>
 <text x="350" y="108">企业置换 p=${pvalue(r.perm_p_value)}（${r.perm_exact?'精确枚举':r.perm_draws+' 次固定种子重排'}）</text>
 <text x="35" y="158">企业级 SRM χ²=${num3(r.srm_chi2)} p=${pvalue(r.srm_p)} ｜ ICC=${num3(r.icc)} ｜ 企业规模 ${r.cluster_size_min}~${r.cluster_size_max} 人（均值 ${num3(r.cluster_size_mean)}）</text>
 </svg>
 <p class="notice ${r.release_eligible?'good':'warning'}">${r.release_eligible?'企业数、簇级 SRM 与观察期门禁通过；发布仍须负责人裁决。':r.block_reasons.map(esc).join('；')}</p>
 <p class="meta">分析依据（${esc(r.version)}）：${esc(r.method)}</p>`}
function userPanel(r){
 return `<div class="comparison"><div><span>原引导 A</span><strong>${pct(r.rate_a)}</strong><small>${r.activated_a} / ${r.n_a} 人</small></div>
 <div class="delta"><span>绝对提升 B − A</span><strong>${pp(r.difference)}</strong><small>95% CI [${pp(r.ci_low)}, ${pp(r.ci_high)}]</small></div>
 <div><span>新引导 B</span><strong>${pct(r.rate_b)}</strong><small>${r.activated_b} / ${r.n_b} 人</small></div></div>
 <svg viewBox="0 0 700 150" role="img" aria-label="两组激活率对比"><text x="0" y="40">A</text><rect x="35" y="15" width="${r.rate_a*600}" height="35" fill="var(--muted)"/><text x="0" y="110">B</text><rect x="35" y="85" width="${r.rate_b*600}" height="35" fill="var(--accent)"/><text x="350" y="45">z=${num3(r.z)} / p=${pvalue(r.p_value)}</text><text x="350" y="110">SRM p=${pvalue(r.srm_p)}</text></svg>
 <p class="notice ${r.release_eligible?'good':'warning'}">${r.release_eligible?'采集分流与观察期门禁通过。发布仍须负责人结合效应与业务价值裁决。':r.block_reasons.map(esc).join('；')}</p>
 <p>预期 A/B：${r.expected_a.toFixed(1)} / ${r.expected_b.toFixed(1)}；SRM χ²=${num3(r.srm_chi2)}；双侧 α=0.05。</p>`}
export function render(){let d=state.selected,r=d?.result;const isEnt=r?.unit==='enterprise';
 return `<div class="split"><section><h2>转化提升，需要完整证据</h2>${d?`<div class="eyebrow">裁决 #${d.id} / ${esc(d.snapshot.experiment.code)} ${badge(d.state)} · ${isEnt?'企业整群随机':'个人随机'}</div>${r?(isEnt?clusterPanel(r):userPanel(r)):`<p class="notice ${d.state==='failed'?'warning':''}">${esc(d.error||'后台队列处理中；刷新可查看结果。')}</p>${d.state==='failed'?'<button id="retry">失败重试（沿用冻结快照）</button>':''}`}`:'<p class="notice">选择实验并提交，后台将冻结协议与样本后计算。</p>'}<h3>裁决档案</h3><div class="records">${state.decisions.map(x=>`<button data-decision="${x.id}">#${x.id} ${esc(x.snapshot.experiment.code)} · ${esc(x.state)}${x.snapshot.experiment.unit==='enterprise'?' · 企业':''}</button>`).join('')}</div></section><aside><h2>提交固定样本分析</h2><form id="decision">${select('实验协议','experiment_id',state.experiments.map(e=>[e.id,e.name]))}<p>个人：双比例 z 检验 + SRM<br>企业：簇稳健方差 + t 区间 + 置换检验<br>企业每臂不足 5 家、未到期、SRM 异常均禁止发布</p><button class="primary">提交后台检验</button></form><button id="refresh">刷新计算状态</button>${d?`<p class="meta" style="margin-top:18px">校验和 ${esc((r?.checksum||'').slice(0,16))}…<br>状态：${esc(d.state)}｜排队→运行→完成/失败全程可查</p>`:''}</aside></div>`}
