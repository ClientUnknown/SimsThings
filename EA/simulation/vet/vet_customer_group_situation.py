import itertoolsfrom protocolbuffers import Business_pb2, DistributorOps_pb2from automation.automation_utils import automation_eventfrom business.business_situation_mixin import BusinessSituationMixinfrom distributor.ops import GenericProtocolBufferOpfrom distributor.system import Distributorfrom event_testing.resolver import DoubleSimResolverfrom event_testing.test_events import TestEventfrom event_testing.tests_with_data import TunableParticipantRanInteractionTestfrom filters.tunable import FilterTermTagfrom interactions import ParticipantTypefrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.interaction_finisher import FinishingTypefrom interactions.priority import Priorityfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, TunableReference, OptionalTunablefrom sims4.tuning.tunable_base import GroupNamesfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonInteractionCompletedSituationState, SituationStateData, TunableInteractionOfInterest, SituationState, TunableSituationJobAndRoleState, CommonSituationStatefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_types import SituationUserFacingTypefrom ui.ui_dialog import UiDialogOkCancel, ButtonTypefrom vet.vet_clinic_handlers import log_vet_flow_entryfrom vet.vet_clinic_utils import get_vet_clinic_zone_director, get_value_of_service_buffimport enumimport filtersimport servicesimport sims4.tuningimport situations.bouncerlogger = sims4.log.Logger('VetCustomerGroupSituation', default_owner='jdimailig')
class CustomerStateTypes(enum.Int, export=False):
    SPAWN = 0
    ARRIVAL = 1
    WAITING = 2
    RECEIVING = 3
    COMPLETE = 4
CUSTOMER_HAS_BEEN_SEEN_STATES = frozenset((CustomerStateTypes.RECEIVING, CustomerStateTypes.COMPLETE))
class _VetCustomerGroupSituationStateBase(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'locked_args': {'allow_join_situation': True, 'time_out': None}}

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._state_start_time = services.time_service().sim_now

    def _additional_tests(self, sim_info, event, resolver):
        return self.owner.is_sim_info_in_situation(sim_info)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._go_to_next_state()

    def _go_to_next_state(self):
        self.owner._change_state(self._next_state())

    def _next_state(self):
        raise NotImplementedError()

class _SpawnGate(SituationState):

    def _on_set_sim_role_state(self, sim, *args, **kwargs):
        super()._on_set_sim_role_state(sim, *args, **kwargs)
        if self.owner.num_of_sims >= self.owner.num_invited_sims:
            self.owner.on_all_sims_spawned()

class _ArrivalState(_VetCustomerGroupSituationStateBase):

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner.get_pet() is None or self.owner.get_pet_owner() is None:
            return False
        return super()._additional_tests(sim_info, event, resolver)

    def _next_state(self):
        return self.owner._waiting_state()

class _WaitingForServiceState(_VetCustomerGroupSituationStateBase):
    FACTORY_TUNABLES = {'service_request_interaction': TunableInteractionOfInterest(description='\n            When this interaction is run by the player on the customer, we will pop up\n            the service request dialog.\n            ', tuning_group=GroupNames.SITUATION), 'service_request_dialog': UiDialogOkCancel.TunableFactory(description='\n            The dialog to display when service_request_interaction runs.\n            \n            The tokens passed in will be the Pet Sim, and the Pet Owner Sim,\n            in that order.\n            ', tuning_group=GroupNames.SITUATION), 'take_on_customer_interaction': TunableReference(description='\n            When the service request dialog is accepted, the vet will \n            run the specified interaction on the pet.', manager=services.get_instance_manager(Types.INTERACTION), class_restrictions=('SuperInteraction',), tuning_group=GroupNames.SITUATION)}

    def __init__(self, service_request_interaction, service_request_dialog, take_on_customer_interaction, **kwargs):
        super().__init__(**kwargs)
        self._showing_dialog = False
        self.service_request_interaction = service_request_interaction
        self.service_request_dialog = service_request_dialog
        self.take_on_customer_interaction = take_on_customer_interaction

    def on_activate(self, reader=None):
        super().on_activate(reader)
        for custom_key in self._interaction_of_interest.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionStart, custom_key)
        for custom_key in self.service_request_interaction.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)
        self.owner.began_waiting()

    def handle_event(self, sim_info, event, resolver):
        if not self._additional_tests(sim_info, event, resolver):
            return
        if event == TestEvent.InteractionStart and resolver(self._interaction_of_interest):
            assigned_vet = resolver.get_participant(ParticipantType.Actor)
            if not assigned_vet.is_selectable:
                self.owner.assign_to_vet(assigned_vet)
        if event == TestEvent.InteractionComplete:
            actor_sim_info = resolver.get_participant(ParticipantType.Actor)
            if actor_sim_info.is_selectable and resolver(self.service_request_interaction):
                self._on_player_interaction_complete(actor_sim_info)
            elif resolver(self._interaction_of_interest):
                self._on_interaction_complete_by_actor(actor_sim_info)

    def _on_player_interaction_complete(self, actor_sim_info):
        if self._showing_dialog:
            return
        self._showing_dialog = True
        target_sim = self.owner.get_pet_owner()
        pet_sim = self.owner.get_pet()
        if target_sim is None or pet_sim is None:
            self.owner._self_destruct()
        self.owner.log_flow_entry('Presenting Service Request Dialog')
        dialog = self.service_request_dialog(actor_sim_info, resolver=DoubleSimResolver(pet_sim, target_sim))
        dialog.show_dialog(on_response=self._on_dialog_response)

    def _on_interaction_complete_by_actor(self, actor_sim_info):
        if not self._showing_dialog:
            if self.owner.assigned_vet is not actor_sim_info:
                self.owner.assign_to_vet(actor_sim_info)
            self._go_to_next_state()

    def _additional_tests(self, sim_info, event, resolver):
        target_sim = resolver.get_participant(ParticipantType.TargetSim)
        if not self.owner.is_sim_info_in_situation(target_sim):
            return False
        return True

    def _on_dialog_response(self, dialog):
        self._showing_dialog = False
        if dialog.response == dialog.response and dialog.response == ButtonType.DIALOG_RESPONSE_OK:
            assigned_vet = dialog.owner.get_sim_instance()
            pet = self.owner.get_pet()
            if assigned_vet is None or pet is None:
                self.owner._self_destruct()
                return
            context = InteractionContext(assigned_vet, InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT, Priority.High, insert_strategy=QueueInsertStrategy.NEXT)
            assigned_vet.push_super_affordance(self.take_on_customer_interaction, pet, context)
            self.owner.assign_to_vet(assigned_vet)
            self._go_to_next_state()

    def _next_state(self):
        return self.owner._service_state()

class _ReceivingServiceState(_VetCustomerGroupSituationStateBase):
    FACTORY_TUNABLES = {'correct_treatment_interaction_test': TunableParticipantRanInteractionTest(description='\n            Keep track of the cost of the correct treatment so the clinic can\n            be charged the expense and the customer can be billed for the treatment.\n            ', locked_args={'running_time': None, 'tooltip': None}), 'acceptable_treatment_interaction_test': TunableParticipantRanInteractionTest(description='\n            Keep track of the cost of an acceptable treatment so the clinic can\n            be charged the expense and the customer can be billed for the treatment.\n            \n            Unlike the Correct Treatments, this does not charge any bonuses for difficulty.\n            ', locked_args={'running_time': None, 'tooltip': None}), 'vet_reassignment_interaction': TunableInteractionOfInterest(description='\n            When this interaction is run by the player on the customer, this allows\n            this customer group to be assigned to the player.\n            ', tuning_group=GroupNames.SITUATION)}

    def __init__(self, correct_treatment_interaction_test, acceptable_treatment_interaction_test, vet_reassignment_interaction, **kwargs):
        super().__init__(**kwargs)
        self.correct_treatment_interaction_test = correct_treatment_interaction_test
        self.acceptable_treatment_interaction_test = acceptable_treatment_interaction_test
        self.vet_reassignment_interaction = vet_reassignment_interaction

    def _on_set_sim_role_state(self, sim, *args, **kwargs):
        super()._on_set_sim_role_state(sim, *args, **kwargs)
        if sim is self.owner.get_pet():
            if sim.sim_info.current_sickness is None:
                logger.warn('Sim {} is not and may never have been sick during this situation', sim)
                self.owner._sickness_difficulty = 0
            else:
                self.owner._sickness_difficulty = sim.sim_info.current_sickness.difficulty_rating
            for interaction in sim.get_all_running_and_queued_interactions():
                if not interaction.queued:
                    pass
                else:
                    interaction.cancel(FinishingType.SITUATIONS, cancel_reason_msg='Pet examination.')
            for interaction in tuple(sim.interaction_refs):
                if not interaction.queued:
                    pass
                elif interaction.context.sim.sim_info is not self.owner.assigned_vet:
                    interaction.cancel(FinishingType.SITUATIONS, cancel_reason_msg='Pet examination.')

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner.on_service_complete()
        super()._on_interaction_of_interest_complete()

    def _next_state(self):
        return self.owner._complete_state()

    def on_activate(self, reader=None):
        super().on_activate(reader)
        for (_, custom_key) in self.acceptable_treatment_interaction_test.get_custom_event_registration_keys():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)
        for (_, custom_key) in self.correct_treatment_interaction_test.get_custom_event_registration_keys():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)
        for custom_key in self.vet_reassignment_interaction.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionStart, custom_key)

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.InteractionComplete:
            if resolver(self.correct_treatment_interaction_test):
                self.owner.track_treatment_cost(resolver._interaction.get_simoleon_cost(), True)
            if resolver(self.acceptable_treatment_interaction_test):
                self.owner.track_treatment_cost(resolver._interaction.get_simoleon_cost(), False)
        elif event == TestEvent.InteractionStart and resolver(self.vet_reassignment_interaction) and self.owner.is_sim_info_in_situation(resolver.get_participant(ParticipantType.TargetSim)):
            self.owner.assign_to_vet(resolver.get_participant(ParticipantType.Actor))

class _ServiceCompleteState(CommonSituationState):

    def timer_expired(self):
        self.owner._self_destruct()
ASSIGNED_VET_ID_TOKEN = 'assigned_vet_id'TREATMENT_COST = 'treatment_cost'SICKNESS_DIFFICULTY = 'sickness_difficulty'SHOULD_AWARD_DIFFICULTY_BONUS = 'should_award_bonus'SHOULD_LEAVE_REVIEW = 'should_leave_review'
class VetCustomerGroupSituation(BusinessSituationMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'situation_job_mapping': TunableMapping(description="\n            A mapping of filter term tag to situation job.\n            \n            The filter term tag is returned as part of the sim filters used to \n            create the guest list for this particular situation.\n            \n            The situation job is the job that the Sim will be assigned to in\n            the situation.\n            \n            e.g. Map a human to 'pet owner', map a cat or dog to 'pet'\n            ", key_name='filter_tag', key_type=TunableEnumEntry(description='\n                The filter term tag returned with the filter results.\n                ', tunable_type=FilterTermTag, default=FilterTermTag.NO_TAG), value_name='job', value_type=TunableReference(description='\n                The job the Sim will receive when added to the situation.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), tuning_group=GroupNames.ROLES), 'owner_job_and_initial_role': TunableSituationJobAndRoleState(description='\n            The job assigned to pet owners and the initial role when the situation starts.\n            ', tuning_group=GroupNames.ROLES), 'pet_job_and_initial_role': TunableSituationJobAndRoleState(description='\n            The job assigned to pets and the initial role when the situation starts.\n            ', tuning_group=GroupNames.ROLES), 'group_filter': OptionalTunable(description='\n            The group filter for these Sims. This filter is what will\n            setup the Sims that need to spawn in. The value of the tags will\n            determine what Job the Sim will end up in.\n            \n            For player situation, this can be disabled as the start situation\n            request should assign participants to jobs.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=filters.tunable.TunableAggregateFilter, tuning_group=GroupNames.ROLES), enabled_by_default=True), '_arrival_state': _ArrivalState.TunableFactory(display_name='1. Arrival State', tuning_group=GroupNames.STATE), '_waiting_state': _WaitingForServiceState.TunableFactory(display_name='2. Waiting For Service State', tuning_group=GroupNames.STATE), '_service_state': _ReceivingServiceState.TunableFactory(display_name='3. Receiving Service State', tuning_group=GroupNames.STATE), '_complete_state': _ServiceCompleteState.TunableFactory(display_name='4. Service Complete State', tuning_group=GroupNames.STATE)}
    REMOVE_INSTANCE_TUNABLES = Situation.SITUATION_START_FROM_UI_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self._assigned_vet_id = None
        self._wait_start_time = None
        self._should_leave_review = False
        self._treatment_cost = None
        self._sickness_difficulty = None
        self._award_difficulty_bonus = None
        reader = self._seed.custom_init_params_reader
        if reader is not None:
            self._assigned_vet_id = reader.read_uint64(ASSIGNED_VET_ID_TOKEN, None)
            self._treatment_cost = reader.read_uint64(TREATMENT_COST, None)
            self._sickness_difficulty = reader.read_float(SICKNESS_DIFFICULTY, None)
            self._award_difficulty_bonus = reader.read_bool(SHOULD_AWARD_DIFFICULTY_BONUS, None)
            self._should_leave_review = reader.read_bool(SHOULD_LEAVE_REVIEW, False)

    @classmethod
    def _states(cls):
        return (SituationStateData(CustomerStateTypes.SPAWN, _SpawnGate), SituationStateData(CustomerStateTypes.ARRIVAL, _ArrivalState, factory=cls._arrival_state), SituationStateData(CustomerStateTypes.WAITING, _WaitingForServiceState, factory=cls._waiting_state), SituationStateData(CustomerStateTypes.RECEIVING, _ReceivingServiceState, factory=cls._service_state), SituationStateData(CustomerStateTypes.COMPLETE, _ServiceCompleteState, factory=cls._complete_state))

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.owner_job_and_initial_role.job, cls.owner_job_and_initial_role.role_state), (cls.pet_job_and_initial_role.job, cls.pet_job_and_initial_role.role_state)]

    @property
    def user_facing_type(self):
        return SituationUserFacingType.VET_SITUATION_EVENT

    @classmethod
    def get_predefined_guest_list(cls):
        if cls.group_filter is None:
            return
        guest_list = SituationGuestList(invite_only=True)
        situation_manager = services.get_zone_situation_manager()
        customer_filter = cls.group_filter
        instanced_sim_ids = [sim.sim_info.id for sim in services.sim_info_manager().instanced_sims_gen()]
        household_sim_ids = [sim_info.id for sim_info in services.active_household().sim_info_gen()]
        auto_fill_blacklist = set()
        for (job, _) in cls._get_tuned_job_and_default_role_state_tuples():
            auto_fill_blacklist.update(situation_manager.get_auto_fill_blacklist(sim_job=job))
        situation_sims = set()
        for situation in situation_manager.get_situations_by_tags(cls.tags):
            situation_sims.update(situation.invited_sim_ids)
        blacklist_sim_ids = set(itertools.chain(situation_sims, instanced_sim_ids, household_sim_ids, auto_fill_blacklist))
        filter_results = services.sim_filter_service().submit_matching_filter(sim_filter=customer_filter, allow_yielding=False, blacklist_sim_ids=blacklist_sim_ids, gsi_source_fn=cls.get_sim_filter_gsi_name)
        for result in filter_results:
            job = cls.situation_job_mapping.get(result.tag, cls.situation_job_mapping[result.tag])
            guest_list.add_guest_info(SituationGuestInfo(result.sim_info.sim_id, job, RequestSpawningOption.MUST_SPAWN, BouncerRequestPriority.EVENT_VIP))
        return guest_list

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self._assigned_vet_id is not None:
            writer.write_uint64(ASSIGNED_VET_ID_TOKEN, self._assigned_vet_id)
        if self._treatment_cost is not None:
            writer.write_uint64(TREATMENT_COST, self._treatment_cost)
        if self._sickness_difficulty is not None:
            writer.write_float(SICKNESS_DIFFICULTY, self._sickness_difficulty)
        if self._award_difficulty_bonus is not None:
            writer.write_bool(SHOULD_AWARD_DIFFICULTY_BONUS, self._award_difficulty_bonus)
        writer.write_bool(SHOULD_LEAVE_REVIEW, self._should_leave_review)

    def start_situation(self):
        if self._seed._guest_list.guest_info_count == 0:
            self._self_destruct()
            return
        super().start_situation()
        host_sim = self._guest_list.host_sim
        if host_sim is not None and not host_sim.is_npc:
            self._change_state(self._waiting_state())
        else:
            self._change_state(_SpawnGate())

    def on_all_sims_spawned(self):
        self._change_state(self._arrival_state())

    @property
    def owner_job(self):
        return self.owner_job_and_initial_role.job

    @property
    def pet_job(self):
        return self.pet_job_and_initial_role.job

    def get_pet_owner(self):
        job = self.owner_job
        pet_owner = next(iter(self.all_sims_in_job_gen(job)), None)
        if pet_owner is None:
            pet_owner = self._get_sim_from_guest_list(job)
        return pet_owner

    def get_pet(self):
        job = self.pet_job
        pet = next(iter(self.all_sims_in_job_gen(job)), None)
        if pet is None:
            pet = self._get_sim_from_guest_list(job)
        return pet

    def get_vet(self):
        vet_sim_info = self.assigned_vet
        if vet_sim_info is None:
            return
        return vet_sim_info.get_sim_instance()

    def began_waiting(self):
        self._wait_start_time = services.time_service().sim_now
        business_manager = services.business_service().get_business_manager_for_zone()
        (pet, pet_owner) = self._get_pet_and_owner_sim_infos()
        if business_manager is not None:
            business_manager.add_customer(pet_owner)
        sims_in_situation = (pet, pet_owner)
        is_player_in_situation = any(not sim.is_npc for sim in sims_in_situation)
        zone_director = get_vet_clinic_zone_director()
        if zone_director is None:
            self._self_destruct()
            return
        zone_director.on_customers_waiting(self.id, tuple(sim.sim_id for sim in sims_in_situation), player_situation=is_player_in_situation)
        self._should_leave_review = self.get_num_playable_sims() == 0
        automation_event(*('VetCustomerBeganWaiting',), SituationId=self.id, PetSimId=pet.sim_id, PetOwnerSimId=pet_owner.sim_id)

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        if job_type is not self.owner_job:
            return
        if self.current_state_type in (_SpawnGate, _ArrivalState):
            return
        self._business_manager = services.business_service().get_business_manager_for_zone()
        if self._business_manager is not None:
            self._business_manager.add_customer(sim.sim_info)

    def _get_pet_and_owner_sim_infos(self):
        pet = self.get_pet()
        pet_owner = self.get_pet_owner()
        pet_sim_info = self._get_sim_info_from_guest_list(self.pet_job) if pet is None else pet.sim_info
        pet_owner_sim_info = self._get_sim_info_from_guest_list(self.owner_job) if pet_owner is None else pet_owner.sim_info
        return (pet_sim_info, pet_owner_sim_info)

    @property
    def wait_start_time(self):
        return self._wait_start_time

    def track_treatment_cost(self, cost, qualifies_for_difficulty_bonus):
        self._treatment_cost = cost
        self._award_difficulty_bonus = qualifies_for_difficulty_bonus

    def get_payment_data(self):
        if None in (self._treatment_cost, self._sickness_difficulty, self._award_difficulty_bonus):
            logger.error('Invalid payment data: {} {} {}', self._treatment_cost, self._sickness_difficulty, self._award_difficulty_bonus)
            self._treatment_cost = 0 if self._treatment_cost is None else self._treatment_cost
            self._sickness_difficulty = 0 if self._sickness_difficulty is None else self._sickness_difficulty
            self._award_difficulty_bonus = False if self._award_difficulty_bonus is None else self._award_difficulty_bonus
        return (self._treatment_cost, self._sickness_difficulty, self._award_difficulty_bonus)

    def apply_value_of_service(self):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is None:
            return
        if self.assigned_vet is None:
            logger.error('Sim {} does not have an assigned vet. Value of service cannot be applied.', self.get_pet())
            return
        if self.get_pet_owner() is None:
            logger.error('Sim {} does not have a pet owner. Value of service cannot be applied.', self.get_pet())
            return
        buff_to_apply = get_value_of_service_buff(business_manager.markup_multiplier, self.assigned_vet)
        if buff_to_apply is not None:
            self.get_pet_owner().add_buff(buff_to_apply)

    def on_service_complete(self):
        self.unassign_from_vet()

    def assign_to_vet(self, vet):
        if self._assigned_vet_id == vet.sim_id:
            return
        if self._assigned_vet_id is not None:
            self.unassign_from_vet()
        self.log_flow_entry('Assigned to {}'.format(repr(vet)))
        self._assigned_vet_id = vet.sim_id
        zone_director = get_vet_clinic_zone_director()
        if zone_director is None:
            self._self_destruct()
            return
        zone_director.on_vet_assigned(self.id, vet.sim_id, tuple(sim.sim_id for sim in self.all_sims_in_situation_gen()))

    @property
    def assigned_vet(self):
        return services.sim_info_manager().get(self._assigned_vet_id)

    def unassign_from_vet(self):
        if self._assigned_vet_id is not None:
            vzd = get_vet_clinic_zone_director()
            if vzd is not None:
                vzd.remove_from_vet(self._assigned_vet_id)
                self._assigned_vet_id = None

    @property
    def waiting_to_be_seen(self):
        return self._cur_state is not None and self._state_to_uid(self._cur_state) == CustomerStateTypes.WAITING

    @property
    def customer_has_been_seen(self):
        return self._cur_state is not None and self._state_to_uid(self._cur_state) in CUSTOMER_HAS_BEEN_SEEN_STATES

    def _on_add_sim_to_situation(self, sim, job_type, role_state_type_override=None):
        super()._on_add_sim_to_situation(sim, job_type, role_state_type_override=role_state_type_override)
        if job_type == self.owner_job:
            (pet_sim_info, pet_owner_sim_info) = self._get_pet_and_owner_sim_infos()
            pet_sim_info.add_linked_sim(pet_owner_sim_info.sim_id)
            pet_owner_sim_info.add_linked_sim(pet_sim_info.sim_id)

    def _on_remove_sim_from_situation(self, sim):
        if not services.current_zone().is_zone_running:
            super()._on_remove_sim_from_situation(sim)
            return
        sim_job = self.get_current_job_for_sim(sim)
        services.get_zone_situation_manager().add_sim_to_auto_fill_blacklist(sim.id, sim_job=sim_job)
        (pet_sim_info, pet_owner_sim_info) = self._get_pet_and_owner_sim_infos()
        pet_sim_info.remove_linked_sim(pet_owner_sim_info.sim_id)
        pet_owner_sim_info.remove_linked_sim(pet_sim_info.sim_id)
        pet_owner = self.get_pet_owner()
        is_pet_owner = False if pet_owner is None else sim is pet_owner
        super()._on_remove_sim_from_situation(sim)
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None and is_pet_owner:
            business_manager.remove_customer(sim, review_business=self._should_leave_review)
            customer_msg = Business_pb2.BusinessCustomerUpdate()
            customer_msg.sim_id = pet_owner_sim_info.sim_id
            op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.BUSINESS_CUSTOMER_REMOVE, customer_msg)
            Distributor.instance().add_op_with_no_owner(op)

    @property
    def current_state_type(self):
        return self._get_state_type(self._cur_state)

    def _get_state_type(self, state):
        return self._uid_to_state_type(self._state_to_uid(state))

    def _change_state(self, state, reader=None):
        new_state_type = self._get_state_type(state)
        self.log_flow_entry('Transition to {}'.format(new_state_type.__name__))
        super()._change_state(state, reader=None)

    def on_remove(self):
        super().on_remove()
        self.unassign_from_vet()
        vzd = get_vet_clinic_zone_director()
        if vzd is not None:
            vzd.on_customer_situation_being_destroyed(self.id)

    def log_flow_entry(self, message):
        log_vet_flow_entry(repr(list(self.all_sims_in_situation_gen())), type(self).__name__, message)
sims4.tuning.instances.lock_instance_tunables(VetCustomerGroupSituation, duration=0, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.NORMAL)