import itertoolsimport randomimport sysimport timefrom event_testing.results import TestResultfrom interactions import ParticipantType, ParticipantTypeSituationSimsfrom performance.test_profiling import TestProfileRecord, ProfileMetricsfrom sims4.utils import classpropertyfrom singletons import DEFAULTimport cachesimport event_testing.test_constantsimport servicesimport sims4.logimport sims4.reloadlogger = sims4.log.Logger('Resolver')with sims4.reload.protected(globals()):
    RESOLVER_PARTICIPANT = 'resolver'
    test_profile = NoneSINGLE_TYPES = frozenset((ParticipantType.Affordance, ParticipantType.InteractionContext, event_testing.test_constants.FROM_DATA_OBJECT, event_testing.test_constants.OBJECTIVE_GUID64, event_testing.test_constants.FROM_EVENT_DATA))
class Resolver:

    def __init__(self, skip_safe_tests=False, search_for_tooltip=False):
        self._skip_safe_tests = skip_safe_tests
        self._search_for_tooltip = search_for_tooltip

    @property
    def skip_safe_tests(self):
        return self._skip_safe_tests

    @property
    def search_for_tooltip(self):
        return self._search_for_tooltip

    @property
    def interaction(self):
        pass

    def get_resolved_args(self, expected):
        if expected is None:
            raise ValueError('Expected arguments from test instance get_expected_args are undefined: {}'.format(expected))
        ret = {}
        for (event_key, participant_type) in expected.items():
            if participant_type in SINGLE_TYPES:
                value = self.get_participant(participant_type, event_key=event_key)
            else:
                value = self.get_participants(participant_type, event_key=event_key)
            ret[event_key] = value
        return ret

    @property
    def profile_metric_key(self):
        pass

    def __call__(self, test):
        if test.expected_kwargs is None:
            expected_args = test.get_expected_args()
            if expected_args:
                test.expected_kwargs = tuple(expected_args.items())
            else:
                test.expected_kwargs = ()
        if test_profile is not None:
            start_time = time.perf_counter()
        resolved_args = {}
        for (event_key, participant_type) in test.expected_kwargs:
            if participant_type in SINGLE_TYPES:
                value = self.get_participants(participant_type, event_key=event_key)
                resolved_args[event_key] = value[0] if value else None
            else:
                resolved_args[event_key] = self.get_participants(participant_type, event_key=event_key)
        if test_profile is not None:
            resolve_end_time = time.perf_counter()
        result = test(**resolved_args)
        if test_profile is not None:
            test_end_time = time.perf_counter()
            resolve_time = resolve_end_time - start_time
            test_time = test_end_time - resolve_end_time
            self._record_test_profile_metrics(test, resolve_time, test_time)
        return result

    def _record_test_profile_metrics(self, test, resolve_time, test_time):
        global test_profile
        try:
            from event_testing.tests import TestSetInstance
            is_test_set = isinstance(test, type) and issubclass(test, TestSetInstance)
            test_name = '[TS]{}'.format(test.__name__) if is_test_set else test.__class__.__name__
            record = test_profile.get(test_name)
            if record is None:
                record = TestProfileRecord(is_test_set=is_test_set)
                test_profile[test_name] = record
            record.metrics.update(resolve_time, test_time)
            resolver_name = type(self).__name__
            resolver_dict = record.resolvers.get(resolver_name)
            if resolver_dict is None:
                resolver_dict = dict()
                record.resolvers[resolver_name] = resolver_dict
            key_name = self.profile_metric_key
            if key_name is None:
                key_name = 'Key'
            metrics = resolver_dict.get(key_name)
            if metrics is None:
                metrics = ProfileMetrics(is_test_set=is_test_set)
                resolver_dict[key_name] = metrics
            metrics.update(resolve_time, test_time)
        except Exception as e:
            logger.exception('Resetting test_profile due to an exception {}.', e, owner='manus')
            test_profile = None

    def get_participant(self, participant_type, **kwargs):
        participants = self.get_participants(participant_type, **kwargs)
        if not participants:
            return
        if len(participants) > 1:
            raise ValueError('Too many participants returned for {}!'.format(participant_type))
        return next(iter(participants))

    def get_participants(self, participant_type, **kwargs):
        raise NotImplementedError('Attempting to use the Resolver base class, use sub-classes instead.')

    def _get_participants_base(self, participant_type, **kwargs):
        if participant_type == RESOLVER_PARTICIPANT:
            return self
        return Resolver.get_particpants_shared(participant_type)

    def get_target_id(self, test, id_type=None):
        expected_args = test.get_expected_args()
        resolved_args = self.get_resolved_args(expected_args)
        resolved_args['id_type'] = id_type
        return test.get_target_id(**resolved_args)

    def get_posture_id(self, test):
        expected_args = test.get_expected_args()
        resolved_args = self.get_resolved_args(expected_args)
        return test.get_posture_id(**resolved_args)

    def get_tags(self, test):
        expected_args = test.get_expected_args()
        resolved_args = self.get_resolved_args(expected_args)
        return test.get_tags(**resolved_args)

    def get_localization_tokens(self, *args, **kwargs):
        return ()

    @staticmethod
    def get_particpants_shared(participant_type):
        if participant_type == ParticipantType.Lot:
            return (services.active_lot(),)
        elif participant_type == ParticipantType.LotOwners:
            owning_household = services.owning_household_of_active_lot()
            if owning_household is not None:
                return tuple(sim_info for sim_info in owning_household.sim_info_gen())
            return ()
        return ()
        if participant_type == ParticipantType.LotOwnersOrRenters:
            owning_household = services.owning_household_of_active_lot()
            if owning_household is not None:
                return tuple(sim_info for sim_info in owning_household.sim_info_gen())
            else:
                current_zone = services.current_zone()
                travel_group = services.travel_group_manager().get_travel_group_by_zone_id(current_zone.id)
                if travel_group is not None:
                    return tuple(sim_info for sim_info in travel_group.sim_info_gen())
            return ()
        if participant_type == ParticipantType.LotOwnerSingleAndInstanced:
            owning_household = services.owning_household_of_active_lot()
            if owning_household is not None:
                for sim_info in owning_household.sim_info_gen():
                    if sim_info.is_instanced():
                        return (sim_info,)
            return ()
        elif participant_type == ParticipantType.ActiveHousehold:
            active_household = services.active_household()
            if active_household is not None:
                return tuple(active_household.sim_info_gen())
            return ()
        elif participant_type == ParticipantType.CareerEventSim:
            career = services.get_career_service().get_career_in_career_event()
            if career is not None:
                return (career.sim_info.get_sim_instance() or career.sim_info,)
            return ()
        elif participant_type == ParticipantType.AllInstancedSims:
            return tuple(services.sim_info_manager().instanced_sims_gen())
        return ()
        if participant_type == ParticipantType.CareerEventSim:
            career = services.get_career_service().get_career_in_career_event()
            if career is not None:
                return (career.sim_info.get_sim_instance() or career.sim_info,)
            return ()
        elif participant_type == ParticipantType.AllInstancedSims:
            return tuple(services.sim_info_manager().instanced_sims_gen())

class GlobalResolver(Resolver):

    def get_participants(self, participant_type, **kwargs):
        result = self._get_participants_base(participant_type, **kwargs)
        if result is not None:
            return result
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        logger.error('GlobalResolver unable to resolve {}', participant_type)
        return ()

class AffordanceResolver(Resolver):

    def __init__(self, affordance, actor):
        super().__init__(skip_safe_tests=False, search_for_tooltip=False)
        self.affordance = affordance
        self.actor = actor

    def __repr__(self):
        return 'AffordanceResolver: affordance: {}, actor {}'.format(self.affordance, self.actor)

    def get_participants(self, participant_type, **kwargs):
        if participant_type == event_testing.test_constants.FROM_DATA_OBJECT:
            return ()
        if participant_type == event_testing.test_constants.OBJECTIVE_GUID64:
            return ()
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        elif participant_type == event_testing.test_constants.SIM_INSTANCE or participant_type == ParticipantType.Actor:
            if self.actor is not None:
                result = _to_sim_info(self.actor)
                if result:
                    return (result,)
            return ()
        return ()
        if participant_type == 0:
            logger.error('Calling get_participants with no flags on {}.', self)
            return ()
        if participant_type == ParticipantType.Affordance:
            return (self.affordance,)
        if participant_type == ParticipantType.AllRelationships:
            return (ParticipantType.AllRelationships,)
        return self._get_participants_base(participant_type, **kwargs)

    def __call__(self, test):
        if not test.supports_early_testing():
            return True
        if test.participants_for_early_testing is None:
            test.participants_for_early_testing = tuple(test.get_expected_args().values())
        for participant in test.participants_for_early_testing:
            if self.get_participants(participant) is None:
                return TestResult.TRUE
        return super().__call__(test)

class InteractionResolver(Resolver):

    def __init__(self, affordance, interaction, target=DEFAULT, context=DEFAULT, custom_sim=None, super_interaction=None, skip_safe_tests=False, search_for_tooltip=False, **interaction_parameters):
        super().__init__(skip_safe_tests, search_for_tooltip)
        self.affordance = affordance
        self._interaction = interaction
        self.target = interaction.target if target is DEFAULT else target
        self.context = interaction.context if context is DEFAULT else context
        self.custom_sim = custom_sim
        self.super_interaction = super_interaction
        self.interaction_parameters = interaction_parameters

    def __repr__(self):
        return 'InteractionResolver: affordance: {}, interaction:{}, target: {}, context: {}, si: {}'.format(self.affordance, self.interaction, self.target, self.context, self.super_interaction)

    @property
    def interaction(self):
        return self._interaction

    @property
    def profile_metric_key(self):
        if self.affordance is None:
            return 'NoAffordance'
        return self.affordance.__name__

    def get_participants(self, participant_type, **kwargs):
        if participant_type == event_testing.test_constants.SIM_INSTANCE:
            participant_type = ParticipantType.Actor
        if participant_type == ParticipantType.Actor:
            sim = self.context.sim
            if sim is not None:
                result = _to_sim_info(sim)
                if result is not None:
                    return (result,)
                return ()
        else:
            if participant_type == ParticipantType.Object:
                if self.target is not None:
                    result = _to_sim_info(self.target)
                    if result is not None:
                        return (result,)
                return ()
            elif participant_type == ParticipantType.TargetSim:
                if self.target is not None and self.target.is_sim:
                    result = _to_sim_info(self.target)
                    if result is not None:
                        return (result,)
                return ()
            return ()
            if participant_type == ParticipantType.ActorPostureTarget:
                if self.interaction is not None:
                    return self.interaction.get_participants(participant_type=participant_type)
                if self.super_interaction is not None:
                    return self.super_interaction.get_participants(participant_type=participant_type)
            elif participant_type == ParticipantType.AssociatedClub or participant_type == ParticipantType.AssociatedClubLeader or participant_type == ParticipantType.AssociatedClubMembers:
                associated_club = self.interaction_parameters.get('associated_club')
                if self.interaction is None and self.super_interaction is None or associated_club is not None:
                    if participant_type == ParticipantType.AssociatedClubLeader:
                        return (associated_club.leader,)
                    if participant_type == ParticipantType.AssociatedClub:
                        return (associated_club,)
                    if participant_type == ParticipantType.AssociatedClubMembers:
                        return tuple(associated_club.members)
            else:
                if participant_type == ParticipantType.ObjectCrafter:
                    if self.target is None or self.target.crafting_component is None:
                        return ()
                    crafting_process = self.target.get_crafting_process()
                    if crafting_process is None:
                        return ()
                    crafter_sim_info = crafting_process.get_crafter_sim_info()
                    if crafter_sim_info is None:
                        return ()
                    return (crafter_sim_info,)
                if participant_type in ParticipantTypeSituationSims:
                    provider_source = None
                    if self._interaction is not None:
                        provider_source = self._interaction
                    elif self.super_interaction is not None:
                        provider_source = self.super_interaction
                    elif self.affordance is not None:
                        provider_source = self.affordance
                    if provider_source is not None:
                        provider = provider_source.get_situation_participant_provider()
                        if provider is not None:
                            return provider.get_participants(participant_type, self)
                        logger.error("Requesting {} in {} that doesn't have a SituationSimParticipantProviderLiability", participant_type, provider_source)
        if participant_type == 0:
            logger.error('Calling get_participants with no flags on {}.', self)
            return ()
        result = self._get_participants_base(participant_type, **kwargs)
        if result is not None:
            return result
        if participant_type == event_testing.test_constants.FROM_DATA_OBJECT:
            return ()
        if participant_type == event_testing.test_constants.OBJECTIVE_GUID64:
            return ()
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        if participant_type == ParticipantType.Affordance:
            return (self.affordance,)
        if participant_type == ParticipantType.InteractionContext:
            return (self.context,)
        if participant_type == ParticipantType.CustomSim:
            if self.custom_sim is not None:
                return (self.custom_sim.sim_info,)
            ValueError('Trying to use CustomSim without passing a custom_sim in InteractionResolver.')
        elif participant_type == ParticipantType.AllRelationships:
            return (ParticipantType.AllRelationships,)
        if self.interaction is not None:
            participants = self.interaction.get_participants(participant_type=participant_type, sim=self.context.sim, target=self.target, listener_filtering_enabled=False, **self.interaction_parameters)
        elif self.super_interaction is not None:
            participants = self.super_interaction.get_participants(participant_type=participant_type, sim=self.context.sim, target=self.target, listener_filtering_enabled=False, target_type=self.affordance.target_type, **self.interaction_parameters)
        else:
            participants = self.affordance.get_participants(participant_type=participant_type, sim=self.context.sim, target=self.target, carry_target=self.context.carry_target, listener_filtering_enabled=False, target_type=self.affordance.target_type, **self.interaction_parameters)
        resolved_participants = set()
        for participant in participants:
            resolved_participants.add(_to_sim_info(participant))
        return tuple(resolved_participants)

    def get_localization_tokens(self, *args, **kwargs):
        return self.interaction.get_localization_tokens(*args, **kwargs)

@caches.clearable_barebones_cache
def _to_sim_info(participant):
    sim_info = getattr(participant, 'sim_info', None)
    if sim_info is None or sim_info.is_baby:
        return participant
    return sim_info

class AwayActionResolver(Resolver):
    VALID_AWAY_ACTION_PARTICIPANTS = ParticipantType.Actor | ParticipantType.TargetSim | ParticipantType.Lot

    def __init__(self, away_action, skip_safe_tests=False, search_for_tooltip=False, **away_action_parameters):
        super().__init__(skip_safe_tests, search_for_tooltip)
        self.away_action = away_action
        self.away_action_parameters = away_action_parameters

    def __repr__(self):
        return 'AwayActionResolver: away_action: {}'.format(self.away_action)

    @property
    def sim(self):
        return self.get_participant(ParticipantType.Actor)

    def get_participants(self, participant_type, **kwargs):
        if participant_type == 0:
            logger.error('Calling get_participants with no flags on {}.', self)
            return ()
        if participant_type == event_testing.test_constants.FROM_DATA_OBJECT:
            return ()
        if participant_type == event_testing.test_constants.OBJECTIVE_GUID64:
            return ()
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        if participant_type & AwayActionResolver.VALID_AWAY_ACTION_PARTICIPANTS:
            return self.away_action.get_participants(participant_type=participant_type, **self.away_action_parameters)
        raise ValueError('Trying to use AwayActionResolver without a valid type: {}'.format(participant_type))

    def get_localization_tokens(self, *args, **kwargs):
        return self.interaction.get_localization_tokens(*args, **kwargs)

class SingleSimResolver(Resolver):

    def __init__(self, sim_info_to_test, additional_participants={}, additional_localization_tokens=(), additional_metric_key_data=None):
        super().__init__()
        self.sim_info_to_test = sim_info_to_test
        self._additional_participants = additional_participants
        self._additional_localization_tokens = additional_localization_tokens
        self._source = None
        if event_testing.resolver.test_profile is not None:
            frame = sys._getframe(self.profile_metric_stack_depth)
            qualified_name = frame.f_code.co_filename
            unqualified_name = qualified_name.split('\\')[-1]
            self._source = unqualified_name
            if additional_metric_key_data is not None:
                self._source = '{}:{}'.format(self._source, additional_metric_key_data)

    def __repr__(self):
        return 'SingleSimResolver: sim_to_test: {}'.format(self.sim_info_to_test)

    @property
    def profile_metric_key(self):
        return 'source:{}'.format(self._source)

    @classproperty
    def profile_metric_stack_depth(cls):
        return 1

    def get_participants(self, participant_type, **kwargs):
        if participant_type == ParticipantType.Actor or participant_type == ParticipantType.CustomSim:
            return (self.sim_info_to_test,)
        elif participant_type == ParticipantType.SignificantOtherActor:
            significant_other = self.sim_info_to_test.get_significant_other_sim_info()
            if significant_other is not None:
                return (significant_other,)
            return ()
        elif participant_type == ParticipantType.PregnancyPartnerActor:
            pregnancy_partner = self.sim_info_to_test.pregnancy_tracker.get_partner()
            if pregnancy_partner is not None:
                return (pregnancy_partner,)
            return ()
        return ()
        if participant_type == ParticipantType.PregnancyPartnerActor:
            pregnancy_partner = self.sim_info_to_test.pregnancy_tracker.get_partner()
            if pregnancy_partner is not None:
                return (pregnancy_partner,)
            return ()
        if participant_type == ParticipantType.AllRelationships:
            return ParticipantType.AllRelationships
        elif participant_type == ParticipantType.ActorFeudTarget:
            feud_target = self.sim_info_to_test.get_feud_target()
            if feud_target is not None:
                return (feud_target,)
            return ()
        return ()
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        if participant_type == ParticipantType.InteractionContext or participant_type == ParticipantType.Affordance:
            return ()
        if participant_type == event_testing.test_constants.SIM_INSTANCE:
            return (self.sim_info_to_test,)
        if participant_type == ParticipantType.Familiar:
            return self._get_familiar_for_sim_info(self.sim_info_to_test)
        if participant_type in self._additional_participants:
            return self._additional_participants[participant_type]
        if participant_type == ParticipantType.PickedZoneId:
            return frozenset()
        result = self._get_participants_base(participant_type, **kwargs)
        if result is not None:
            return result
        raise ValueError('Trying to use {} with unsupported participant: {}'.format(type(self).__name__, participant_type))

    def _get_familiar_for_sim_info(self, sim_info):
        familiar_tracker = self.sim_info_to_test.familiar_tracker
        if familiar_tracker is None:
            return ()
        familiar = familiar_tracker.get_active_familiar()
        if familiar is None:
            return ()
        if familiar.is_sim:
            return (familiar.sim_info,)
        return (familiar,)

    def get_localization_tokens(self, *args, **kwargs):
        return (self.sim_info_to_test,) + self._additional_localization_tokens

    def set_additional_participant(self, participant_type, value):
        self._additional_participants[participant_type] = value

class DoubleSimResolver(SingleSimResolver):

    def __init__(self, sim_info, target_sim_info, **kwargs):
        super().__init__(sim_info, **kwargs)
        self.target_sim_info = target_sim_info

    def __repr__(self):
        return 'DoubleSimResolver: sim: {} target_sim: {}'.format(self.sim_info_to_test, self.target_sim_info)

    @classproperty
    def profile_metric_stack_depth(cls):
        return 2

    def get_participants(self, participant_type, **kwargs):
        if participant_type == ParticipantType.TargetSim:
            return (self.target_sim_info,)
        if participant_type == ParticipantType.SignificantOtherTargetSim:
            return (self.target_sim_info.get_significant_other_sim_info(),)
        if participant_type == ParticipantType.FamiliarOfTarget:
            return self._get_familiar_for_sim_info(self.target_sim_info)
        return super().get_participants(participant_type, **kwargs)

    def get_localization_tokens(self, *args, **kwargs):
        return (self.sim_info_to_test, self.target_sim_info) + self._additional_localization_tokens

class DataResolver(Resolver):

    def __init__(self, sim_info, event_kwargs=None):
        super().__init__()
        self.sim_info = sim_info
        if event_kwargs is not None:
            self._interaction = event_kwargs.get('interaction', None)
            self.on_zone_load = event_kwargs.get('init', False)
        else:
            self._interaction = None
            self.on_zone_load = False
        self.event_kwargs = event_kwargs
        self.data_object = None
        self.objective_guid64 = None

    def __repr__(self):
        return 'DataResolver: participant: {}'.format(self.sim_info)

    def __call__(self, test, data_object=None, objective_guid64=None):
        if data_object is not None:
            self.data_object = data_object
            self.objective_guid64 = objective_guid64
        return super().__call__(test)

    @property
    def interaction(self):
        return self._interaction

    @property
    def profile_metric_key(self):
        interaction_name = None
        if self._interaction is not None:
            interaction_name = self._interaction.aop.affordance.__name__
        objective_name = 'Invalid'
        if self.objective_guid64 is not None:
            objective_manager = services.objective_manager()
            objective = objective_manager.get(self.objective_guid64)
            objective_name = objective.__name__
        return 'objective:{} (interaction:{})'.format(objective_name, interaction_name)

    def get_resolved_arg(self, key):
        return self.event_kwargs.get(key, None)

    def get_participants(self, participant_type, event_key=None):
        result = self._get_participants_base(participant_type, event_key=event_key)
        if result is not None:
            return result
        if participant_type == event_testing.test_constants.SIM_INSTANCE:
            return (self.sim_info,)
        if participant_type == event_testing.test_constants.FROM_DATA_OBJECT:
            return (self.data_object,)
        if participant_type == event_testing.test_constants.OBJECTIVE_GUID64:
            return (self.objective_guid64,)
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            if not self.event_kwargs:
                return ()
            return (self.event_kwargs.get(event_key),)
        if self._interaction is not None:
            return tuple(getattr(participant, 'sim_info', participant) for participant in self._interaction.get_participants(participant_type))
        if participant_type == ParticipantType.Actor:
            return (self.sim_info,)
        if participant_type == ParticipantType.AllRelationships:
            sim_mgr = services.sim_info_manager()
            relations = set(sim_mgr.get(relations.get_other_sim_id(self.sim_info.sim_id)) for relations in self.sim_info.relationship_tracker)
            return tuple(relations)
        if participant_type == ParticipantType.TargetSim:
            if not self.event_kwargs:
                return ()
            target_sim_id = self.event_kwargs.get(event_testing.test_constants.TARGET_SIM_ID)
            if target_sim_id is None:
                return ()
            return (services.sim_info_manager().get(target_sim_id),)
        if participant_type == ParticipantType.ActiveHousehold:
            active_household = services.active_household()
            if active_household is not None:
                return tuple(active_household.sim_info_gen())
        if self.on_zone_load:
            return ()
        raise ValueError('Trying to use DataResolver with type that is not supported by DataResolver: {}'.format(participant_type))

class SingleObjectResolver(Resolver):

    def __init__(self, obj):
        super().__init__()
        self._obj = obj

    def __repr__(self):
        return 'SingleObjectResolver: object: {}'.format(self._obj)

    def get_participants(self, participant_type, **kwargs):
        if participant_type == ParticipantType.Object:
            return (self._obj,)
        if participant_type == ParticipantType.StoredSim:
            stored_sim_info = self._obj.get_stored_sim_info()
            return (stored_sim_info,)
        if participant_type == ParticipantType.StoredSimOrNameData:
            stored_sim_name_data = self._obj.get_stored_sim_info_or_name_data()
            return (stored_sim_name_data,)
        if participant_type == ParticipantType.OwnerSim:
            owner_sim_info_id = self._obj.get_sim_owner_id()
            owner_sim_info = services.sim_info_manager().get(owner_sim_info_id)
            return (owner_sim_info,)
        if participant_type == ParticipantType.ObjectParent:
            if self._obj is None or self._obj.parent is None:
                return ()
            return (self._obj.parent,)
        if participant_type == ParticipantType.ObjectChildren:
            if self._obj is None:
                return ()
            if self._obj.is_part:
                return tuple(self._obj.part_owner.children_recursive_gen())
            return tuple(self._obj.children_recursive_gen())
        if participant_type == ParticipantType.RandomInventoryObject:
            return (random.choice(tuple(self._obj.inventory_component.visible_storage)),)
        result = self._get_participants_base(participant_type, **kwargs)
        if result is not None:
            return result
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        raise ValueError('Trying to use SingleObjectResolver with something that is not an Object: {}'.format(participant_type))

    def get_localization_tokens(self, *args, **kwargs):
        return (self._obj,)

class DoubleObjectResolver(Resolver):

    def __init__(self, source_obj, target_obj):
        super().__init__()
        self._source_obj = source_obj
        self._target_obj = target_obj

    def __repr__(self):
        return 'DoubleObjectResolver: actor_object: {}, target_object:{}'.format(self._source_obj, self._target_obj)

    def get_participants(self, participant_type, **kwargs):
        result = self._get_participants_base(participant_type, **kwargs)
        if result is not None:
            return result
        if participant_type == ParticipantType.Actor or (participant_type == ParticipantType.PickedObject or participant_type == ParticipantType.CarriedObject) or participant_type == ParticipantType.LiveDragActor:
            if self._source_obj.is_sim:
                return (self._source_obj.sim_info,)
            return (self._source_obj,)
        if participant_type == ParticipantType.Listeners or (participant_type == ParticipantType.Object or participant_type == ParticipantType.TargetSim) or participant_type == ParticipantType.LiveDragTarget:
            if self._target_obj.is_sim:
                return (self._target_obj.sim_info,)
            return (self._target_obj,)
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        if participant_type == ParticipantType.LinkedPostureSim and self._source_obj.is_sim:
            posture = self._source_obj.posture
            if posture.multi_sim:
                return (posture.linked_posture.sim.sim_info,)
        raise ValueError('Trying to use DoubleObjectResolver with something that is not supported: Participant {}, Resolver {}'.format(participant_type, self))

    def get_localization_tokens(self, *args, **kwargs):
        return (self._source_obj, self._target_obj)

class SingleActorAndObjectResolver(Resolver):

    def __init__(self, actor_sim_info, obj, source):
        super().__init__()
        self._sim_info = actor_sim_info
        self._obj = obj
        self._source = source

    def __repr__(self):
        return 'SingleActorAndObjectResolver: sim_info: {}, object: {}'.format(self._sim_info, self._obj)

    @property
    def profile_metric_key(self):
        return 'source:{} object:{}'.format(self._source, self._obj)

    def get_participants(self, participant_type, **kwargs):
        result = self._get_participants_base(participant_type, **kwargs)
        if result is not None:
            return result
        if participant_type == ParticipantType.Actor or participant_type == ParticipantType.CustomSim or participant_type == event_testing.test_constants.SIM_INSTANCE:
            return (self._sim_info,)
        if participant_type == ParticipantType.Object:
            return (self._obj,)
        if participant_type == ParticipantType.ObjectParent:
            if self._obj is None or self._obj.parent is None:
                return ()
            return (self._obj.parent,)
        if participant_type == ParticipantType.StoredSim:
            stored_sim_info = self._obj.get_stored_sim_info()
            return (stored_sim_info,)
        if participant_type == ParticipantType.OwnerSim:
            owner_sim_info_id = self._obj.get_sim_owner_id()
            owner_sim_info = services.sim_info_manager().get(owner_sim_info_id)
            return (owner_sim_info,)
        if participant_type == ParticipantType.Affordance or participant_type == ParticipantType.InteractionContext or participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        raise ValueError('Trying to use SingleActorAndObjectResolver with something that is not supported: {}'.format(participant_type))

    def get_localization_tokens(self, *args, **kwargs):
        return (self._sim_info, self._obj)

class DoubleSimAndObjectResolver(Resolver):

    def __init__(self, actor_sim_info, target_sim_info, obj, source):
        super().__init__()
        self._actor_sim_info = actor_sim_info
        self._target_sim_info = target_sim_info
        self._obj = obj
        self._source = source

    def __repr__(self):
        return f'DoubleActorAndObjectResolver: actor_sim_info: {self._actor_sim_info}, target_sim_info: {self._target_sim_info}, object: {self._obj}'

    @property
    def profile_metric_key(self):
        return f'source:{self._source} object:{self._obj}'

    def get_participants(self, participant_type, **kwargs):
        result = self._get_participants_base(participant_type, **kwargs)
        if result is not None:
            return result
        if participant_type == ParticipantType.Actor or participant_type == ParticipantType.CustomSim or participant_type == event_testing.test_constants.SIM_INSTANCE:
            return (self._actor_sim_info,)
        if participant_type == ParticipantType.TargetSim:
            return (self._target_sim_info,)
        if participant_type == ParticipantType.SignificantOtherTargetSim:
            return (self._target_sim_info.get_significant_other_sim_info(),)
        if participant_type == ParticipantType.Object:
            return (self._obj,)
        if participant_type == ParticipantType.ObjectParent:
            if self._obj is None or self._obj.parent is None:
                return ()
            return (self._obj.parent,)
        if participant_type == ParticipantType.StoredSim:
            stored_sim_info = self._obj.get_stored_sim_info()
            return (stored_sim_info,)
        if participant_type == ParticipantType.OwnerSim:
            owner_sim_info_id = self._obj.get_sim_owner_id()
            owner_sim_info = services.sim_info_manager().get(owner_sim_info_id)
            return (owner_sim_info,)
        if participant_type == ParticipantType.Affordance:
            return ()
        if participant_type == ParticipantType.InteractionContext:
            return ()
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        raise ValueError(f'Trying to use DoubleActorAndObjectResolver with something that is not supported: {participant_type}')

    def get_localization_tokens(self, *args, **kwargs):
        return (self._sim_info, self._target_sim_info, self._obj)

class PhotoResolver(SingleActorAndObjectResolver):

    def __init__(self, photographer, photo_object, photo_targets, source):
        super().__init__(photographer, photo_object, source)
        self._photo_targets = photo_targets

    def __repr__(self):
        return 'PhotoResolver: photographer: {}, photo_object:{}, photo_targets:{}'.format(self._sim_info, self._obj, self._photo_targets)

    def get_participants(self, participant_type, **kwargs):
        if participant_type == ParticipantType.PhotographyTargets:
            return self._photo_targets
        return super().get_participants(participant_type, **kwargs)
