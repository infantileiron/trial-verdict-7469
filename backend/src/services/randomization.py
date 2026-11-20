"""企业整群随机的纯函数：确定性哈希分组，不依赖数据库或进程随机状态。

分组依据 sha256(实验编号|实验开始时间|企业键) 的摘要：同一企业在同一实验内
永远映射到同一组，重试与并发请求得到一致结果，可离线复算；
预期 A 组占比由实验协议 a_ratio 决定。首次曝光时把映射落库锁定，之后只读锁定值。
"""
import hashlib

def hash_group(exp_code,exp_starts_at,enterprise_key,a_ratio):
 digest=hashlib.sha256(f'{exp_code}|{exp_starts_at}|{enterprise_key}'.encode()).hexdigest()
 # 取前64位摘要做均匀分桶，按协议 A 组占比切分，保证可离线复算
 bucket=int(digest[:16],16)/0x10000000000000000
 return 'A' if bucket<a_ratio else 'B'
