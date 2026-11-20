export const pct=n=>(n*100).toFixed(2)+'%';
export const pp=n=>(n*100).toFixed(2)+' pp';
export const pvalue=n=>n<.001?n.toExponential(2):n.toFixed(4);
export const time=s=>s?new Date(s).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}):'—';
export const num3=n=>(n??0).toFixed(3);
