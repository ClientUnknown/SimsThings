from sims4.tuning.instances import TunedInstanceMetaclassimport sims
def format_object_name(obj):
    if not isinstance(type(obj), TunedInstanceMetaclass):
        return str(obj)
    if isinstance(obj, sims.sim.Sim):
        return obj.full_name
    name = type(obj).__name__
    obj_str = str(obj)
    if name in obj_str:
        return name
    else:
        return '{0} ({1})'.format(name, obj_str)

def format_object_list_names(items):
    return ', '.join(format_object_name(item) for item in items)

def format_enum_name(enum_val):
    return str(enum_val).split('.')[-1]

def parse_filter_to_list(filter):
    filter_list = None
    if filter is not None:
        filter_list = filter.split(',')
    return filter_list
