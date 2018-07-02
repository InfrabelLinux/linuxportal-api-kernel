from lp_api_kernel.cache import LpCache
from lp_api_kernel.exceptions import InvalidParameterException, ItemNotFoundException
import json


class RemoteCache(LpCache):

    def set(self, key_parts_s, data):
        key = self.mk_key(key_parts_s)
        if not isinstance(data, str):
            data = json.dumps(data)
        if self.a.set(key, data, ex=self.ttl):
            return True
        raise InvalidParameterException('Failed to set {0}.'.format(key))

    def get(self, key_parts_s, parse=False):
        key = self.mk_key(key_parts_s)
        data = self.a.get(key)
        if not data:
            raise ItemNotFoundException('No item with key {0} in the cache.'.format(key))
        if parse:
            return json.loads(data.decode('utf-8'))
        return data.decode('utf-8')
