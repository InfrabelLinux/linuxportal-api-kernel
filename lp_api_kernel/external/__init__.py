from lp_api_kernel.internal import BaseInternalApi
import json
import requests
import urllib3
from lp_api_kernel.cache.remote import RemoteCache
from lp_api_kernel.exceptions import ItemNotFoundException
from requests.adapters import HTTPAdapter
import ssl
from urllib3.contrib import pyopenssl


class InsecureAdapter(HTTPAdapter):

    def __init__(self, *args, insecure_ciphers=(), **kwargs):
        super(InsecureAdapter, self).__init__(*args, **kwargs)
        self.__insecure_ciphers = insecure_ciphers

    def create_ssl_context(self):
        # ctx = create_urllib3_context(ciphers=FORCED_CIPHERS)
        ctx = ssl.create_default_context()
        # allow TLS 1.0 and TLS 1.2 and later (disable SSLv3 and SSLv2)
        ctx.options |= ssl.OP_NO_SSLv2
        ctx.options |= ssl.OP_NO_SSLv3
        ctx.check_hostname = False
        ctx.set_ciphers(self.__insecure_ciphers)
        return ctx

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_context'] = self.create_ssl_context()
        return super(InsecureAdapter, self).init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs['ssl_context'] = self.create_ssl_context()
        return super(InsecureAdapter, self).proxy_manager_for(*args, **kwargs)


class BaseExternalApi(BaseInternalApi):

    def __init__(self, base_url='', auth=(), cache_ttl=3600, insecure_ciphers=(),
                 cache_host=None, cache_db=None, cache_port=None, **kwargs):
        super(BaseExternalApi, self).__init__(**kwargs)
        self.base = base_url
        self.auth = auth
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.c = RemoteCache(host=cache_host, db=cache_db, port=cache_port, ttl=cache_ttl)
        self.__insecure_ciphers = insecure_ciphers

    def url(self, endpoint, endpoint_is_url=False):
        if endpoint == '':
            url = self.base
        else:
            if not endpoint_is_url:
                if endpoint[:1] == '/':
                    url = '{0}/{1}'.format(self.base, endpoint[1:])
                else:
                    url = '{0}/{1}'.format(self.base, endpoint)
            else:
                url = endpoint
        return url

    def insecure_target(self, url, method):
        s = requests.Session()
        s.mount('https://', InsecureAdapter(self.__insecure_ciphers))
        return getattr(s, method)

    def request(self, method='get', endpoint='', data=None, content_type='application/json', headers=None,
                endpoint_is_url=False, target_is_insecure=False, **kwargs):
        method = method.lower()
        url = self.url(endpoint, endpoint_is_url)

        action_f = getattr(requests, method)
        if headers:
            if 'Content-Type' not in headers:
                headers['Content-Type'] = content_type
        else:
            headers = {
                'Content-Type': content_type
            }

        if data:
            if content_type == 'application/json' and not isinstance(data, str):
                data = json.dumps(data)
            if target_is_insecure:
                action_f = self.insecure_target(url, method)
                pyopenssl.extract_from_urllib3()
            result = action_f(url, headers=self.headers(headers), verify=False, data=data,
                              auth=self.auth, **kwargs)
        else:
            if target_is_insecure:
                action_f = self.insecure_target(url, method)
                pyopenssl.extract_from_urllib3()
            result = action_f(url, headers=self.headers(headers), verify=False,
                              auth=self.auth, **kwargs)
        if result.status_code >= 400:
            raise requests.HTTPError('The request generated an error: {0}: {1}'.format(result.status_code, result.text),
                                     response=result)

        return result

    def cached_request(self, method='get', endpoint='', data=None, content_type='application/json', headers=None,
                       endpoint_is_url=False, cache_post=False, params=None, **kwargs):
        url = self.url(endpoint, endpoint_is_url)
        if method == 'get' or (method == 'post' and cache_post):
            try:
                if method == 'post' and data:
                    if content_type == 'application/json' and not isinstance(data, str):
                        data = json.dumps(data)
                    result_text = self.c.get([url, method, data, json.dumps(params)])
                else:
                    result_text = self.c.get([url, method, json.dumps(params)])
            except ItemNotFoundException:
                result = self.request(method=method, endpoint=endpoint, data=data, content_type=content_type,
                                      headers=headers, endpoint_is_url=endpoint_is_url, params=params, **kwargs)
                if method == 'post' and data:
                    if content_type == 'application/json' and not isinstance(data, str):
                        data = json.dumps(data)
                    self.c.set([url, method, data, json.dumps(params)], result.json())
                    result_text = self.c.get([url, method, data, json.dumps(params)])
                else:
                    self.c.set([url, method, json.dumps(params)], result.json())
                    result_text = self.c.get([url, method, json.dumps(params)])
            return json.loads(result_text)
        else:
            result = self.request(method=method, endpoint=endpoint, data=data, content_type=content_type,
                                  headers=headers, endpoint_is_url=endpoint_is_url, params=params, **kwargs)
            return result.json()

    def headers(self, extra_headers=None):
        __headers = {
            'Accept': 'application/json'
        }
        headers = __headers.copy()
        if extra_headers:
            headers.update(extra_headers)
        return headers
