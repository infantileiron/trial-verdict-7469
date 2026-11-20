import math,hashlib,json,itertools
from datetime import datetime,timezone
from src.utils.stats_util import norm_sf,chi2_sf,t_sf_two_sided,Z975
from src.constants.enums import MIN_CLUSTERS_PER_ARM
VERSION='two-proportion-srm-1.0'
CLUSTER_VERSION='cluster-rate-robust-1.0'
PERM_SEED=20261120
PERM_REPS=10000
def _checksum(snapshot):return hashlib.sha256(json.dumps(snapshot,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def calculate(snapshot):
 """个人随机实验：双侧双比例 z 检验 + Wald 区间 + SRM（口径与 two-proportion-srm-1.0 一致）。"""
 exp=snapshot['experiment'];events=snapshot['events']
 exposed={g:{e['user_key'] for e in events if e['group']==g and e['kind']=='exposure'} for g in ('A','B')}
 activated={g:{e['user_key'] for e in events if e['group']==g and e['kind']=='activation'}&exposed[g] for g in ('A','B')}
 n0,n1=[len(exposed[g]) for g in ('A','B')];c0,c1=[len(activated[g]) for g in ('A','B')]
 if min(n0,n1)<2:raise ValueError('每组至少需2名曝光用户，无法计算当前比例差异')
 p0,p1=c0/n0,c1/n1;delta=p1-p0;pooled=(c0+c1)/(n0+n1)
 se0=math.sqrt(pooled*(1-pooled)*(1/n0+1/n1))
 z=delta/se0 if se0 else 0.0;pv=float(2*norm_sf(abs(z))) if se0 else 1.0
 se=math.sqrt(p0*(1-p0)/n0+p1*(1-p1)/n1);margin=float(Z975)*se
 expected=[(n0+n1)*exp['a_ratio'],(n0+n1)*(1-exp['a_ratio'])]
 srm=sum((a-b)**2/b for a,b in zip([n0,n1],expected));srm_p=float(chi2_sf(srm,1))
 approximate=min(n0,n1)>=20 and min(c0,n0-c0,c1,n1-c1)>=5
 matured=datetime.now(timezone.utc)>=datetime.fromisoformat(exp['ends_at'])
 reasons=[]
 if not matured:reasons.append('实验未到预定结束时间，禁止提前发布')
 if srm_p<.01:reasons.append('SRM p<0.01，先排查随机分流与事件采集')
 if not approximate:reasons.append('每组至少20人且成功/失败各至少5人，当前不满足正态近似')
 return dict(n_a=n0,n_b=n1,activated_a=c0,activated_b=c1,rate_a=p0,rate_b=p1,difference=delta,relative_lift=delta/p0 if p0 else None,z=z,p_value=pv,ci_low=max(-1,delta-margin),ci_high=min(1,delta+margin),srm_chi2=srm,srm_p=srm_p,expected_a=expected[0],expected_b=expected[1],matured=matured,approximation_valid=approximate,release_eligible=not reasons,block_reasons=reasons,significant_positive=delta>0 and pv<.05,version=VERSION,checksum=_checksum(snapshot),method='双侧双比例z检验；95%绝对提升Wald区间；SRM卡方df=1；曝光用户去重，激活为曝光子集；差异方向B−A')

def _lcg(seed):
 """确定性伪随机源：保证置换检验可复算（不依赖运行环境随机状态）。"""
 state=seed & 0xFFFFFFFF
 def nxt():
  nonlocal state
  state=(state*1103515245+12345)&0xFFFFFFFF
  return state/0x100000000
 return nxt

def _permutation_p(clusters,obs):
 """企业组别置换检验：在企业总数上重排 A/B 标签，估计 B−A 人均激活差的双侧 p。

 企业是独立单位，置换在簇层面进行而非成员层面，簇大小悬殊时仍保持正确的检验水平。
 组合数不超过2万时枚举全部组合，否则用固定种子蒙特卡洛（含观测排列）。
 """
 values=[c['rate'] for c in clusters];sizes=[c['n'] for c in clusters];groups=[c['group'] for c in clusters]
 k=sum(1 for g in groups if g=='A');m=len(groups)
 def diff(assign):
  ia=[i for i,g in enumerate(assign) if g=='A'];ib=[i for i,g in enumerate(assign) if g=='B']
  na=sum(sizes[i] for i in ia);nb=sum(sizes[i] for i in ib)
  pa=sum(values[i]*sizes[i] for i in ia)/na;pb=sum(values[i]*sizes[i] for i in ib)/nb
  return pb-pa
 comb=math.comb(m,k)
 ge=1;total=0
 if comb<=20000:
  for chosen in itertools.combinations(range(m),k):
   assign=['B']*m
   for i in chosen:assign[i]='A'
   total+=1
   if abs(diff(assign))>=abs(obs)-1e-15:ge+=1
  exact=True
 else:
  rnd=_lcg(PERM_SEED);idx=list(range(m));total=PERM_REPS
  for _ in range(PERM_REPS):
   for i in range(m-1,0,-1):
    j=int(rnd()*(i+1));idx[i],idx[j]=idx[j],idx[i]
   assign=['B']*m
   for i in idx[:k]:assign[i]='A'
   if abs(diff(assign))>=abs(obs)-1e-15:ge+=1
  exact=False
 return ge/(total+1),exact,total+1
def _icc(clusters):
 """按企业聚合的二分类结局组内相关系数（单因素 ANOVA 口径，负 ICC 截断为0并标注原值）。"""
 ns=[c['n'] for c in clusters];ys=[c['x'] for c in clusters]
 N=sum(ns);K=len(ns)
 if K<2 or N<=K:return 0.0,0.0
 grand=sum(ys)/N
 ssb=sum(n*((y/n)-grand)**2 for n,y in zip(ns,ys))
 # 组内平方和：每家企业内 Σ(yij-均值j)² = x·(1-x/n)+(n-x)·(x/n)
 ssw=sum(y*(1-y/n)+(n-y)*(y/n) for n,y in zip(ns,ys))
 msb=ssb/(K-1);msw=ssw/(N-K) if N>K else 0.0
 n0=(N-sum(n*n for n in ns)/N)/(K-1)
 # ANOVA ICC(1) = (MSB-MSW)/(MSB+(n0-1)MSW)
 denom=msb+(n0-1)*msw
 raw=(msb-msw)/denom if denom>0 else 0.0
 return max(0.0,raw),raw

def calculate_cluster(snapshot):
 """企业整群随机实验：以企业为独立单位估计整体人均激活提升与95%置信范围。

 估计量为成员加权（整体人均）激活率差 B−A；方差采用企业簇稳健（夹心）估计，
 自由度用 Welch–Satterthwaite，避免把同企业成员当独立样本而夸大试用效果。
 另附企业组别置换检验、簇级 SRM 与 ICC，并执行小样本门禁。
 """
 exp=snapshot['experiment'];events=snapshot['events']
 membership={m['user_key']:m['enterprise_id'] for m in snapshot.get('members',[])}
 by_ent={}
 for e in events:
  ent=e.get('enterprise_id') or membership.get(e['user_key'])
  if ent is None:continue
  cell=by_ent.setdefault(ent,{'group':e['group'],'exposed':set(),'activated':set()})
  if cell['group']!=e['group']:
   raise ValueError('存在跨组企业事件，采集口径已被污染，拒绝计算')
  if e['kind']=='exposure':cell['exposed'].add(e['user_key'])
  if e['kind']=='activation':cell['activated'].add(e['user_key'])
 clusters=[]
 for ent,c in by_ent.items():
  exposed=c['exposed'];activated=c['activated']&exposed
  if not exposed:continue
  n=len(exposed);x=len(activated)
  clusters.append({'enterprise_id':ent,'group':c['group'],'n':n,'x':x,'rate':x/n})
 ka=sum(1 for c in clusters if c['group']=='A');kb=sum(1 for c in clusters if c['group']=='B')
 if min(ka,kb)<2:raise ValueError('每组至少需2家曝光企业，企业样本不足，无法按独立单位估计')
 def arm(g):return [c for c in clusters if c['group']==g]
 def pooled_rate(cs):
  n=sum(c['n'] for c in cs);x=sum(c['x'] for c in cs)
  return x/n if n else 0.0,n,x
 pa,na,xa=pooled_rate(arm('A'));pb,nb,xb=pooled_rate(arm('B'))
 delta=pb-pa
 # 簇稳健方差：对每家企业的加权贡献做夹心估计，再按臂汇总，天然容纳企业大小悬殊
 def arm_var(cs,rate):
  k=len(cs)
  if k<2:return 0.0
  n=sum(c['n'] for c in cs)
  contrib=[(c['n']/n)*(c['rate']-rate) for c in cs]
  return sum(u*u for u in contrib)*k/(k-1)
 va=arm_var(arm('A'),pa);vb=arm_var(arm('B'),pb)
 se=math.sqrt(va+vb)
 # Welch–Satterthwaite 自由度（簇层面），企业数量少时用 t 分位收宽区间以防虚假显著
 df=(va+vb)**2/(va*va/(ka-1)+vb*vb/(kb-1)) if va+vb>0 else ka+kb-2
 tcrit=_t_ppf_0975(df)
 margin=tcrit*se
 ci_low,ci_high=max(-1,delta-margin),min(1,delta+margin)
 tstat=delta/se if se>0 else 0.0
 p_t=float(t_sf_two_sided(abs(tstat),df)) if se>0 else 1.0
 perm_p,exact,perm_n=_permutation_p(clusters,delta)
 # 簇级 SRM：以企业计数对预期分流比例做卡方，成员数仅作覆盖展示
 total_k=ka+kb
 expected=[total_k*exp['a_ratio'],total_k*(1-exp['a_ratio'])]
 srm=sum((o-e)**2/e for o,e in zip([ka,kb],expected))
 srm_p=float(chi2_sf(srm,1))
 icc,icc_raw=_icc(clusters)
 sizes=[c['n'] for c in clusters]
 mean_size=sum(sizes)/len(sizes)
 matured=datetime.now(timezone.utc)>=datetime.fromisoformat(exp['ends_at'])
 reasons=[]
 if not matured:reasons.append('实验未到预定结束时间，禁止提前发布')
 if srm_p<.01:reasons.append('企业级SRM p<0.01，先排查整群随机分流与企业归属采集')
 if min(ka,kb)<MIN_CLUSTERS_PER_ARM:
  reasons.append(f'每组至少{MIN_CLUSTERS_PER_ARM}家曝光企业（当前A={ka}/B={kb}），企业数量过少禁止发布')
 if se==0:reasons.append('企业间无方差或信息不足，置信区间不可识别，证据不足')
 sig_pos=delta>0 and p_t<.05 and perm_p<.05 and ci_low>0
 if not sig_pos and delta>0:
  reasons.append('企业簇稳健t检验、置换检验或95%置信区间未同时支持正向显著，证据不足')
 return dict(unit='enterprise',clusters_a=ka,clusters_b=kb,members_a=na,members_b=nb,
  activated_a=xa,activated_b=xb,rate_a=pa,rate_b=pb,difference=delta,
  relative_lift=delta/pa if pa else None,cluster_se=se,welch_df=df,t_stat=tstat,
  p_value=p_t,perm_p_value=perm_p,perm_exact=exact,perm_draws=perm_n,
  ci_low=ci_low,ci_high=ci_high,icc=icc,icc_raw=icc_raw,
  cluster_size_min=min(sizes),cluster_size_max=max(sizes),
  cluster_size_mean=mean_size,
  srm_chi2=srm,srm_p=srm_p,srm_level='enterprise',expected_clusters_a=expected[0],
  expected_clusters_b=expected[1],matured=matured,min_clusters_per_arm=MIN_CLUSTERS_PER_ARM,
  release_eligible=not reasons,block_reasons=reasons,significant_positive=sig_pos,
  version=CLUSTER_VERSION,checksum=_checksum(snapshot),
  method='企业为独立随机单位；整体人均激活率差B−A；企业簇稳健夹心方差；Welch–Satterthwaite自由度t区间95%；企业组别置换检验；簇级SRM卡方df=1；ICC(ANOVA)；成员仅在企业内相关，不按个人独立计数')

def _t_ppf_0975(df):
 """t 分布 0.975 分位数：对 df 二分求解（双侧95%区间用）。"""
 from src.utils.stats_util import t_sf_two_sided
 lo,hi=0.0,100.0
 for _ in range(80):
  mid=(lo+hi)/2
  if t_sf_two_sided(mid,df)>0.05:lo=mid
  else:hi=mid
 return (lo+hi)/2

def calculate_for_snapshot(snapshot):
 """worker 与发布复核统一入口：按冻结协议的随机化单位分派算法。"""
 if snapshot['experiment'].get('unit')=='enterprise':
  return calculate_cluster(snapshot)
 return calculate(snapshot)
