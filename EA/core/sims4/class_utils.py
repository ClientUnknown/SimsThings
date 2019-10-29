import builtinsimport sysfrom caches import cachedimport sims4.loglogger = sims4.log.Logger('Utils')
@cached
def find_class(path, class_name):
    builtins.__import__(path)
    module = sys.modules[path]
    cls = module
    try:
        for attr in class_name.split('.'):
            cls = getattr(cls, attr)
    except AttributeError:
        logger.error('{} object has no attribute {}', cls, attr)
        return
    return cls
