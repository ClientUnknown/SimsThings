from objects.base_interactions import ProxyInteractionfrom sims4.utils import classproperty, flexmethod
class EnsembleConstraintProxyInteraction(ProxyInteraction):
    INSTANCE_SUBCLASSES_ONLY = True

    @classproperty
    def proxy_name(cls):
        return '[Ensemble]'

    @classmethod
    def generate(cls, proxied_affordance, ensemble):
        result = super().generate(proxied_affordance)
        result.ensemble = ensemble
        return result

    @flexmethod
    def _constraint_gen(cls, inst, *args, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        for constraint in super(__class__, inst_or_cls)._constraint_gen(*args, **kwargs):
            yield constraint
        yield inst_or_cls.ensemble.get_center_of_mass_constraint()
