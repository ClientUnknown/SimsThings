from _sims4_collections import frozendictfrom _weakrefset import WeakSetfrom types import SimpleNamespacefrom animation.animation_utils import flush_all_animationsfrom animation.posture_manifest_constants import STAND_NO_CARRY_NO_SURFACE_POSTURE_MANIFEST, STAND_CONSTRAINTfrom carry.carry_utils import create_carry_constraintfrom drama_scheduler.drama_node_types import DramaNodeTypefrom element_utils import build_critical_sectionfrom event_testing.resolver import SingleSimResolverfrom event_testing.results import TestResultfrom interactions import ParticipantType, TargetType, ParticipantTypeSingle, ParticipantTypeObjectfrom interactions.aop import AffordanceObjectPairfrom interactions.base.interaction import InteractionIntensityfrom interactions.base.super_interaction import SuperInteractionfrom interactions.base.tuningless_interaction import create_tuningless_superinteractionfrom interactions.constraints import TunableWelcomeConstraint, TunableSpawnPoint, Anywherefrom interactions.context import InteractionContextfrom interactions.utils.tunable import SetGoodbyeNotificationElementfrom objects import ALL_HIDDEN_REASONSfrom objects.terrain import TravelMixinfrom sims.outfits.outfit_enums import OutfitCategory, OutfitChangeReasonfrom sims.outfits.outfit_tuning import OutfitTuningfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableEnumEntry, OptionalTunable, Tunable, TunableLotDescription, AutoFactoryInit, HasTunableSingletonFactory, TunableVariant, TunableEnumWithFilter, TunableSetfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom singletons import DEFAULTfrom situations.complex.caregiver_situation import CaregiverSituationfrom statistics import skillfrom tag import Tagfrom world import regionfrom world.lot import get_lot_id_from_instance_idfrom world.travel_tuning import TRAVEL_SIM_LIABILITY, TravelSimLiabilityimport servicesimport sims4.loglogger = sims4.log.Logger('Travel')
class TravelInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'travel_xevt': OptionalTunable(description='\n            If enabled, specify an xevent at which the Sim will disappear from\n            the world.\n            ', tunable=Tunable(description='\n                The xevent at which the Sim will disappear from the world.\n                ', tunable_type=int, needs_tuning=False, default=100)), 'travel_care_dependents': Tunable(description="\n            If checked, this interaction detects whether or not the traveling\n            Sim is any other Sim's (e.g. toddler) caregiver. If so, it does two\n            things:\n             * If the caregiver situation specifies it, it creates a constraint\n             for this SI (e.g. carry a toddler).\n             * It automatically despawns care dependents.\n            ", tunable_type=bool, default=True)}

    @classmethod
    def _define_supported_postures(cls):
        return frozendict({ParticipantType.Actor: STAND_NO_CARRY_NO_SURFACE_POSTURE_MANIFEST})

    def __init__(self, aop, context, **kwargs):
        super().__init__(aop, context, **kwargs)
        self.from_zone_id = kwargs['from_zone_id']
        self.to_zone_id = kwargs['to_zone_id']
        self.on_complete_callback = kwargs['on_complete_callback']
        self.on_complete_context = kwargs['on_complete_context']
        self._care_dependents = WeakSet()
        self._care_dependent_required = None
        if self.travel_care_dependents:
            self._find_care_dependents(context)

    def _find_care_dependents(self, context):
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is not None:
            for situation in situation_manager.get_situations_by_type(CaregiverSituation):
                excluding_interaction_types = (TravelInteraction.get_interaction_type(),)
                care_dependent = situation.get_care_dependent_if_last_caregiver(context.sim.sim_info, excluding_interaction_types)
                if care_dependent is not None:
                    self._care_dependents.add(care_dependent)

    def _get_primary_care_dependent(self):
        if self._care_dependent_required is None:
            self._care_dependent_required = next(iter(self._care_dependents), None)
        return self._care_dependent_required

    def _get_required_sims(self, *args, **kwargs):
        required_sims = super()._get_required_sims(*args, **kwargs)
        care_dependent = self._get_primary_care_dependent()
        if care_dependent is not None:
            required_sims.add(care_dependent)
        return required_sims

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, *args, to_zone_id=DEFAULT, **kwargs):
        yield from super(__class__, inst if inst is not None else cls)._constraint_gen(sim, target, *args, **kwargs)
        if inst is not None:
            care_dependent = inst._get_primary_care_dependent()
            if care_dependent is not None:
                yield create_carry_constraint(care_dependent)

    def _setup_gen(self, timeline):
        if self.travel_xevt is not None:

            def on_travel_visuals(*_, **__):
                self.sim.remove_from_client()
                care_dependent = self._get_primary_care_dependent()
                if care_dependent is not None and care_dependent.parent is self.sim:
                    care_dependent.remove_from_client()

            self.store_event_handler(on_travel_visuals, handler_id=self.travel_xevt)
        result = yield from super()._setup_gen(timeline)
        return result

    def _run_interaction_gen(self, timeline):
        self.save_and_destroy_sim(False, self.sim.sim_info)

    def _exited_pipeline(self, *args, **kwargs):
        self.sim.socials_locked = False
        return super()._exited_pipeline(*args, **kwargs)

    def save_and_destroy_sim(self, on_reset, sim_info):
        if services.current_zone().is_zone_shutting_down:
            return

        def update_selectable_sim():
            if not sim_info.is_npc:
                services.client_manager().get_first_client().send_selectable_sims_update()

        try:
            logger.debug('Saving sim during TravelInteraction for {}', sim_info)
            sim_info.inject_into_inactive_zone(self.to_zone_id, skip_instanced_check=True)
            if sim_info.save_sim() is None:
                logger.error('Failure saving during TravelInteraction for {}', sim_info)
        finally:
            logger.debug('Destroying sim {}', sim_info)
            if on_reset:
                if self.sim is not None:
                    services.object_manager().remove(self.sim)
                update_selectable_sim()
            elif self.sim is not None:
                self.sim.schedule_destroy_asap(source=self, cause='Destroying sim on travel.')
lock_instance_tunables(TravelInteraction, basic_reserve_object=None, basic_focus=None, allow_from_object_inventory=False, allow_from_sim_inventory=False, intensity=InteractionIntensity.Default, basic_liabilities=[], animation_stat=None, _provided_posture_type=None, supported_posture_type_filter=[], force_autonomy_on_inertia=False, force_exit_on_inertia=False, pre_add_autonomy_commodities=[], pre_run_autonomy_commodities=[], post_guaranteed_autonomy_commodities=[], post_run_autonomy_commodities=SimpleNamespace(requests=[], fallback_notification=None), opportunity_cost_multiplier=1, autonomy_can_overwrite_similar_affordance=False, subaction_selection_weight=1, relationship_scoring=False, _party_size_weight_tuning=[], joinable=[], rallyable=None, autonomy_preference=None, outfit_change=None, outfit_priority=None, object_reservation_tests=[], cancel_replacement_affordances=None, privacy=None, provided_affordances=[], canonical_animation=None, ignore_group_socials=False, utility_info=None, skill_loot_data=skill.EMPTY_SKILL_LOOT_DATA)
class TravelSpecificLot(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'destination_lot': TunableLotDescription(description='\n            The lot description of the destination lot.\n            ')}

    def __call__(self, interaction, target, context):
        lot_id = get_lot_id_from_instance_id(self.destination_lot)
        zone_id = services.get_persistence_service().resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True)
        return zone_id

class TravelParticipantZone(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant_to_visit': TunableEnumEntry(description='\n            The participant we want to visit.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.TargetSim)}

    def __call__(self, interaction, target, context):
        participant = interaction.get_participant(self.participant_to_visit, sim=context.sim, target=target)
        if participant is not None and participant.zone_id and participant.zone_id is not None:
            return participant.zone_id
        return 0

class TravelParticipantHomeZone(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant_with_home': TunableEnumEntry(description='\n            The participant whose home we want to visit.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), 'allow_travel_group_zone': Tunable(description="\n            Whether or not we include the participant's travel group home.\n            ", tunable_type=bool, default=True)}

    def __call__(self, interaction, target, context):
        participant = interaction.get_participant(self.participant_with_home, sim=context.sim, target=target)
        if participant is not None:
            if self.allow_travel_group_zone:
                zone_id = participant.sim_info.vacation_or_home_zone_id
            else:
                zone_id = participant.household.home_zone_id
            if zone_id and zone_id is not None:
                return zone_id
        return 0

class TravelObjectHouseholdOwnerHomeZone(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The object whose household we want to visit.\n            ', tunable_type=ParticipantTypeObject, default=ParticipantTypeObject.Object)}

    def __call__(self, interaction, target, context):
        participant = interaction.get_participant(self.participant, sim=context.sim, target=target)
        if participant is not None:
            household = services.household_manager().get(participant.household_owner_id)
            if household is not None:
                return household.home_zone_id
        return 0

class GoToSpecificLotTravelInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'destination': TunableVariant(description='\n            This is the process of how we determine which zone the Sim will\n            travel to.\n            ', specific_lot=TravelSpecificLot.TunableFactory(), participant_zone=TravelParticipantZone.TunableFactory(), participant_home_zone=TravelParticipantHomeZone.TunableFactory(), object_household_owner_zone=TravelObjectHouseholdOwnerHomeZone.TunableFactory(), default='participant_home_zone'), 'check_region_compatibility': Tunable(description="\n            If checked, the interaction will fail if the actor's region is not\n            compatible with the destination region.\n            ", tunable_type=bool, default=False)}

    @classmethod
    def _test(cls, target, context, **kwargs):
        zone_id = cls.destination(cls, target, context)
        if cls.check_region_compatibility:
            to_region = region.get_region_instance_from_zone_id(zone_id)
            from_region = region.get_region_instance_from_zone_id(cls.sim.zone_id)
            if not from_region.is_region_compatible(to_region):
                return TestResult(False, 'GoToSpecificLotTravelInteraction: Actor region {} is not compatible with destination {}.'.format(from_region, to_region))
        if zone_id and zone_id is None:
            return TestResult(False, 'GoToSpecificLotTravelInteraction: {} could not get a valid zone from tuning or participants.', cls)
        return TestResult.TRUE

    def _setup_gen(self, timeline):
        zone_id = self.destination(self, self.target, self.context)
        if zone_id and zone_id is not None:
            self.interaction_parameters['picked_zone_ids'] = frozenset((zone_id,))
        else:
            logger.error('GoToSpecificLotTravelInteraction {} has invalid destination.'.format(self), owner='rmccord')
            return False
        result = yield from super()._setup_gen(timeline)
        return result

class GoHomeTravelInteraction(TravelMixin, TravelInteraction):
    INSTANCE_TUNABLES = {'front_door_constraint': TunableWelcomeConstraint(description="\n            The Front Door Constraint for when the active lot is the Sim's home\n            lot.\n            ", radius=5.0, tuning_group=GroupNames.TRAVEL), 'home_spawn_point_constraint': TunableSpawnPoint(description="\n            This is the Spawn Point Constraint for when the Sim's home lot is on\n            the current street, but is not active. We should be tuning the\n            Arrival Spawner Tag(s) here.\n            ", tuning_group=GroupNames.TRAVEL), 'street_spawn_point_constraint': TunableSpawnPoint(description="\n            This is the Spawn Point Constraint for when the Sim's home lot is\n            not on the current street. We should likely be tuning Walkby Spawner\n            Tags here.\n            ", tuning_group=GroupNames.TRAVEL), 'attend_career': Tunable(description='\n            If set, Sim will automatically go to work after going home.\n            ', tunable_type=bool, default=False), 'force_allow_autonomous_travel': Tunable(description="\n            In most cases we don't want household sims traveling home autonomously.\n            If checked, this override will allow it for certain edge cases,\n            such as for sending household children home for the ClothingOptional lot trait.\n            ", tunable_type=bool, default=False)}

    def __init__(self, aop, context, to_zone_id=DEFAULT, **kwargs):
        if to_zone_id is DEFAULT:
            to_zone_id = context.sim.sim_info.vacation_or_home_zone_id
        super().__init__(aop, context, from_zone_id=context.sim.zone_id, to_zone_id=to_zone_id, on_complete_callback=None, on_complete_context=None, **kwargs)

    def should_fade_sim_out(self):
        if self.to_zone_id == services.current_zone_id():
            return False
        return True

    @classmethod
    def _common_test(cls, target, context, **kwargs):
        sim = context.sim
        test_result = super()._test(target, context, **kwargs)
        if not test_result:
            return test_result
        if target is not None and target is not sim:
            return TestResult(False, 'Self Interactions cannot target other Sims.')
        if sim.sim_info.is_npc or cls.force_allow_autonomous_travel or context.source == InteractionContext.SOURCE_AUTONOMY:
            return TestResult(False, 'Selectable Sims cannot go home autonomously.')
        test_result = cls.travel_test(context)
        if not test_result:
            return test_result
        return TestResult.TRUE

    @classmethod
    def _test(cls, target, context, **kwargs):
        test_result = cls._common_test(target, context, **kwargs)
        if not test_result:
            return test_result
        sim = context.sim
        current_zone = services.current_zone()
        active_lot = current_zone.lot
        if current_zone.id == sim.sim_info.vacation_or_home_zone_id and active_lot.is_position_on_lot(sim.position):
            return TestResult(False, 'Selectable Sims cannot go home if they are already at home.')
        return TestResult.TRUE

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, *args, to_zone_id=DEFAULT, **kwargs):
        yield from super(__class__, inst if inst is not None else cls)._constraint_gen(sim, target, *args, **kwargs)
        yield services.current_zone().get_spawn_point_ignore_constraint()
        inst_or_cls = inst if inst is not None else cls
        home_zone_id = sim.sim_info.vacation_or_home_zone_id if to_zone_id is DEFAULT else to_zone_id
        if home_zone_id == services.current_zone_id():
            if services.get_door_service().has_front_door():
                yield inst_or_cls.front_door_constraint.create_constraint(sim)
            else:
                yield inst_or_cls.home_spawn_point_constraint.create_constraint(sim, lot_id=services.current_zone().lot.lot_id)
        elif sim.sim_info.is_child_or_older:
            persistence_service = services.get_persistence_service()
            zone_data = persistence_service.get_zone_proto_buff(home_zone_id)
            if zone_data is not None and zone_data.world_id == services.current_zone().world_id:
                home_lot_id = zone_data.lot_id
                yield inst_or_cls.home_spawn_point_constraint.create_constraint(sim, lot_id=home_lot_id)
            else:
                yield inst_or_cls.street_spawn_point_constraint.create_constraint(sim)

    def _run_interaction_gen(self, timeline):
        if self.to_zone_id == services.current_zone_id():
            return
        additional_sims = list(self._care_dependents)
        drama_scheduler = services.drama_scheduler_service()
        if drama_scheduler is not None:
            drama_nodes = drama_scheduler.get_running_nodes_by_drama_node_type(DramaNodeType.TUTORIAL)
            if drama_nodes:
                tutorial_drama_node = drama_nodes[0]
                housemate_sim_info = tutorial_drama_node.get_housemate_sim_info()
                housemate_sim = housemate_sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                if housemate_sim is not None and housemate_sim is not self.sim:
                    additional_sims.append(housemate_sim)
        selectable_sim_infos = services.get_selectable_sims()
        selectable_sims = selectable_sim_infos.get_instanced_sims(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if self.sim.is_human:
            if sum(1 for sim in selectable_sims if sim.is_human and sim.sim_info.is_child_or_older) == 1:
                additional_sims.extend([sim for sim in selectable_sims if sim.is_pet])
            familiar_tracker = self.sim.sim_info.familiar_tracker
            if familiar_tracker is not None:
                active_familiar = familiar_tracker.get_active_familiar()
                if active_familiar is not None and active_familiar.is_sim:
                    additional_sims.append(active_familiar)
        travel_liability = TravelSimLiability(self, self.sim.sim_info, self.to_zone_id, is_attend_career=self.attend_career, additional_sims=additional_sims)
        for next_sim_info in selectable_sim_infos:
            next_sim = next_sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if next_sim is None:
                pass
            elif next_sim is self.sim:
                pass
            elif next_sim in additional_sims:
                pass
            else:
                self.add_liability(TRAVEL_SIM_LIABILITY, travel_liability)
                break
        travel_liability.travel_player()

    def on_reset(self):
        self.sim.fade_in()
        super().on_reset()
lock_instance_tunables(GoHomeTravelInteraction, fade_sim_out=True)
class GoHomeFromVacationTravelInteraction(GoHomeTravelInteraction):

    def __init__(self, aop, context, **kwargs):
        to_zone_id = context.sim.sim_info.household.home_zone_id
        super().__init__(aop, context=context, to_zone_id=to_zone_id, **kwargs)

    @classmethod
    def _test(cls, target, context, **kwargs):
        return cls._common_test(target, context, **kwargs)

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, *args, **kwargs):
        travel_group = sim.sim_info.travel_group
        if len(travel_group) == 1:
            yield Anywhere()
        else:
            yield from super()._constraint_gen(sim, target, *args, to_zone_id=sim.sim_info.household.home_zone_id, **kwargs)

class NPCLeaveLotInteraction(TravelInteraction):

    def __init__(self, aop, context, **kwargs):
        to_zone_id = context.sim.sim_info.vacation_or_home_zone_id
        super().__init__(aop, context, from_zone_id=context.sim.zone_id, to_zone_id=to_zone_id, on_complete_callback=None, on_complete_context=None, **kwargs)
        self.register_on_finishing_callback(self._on_finishing_callback)

    def run_pre_transition_behavior(self):
        actor = self.get_participant(ParticipantType.Actor)
        lot_owners = self.get_participants(ParticipantType.LotOwners)
        notification = actor.sim_info.goodbye_notification
        if notification not in (None, SetGoodbyeNotificationElement.NEVER_USE_NOTIFICATION_NO_MATTER_WHAT):
            for lot_owner in lot_owners:
                if not lot_owner.is_selectable:
                    pass
                else:
                    resolver = self.get_resolver()
                    dialog = notification(lot_owner, resolver=resolver)
                    if dialog is not None:
                        dialog.show_dialog()
                    break
        actor.sim_info.clear_goodbye_notification()
        return super().run_pre_transition_behavior()

    @classmethod
    def generate_aop(cls, target, context, **kwargs):
        actual_target = target if cls.target_type == TargetType.OBJECT else None
        return AffordanceObjectPair(cls, actual_target, cls, None, **kwargs)

    @classmethod
    def _test(cls, target, context, **kwargs):
        if not context.sim.sim_info.is_npc:
            return TestResult(False, 'Only for NPCs.')
        return TestResult.TRUE

    def _on_finishing_callback(self, interaction):
        if self.transition_failed:
            services.get_zone_situation_manager().make_sim_leave_now_must_run(self.sim)
        self.unregister_on_finishing_callback(self._on_finishing_callback)

    @flexmethod
    def constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        inst_or_cls = cls if inst is None else inst
        for constraint in inst_or_cls._constraint_gen(sim, target, participant_type):
            constraint = constraint.get_multi_surface_version()
            yield constraint

    def _run_interaction_gen(self, timeline):
        yield from super()._run_interaction_gen(timeline)
        client = services.client_manager().get_first_client()
        for sim in self._care_dependents:
            if sim is not None:
                sim.sim_info.inject_into_inactive_zone(self.to_zone_id, skip_instanced_check=True)
                sim.sim_info.save_sim()
                sim.schedule_destroy_asap(post_delete_func=client.send_selectable_sims_update, source=self, cause='Destroying sim in travel liability')

class ForceChangeToCurrentOutfit(SuperInteraction):
    INSTANCE_SUBCLASSES_ONLY = True

    def build_basic_elements(self, sequence=()):
        sequence = super().build_basic_elements(sequence=sequence)
        outfit_category_and_index = self.sim.get_current_outfit()
        exit_change = build_critical_section(sequence, self.sim.sim_info.get_change_outfit_element(outfit_category_and_index, do_spin=True, interaction=self), flush_all_animations)
        return exit_change

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, *args, to_zone_id=DEFAULT, **kwargs):
        yield from super()._constraint_gen(sim, target, *args, **kwargs)
        yield STAND_CONSTRAINT
create_tuningless_superinteraction(ForceChangeToCurrentOutfit)