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
