import redis
import hashlib


class LpCache:

    def __init__(self, host, port, db, ttl=300):
        self.a = redis.StrictRedis(host=host, port=port, db=db)
        self.ttl = ttl

    def mk_key(self, parts):
        return hashlib.sha1(''.join(parts).encode('utf-8')).hexdigest()

