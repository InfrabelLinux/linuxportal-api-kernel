from abc import ABCMeta, abstractmethod
from functools import wraps
from flask import logging
from lp_api_kernel.exceptions import MissingParameterException, InvalidParameterException
import re


class BaseInternalApi:
    __metaclass__ = ABCMeta

    def __init__(self, api_class=None, **kwargs):
        if api_class:
            self.a = api_class(**kwargs)
        self.api = []
        self.logger = logging.getLogger('flask.app')

    @abstractmethod
    def create(self, **kwargs):
        return

    @abstractmethod
    def read(self, **kwargs):
        return

    @abstractmethod
    def update(self, **kwargs):
        return

    @abstractmethod
    def delete(self, **kwargs):
        return

    @abstractmethod
    def list(self, **kwargs):
        return

    def check_input_data(self, input_data, required=None, strict=False):
        if hasattr(self, 'required') and not required:
            required = self.required
        for r in required:
            if r not in input_data or input_data[r] is None:
                raise MissingParameterException('The parameter {0} is required.'.format(r))
            if strict:
                try:
                    if len(input_data[r]) == 0:
                        raise MissingParameterException('The parameter {0} must have a value.'.format(r))
                except TypeError:
                    pass
        return True

    def default_parameter(self, input_data, defaults=None):
        if hasattr(self, 'defaults') and not defaults:
            defaults = self.defaults
        input_data_with_defaults = input_data.copy()
        for d in defaults.keys():
            if d not in input_data:
                input_data_with_defaults[d] = defaults[d]
        return input_data_with_defaults

    def caller(self, func, **kwargs):
        r = []
        for a in self.api:
            f = getattr(a, func)
            r.append(f(**kwargs))
        return r

    def hostname_from_fqdn(self, fqdn):
        return fqdn.split('.')[0]

    def fqdn(self, hostname):
        if len(hostname.split('.')) == 1:
            return '{0}.msnet.railb.be'.format(hostname)
        return hostname

    def domain_from_fqdn(self, fqdn):
        parts = fqdn.split('.', maxsplit=1)
        if len(parts) > 1:
            return parts[-1]
        raise InvalidParameterException('This hostname has no domain.')

    def hostname_components(self, hostname):
        hostname = self.hostname_from_fqdn(hostname)
        hostname_re = re.compile('^([a-z])([a-z]{3})([a-z])([a-z])([a-z]{2})([a-z])([a-z])([0-9]+)$',
                                 flags=re.IGNORECASE)
        parts = {
            'hostname': hostname,
            'fqdn': self.fqdn(hostname),
            'company': None,
            'entity': None,
            'datacenter': None,
            'zone': None,
            'type': None,
            'os': None,
            'system': None
        }
        try:
            parts['domain'] = self.domain_from_fqdn(parts['fqdn'])
        except InvalidParameterException:
            parts['domain'] = None
        m = hostname_re.match(hostname)
        if not m:
            return parts
        parts['company'] = m.group(1)
        parts['entity'] = m.group(2)
        parts['datacenter'] = m.group(3)
        parts['zone'] = m.group(4)
        parts['type'] = m.group(5)
        parts['os'] = m.group(6)
        parts['system'] = m.group(7)
        return parts

    def is_cluster(self, hostname):
        parts = self.hostname_components(hostname)
        if 'system' in parts and parts['system']:
            if parts['system'].lower() == 'c' or parts['system'].lower() == 'r':
                return True
        return False
