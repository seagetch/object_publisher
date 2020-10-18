from functools import partial


class PublishedMethod:

    def __init__(self, func):
        
        self.func = func
        self.metadata = {}
    
    
    def set_metadata(self, **metadata):

        self.metadata = metadata

        
    def __get__(self, obj, klass):

        return partial(self.func, obj)

    
def publish(*args,**kwargs):

    if len(args) == 1 and callable(args[0]):
        result = PublishedMethod(args[0])
        result.set_metadata(**kwargs)
        return result

    elif len(args) >= 1:
        raise Exception("unsupported positional args: %s"%([str(a) for a in args]))

    elif len(kwargs) >= 1:
        def decorator(func):
            result = PublishedMethod(func)
            result.set_metadata(**kwargs)
            return result
        return decorator

    raise Exception("unexpected usage")

    
class PublisherBase:
    
    def __init__(self, *, object=None, klass=None, allocator=None, deallocator=None):

        if not klass is None:
            if allocator is None:
                allocator   = lambda  : klass()
                deallocator = lambda x: None

        elif not object is None:
            allocator   = lambda  : object
            deallocator = lambda x: None
            klass   = object.__class__

        if klass is None:
            raise Exception("No class nor object is specified.")
        
        self.klass       = klass
        self.allocator   = allocator
        self.deallocator = deallocator

    
    @staticmethod
    def _enumerate_published(klass):
        
        for k,v in klass.__dict__.items():
            if isinstance(v, PublishedMethod):
                yield (k, v)
