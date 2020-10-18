import sys
import argparse
import inspect
from pprint import pprint

try:
    import docstring_parser
except ModuleNotFoundError:
    
    class docstring_parser:
        def __init__(self):
            self.short_description = ""
            self.long_description  = ""
            self.params = []
        @classmethod
        def parse(cls, doc):
            return docstring_parser()

from object_publisher.base import *


class CLI(PublisherBase):
    
    def __init__(self, *, object=None, klass=None, allocator=None, deallocator=None, parser=None):
        
        super(CLI, self).__init__(object=object, klass=klass, allocator=allocator, deallocator=deallocator)
        klass = self.klass

        if not parser:
            parser = argparse.ArgumentParser(prog=klass.__name__)

        subparsers = parser.add_subparsers(help='sub-command help', dest="#method")
        for k,v in self._enumerate_published(klass):
            doc        = docstring_parser.parse(v.func.__doc__)
            doc_params = doc.params
            param_dict = dict([(p.arg_name, p.description) for p in doc_params])

            subparser = subparsers.add_parser(k, help=doc.short_description)
            params    = list(inspect.signature(v.func).parameters.items())[1:]

            for param_name, param in params:
                description = param_dict[param_name] if param_name in param_dict else ""
                if param.default == inspect.Parameter.empty:
                    subparser.add_argument("*%s"%param_name, metavar="<%s>"%param_name, help=description)
                else:
                    subparser.add_argument("--%s"%param_name, metavar="<%s>"%param_name, dest="**%s"%param_name, default=param.default, help=description)
        
        self.parser  = parser

        
    def run_on_parsed(self, parsed):
        
        method = None
        args   = []
        kwargs = {}
        object = self.allocator()
        try:
            for k, v in vars(parsed).items():
                if k == "#method":
                    method = v
                elif k.startswith("**"):
                    kwargs[k.replace("**","")] = v
                elif k.startswith("*"):
                    args.append(v)
                else:
                    raise Exception("Unknown argument: %s"%k)

            if not method:
                raise Exception("Invalid argument format.")

            if hasattr(object, method):
                result = getattr(object, method)(*args, **kwargs)
                pprint(result)
                return result
            
        finally:
            self.deallocator(object)
        
        raise Exception("method not found.")

        
    def run(self, sys_argv):
        
        parsed = self.parser.parse_args(sys_argv)
        self.run_on_parsed(parsed)