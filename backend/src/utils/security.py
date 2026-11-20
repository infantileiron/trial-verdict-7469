import hashlib,hmac,os,time,jwt
KEY=os.environ['JWT_SECRET']
def hash_password(p):return hashlib.pbkdf2_hmac('sha256',p.encode(),b'trial-verdict-demo-v1',160000).hex()
def verify(p,h):return hmac.compare_digest(hash_password(p),h)
def token(u):return jwt.encode({'sub':str(u.id),'exp':int(time.time())+28800},KEY,algorithm='HS256')
