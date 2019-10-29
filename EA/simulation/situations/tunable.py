import itertoolsfrom interactions import ParticipantTypefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom interactions.utils.loot_basic_op import BaseLootOperationfrom objects import ALL_HIDDEN_REASONSfrom sims4.tuning.tunable import TunableVariant, TunableList, TunableReference, TunableSingletonFactory, TunableFactory, Tunable, TunableMapping, OptionalTunable, TunableThreshold, TunableTuple, TunableSimMinute, TunableEnumEntry, TunableEnumFlags, TunableSet, TunableEnumWithFilterfrom singletons import DEFAULTfrom situations.situation_guest_info_factory import SituationGuestInfoFactoryfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfo, SituationInvitationPurposefrom situations.situation_phase import SituationPhasefrom snippets import TunableAffordanceFilterSnippetfrom statistics.statistic_conditions import TunableTimeRangeCondition, TunableEventBasedConditionfrom tag import Tagimport servicesimport sims4.logimport sims4.resourcesimport venues.venue_constantslogger = sims4.log.Logger('Situations')
class TunableSituationCreationUI(TunableFactory):

    @staticmethod
    def _factory(resolver, targeted_situation_participant, situations_available, **kwargs):

        def craft_situation(resolver, targeted_situation_participant, situations_available):
            actor = resolver.get_participant(ParticipantType.Actor)
            target = resolver.get_participant(targeted_situation_participant) if targeted_situation_participant is not None else None
            if targeted_situation_participant is not None and target is None:
                logger.error('None participant for: {} on resolver: {}'.format(targeted_situation_participant, resolver), owner='rmccord')
            services.get_zone_situation_manager().send_situation_start_ui(actor, target=target, situations_available=situations_available)
            return True

        return lambda : craft_situation(resolver, targeted_situation_participant, situations_available)

    FACTORY_TYPE = _factory

    def __init__(self, **kwargs):
        super().__init__(description='\n            Triggers the Situation Creation UI.\n            ', targeted_situation_participant=OptionalTunable(description='\n                    Tuning to make this situation creature UI to use the targeted\n                    situation UI instead of the regular situation creation UI.\n                    ', tunable=TunableEnumEntry(description='\n                        The target participant for this Situation.\n                        ', tunable_type=ParticipantType, default=ParticipantType.TargetSim)), situations_available=OptionalTunable(description="\n                An optional list of situations to filter with. This way, we can\n                pop up the plan an event flow, but restrict the situations that\n                are available. They still have to test for availability, but we\n                won't show others if one or more of these succeed.\n                \n                If the list contains any situations, other situations will not\n                show up if any in the list pass their tests. If the list is\n                empty or this field is disabled, then any situations that pass\n                their tests will be available.\n                ", tunable=TunableList(description='\n                    A list of Situations to restrict the Plan an Event flow.\n                    ', tunable=TunableReference(description='\n                        An available Situation in the Plan an Event flow.\n                        ', manager=services.situation_manager()))))

class TunableSituationStart(TunableFactory):

    @staticmethod
    def _factory(resolver, situation, user_facing=True, invite_participants=None, invite_actor=True, actor_init_job=None, invite_picked_sims=True, invite_target_sim=True, target_init_job=None, invite_household_sims_on_active_lot=False, situation_default_target=None, situation_created_callback=None, linked_sim_participant=None, situation_guest_info=None, **kwargs):

        def start_situation(resolver, situation, user_facing=True, invite_participants=None, invite_actor=True, actor_init_job=None, invite_picked_sims=True, invite_target_sim=True, target_init_job=None, invite_household_sims_on_active_lot=False, situation_default_target=None, situation_created_callback=None, linked_sim_participant=None, situation_guest_info=None, **kwargs):
            situation_manager = services.get_zone_situation_manager()

            def create_guest_info(sim_id, job_type):
                if situation_guest_info is None:
                    return SituationGuestInfo.construct_from_purpose(sim_id, job_type, SituationInvitationPurpose.INVITED)
                return situation_guest_info(sim_id, job_type)

            guest_list = situation.get_predefined_guest_list()
            if guest_list is None:
                sim = resolver.get_participant(ParticipantType.Actor)
                guest_list = SituationGuestList(invite_only=True, host_sim_id=sim.id)
                if situation.targeted_situation is not None:
                    target_sim = resolver.get_participant(ParticipantType.PickedSim)
                    if target_sim is None:
                        target_sim = resolver.get_participant(ParticipantType.TargetSim)
                    target_sim_id = target_sim.id if target_sim is not None else None
                    job_assignments = situation.get_prepopulated_job_for_sims(sim, target_sim_id)
                    for (sim_id, job_type_id) in job_assignments:
                        job_type = services.situation_job_manager().get(job_type_id)
                        guest_info = create_guest_info(sim_id, job_type)
                        guest_list.add_guest_info(guest_info)
                else:
                    default_job = situation.default_job()
                    if invite_picked_sims:
                        target_sims = resolver.get_participants(ParticipantType.PickedSim)
                        if target_sims:
                            for sim_or_sim_info in target_sims:
                                guest_info = create_guest_info(sim_or_sim_info.sim_id, default_job)
                                guest_list.add_guest_info(guest_info)
                    if invite_target_sim:
                        target_sim = resolver.get_participant(ParticipantType.TargetSim)
                        if target_sim is not None:
                            init_job = target_init_job if target_init_job is not None else default_job
                            guest_info = create_guest_info(target_sim.sim_id, init_job)
                            guest_list.add_guest_info(guest_info)
                    if invite_actor and guest_list.get_guest_info_for_sim(sim) is None:
                        init_job = actor_init_job if actor_init_job is not None else default_job
                        guest_info = create_guest_info(sim.sim_id, init_job)
                        guest_list.add_guest_info(guest_info)
                    if invite_household_sims_on_active_lot:
                        sims_to_invite = resolver.get_participants(ParticipantType.ActiveHousehold)
                        if sims_to_invite:
                            for sim_info in sims_to_invite:
                                if guest_list.get_guest_info_for_sim(sim_info) is not None:
                                    pass
                                elif sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
                                    guest_info = create_guest_info(sim_info.sim_id, default_job)
                                    guest_list.add_guest_info(guest_info)
                    for (paticipant_type, situation_jobs) in invite_participants.items():
                        target_sims = resolver.get_participants(paticipant_type)
                        if target_sims:
                            jobs = situation_jobs if situation_jobs is not None else (default_job,)
                            for (sim_or_sim_info, job_to_assign) in zip(target_sims, itertools.cycle(jobs)):
                                if not sim_or_sim_info.is_sim:
                                    pass
                                else:
                                    guest_info = create_guest_info(sim_or_sim_info.sim_id, job_to_assign)
                                    guest_list.add_guest_info(guest_info)
            zone_id = resolver.get_participant(ParticipantType.PickedZoneId) or 0
            default_target_id = None
            default_location = None
            if situation_default_target is not None:
                target_obj = resolver.get_participant(situation_default_target)
                if target_obj is not None:
                    default_target_id = target_obj.id
                    if target_obj.is_sim:
                        sim_instance = target_obj.get_sim_instance()
                        if sim_instance is not None:
                            default_location = sim_instance.location
                    else:
                        default_location = target_obj.location
            linked_sim_id = 0
            if linked_sim_participant is not None:
                linked_sim = resolver.get_participant(linked_sim_participant)
                if linked_sim is not None:
                    linked_sim_id = linked_sim.sim_id
            situation_id = situation_manager.create_situation(situation, guest_list=guest_list, user_facing=user_facing, zone_id=zone_id, default_target_id=default_target_id, default_location=default_location, linked_sim_id=linked_sim_id, **kwargs)
            if situation_id is None:
                return False
            if situation_created_callback is not None:
                situation_created_callback(situation_id)
            return True

        return lambda : start_situation(resolver, situation, user_facing=user_facing, invite_participants=invite_participants, invite_actor=invite_actor, actor_init_job=actor_init_job, invite_picked_sims=invite_picked_sims, invite_target_sim=invite_target_sim, target_init_job=target_init_job, invite_household_sims_on_active_lot=invite_household_sims_on_active_lot, situation_default_target=situation_default_target, situation_created_callback=situation_created_callback, linked_sim_participant=linked_sim_participant, situation_guest_info=situation_guest_info, **kwargs)

    def __init__(self, **kwargs):
        super().__init__(situation=TunableReference(description='\n                The Situation to start when this Interaction runs.\n                ', manager=services.situation_manager()), user_facing=Tunable(description='\n                If checked, then the situation will be user facing (have goals, \n                and scoring).\n                \n                If not checked, then situation will not be user facing.\n                \n                This setting does not override the user option to make all\n                situations non-scoring.\n                \n                Example: \n                    Date -> Checked\n                    Invite To -> Not Checked\n                ', tunable_type=bool, default=True), linked_sim_participant=OptionalTunable(description='\n                If enabled, this situation will be linked to the specified Sim.\n                ', tunable=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.Actor)), invite_participants=TunableMapping(description="\n                The map to invite certain participants into the situation as\n                specified job if assigned. Otherwise will invite them as\n                situation's default job.\n                ", key_type=TunableEnumEntry(description='\n                    The participant of who will join the situation.\n                    ', tunable_type=ParticipantType, default=ParticipantType.Actor), key_name='participants_to_invite', value_type=OptionalTunable(tunable=TunableList(description='\n                        A list of situation jobs that can be specified.  If a\n                        single job is specified then all Sims will be given\n                        that job.  Otherwise we will loop through all of the\n                        Sims invited and give them jobs in list order.  The\n                        list will begin to be repeated if we run out of jobs.\n                        \n                        NOTE: We cannot guarantee the order of the Sims being\n                        passed in most of the time.  Use this if you want a\n                        distribution of different jobs, but without a guarantee\n                        that Sims will be assigned to each one.\n                        ', tunable=TunableReference(manager=services.situation_job_manager())), disabled_name='use_default_job', enabled_name='specify_job'), value_name='invite_to_job'), invite_actor=Tunable(description='\n                If checked, then the actor of this interaction will be invited\n                in the default job. This is the common case.\n                \n                If not checked, then the actor will not be invited. The Tell\n                A Ghost Story interaction spawning a Ghost walkby is an example.\n                \n                If your situation takes care of all the sims that should be in\n                the default job itself (such as auto-invite) it will probably\n                not work if this is checked.\n                ', tunable_type=bool, default=True), actor_init_job=OptionalTunable(description='\n                The Situation job actor would be assigned while join the situation.\n                ', tunable=TunableReference(manager=services.situation_job_manager()), disabled_name='use_default_job', enabled_name='specify_job'), invite_picked_sims=Tunable(description='\n                If checked then any picked sims of this interaction will be\n                invited to the default job.  This is the common case.\n                \n                If not checked, then any picked sims will not be invited.  The\n                Tell A Ghost Story interaction spawning a Ghost walkby is an\n                example.\n                \n                If your situation takes care of all the sims that should be in\n                the default job itself (such as auto-invite) it will probably\n                not work if this is checked.\n                ', tunable_type=bool, default=True), invite_target_sim=Tunable(description='\n                If checked then the target sim of this interaction will be\n                invited to the default job.  This is the common case.\n                \n                If not checked, then the target sim will not be invited.  The\n                Tell A Ghost Story interaction spawning a Ghost walkby is an\n                example.\n                \n                If your situation takes care of all the sims that should be in\n                the default job itself (such as auto-invite) it will probably\n                not work if this is checked.\n                ', tunable_type=bool, default=True), target_init_job=OptionalTunable(description='\n                The Situation job target would be assigned while join the situation.\n                ', tunable=TunableReference(manager=services.situation_job_manager()), disabled_name='use_default_job', enabled_name='specify_job'), invite_household_sims_on_active_lot=Tunable(description='\n                If checked then all instanced sims on the active lot will be\n                invited. This is not a common case. An example of this is\n                leaving the hospital after having a baby, bringing both sims\n                home.\n                \n                If not checked, then no additional sims will be invited.\n                \n                If your situation takes care of all the sims that should be in\n                the default job itself (such as auto-invite) it will probably\n                not work if this is checked.\n                ', tunable_type=bool, default=False), situation_default_target=OptionalTunable(description='\n                If enabled, the participant of the interaction will be set as\n                the situation target object.\n                ', tunable=TunableEnumEntry(description="\n                    The participant that will be set as the situation's default target\n                    ", tunable_type=ParticipantType, default=ParticipantType.Object)), situation_guest_info=OptionalTunable(description='\n                By default, situation guest infos are created as an invite.\n                This overrrides that behavior.\n                ', tunable=SituationGuestInfoFactory()), description='Start a Situation as part of this Interaction.', **kwargs)

    FACTORY_TYPE = _factory

class CreateSituationElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'create_situation': TunableVariant(description='\n            Determine how to create a specific situation.\n            ', situation_creation_ui=TunableSituationCreationUI(), situation_start=TunableSituationStart())}

    def _do_behavior(self, *args, **kwargs):
        return self.create_situation(self.interaction.get_resolver(), *args, **kwargs)()

class DestroySituationsByTagsMixin:
    FACTORY_TUNABLES = {'situation_tags': TunableSet(description='\n            A situation must match at least one of the tuned tags in order to\n            be destroyed.\n            ', tunable=TunableEnumWithFilter(tunable_type=Tag, filter_prefixes=['situation'], default=Tag.INVALID, pack_safe=True)), 'required_participant': TunableEnumFlags(description='\n            If tuned, only situations with this participant will be destroyed.\n            ', enum_type=ParticipantType, default=ParticipantType.Invalid)}

    def _destroy_situations_by_tags(self, resolver):
        situation_manager = services.get_zone_situation_manager()
        situations = situation_manager.get_situations_by_tags(self.situation_tags)
        if situations:
            participant = None
            if self.required_participant is not None and self.required_participant != ParticipantType.Invalid:
                participant = resolver.get_participant(self.required_participant)
                if participant is None or not participant.is_sim:
                    return False
            for situation in situations:
                if participant and not situation.is_sim_info_in_situation(participant.sim_info):
                    pass
                else:
                    situation_manager.destroy_situation_by_id(situation.id)
        return True

class DestroySituationsByTagsElement(DestroySituationsByTagsMixin, XevtTriggeredElement):

    def _do_behavior(self, *args, **kwargs):
        self._destroy_situations_by_tags(self.interaction)
        return True

class JoinSituationElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'situation_type': TunableReference(description='\n            The situation to join.\n            ', manager=services.situation_manager()), 'situation_job': OptionalTunable(description='\n            The situation job that sim will get to while join the situation.\n            ', tunable=TunableReference(manager=services.situation_job_manager()), disabled_name='use_default_job', enabled_name='specify_job', disabled_value=DEFAULT), 'subject': TunableEnumFlags(description='\n            The participant of who will join the situation.\n            ', enum_type=ParticipantType, default=ParticipantType.Actor)}

    def _do_behavior(self, *args, **kwargs):
        situation_manager = services.get_zone_situation_manager()
        situation = situation_manager.get_situation_by_type(self.situation_type)
        if situation is None:
            logger.error('Fail to join situation since cannot find running situation {} for interaction {}', self.situation_type, self.interaction, owner='cjiang')
            return False
        subject = self.interaction.get_participant(self.subject)
        if subject is None or not subject.is_sim:
            logger.error('Fail to join situation since subject {} is not sim for interaction {}', self.subject, self.interaction, owner='cjiang')
            return False
        situation.invite_sim_to_job(subject, job=self.situation_job)
        return True

class LeaveSituationElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'situation_types': TunableList(description='\n            A list of all situations the Sim needs to leave.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SITUATION), pack_safe=True)), 'subject': TunableEnumFlags(description='\n            The participant of who will join the situation.\n            ', enum_type=ParticipantType, default=ParticipantType.Actor)}

    def _do_behavior(self, *args, **kwargs):
        subject = self.interaction.get_participant(self.subject)
        if subject is None or not subject.is_sim:
            logger.error('Fail to leave situation since subject {} is not sim for interaction {}', self.subject, self.interaction, owner='cjiang')
            return False
        situation_manager = services.get_zone_situation_manager()
        for situation in situation_manager.running_situations():
            if isinstance(situation, self.situation_types):
                situation_manager.remove_sim_from_situation(subject, situation.id)
        return True

class CreateSituationLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'create_situation': TunableSituationStart()}

    def __init__(self, create_situation, **kwargs):
        super().__init__(**kwargs)
        self.create_situation = create_situation

    def _apply_to_subject_and_target(self, subject, target, resolver):
        self.create_situation(resolver)()

class TunableUserAskNPCToLeave(TunableFactory):

    @staticmethod
    def _factory(interaction, subject, sequence=()):

        def ask_sim_to_leave(_):
            situation_manager = services.get_zone_situation_manager()
            subjects = interaction.get_participants(subject)
            for sim in subjects:
                situation_manager.user_ask_sim_to_leave_now_must_run(sim)

        return (sequence, ask_sim_to_leave)

    def __init__(self, **kwargs):
        super().__init__(subject=TunableEnumEntry(description='\n                                     Who to ask to leave.\n                                     ', tunable_type=ParticipantType, default=ParticipantType.TargetSim), description="\n                Ask the subjects to leave the lot. Only applies to NPCs who don't live here.\n                Situations the subjects are in may introduce additional behavior before they leave.\n                ")

    FACTORY_TYPE = _factory

class TunableMakeNPCLeaveMustRun(TunableFactory):

    @staticmethod
    def _factory(interaction, subject, sequence=()):

        def make_sim_leave(_):
            situation_manager = services.get_zone_situation_manager()
            subjects = interaction.get_participants(subject)
            for sim in subjects:
                situation_manager.make_sim_leave_now_must_run(sim)

        return (sequence, make_sim_leave)

    def __init__(self, **kwargs):
        super().__init__(subject=TunableEnumEntry(description='\n                                     Who to ask to leave.\n                                     ', tunable_type=ParticipantType, default=ParticipantType.Actor), description="Make the subject leave the lot proto. E.g. for motive distress. Only applies to NPCs who don't live here.")

    FACTORY_TYPE = _factory

class TunableSituationCondition(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, time_based=TunableTimeRangeCondition(description='The minimum and maximum amount of time required to satisify this condition.'), event_based=TunableEventBasedCondition(description='A condition that is satsified by some event'), default='time_based', **kwargs)

class TunableSummonNpc(TunableFactory):

    @staticmethod
    def _factory(interaction, subject, purpose, sequence=None, **kwargs):
        venue = services.get_current_venue()
        if venue is None:
            return sequence

        def summon(_):
            subjects = interaction.get_participants(subject)
            sim_info_manager = services.sim_info_manager()
            sim_infos = [sim_info_manager.get(sim_or_sim_info.sim_id) for sim_or_sim_info in subjects]
            host_sim = interaction.get_participant(ParticipantType.Actor)
            venue.summon_npcs(sim_infos, purpose, host_sim.sim_info)

        return (sequence, summon)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, subject=TunableEnumEntry(description='\n                Who to summon.\n                For social interactions use TargetSim.\n                For picker based interactions (phone, rel panel) use PickedSim.\n                ', tunable_type=ParticipantType, default=ParticipantType.TargetSim), purpose=TunableEnumEntry(description='\n                The purpose/reason the NPC is being summoned.\n                ', tunable_type=venues.venue_constants.NPCSummoningPurpose, default=venues.venue_constants.NPCSummoningPurpose.DEFAULT), **kwargs)

    FACTORY_TYPE = _factory

class TunableAffordanceScoring(TunableFactory):

    @staticmethod
    def _factory(affordance_list, score, **kwargs):
        affordance = kwargs.get('affordance')
        if affordance and affordance_list(affordance):
            return score
        return 0

    FACTORY_TYPE = _factory

    def __init__(self, **kwargs):
        super().__init__(affordance_list=TunableAffordanceFilterSnippet(), score=Tunable(int, 1, description='score sim will receive if running affordance'))

class TunableQualityMultiplier(TunableFactory):

    @staticmethod
    def _factory(obj, stat_to_check, threshold, multiplier):
        tracker = obj.get_tracker(stat_to_check)
        value = tracker.get_value(stat_to_check)
        if threshold.compare(value):
            return multiplier
        return 1

    FACTORY_TYPE = _factory

    def __init__(self, **kwargs):
        super().__init__(stat_to_check=TunableReference(services.statistic_manager()), threshold=TunableThreshold(description='Stat should be greater than this value for object creation to score.'), multiplier=Tunable(float, 1, description='Multiplier to be applied to score if object is created with this quality'))

class TunableSituationPhase(TunableSingletonFactory):
    FACTORY_TYPE = SituationPhase

    def __init__(self, **kwargs):
        super().__init__(job_list=TunableMapping(description='A list of roles associated with the situation.', key_type=TunableReference(services.situation_job_manager(), description='Job reference'), value_type=TunableReference(services.get_instance_manager(sims4.resources.Types.ROLE_STATE), description='Role the job will perform'), key_name='job', value_name='role'), exit_conditions=TunableList(TunableTuple(conditions=TunableList(TunableSituationCondition(description='A condition for a situation or single phase.'), description='A list of conditions that all must be satisfied for the group to be considered satisfied.')), description='A list of condition groups of which if any are satisfied, the group is satisfied.'), duration=TunableSimMinute(description='\n                                                    How long the phase will last in sim minutes.\n                                                    0 means forever, which should be used on the last phase of the situation.\n                                                    ', default=60), **kwargs)
