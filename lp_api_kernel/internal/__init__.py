from abc import ABCMeta, abstractmethod
from lp_api_kernel.exceptions import MissingParameterException, InvalidParameterException
from logging import getLogger


class BaseInternalApi:
    __metaclass__ = ABCMeta

    def __init__(self, api_class=None, **kwargs):
        if api_class:
            self.a = api_class(**kwargs)
        self.api = []
        self.logger = getLogger('flask.app')

    @abstractmethod
    def create(self, *args, **kwargs):
        """
        Function to create something.
        :param args:
        :param kwargs:
        :return:
        """
        return

    @abstractmethod
    def read(self, *args, **kwargs):
        """
        Function to read a single item.
        :param args:
        :param kwargs:
        :return:
        """
        return

    @abstractmethod
    def update(self, *args, **kwargs):
        """
        Function to update a single item.
        :param args:
        :param kwargs:
        :return:
        """
        return

    @abstractmethod
    def delete(self, *args, **kwargs):
        """
        Function do delete a single item.
        :param args:
        :param kwargs:
        :return:
        """
        return

    @abstractmethod
    def list(self, *args, **kwargs):
        """
        Function to list all items.
        :param args:
        :param kwargs:
        :return:
        """
        return

    def check_input_data(self, input_data, required=None, strict=False):
        """
        For functions that take a dict of key, value pairs, this function will check
        that all required keys are present.
        :param input_data:
        :param required:
        :param strict:
        :return:
        """
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
        """
        For functions that take a dict of key, value pairs, this function will ensure that all
        keys that are also in defaults have the default value set.
        :param input_data:
        :param defaults:
        :return:
        """
        if hasattr(self, 'defaults') and not defaults:
            defaults = self.defaults
        input_data_with_defaults = input_data.copy()
        for d in defaults.keys():
            if d not in input_data:
                input_data_with_defaults[d] = defaults[d]
        return input_data_with_defaults

    def caller(self, func, *args, **kwargs):
        """
        Call a function from the self.api array.
        :param func:
        :param kwargs:
        :return:
        """
        r = []
        for a in self.api:
            f = getattr(a, func)
            r.append(f(*args, **kwargs))
        return r
