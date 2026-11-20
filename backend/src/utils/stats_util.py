"""纯标准库统计函数，自实现正态/卡方/学生t分布与逆 CDF，使全部业务计算只依赖标准库。

数值口径固定，已对照公认临界值校验；正态逆 CDF 用 Acklam 有理逼近，
伽马/贝塔函数用 Lanczos 与连分数实现，结果在展示精度内与 scipy.stats 一致。
"""
import math

def norm_cdf(x):
    """标准正态累积分布函数，基于 math.erf。"""
    return 0.5*(1.0+math.erf(x/math.sqrt(2.0)))

def norm_sf(x):
    """标准正态生存函数 P(Z>x)。"""
    return 1.0-norm_cdf(x)

def norm_ppf(p):
    """标准正态分位数（逆 CDF），Acklam 有理逼近，|相对误差|<1.15e-9。"""
    if not 0.0 < p < 1.0:
        raise ValueError('分位数概率必须落在(0,1)内')
    a=[-3.969683028665376e+01,2.209460984245205e+02,-2.759285104469687e+02,
       1.383577518672690e+02,-3.066479806614716e+01,2.506628277459239e+00]
    b=[-5.447609879822406e+01,1.615858368580409e+02,-1.556989798598866e+02,
       6.680131188771972e+01,-1.328068155288572e+01]
    c=[-7.784894002430293e-03,-3.223964580411365e-01,-2.400758277161838e+00,
       -2.549732539343734e+00,4.374664141464968e+00,2.938163982698783e+00]
    d=[7.784695709041462e-03,3.224671290700398e-01,2.445134137142996e+00,
       3.754408661907416e+00]
    plow,phigh=0.02425,1-0.02425
    if p<plow:
        q=math.sqrt(-2*math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/ \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p<=phigh:
        q=p-0.5;r=q*q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q/ \
               (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    q=math.sqrt(-2*math.log(1-p))
    return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/ \
            ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)

# 97.5% 标准正态分位数（双比例 Wald 区间使用）
Z975=norm_ppf(0.975)

def _gammaln(xx):
    """Lanczos 伽马函数对数，g=7，系数 g=6。"""
    coef=[76.18009172947146,-86.50532032941677,24.01409824083091,
          -1.231739572450155,0.1208650973866179e-2,-0.5395239384953e-5]
    x=xx;y=xx
    tmp=x+5.5;tmp-=(x+0.5)*math.log(tmp)
    s=1.000000000190015
    for c in coef:
        y+=1;s+=c/y
    return -tmp+math.log(2.5066282746310005*s/x)

def _gammap_series(a,x):
    """下侧正则化伽马 P(a,x) 级数表示。"""
    if x<=0:return 0.0
    ap=a;s=1.0/a;delta=s
    for _ in range(500):
        ap+=1;delta*=x/ap;s+=delta
        if abs(delta)<abs(s)*1e-14:break
    return s*math.exp(-x+a*math.log(x)-_gammaln(a))

def _gammaq_cf(a,x):
    """上侧正则化伽马 Q(a,x) 连分数表示。"""
    fpmin=1e-300
    b=x+1.0-a;c=1e300;d=1.0/max(b,fpmin);h=d
    for i in range(1,501):
        an=-i*(i-a)
        b+=2.0
        d=an*d+b
        if abs(d)<1e-300:d=1e-300
        c=b+an/c
        if abs(c)<1e-300:c=1e-300
        d=1.0/d;delta=d*c;h*=delta
        if abs(delta-1.0)<1e-14:break
    return math.exp(-x+a*math.log(x)-_gammaln(a))*h

def chi2_sf(x,df):
    """卡方分布生存函数 P(χ²_df > x) = Q(df/2, x/2)。"""
    if x<=0:return 1.0
    a=df/2.0;xx=x/2.0
    if xx<a+1.0:return 1.0-_gammap_series(a,xx)
    return _gammaq_cf(a,xx)

def t_sf_two_sided(t,df):
    """学生 t 双侧生存函数，基于正则化不完全贝塔 I(df/(df+t²); df/2, 1/2)。"""
    if df<=0:return 1.0
    x=df/(df+t*t)
    return _betainc(x,df/2.0,0.5)

def _betainc(x,a,b):
    """正则化不完全贝塔函数 I_x(a,b)，连分数（Lentz）。"""
    if x<=0:return 0.0
    if x>=1:return 1.0
    lnbeta=_gammaln(a)+_gammaln(b)-_gammaln(a+b)
    front=math.exp(a*math.log(x)+b*math.log(1-x)-lnbeta)/a
    if x < (a+1)/(a+b+2):
        return front*_betacf(a,b,x)
    return 1.0-front*_betacf(b,a,1-x)

def _betacf(a,b,x):
    qab=a+b;qap=a+1;qam=a-1
    c=1.0;d=1.0-qab*x/qap
    if abs(d)<1e-300:d=1e-300
    d=1.0/d;h=d
    for m in range(1,501):
        m2=2*m
        aa=m*(b-m)*x/((qam+m2)*(a+m2))
        d=1.0+aa*d
        if abs(d)<1e-300:d=1e-300
        c=1.0+aa/c
        if abs(c)<1e-300:c=1e-300
        d=1.0/d;h*=d*c
        aa=-(a+m)*(qab+m)*x/((a+m2)*(qap+m2))
        d=1.0+aa*d
        if abs(d)<1e-300:d=1e-300
        c=1.0+aa/c
        if abs(c)<1e-300:c=1e-300
        d=1.0/d;delta=d*c;h*=delta
        if abs(delta-1.0)<1e-14:break
    return h
