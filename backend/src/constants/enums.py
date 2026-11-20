ROLES=('admin','analyst','viewer')
GROUPS=('A','B')
EVENT_KINDS=('exposure','activation')
STATES=('queued','running','done','failed')
ACTIONS=('publish_b','keep_a')
# 实验随机化单位：user=个人随机（旧实验口径，保留），enterprise=企业整群随机（新实验）
UNITS=('user','enterprise')
# 企业级实验发布前每组至少需要的曝光企业数，避免企业数量过少导致虚假显著
MIN_CLUSTERS_PER_ARM=5
