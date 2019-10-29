from aspirations.aspiration_tuning import AspirationBasicfrom aspirations.aspiration_types import AspriationTypefrom event_testing import objective_tuningfrom event_testing.resolver import DoubleSimResolverfrom interactions import ParticipantTypefrom relationships.relationship_tests import TunableRelationshipTestfrom sims import genealogy_trackerfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableEnumEntry, TunableReference, TunableVariant, OptionalTunable, TunableRangefrom sims4.utils import classproperty, constpropertyfrom situations.situation_goal import TunableWeightedSituationGoalReferencefrom statistics.commodity import RuntimeCommodity, CommodityTimePassageFixupTypeimport servicesimport sims4.tuning.tunablelogger = sims4.log.Logger('Whimset', default_owner='jjacobson')
class GeneTargetFactory(sims4.tuning.tunable.TunableFactory):

    @staticmethod
    def factory(sim_info, relationship):
        family_member_sim_id = sim_info.get_relation(relationship)
        if family_member_sim_id is None:
            return
        else:
            family_member_sim_info = services.sim_info_manager().get(family_member_sim_id)
            if family_member_sim_info is not None and (family_member_sim_info.is_baby or family_member_sim_info.is_instanced()):
                return family_member_sim_info

    FACTORY_TYPE = factory

    def __init__(self, **kwargs):
        super().__init__(description='\n            This option tests for completion of a tuned Achievement.\n            ', relationship=TunableEnumEntry(genealogy_tracker.FamilyRelationshipIndex, genealogy_tracker.FamilyRelationshipIndex.FATHER), **kwargs)

class RelationTargetFactory(sims4.tuning.tunable.TunableFactory):

    @staticmethod
    def factory(sim_info, relationship_test):
        relationship_match = None
        for relation in sim_info.relationship_tracker:
            relation_sim_info = services.sim_info_manager().get(relation.get_other_sim_id(sim_info.sim_id))
            if not relation_sim_info.is_baby:
                if relation_sim_info.is_instanced():
                    resolver = DoubleSimResolver(sim_info, relation_sim_info)
                    relationship_match = resolver(relationship_test)
                    if relationship_match:
                        return relation_sim_info
            resolver = DoubleSimResolver(sim_info, relation_sim_info)
            relationship_match = resolver(relationship_test)
            if relation_sim_info is not None and relationship_match:
                return relation_sim_info

    FACTORY_TYPE = factory

    def __init__(self, **kwargs):
        super().__init__(description='\n            This option tests for completion of a tuned Achievement.\n            ', relationship_test=TunableRelationshipTest(description='\n                The relationship state that this goal will complete when\n                obtained.\n                ', locked_args={'subject': ParticipantType.Actor, 'tooltip': None, 'target_sim': ParticipantType.TargetSim, 'num_relations': 0}), **kwargs)

class TunableWhimSetTargetVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, genealogy_target=GeneTargetFactory(), relationship_target=RelationTargetFactory(), default='genealogy_target', **kwargs)

class WhimSetBaseMixin:
    INSTANCE_TUNABLES = {'force_target': OptionalTunable(description='\n            Upon WhimSet activation, use this option to seek out and set a\n            specific target for this set. If the desired target does not exist\n            or is not instanced on the lot, WhimSet will not activate.\n            ', tunable=TunableWhimSetTargetVariant()), 'secondary_target': OptionalTunable(description='\n            Upon WhimSet activation, define a Sim that is used as a flavor\n            target, such that text can reference it. For example, a Dare whim\n            might use this field such that a "Flirt with Bobby" whim has a\n            "(From Being Dared by Frank)" origin.\n            ', tunable=TunableWhimSetTargetVariant()), 'whims': sims4.tuning.tunable.TunableList(description='\n            List of weighted goals.', tunable=TunableWeightedSituationGoalReference(pack_safe=True)), 'connected_whims': sims4.tuning.tunable.TunableMapping(description='\n            A tunable list of whims that upon a goal from this list succeeding will activate.', key_type=TunableReference(services.get_instance_manager(sims4.resources.Types.SITUATION_GOAL), description='The goal to map.'), value_type=sims4.tuning.tunable.TunableList(description='\n                A tunable list of whim sets that upon this whim goal completing will activate', tunable=sims4.tuning.tunable.TunableReference(description='\n                    These Aspiration Whim Sets become active automatically upon completion of this whim.', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions='AspirationWhimSet'))), 'connected_whim_sets': sims4.tuning.tunable.TunableList(description='\n            A tunable list of whim sets that upon a goal from this list succeeding will activate', tunable=sims4.tuning.tunable.TunableReference(description='\n                These Aspiration Whim Sets become active automatically upon completion of a whim from this set.', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions='AspirationWhimSet')), 'whim_reason': TunableLocalizedStringFactory(description="\n            The reason that shows in the whim tooltip for the reason that this\n            whim was chosen for the sim.\n            \n            0 (Number): The most relevant numerical value pertaining to the\n            completion of this goal. This is usually the number of iterations\n            required to complete it although it could also be other values such as\n            the price of the item that the user is required to purchase.\n            \n            1 (Sim): The Sim who owns the goal.\n            \n            2 (Sim): The Sim the goal is directed at.\n            \n            3 (Sim): The goal's secondary SimInfo, if one exists.\n            "), 'cooldown_timer': sims4.tuning.tunable.TunableRange(description='\n            Number of Sim minutes this set of Whims is de-prioritized after de-activation.', tunable_type=float, minimum=0, maximum=3600, default=60)}

    @constproperty
    def aspiration_type():
        return AspriationType.WHIM_SET

    @classmethod
    def get_priority(cls, sim_info):
        raise NotImplementedError

    @classmethod
    def activate(cls, whims_tracker, chained, target):
        pass

    @classproperty
    def deactivate_on_completion(cls):
        return cls in cls.connected_whim_sets

class AspirationWhimSet(WhimSetBaseMixin, AspirationBasic):
    INSTANCE_TUNABLES = {'objectives': sims4.tuning.tunable.TunableList(description='\n            A Set of objectives for completing an aspiration.', tunable=sims4.tuning.tunable.TunableReference(description='\n                One objective for an aspiration', manager=services.get_instance_manager(sims4.resources.Types.OBJECTIVE)), unique_entries=True), 'activated_priority': sims4.tuning.tunable.TunableRange(description='\n            Priority for this set to be chosen if triggered by contextual events.', tunable_type=int, minimum=0, maximum=10, default=6), 'priority_decay_rate': sims4.tuning.tunable.TunableRange(description="\n            The decay rate of a whimset's priority.  A whimset's priority will\n            only decay when a whim of that whimset is active.  A whimset's\n            priority will converge to the whimset's base priority.\n            ", tunable_type=float, default=0.01, minimum=0.0), 'timeout_retest': sims4.tuning.tunable.TunableReference(description='\n            Tuning an objective here will re-test the WhimSet for contextual\n            relevance upon active timer timeout; If the objective test passes,\n            the active timer will be refreshed. Note you can only use tests\n            without data passed in, other types will result in an assert on\n            load.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECTIVE), allow_none=True), 'chained_priority': sims4.tuning.tunable.TunableRange(description='\n            Priority for this set to be chosen if triggered by a previous whim set.', tunable_type=int, minimum=0, maximum=15, default=11)}
    priority_commodity = None

    @classmethod
    def _tuning_loaded_callback(cls):
        commodity = RuntimeCommodity.generate(cls.__name__)
        commodity.decay_rate = cls.priority_decay_rate
        commodity.convergence_value = 0
        commodity.remove_on_convergence = False
        commodity.visible = False
        if cls.activated_priority > cls.chained_priority:
            commodity.max_value_tuning = cls.activated_priority
        else:
            commodity.max_value_tuning = cls.chained_priority
        commodity.min_value_tuning = 0
        commodity.initial_value = 0
        commodity._time_passage_fixup_type = CommodityTimePassageFixupType.DO_NOT_FIXUP
        cls.priority_commodity = commodity

    @classmethod
    def _verify_tuning_callback(cls):
        if cls.activated_priority == 0 and cls.chained_priority == 0:
            logger.error('No priority tuned for value greater than 0 in {}', cls)
        for objective in cls.objectives:
            if objective.objective_completion_type == objective_tuning.SimInfoStatisticObjectiveTrack:
                logger.error("{} Objective in {} Whim Set tuned with incorrect Objective test type; use 'iterations', 'unique_locations', or 'unique targets'.", objective, cls)
            if not objective.resettable:
                logger.error('{} Objective in {} Whim Set tuned as a Whim Aspiration Objective but not tuned as resettable. All Aspriation Whim Set objectives must be resettable.', objective, cls)
        if cls.timeout_retest is not None and (cls.timeout_retest.objective_test.USES_EVENT_DATA or cls.timeout_retest.objective_test.USES_DATA_OBJECT):
            logger.error('Bad Tuning! {} Objective Test {} in Whim Set being used as a timeout_retest cannot use event or object data.', cls.timeout_retest.objective_test, cls)

    @classmethod
    def get_priority(cls, sim_info):
        whimset_priority_stat = sim_info.get_statistic(cls.priority_commodity, add=False)
        if whimset_priority_stat is None:
            return 0
        return whimset_priority_stat.get_user_value()
lock_instance_tunables(AspirationWhimSet, do_not_register_events_on_load=False, screen_slam=None)
class ObjectivelessWhimSet(WhimSetBaseMixin, AspirationBasic):
    INSTANCE_TUNABLES = {'priority': TunableRange(description='\n            The priority of this whim set.\n            ', tunable_type=float, minimum=0, default=5)}
    REMOVE_INSTANCE_TUNABLES = ('objective_completion_type',)

    @classmethod
    def get_priority(cls, sim_info):
        return cls.priority

    @constproperty
    def update_on_load():
        return False

    @classproperty
    def deactivate_on_completion(cls):
        return False
lock_instance_tunables(ObjectivelessWhimSet, do_not_register_events_on_load=True, objectives=(), screen_slam=None)