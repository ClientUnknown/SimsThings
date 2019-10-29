from balloon.balloon_enums import BalloonTypeEnumfrom interactions.utils.tunable_icon import TunableIconVariantfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableRange, TunableEnumEntry, TunableResourceKey, OptionalTunablefrom sims4.tuning.tunable_base import FilterTagfrom singletons import DEFAULTimport sims4.resources
class BalloonIcon(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'weight': TunableRange(description='\n            The weight to assign to this balloon.\n            ', tunable_type=float, default=1, minimum=1), 'balloon_type': TunableEnumEntry(description='\n            The visual style of the balloon background. For example if it is a\n            speech balloon or a thought balloon.\n            ', tunable_type=BalloonTypeEnum, default=BalloonTypeEnum.THOUGHT), 'icon': TunableIconVariant(description='\n            The Icon that will be showed within the balloon.\n            '), 'overlay': TunableResourceKey(description='\n            The overlay for the balloon, if present.\n            ', resource_types=sims4.resources.CompoundTypes.IMAGE, default=None, allow_none=True), 'debug_overlay_override': TunableResourceKey(description='\n            The overlay for the balloon in debug, if present. This overlay will\n            be placed on the balloon instead of overlay in debug only.\n            ', resource_types=sims4.resources.CompoundTypes.IMAGE, default=None, allow_none=True, tuning_filter=FilterTag.EXPERT_MODE), 'category_icon': OptionalTunable(description='\n            If enabled balloon will display an additional category icon.\n            ', tunable=TunableIconVariant(description='\n                The Icon that will be showed within the balloon.\n                '), disabled_name='no_category_icon', enabled_name='show_category_icon')}

    def get_balloon_icons(self, resolver, balloon_type=DEFAULT, gsi_entries=None, gsi_category=None, gsi_interaction=None, gsi_balloon_target_override=None, gsi_test_result=None):
        if balloon_type is not DEFAULT:
            self.balloon_type = balloon_type
        if gsi_entries is not None:
            setattr(self, 'gsi_category', gsi_category)
            gsi_entries.append({'test_result': str(gsi_test_result), 'balloon_type': str(self.balloon_type), 'weight': self.weight, 'icon': str(self.icon(gsi_interaction, balloon_target_override=gsi_balloon_target_override)), 'balloon_category': self.gsi_category})
        if gsi_test_result is None or gsi_test_result:
            return [(self.weight, self)]
        return ()
