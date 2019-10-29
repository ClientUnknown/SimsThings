import functoolsfrom sims4.collections import ListSetfrom sims4.repr_utils import standard_reprimport sims4.loglogger = sims4.log.Logger('Assertions')ENABLE_INTRUSIVE_ASSERTIONS = False
def not_recursive(func):
    return func

def not_recursive_gen(func):
    return func

def hot_path(fn):
    return fn
