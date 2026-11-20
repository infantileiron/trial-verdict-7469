/** @typedef {{id:number,code:string,name:string,starts_at:string,ends_at:string,a_ratio:number,hypothesis:string}} Experiment */
/** @typedef {{id:number,experiment_id:number,user_key:string,group:'A'|'B',kind:'exposure'|'activation',occurred_at:string}} TrialEvent */
/** @typedef {{id:number,experiment_id:number,state:string,result:object,snapshot:object,rationale:string,action:string,published_at:string}} Decision */
export const CONTRACT_VERSION='1.0';
