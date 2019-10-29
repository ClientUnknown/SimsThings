from objects.placement.placement_helper import PlacementHelperfrom sims4.tuning.geometric import TunableCurvefrom sims4.tuning.tunable import TunableReference, HasTunableSingletonFactory, AutoFactoryInit, TunableRange, Tunablefrom ui.ui_dialog_notification import TunableUiDialogNotificationReferenceimport servicesimport sims4.resources
class CullingTuning:
    CULLING_GHOST_COMMODITY = TunableReference(description="\n        The commodity that defines the strength of a ghost's connection to the\n        physical world. Sims with low values are close to being culled.\n        \n        This commodity being low also unlocks the ability for the player to run\n        certain interactions that strengthens a ghost's connection to the\n        physical world.\n        ", manager=services.get_instance_manager(sims4.resources.Types.STATISTIC))
    CULLING_GHOST_WARNING_THRESHOLD = Tunable(description="\n        Once a ghost's culling commodity is below this threshold, a warning\n        notification is displayed.\n        ", tunable_type=float, default=0)
    CULLING_GHOST_WARNING_NOTIFICATION = TunableUiDialogNotificationReference(description="\n        This is a notification that is displayed whenever a ghost's culling\n        commodity reaches the threshold defined by\n        CULLING_GHOST_WARNING_THRESHOLD.\n        ")
    CULLING_OFFLOT_URNSTONE_PLACEMENT = PlacementHelper.TunableFactory(description="\n        When Sims die off-lot, we attempt to place an urnstone at their old\n        household's home lot, upon travel. Define how urnstones should be\n        automatically placed.\n        ")
    CULLING_SCORE_IN_WORLD = TunableRange(description='\n        A bonus score that is applied to all Sims living in the world. This\n        makes them less likely to be culled.\n        ', tunable_type=float, minimum=0, default=10)
    CULLING_SCORE_PREMADE = TunableRange(description='\n        A bonus score that is applied to all Sims that are premade. This makes\n        them less likely to be culled.\n        ', tunable_type=float, minimum=0, default=10)
    CULLING_NOTIFICATION_IN_WORLD = TunableUiDialogNotificationReference(description='\n        This is a flavor notification that is displayed whenever a non-player\n        household living in the world is culled, as long as this household has a\n        meaningful relationship with the active household.\n        ')
    RELATIONHSIP_DEPTH_WEIGHT = Tunable(description='\n        Multiplier used to modify relationship depth to determine how\n        important depth is in culling score.  The higher the multiplier the\n        more relationship depth is added to culling score.  The lower the\n        culling score the more likely sim has a chance of being deleted.\n        ', tunable_type=float, default=0.5)
    RELATIONSHIP_TRACKS_MULTIPLIER = Tunable(description='\n        Multiply the number of tracks by this multiplier to provide an\n        additional score to determine if sim should be culled. The higher\n        the multiplier the more the number of tracks bonus is added to\n        culling score.  The lower the culling score the more likely sim has\n        a chance of being deleted.\n        ', tunable_type=float, default=2)
    RELATIONSHIP_INSTANTIATION_TIME_CURVE = TunableCurve(description="\n        Define a relationship score modifier based on the time since the\n        relationship target Sim was instantiated. The idea is that\n        relationships with Sims that haven't been instantiated recently\n        should count less.\n        ", x_axis_name='Days_Since_Instantiation', y_axis_name='Score_Multiplier')
    LAST_INSTANTIATED_MAX = TunableRange(description='\n        Number of days before "last time instantiated" is no longer\n        considered for culling.\n        \n        Example: if set to 10, after 10 sim days only relationship depth\n        and track are considered when scoring sim for culling.\n        ', tunable_type=float, default=30, minimum=1)
    LAST_INSTANTIATED_WEIGHT = Tunable(description='\n        Multiplier used to modify since "last time instantiated" to\n        determine how important depth is in culling score.\n        ', tunable_type=float, default=0.5)
    FAME_CULLING_BONUS_CURVE = TunableCurve(description='\n        A curve specifying the culling bonus that a Sim receives at a given\n        Fame rank.\n        ', x_axis_name='Rank', y_axis_name='Bonus')

class CullingBehaviorDefault(HasTunableSingletonFactory, AutoFactoryInit):

    def is_immune_to_culling(self):
        return False

    def get_culling_npc_score(self):
        return 0

class CullingBehaviorImmune(HasTunableSingletonFactory, AutoFactoryInit):

    def is_immune_to_culling(self):
        return True

    def get_culling_npc_score(self):
        return 0

class CullingBehaviorImportanceAsNpc(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'additional_culling_immunity': TunableRange(description='\n            This number will be a boost a Sims importance when the culling \n            system scores this Sim. Higher the number, lower the probability \n            of this Sim being culled.\n            ', tunable_type=int, default=0, minimum=0)}

    def is_immune_to_culling(self):
        return False

    def get_culling_npc_score(self):
        return self.additional_culling_immunity
