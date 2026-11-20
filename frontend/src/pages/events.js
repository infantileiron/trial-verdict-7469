import {state} from '../stores/session.js';import {table} from '../components/common/table.js';import {field,select} from '../components/common/fields.js';import {time} from '../utils/format.js';import {esc} from '../utils/html.js';import {UNITS} from '../constants/enums.js';
export function render(){
 return `<div class="split"><section><h2>采集链核对 / ${state.events.length} 条</h2>
 <p class="notice">个人实验：同一用户只归属一组，组别手选并校验跨组。企业实验：成员按企业归属采集，组别在企业首曝时锁定，跨组事件 409 拒收；列表最近 80 条，全量进入冻结快照。</p>
 ${table(['用户','实验','企业ID','组别','事件','上海时间'],state.events.slice(0,80).map(e=>[e.user_key,state.experiments.find(x=>x.id===e.experiment_id)?.code,e.enterprise_id??'—',e.group,e.kind==='exposure'?'曝光':'激活',time(e.occurred_at)]))}
 </section><aside><h2>录入试用事件</h2><form id="event">
 ${select('实验','experiment_id',state.experiments.map(e=>[e.id,e.name+'（'+(UNITS[e.unit]||UNITS.user)+'）']))}
 ${field('成员/用户唯一键','user_key','text','required')}
 <label>随机组别（仅个人实验生效，企业实验由锁定决定）<select name="group"><option value="">企业实验留空</option><option value="A">A · 原引导</option><option value="B">B · 新引导</option></select></label>
 ${select('事件类型','kind',[['exposure','曝光'],['activation','激活']])}
 ${field('事件时间 · 上海','occurred_at','datetime-local','required')}
 <p class="muted" id="event-hint">企业实验请先在「企业分组」登记企业与成员。</p>
 <button class="primary">核对并入库</button></form></aside></div>`}
