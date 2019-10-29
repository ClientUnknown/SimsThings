from event_testing.resolver import SingleSimResolverfrom event_testing.tests_with_data import InteractionTestEventsfrom interactions.utils.loot import LootActionsfrom services import sim_info_managerfrom sims import sim_spawner_service, sim_infofrom sims.sim import Simfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableSet, TunableList, Tunable, OptionalTunable, TunableReference, TunableVariantfrom sims4.tuning.tunable_base import ExportModes, GroupNamesfrom situations.situation_curve import SituationCurvefrom tunable_utils.taggables_tests import SituationIdentityTestfrom zone_modifier.zone_modifier_actions import ZoneInteractionTriggers, ZoneModifierWeeklySchedulefrom zone_modifier.zone_modifier_household_actions import ZoneModifierHouseholdActionVariantsimport servicesimport sims4.resourceslogger = sims4.log.Logger('ZoneModifier', default_owner='bnguyen')
class ZoneModifier(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.ZONE_MODIFIER)):
    INSTANCE_TUNABLES = {'zone_modifier_locked': Tunable(description='\n            Whether this is a locked trait that cannot be assigned/removed\n            through build/buy.\n            ', tunable_type=bool, default=False, export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'enter_lot_loot': TunableSet(description='\n            Loot applied to Sims when they enter or spawn in on the lot while\n            this zone modifier is active.\n            \n            NOTE: The corresponding exit loot is not guaranteed to be given.\n            For example, if the Sim walks onto the lot, player switches to a\n            different zone, then summons that Sim, that Sim will bypass\n            getting the exit loot.\n            A common use case for exit lot loot is to remove buffs granted\n            by this zone_mod.  This case is already covered as buffs are \n            automatically removed if they are non-persistable (have no associated commodity)\n            ', tunable=LootActions.TunableReference(pack_safe=True), tuning_group=GroupNames.LOOT), 'exit_lot_loot': TunableSet(description='\n            Loot applied to Sims when they exit or spawn off of the lot while\n            this zone modifier is active.\n            \n            NOTE: This loot is not guaranteed to be given after the enter loot.\n            For example, if the Sim walks onto the lot, player switches to a\n            different zone, then summons that Sim, that Sim will bypass\n            getting the exit loot.\n            A common use case for exit lot loot is to remove buffs granted\n            by this zone_mod.  This case is already covered as buffs are \n            automatically removed if they are non-persistable (have no associated commodity)\n            ', tunable=LootActions.TunableReference(pack_safe=True), tuning_group=GroupNames.LOOT), 'interaction_triggers': TunableList(description='\n            A mapping of interactions to possible loots that can be applied\n            when an on-lot Sim executes them if this zone modifier is set.\n            ', tunable=ZoneInteractionTriggers.TunableFactory()), 'schedule': ZoneModifierWeeklySchedule.TunableFactory(description='\n            Schedule to be activated for this particular zone modifier.\n            '), 'household_actions': TunableList(description='\n            Actions to apply to the household that owns this lot when this zone\n            modifier is set.\n            ', tunable=ZoneModifierHouseholdActionVariants(description='\n                The action to apply to the household.\n                ')), 'prohibited_situations': OptionalTunable(description='\n            Optionally define if this zone should prevent certain situations\n            from running or getting scheduled.\n            ', tunable=SituationIdentityTest.TunableFactory(description='\n                Prevent a situation from running if it is one of the specified \n                situations or if it contains one of the specified tags.\n                ')), 'venue_requirements': TunableVariant(description='\n            Whether or not we use a blacklist or white list for the venue\n            requirements on this zone modifier.\n            ', allowed_venue_types=TunableSet(description='\n                A list of venue types that this Zone Modifier can be placed on.\n                All other venue types are not allowed.\n                ', tunable=TunableReference(description='\n                    A venue type that this Zone Modifier can be placed on.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.VENUE), pack_safe=True)), prohibited_venue_types=TunableSet(description='\n                A list of venue types that this Zone Modifier cannot be placed on.\n                ', tunable=TunableReference(description='\n                    A venue type that this Zone Modifier cannot be placed on.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.VENUE), pack_safe=True)), export_modes=ExportModes.All), 'conflicting_zone_modifiers': TunableSet(description='\n            Conflicting zone modifiers for this zone modifier. If the lot has any of the\n            specified zone modifiers, then it is not allowed to be equipped with this\n            one.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ZONE_MODIFIER), pack_safe=True), export_modes=ExportModes.All), 'additional_situations': SituationCurve.TunableFactory(description="\n            An additional schedule of situations that can be added in addition\n            a situation scheduler's source tuning.\n            ", get_create_params={'user_facing': False}), 'zone_wide_loot': TunableSet(description='\n            Loot applied to all sims when they spawn into a zone with \n            this zone modifier.  This loot is also applied to all sims in the\n            zone when this zone modifier is added to a lot.\n            ', tunable=LootActions.TunableReference(pack_safe=True), tuning_group=GroupNames.LOOT), 'cleanup_loot': TunableSet(description='\n            Loot applied to all sims when this zone modifier is removed.\n            ', tunable=LootActions.TunableReference(pack_safe=True), tuning_group=GroupNames.LOOT), 'spin_up_lot_loot': TunableSet(description='\n            Loot applied to all sims on the lot when the zone spins up.\n            ', tunable=LootActions.TunableReference(pack_safe=True), tuning_group=GroupNames.LOOT), 'ignore_route_events_during_zone_spin_up': Tunable(description="\n            Don't handle sim route events during zone spin up.  Useful for preventing\n            unwanted loot from being applied when enter_lot_loot runs situation blacklist tests.\n            If we require sims to retrieve loot on zone spin up, we can tune spin_up_lot_loot. \n            ", tunable_type=bool, default=False)}

    @classmethod
    def on_start_actions(cls):
        cls.register_interaction_triggers()

    @classmethod
    def on_spin_up_actions(cls):
        services.sim_spawner_service().register_sim_spawned_callback(cls._grant_zone_wide_loot)
        cls._grant_spin_up_lot_loot()
        cls._grant_zone_wide_loot_to_all_sims()

    @classmethod
    def on_add_actions(cls):
        services.sim_spawner_service().register_sim_spawned_callback(cls._grant_zone_wide_loot)
        cls.register_interaction_triggers()
        cls.start_household_actions()
        cls._grant_zone_wide_loot_to_all_sims()

    @classmethod
    def on_stop_actions(cls):
        services.sim_spawner_service().unregister_sim_spawned_callback(cls._grant_zone_wide_loot)
        cls.unregister_interaction_triggers()
        cls.stop_household_actions()

    @classmethod
    def on_remove_actions(cls):
        services.sim_spawner_service().unregister_sim_spawned_callback(cls._grant_zone_wide_loot)
        cls.unregister_interaction_triggers()
        cls.stop_household_actions()
        cls._grant_cleanup_loot_to_all_sims()

    @classmethod
    def _grant_zone_wide_loot(cls, sim):
        if not cls.zone_wide_loot:
            return
        if not sim.is_sim:
            logger.error('Non sim object: {}, passed in to _grant_zone_wide_loot', type(sim))
            return
        sim_info = sim.sim_info
        if sim_info is None:
            return
        loot_resolver = SingleSimResolver(sim_info)
        for loot in cls.zone_wide_loot:
            loot.apply_to_resolver(loot_resolver)

    @classmethod
    def _grant_spin_up_lot_loot(cls):
        sim_info_manager = services.sim_info_manager()
        if cls.spin_up_lot_loot and sim_info_manager is None:
            return
        for sim in sim_info_manager.instanced_sims_on_active_lot_gen(include_spawn_point=True):
            if sim is None:
                pass
            else:
                loot_resolver = SingleSimResolver(sim.sim_info)
                for loot in cls.spin_up_lot_loot:
                    loot.apply_to_resolver(loot_resolver)

    @classmethod
    def _grant_zone_wide_loot_to_all_sims(cls):
        sim_info_manager = services.sim_info_manager()
        for sim_info in sim_info_manager.instanced_sim_info_including_baby_gen():
            cls._grant_zone_wide_loot(sim_info)

    @classmethod
    def _grant_cleanup_loot_to_all_sims(cls):
        if not cls.cleanup_loot:
            return
        sim_info_manager = services.sim_info_manager()
        for sim_info in sim_info_manager.instanced_sim_info_including_baby_gen():
            loot_resolver = SingleSimResolver(sim_info)
            for loot in cls.cleanup_loot:
                loot.apply_to_resolver(loot_resolver)

    @classmethod
    def handle_event(cls, sim_info, event, resolver):
        if event not in InteractionTestEvents:
            return
        sim = sim_info.get_sim_instance()
        if sim is None or not sim.is_on_active_lot():
            return
        for trigger in cls.interaction_triggers:
            trigger.handle_interaction_event(sim_info, event, resolver)

    @classmethod
    def start_household_actions(cls):
        if not cls.household_actions:
            return
        household_id = services.owning_household_id_of_active_lot()
        if household_id is not None:
            for household_action in cls.household_actions:
                household_action.start_action(household_id)

    @classmethod
    def stop_household_actions(cls):
        if not cls.household_actions:
            return
        household_id = services.owning_household_id_of_active_lot()
        if household_id is not None:
            for household_action in cls.household_actions:
                household_action.stop_action(household_id)

    @classmethod
    def register_interaction_triggers(cls):
        services.get_event_manager().register_tests(cls, cls._get_trigger_tests())

    @classmethod
    def unregister_interaction_triggers(cls):
        services.get_event_manager().unregister_tests(cls, cls._get_trigger_tests())

    @classmethod
    def _get_trigger_tests(cls):
        tests = list()
        for trigger in cls.interaction_triggers:
            tests.extend(trigger.get_trigger_tests())
        return tests

    @classmethod
    def is_situation_prohibited(cls, situation_type):
        if cls.prohibited_situations is None:
            return False
        return cls.prohibited_situations(situation=situation_type)
