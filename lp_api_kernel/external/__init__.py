from lp_api_kernel.internal import BaseInternalApi
import json
import requests
import urllib3
from lp_api_kernel.cache.remote import RemoteCache
from lp_api_kernel.exceptions import ItemNotFoundException
from requests.adapters import HTTPAdapter
import ssl
from urllib3.contrib import pyopenssl
from os import environ


class InsecureAdapter(HTTPAdapter):
    """
    Sometimes, your remote is too insecure for Python.
    Provide the insecure_ciphers array to .__init__() (with a single string value
    containing supported ciphers) and it will fallback to those.
    """

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
    """
    An API that is geared to connecting with remotes. Supports insecure remotes,
    remotes that require authentication and caching (using Redis).
    """

    def __init__(self, *args, base_url='', auth=(), cache_ttl=3600, insecure_ciphers=(),
                 cache_host=environ.get('CACHE_HOST'), cache_db=environ.get('CACHE_DATABASE'),
                 cache_port=environ.get('CACHE_PORT'), **kwargs):
        """
        :param base_url: URL base (e.g. https://my.app/application) where the remote parameter is glued to.
        :param auth: (username, password)
        :param cache_ttl: default 300 (seconds)
        :param insecure_ciphers: list containing a single string listing the insecure ciphers you have to support
                                 (optional!)
        :param cache_host: Redis host.
        :param cache_db: Redis DB.
        :param cache_port: Redis port.
        :param kwargs:
        """
        super(BaseExternalApi, self).__init__(*args, **kwargs)
        self.base = base_url
        self.auth = auth
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.c = RemoteCache(host=cache_host, db=cache_db, port=cache_port, ttl=cache_ttl)
        self.__insecure_ciphers = insecure_ciphers

    def url(self, endpoint, endpoint_is_url=False):
        """
        From an endpoint and self.base, create an URL.
        :param endpoint:
        :param endpoint_is_url:
        :return:
        """
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

    def request(self, method, endpoint, *args, data=None, content_type='application/json', headers=None,
                endpoint_is_url=False, target_is_insecure=False, **kwargs):
        """
        Perform a request. Kind of a pass-through to requests.request, but with some goodies. `**kwargs` and `*args`
        are passed to requests.request.
        :param method:
        :param endpoint:
        :param args:
        :param data:
        :param content_type:
        :param headers:
        :param endpoint_is_url:
        :param target_is_insecure: will use the insecure adapter with the insecure ciphers
        :param kwargs:
        :return:
        """
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
            result = action_f(url, *args, headers=self.headers(headers), verify=False, data=data,
                              auth=self.auth, **kwargs)
        else:
            if target_is_insecure:
                action_f = self.insecure_target(url, method)
                pyopenssl.extract_from_urllib3()
            result = action_f(url, *args, headers=self.headers(headers), verify=False,
                              auth=self.auth, **kwargs)
        if result.status_code >= 400:
            raise requests.HTTPError('The request generated an error: {0}: {1}'.format(result.status_code, result.text),
                                     response=result)

        return result.json()

    def cached_request(self, method, endpoint, *args, data=None, content_type='application/json', headers=None,
                       endpoint_is_url=False, cache_post=False, params=None, **kwargs):
        """
        Perform a request against the cache. If not present, will be added. Can also cache post requests for
        non-REST API's.
        :param method:
        :param endpoint:
        :param args:
        :param data:
        :param content_type:
        :param headers:
        :param endpoint_is_url:
        :param cache_post:
        :param params:
        :param kwargs:
        :return:
        """
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
                result = self.request(*args, method=method, endpoint=endpoint, data=data, content_type=content_type,
                                      headers=headers, endpoint_is_url=endpoint_is_url, params=params, **kwargs)
                if method == 'post' and data:
                    if content_type == 'application/json' and not isinstance(data, str):
                        data = json.dumps(data)
                    self.c.set([url, method, data, json.dumps(params)], result)
                    result_text = self.c.get([url, method, data, json.dumps(params)])
                else:
                    self.c.set([url, method, json.dumps(params)], result)
                    result_text = self.c.get([url, method, json.dumps(params)])
            return json.loads(result_text)
        else:
            result = self.request(*args, method=method, endpoint=endpoint, data=data, content_type=content_type,
                                  headers=headers, endpoint_is_url=endpoint_is_url, params=params, **kwargs)
            return result

    def headers(self, extra_headers=None):
        __headers = {
            'Accept': 'application/json'
        }
        headers = __headers.copy()
        if extra_headers:
            headers.update(extra_headers)
        return headers
