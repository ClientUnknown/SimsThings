from statistics.statistic import Statisticimport sims4.resources
class RuntimeStatistic(Statistic):
    INSTANCE_SUBCLASSES_ONLY = True

    @classmethod
    def generate(cls, name):
        ProxyClass = type(cls)(name, (cls,), {'INSTANCE_SUBCLASSES_ONLY': True})
        ProxyClass.reloadable = False
        key = sims4.resources.get_resource_key(name, ProxyClass.tuning_manager.TYPE)
        ProxyClass.tuning_manager.register_tuned_class(ProxyClass, key)
        return ProxyClass
