from sickness.sickness import Sicknessfrom sims4.resources import Typesimport services
def all_sicknesses_gen():
    for sickness in services.get_instance_manager(Types.SICKNESS).types.values():
        if issubclass(sickness, Sickness):
            yield sickness

def all_sickness_weights_gen(resolver, criteria_func=lambda x: True):
    for sickness in all_sicknesses_gen():
        if not criteria_func(sickness):
            pass
        else:
            weight = sickness.get_sickness_weight(resolver)
            if not weight:
                pass
            else:
                yield (weight, sickness)
