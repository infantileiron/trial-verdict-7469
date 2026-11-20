import math,hashlib,json
from datetime import datetime,timezone
from scipy.stats import norm,chi2
VERSION='two-proportion-srm-1.0'
def calculate(snapshot):
 exp=snapshot['experiment'];events=snapshot['events']
 exposed={g:{e['user_key'] for e in events if e['group']==g and e['kind']=='exposure'} for g in ('A','B')}
 activated={g:{e['user_key'] for e in events if e['group']==g and e['kind']=='activation'}&exposed[g] for g in ('A','B')}
 n0,n1=[len(exposed[g]) for g in ('A','B')];c0,c1=[len(activated[g]) for g in ('A','B')]
 if min(n0,n1)<2:raise ValueError('每组至少需2名曝光用户，无法计算当前比例差异')
 p0,p1=c0/n0,c1/n1;delta=p1-p0;pooled=(c0+c1)/(n0+n1)
 se0=math.sqrt(pooled*(1-pooled)*(1/n0+1/n1))
 z=delta/se0 if se0 else 0.0;pv=float(2*norm.sf(abs(z))) if se0 else 1.0
 se=math.sqrt(p0*(1-p0)/n0+p1*(1-p1)/n1);margin=float(norm.ppf(.975))*se
 expected=[(n0+n1)*exp['a_ratio'],(n0+n1)*(1-exp['a_ratio'])]
 srm=sum((a-b)**2/b for a,b in zip([n0,n1],expected));srm_p=float(chi2.sf(srm,1))
 approximate=min(n0,n1)>=20 and min(c0,n0-c0,c1,n1-c1)>=5
 matured=datetime.now(timezone.utc)>=datetime.fromisoformat(exp['ends_at'])
 reasons=[]
 if not matured:reasons.append('实验未到预定结束时间，禁止提前发布')
 if srm_p<.01:reasons.append('SRM p<0.01，先排查随机分流与事件采集')
 if not approximate:reasons.append('每组至少20人且成功/失败各至少5人，当前不满足正态近似')
 return dict(n_a=n0,n_b=n1,activated_a=c0,activated_b=c1,rate_a=p0,rate_b=p1,difference=delta,relative_lift=delta/p0 if p0 else None,z=z,p_value=pv,ci_low=max(-1,delta-margin),ci_high=min(1,delta+margin),srm_chi2=srm,srm_p=srm_p,expected_a=expected[0],expected_b=expected[1],matured=matured,approximation_valid=approximate,release_eligible=not reasons,block_reasons=reasons,significant_positive=delta>0 and pv<.05,version=VERSION,checksum=hashlib.sha256(json.dumps(snapshot,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),method='双侧双比例z检验；95%绝对提升Wald区间；SRM卡方df=1；曝光用户去重，激活为曝光子集；差异方向B−A')
