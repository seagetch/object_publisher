import flask
import json
import traceback
import inspect

from object_publisher.base import *


class AppHandler:

    
    def __init__(self, klass, allocator, deallocator, caller, args_dict, kwargs_dict, sources):
        self.klass       = klass
        self.allocator   = allocator
        self.deallocator = deallocator
        self.caller      = caller
        self.args_dict   = args_dict
        self.kwargs_dict = kwargs_dict
        self.__name__    = "%s#%s"%(klass.__name__, caller.func.__name__)
        self.sources     = sources

        
    def __call__(self, **path_args):
        object = self.allocator()
        
        try:
            args   = [inspect.Parameter.empty] * len(self.args_dict)
            kwargs = {}

            for arg_k, arg_v in path_args.items():
                arg_index = self.args_dict[arg_k]
                args[arg_index] = arg_v

            params = getattr(flask.request, self.sources)
            if hasattr(params, "to_dict"):
                params = params.to_dict()
                
            if not params:
                params = {}

            for arg_k, arg_v in params.items():
                if arg_k in self.args_dict:
                    arg_index = self.args_dict[arg_k]
                    args[arg_index] = arg_v
                
                elif arg_k in self.kwargs_dict:
                    kwargs[arg_k] = arg_v
                    
            for i, a in enumerate(args):
                if a == inspect.Parameter.empty:
                    return flask.jsonify("No parameter found for positional argument at %d"%i), 400
                
            return flask.jsonify(self.caller.__get__(object, type(object))(*args, **kwargs))
        
        except Exception as e:
            print(traceback.format_exc())
            return flask.jsonify(str(e)), 500
        
        finally:
            self.deallocator(object)

        
class Flask(PublisherBase):

    def __init__(self, *, object=None, klass=None, allocator=None, deallocator=None, app = None):

        super(Flask, self).__init__(object=object, klass=klass, allocator=allocator, deallocator=deallocator)

        klass       = self.klass
        allocator   = self.allocator
        deallocator = self.deallocator

        if not app:
            app = flask.Flask(klass.__name__)
            app.config["JSON_AS_ASCII"] = False

        for k,v in self._enumerate_published(klass):
            flask_meta = v.metadata.get("flask")
            
            resources = (flask_meta.get("path") if flask_meta else []) or []
            path      = ("/%s"%klass.__name__) + "/" + "/".join(["<%s>"%r for r in resources] + [k])
            params    = list(inspect.signature(v.func).parameters.items())[1:]
            
            method    = flask_meta.get("method") if flask_meta else None
            sources   = (flask_meta.get("params") if flask_meta else None) or "args"

            if method is None:
                if sources != "args":
                    method = "POST"
                else:
                    method = "GET"
            
            if not method in ("GET", "POST", "PUT", "DELETE"):
                raise Exception("invalid value for flask.method: '%s'"%method)

            if not sources in ("args", "form", "json"):
                raise Exception("invalid value for flask.params: '%s'"%sources)

            # TBD: variables in 'resources' must exist in params.
            
            args_dict = {}
            kwargs_dict = {}
            
            for index, (param_name, param) in enumerate(params):
                if param_name in resources:
                    args_dict[param_name] = index
                elif param.default == inspect.Parameter.empty:
                    args_dict[param_name] = index
                else:
                    kwargs_dict[param_name] = param.default
            
            handler = AppHandler(klass, allocator, deallocator, v, args_dict, kwargs_dict, sources)
            app.route(path, methods=[method])(handler)
            
        self.app = app
    
    
    def run(self, *args, **kwargs):
    
        return self.app.run(*args, **kwargs)