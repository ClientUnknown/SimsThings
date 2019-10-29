from distributor.shared_messages import IconInfoDatafrom event_testing.test_events import TestEventfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableTuple, TunableMappingfrom sims4.tuning.tunable_base import GroupNamesfrom situations.complex.service_npc_situation import TunableFinishJobStateAndTestfrom situations.service_npcs import ServiceNpcEndWorkReasonfrom situations.service_npcs.butler.butler_loot_ops import ButlerSituationStatesfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationStateData, CommonSituationState, SituationState, TunableSituationJobAndRoleStatefrom situations.situation_types import SituationCreationUIOptionimport event_testingimport servicesimport sims4logger = sims4.log.Logger('SituationButler', default_owner='camilogarcia')
class ButlerSituationStateMixin(CommonSituationState):

    def on_activate(self, reader):
        super().on_activate(reader)
        finish_job_states = self.owner.finish_job_states
        for (_, finish_job_state) in finish_job_states.items():
            for (_, custom_key) in finish_job_state.enter_state_test.get_custom_event_registration_keys():
                self._test_event_register(event_testing.test_events.TestEvent.InteractionComplete, custom_key)

    def handle_event(self, sim_info, event, resolver):
        finish_job_states = self.owner.finish_job_states
        for (finish_reason, finish_job_state) in finish_job_states.items():
            if resolver(finish_job_state.enter_state_test):
                self._change_state(LeaveSituationState(finish_reason))
                break

    def _test_event(self, event, sim_info, resolver, test):
        if event in test.test_events:
            return self.owner.test_interaction_complete_by_job_holder(sim_info, resolver, self.owner.default_job(), test)
        return False

    def timer_expired(self):
        self.owner.try_set_next_state(self.next_state())

class _ButlerCleaningState(ButlerSituationStateMixin):

    @property
    def next_state(self):
        return self.owner.butler_states.gardening_state

    @property
    def situation_state(self):
        return ButlerSituationStates.CLEANING

class _ButlerGardeningState(ButlerSituationStateMixin):

    @property
    def next_state(self):
        return self.owner.butler_states.repair_state

    @property
    def situation_state(self):
        return ButlerSituationStates.GARDENING

class _ButlerChildcareState(ButlerSituationStateMixin):

    @property
    def next_state(self):
        return self.owner.butler_states.default_state

    @property
    def situation_state(self):
        return ButlerSituationStates.CHILDCARE

class _ButlerRepairState(ButlerSituationStateMixin):

    @property
    def next_state(self):
        return self.owner.butler_states.childcare_state

    @property
    def situation_state(self):
        return ButlerSituationStates.REPAIR

class _ButlerDefaultState(ButlerSituationStateMixin):

    @property
    def next_state(self):
        return self.owner.butler_states.cleaning_state

    @property
    def situation_state(self):
        return ButlerSituationStates.DEFAULT

class LeaveSituationState(SituationState):

    def __init__(self, leave_role_reason=None):
        super().__init__()
        self._leave_role_reason = leave_role_reason

    def on_activate(self, reader):
        super().on_activate(reader)
        if reader is None:
            service_sim = self.owner.service_sim()
            self.owner._on_leaving_situation(self._leave_role_reason)
            if service_sim is None:
                logger.warn('Service sim is None for {}.', self)
                return
            services.get_zone_situation_manager().make_sim_leave_now_must_run(service_sim)

class ServiceNpcButlerSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'_butler_job': TunableSituationJobAndRoleState(description='\n                The job for Butler in this situation and the \n                corresponding starting role state for service Sim.\n                ', display_name='Butler Npc Job'), 'butler_states': TunableTuple(cleaning_state=_ButlerCleaningState.TunableFactory(description='\n                Situation State for the butler to run all the clean \n                interactions.\n                '), gardening_state=_ButlerGardeningState.TunableFactory(description='\n                Situation State for the butler to run all the gardening\n                interactions.\n                '), childcare_state=_ButlerChildcareState.TunableFactory(description='\n                Situation State for the butler to run all the childcare\n                interactions.\n                '), repair_state=_ButlerRepairState.TunableFactory(description='\n                Situation State for the butler to run all the repair\n                interactions.\n                '), default_state=_ButlerDefaultState.TunableFactory(description='\n                Situation State for the butler to run all its default\n                interaction when no other service state is selected.\n                '), tuning_group=GroupNames.SITUATION), 'finish_job_states': TunableMapping(description='\n            Tune pairs of job finish role states with job finish tests. When\n            those tests pass, the sim will transition to the paired role state.\n            The situation will also be transitioned to the Leaving situation\n            state.\n            ', key_type=ServiceNpcEndWorkReason, value_type=TunableFinishJobStateAndTest())}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _ButlerDefaultState, factory=cls.butler_states.default_state), SituationStateData(2, _ButlerCleaningState, factory=cls.butler_states.default_state), SituationStateData(3, _ButlerGardeningState, factory=cls.butler_states.default_state), SituationStateData(4, _ButlerChildcareState, factory=cls.butler_states.default_state), SituationStateData(5, _ButlerRepairState, factory=cls.butler_states.default_state), SituationStateData(6, LeaveSituationState, factory=cls.butler_states.default_state))

    @classmethod
    def default_job(cls):
        return cls._butler_job.job

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.butler_states.default_state._tuned_values.job_and_role_changes.items())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._locked_states = set()
        reader = self._seed.custom_init_params_reader
        self._service_npc_type = services.service_npc_manager().get(reader.read_uint64('service_npc_type_id', 0))
        if self._service_npc_type is None:
            raise ValueError('Invalid service npc type for situation: {}'.format(self))
        self._hiring_household = services.household_manager().get(reader.read_uint64('household_id', 0))
        if self._hiring_household is None:
            raise ValueError('Invalid household for situation: {}'.format(self))
        self._service_start_time = services.time_service().sim_now

    def start_situation(self):
        super().start_situation()
        self._change_state(self.butler_states.default_state())

    def try_set_next_state(self, new_situation_state):
        if new_situation_state.situation_state in self._locked_states:
            new_situation_state.owner = self
            self.try_set_next_state(new_situation_state.next_state())
            return
        self._change_state(new_situation_state)

    def service_sim(self):
        sim = next(self.all_sims_in_situation_gen(), None)
        return sim

    def enable_situation_state(self, new_situation_state):
        if new_situation_state in self._locked_states:
            self._locked_states.remove(new_situation_state)
        services.get_event_manager().process_event(TestEvent.AvailableDaycareSimsChanged, sim_info=self.service_sim().sim_info)

    def disable_situation_state(self, new_situation_state):
        self._locked_states.add(new_situation_state)
        if self._cur_state.situation_state == new_situation_state:
            self.try_set_next_state(self._cur_state)
        services.get_event_manager().process_event(TestEvent.AvailableDaycareSimsChanged, sim_info=self.service_sim().sim_info)

    @property
    def is_in_childcare_state(self):
        return ButlerSituationStates.CHILDCARE not in self._locked_states

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        writer.write_uint64('household_id', self._hiring_household.id)
        writer.write_uint64('service_npc_type_id', self._service_npc_type.guid64)

    def _on_set_sim_job(self, sim, job_type):
        service_record = self._hiring_household.get_service_npc_record(self._service_npc_type.guid64)
        service_record.add_preferred_sim(sim.sim_info.id)
        self._service_npc_type.on_service_sim_entered_situation(sim, self)
        services.get_event_manager().process_event(TestEvent.AvailableDaycareSimsChanged, sim_info=self.service_sim().sim_info)
        services.current_zone().service_npc_service.register_service_npc(sim.id, self._service_npc_type)

    def _on_leaving_situation(self, end_work_reason):
        service_npc_type = self._service_npc_type
        household = self._hiring_household
        try:
            now = services.time_service().sim_now
            time_worked = now - self._service_start_time
            time_worked_in_hours = time_worked.in_hours()
            cost = service_npc_type.get_cost(time_worked_in_hours)
            if cost > 0:
                (paid_amount, billed_amount) = service_npc_type.try_charge_for_service(household, cost)
                if billed_amount:
                    end_work_reason = ServiceNpcEndWorkReason.NOT_PAID
            else:
                billed_amount = 0
            service_record = household.get_service_npc_record(service_npc_type.guid64)
            service_record.time_last_finished_service = now
            self._send_leave_notification(end_work_reason, paid_amount, billed_amount)
            if end_work_reason == ServiceNpcEndWorkReason.FIRED or end_work_reason == ServiceNpcEndWorkReason.NOT_PAID:
                service_sim = self.service_sim()
                if service_record is not None:
                    service_record.add_fired_sim(service_sim.id)
                    service_record.remove_preferred_sim(service_sim.id)
                    services.current_zone().service_npc_service.on_service_sim_fired(service_sim.id, service_npc_type)
            services.current_zone().service_npc_service.cancel_service(household, service_npc_type)
        except Exception as e:
            logger.exception('Exception while executing _on_leaving_situation for situation {}', self, exc=e)
        finally:
            services.current_zone().service_npc_service.cancel_service(household, service_npc_type)
        return end_work_reason

    def _send_leave_notification(self, end_work_reason, *localization_args):
        end_work_tuning = self.finish_job_states[end_work_reason]
        notification = end_work_tuning.notification
        if notification is None:
            return
        for client in services.client_manager().values():
            recipient = client.active_sim
            if recipient is not None:
                dialog = notification(recipient)
                dialog.show_dialog(additional_tokens=localization_args, icon_override=IconInfoData(obj_instance=self.service_sim()))
                break
lock_instance_tunables(ServiceNpcButlerSituation, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, venue_situation_player_job=None)