from sims4.tuning.tunable import TunableVariantfrom socials.jigs.jig_type_animation import SocialJigAnimationfrom socials.jigs.jig_type_definition import SocialJigFromDefinitionfrom socials.jigs.jig_type_explicit import SocialJigExplicitfrom socials.jigs.jig_type_legacy import SocialJigLegacy
class TunableJigVariant(TunableVariant):

    def __init__(self, **kwargs):
        super().__init__(definition=SocialJigFromDefinition.TunableFactory(), explicit=SocialJigExplicit.TunableFactory(), legacy=SocialJigLegacy.TunableFactory(), animation=SocialJigAnimation.TunableFactory(), default='definition', **kwargs)
