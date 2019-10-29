from interactions.base.super_interaction import SuperInteractionfrom interactions.social.social_super_interaction import SocialSuperInteractionfrom sims4.utils import flexmethodfrom singletons import DEFAULT
class DisciplineTemplateMixin:

    def __init__(self, *args, template_display_name=None, template_outcome_basic_extras=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._display_name_override = template_display_name
        self._additional_outcome_basic_extra = template_outcome_basic_extras

    def build_basic_extras(self, sequence=()):
        sequence = super().build_basic_extras(sequence=sequence)
        if self._additional_outcome_basic_extra:
            for factory in reversed(self._additional_outcome_basic_extra):
                sequence = factory(self, sequence=sequence)
        return sequence

    @flexmethod
    def _get_name(cls, inst, target=DEFAULT, context=DEFAULT, template_display_name=None, **interaction_parameters):
        if template_display_name is not None:
            inst_or_cls = inst if inst is not None else cls
            target = inst.target if inst is not None else target
            return super(SuperInteraction, inst_or_cls).create_localized_string(template_display_name, target=target, context=context, **interaction_parameters)
        return super(SuperInteraction, inst if inst is not None else cls)._get_name(target=target, context=context, **interaction_parameters)

class DisciplineTemplateSuperInteraction(DisciplineTemplateMixin, SuperInteraction):
    pass

class DisciplineTemplateSocialSuperInteraction(DisciplineTemplateMixin, SocialSuperInteraction):
    pass
