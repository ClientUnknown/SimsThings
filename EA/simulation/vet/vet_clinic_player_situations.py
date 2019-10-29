from protocolbuffers import Situations_pb2from distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import build_icon_info_msgfrom distributor.system import Distributorfrom event_testing.test_events import TestEventfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableResourceKey, TunableEnumEntryfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.base_situation import SituationDisplayPriorityfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, SituationStateData, SituationStatefrom situations.situation_goal import UiSituationGoalStatusfrom situations.situation_meter import StatBasedSituationMeterDatafrom situations.situation_types import SituationCreationUIOption, SituationSerializationOption, SituationDisplayTypeimport distributorimport servicesimport sims4logger = sims4.log.Logger('VetClinicPlayerSituation', default_owner='jdimailig')SICKNESS_MAJOR_GOAL_ID = 1SICKNESS_MINOR_GOAL_IDS = [2, 3, 4, 5, 6]PATIENT_STRESS_METER_ID = 1DIAGNOSIS_PROGRESS_METER_ID = 2ICON_CONTROL_ID = 0
class WaitForDiagnosisActorsState(SituationState):

    def _on_set_sim_role_state(self, sim, *args, **kwargs):
        super()._on_set_sim_role_state(sim, *args, **kwargs)
        if self.owner.num_of_sims >= self.owner.num_invited_sims:
            self._change_state(DiagnosisSituationState())

class DiagnosisSituationState(SituationState):

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self._progress_stat_meter = None
        self._stress_stat_meter = None

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        self._test_event_register(TestEvent.DiagnosisUpdated, custom_key=self.owner.get_pet().sim_id)
        self.owner.send_icon_update_to_client()
        self.owner.refresh_situation_goals()
        self._setup_situation_meters()
        self._update_situation_meters()

    def on_deactivate(self):
        super().on_deactivate()
        if self._progress_stat_meter is not None:
            self._progress_stat_meter.destroy()
        if self._stress_stat_meter is not None:
            self._stress_stat_meter.destroy()

    def handle_event(self, sim_info, event, resolver):
        self.owner.refresh_situation_goals(resolver=resolver)
        self._update_situation_meters()

    def _setup_situation_meters(self):
        self._progress_stat_meter = self.owner._progress_meter_settings.create_meter_with_sim_info(self.owner, self.owner.get_pet().sim_info)
        self._stress_stat_meter = self.owner._stress_meter_settings.create_meter_with_sim_info(self.owner, self.owner.get_pet().sim_info)

    def _update_situation_meters(self):
        if self._progress_stat_meter is not None:
            self._progress_stat_meter.send_update_if_dirty()
        if self._stress_stat_meter is not None:
            self._stress_stat_meter.send_update_if_dirty()

class VetClinicDiagnosisSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'vet_job': TunableSituationJobAndRoleState(description='\n            The job and role which the vet Sim is placed into.\n            ', tuning_group=GroupNames.ROLES), 'pet_job': TunableSituationJobAndRoleState(description='\n            The job and role which the pet Sim is placed into.\n            ', tuning_group=GroupNames.ROLES), 'undiscovered_sickness_text': TunableLocalizedStringFactory(description='\n            Text to use if a sickness is undiscovered.\n            ', tuning_group=GroupNames.UI), 'undiscovered_symptom_text': TunableLocalizedStringFactory(description='\n            Text to use if a symptom is undiscovered.\n            ', tuning_group=GroupNames.UI), '_progress_meter_settings': StatBasedSituationMeterData.TunableFactory(description='\n            The meter used to track the progress of the diagnosis.\n            ', tuning_group=GroupNames.SITUATION, locked_args={'_meter_id': DIAGNOSIS_PROGRESS_METER_ID}), '_stress_meter_settings': StatBasedSituationMeterData.TunableFactory(description='\n            The meter used to track the stress level of the patient.\n            ', tuning_group=GroupNames.SITUATION, locked_args={'_meter_id': PATIENT_STRESS_METER_ID}), 'audio_sting_on_symptom_discovery': TunableResourceKey(description='\n            The sound to play when a symptom is discovered.\n            ', resource_types=(sims4.resources.Types.PROPX,), default=None, allow_none=True, tuning_group=GroupNames.AUDIO)}
    REMOVE_INSTANCE_TUNABLES = ('_buff', 'targeted_situation', '_resident_job', '_relationship_between_job_members', 'force_invite_only', 'screen_slam_gold', 'screen_slam_silver', 'screen_slam_bronze', 'screen_slam_no_medal', 'main_goal', '_main_goal_visibility_test', 'minor_goal_chains', '_hidden_scoring_override', '_implies_greeted_status', '_level_data', 'weight_multipliers', 'recommended_job_object_notification', 'recommended_job_object_text') + Situation.SITUATION_START_FROM_UI_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, WaitForDiagnosisActorsState), SituationStateData(2, DiagnosisSituationState))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.vet_job.job, cls.vet_job.role_state), (cls.pet_job.job, cls.pet_job.role_state)]

    @classmethod
    def default_job(cls):
        return cls.vet_job.job

    @classmethod
    def get_tuned_jobs(cls):
        return [cls.vet_job.job, cls.pet_job.job]

    @classproperty
    def situation_serialization_option(cls):
        return SituationSerializationOption.DONT

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self._started_from_load = services.current_zone() is None or not services.current_zone().is_zone_running

    @property
    def situation_display_type(self):
        return SituationDisplayType.VET

    @property
    def situation_display_priority(self):
        return SituationDisplayPriority.VET

    def get_pet(self):
        if self._started_from_load:
            return self._get_sim_from_guest_list(self.pet_job.job)
        return next(iter(self.all_sims_in_job_gen(self.pet_job.job)), None)

    def get_vet(self):
        if self._started_from_load:
            return self._get_sim_from_guest_list(self.vet_job.job)
        return next(iter(self.all_sims_in_job_gen(self.vet_job.job)), None)

    def start_situation(self):
        super().start_situation()
        self._register_test_event(TestEvent.BusinessClosed)
        self._change_state(WaitForDiagnosisActorsState())

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.BusinessClosed:
            self._self_destruct()

    def get_create_op(self, *args, **kwargs):
        return distributor.ops.SituationStartOp(self, self.build_situation_start_message(), immediate=True)

    def on_added_to_distributor(self):
        super().on_added_to_distributor()
        if self._started_from_load and None not in (self.get_pet(), self.get_vet()):
            self._change_state(DiagnosisSituationState())

    def build_situation_start_message(self):
        msg = super().build_situation_start_message()
        with ProtocolBufferRollback(msg.meter_data) as meter_data_msg:
            self._progress_meter_settings.build_data_message(meter_data_msg)
        with ProtocolBufferRollback(msg.meter_data) as meter_data_msg:
            self._stress_meter_settings.build_data_message(meter_data_msg)
        return msg

    def has_offered_goals(self):
        return False

    def refresh_situation_goals(self, resolver=None):
        self._send_goal_update_to_client(resolver=resolver)

    def send_icon_update_to_client(self):
        msg = Situations_pb2.SituationIconUpdate()
        msg.situation_id = self.id
        build_icon_info_msg(self.get_pet().get_icon_info_data(), None, msg.icon_info)
        msg.icon_info.control_id = ICON_CONTROL_ID
        op = distributor.ops.SituationIconUpdateOp(msg)
        Distributor.instance().add_op(self, op)

    def _send_goal_update_to_client(self, resolver=None, completed_goal=None):
        pet = self.get_pet()
        if pet is None:
            return
        sickness = pet.sim_info.current_sickness
        op = distributor.ops.SituationGoalUpdateOp(self._create_situation_goal_update_msg(pet, sickness, resolver))
        Distributor.instance().add_op(self, op)

    def _create_situation_goal_update_msg(self, pet, sickness, resolver):
        msg = Situations_pb2.SituationGoalsUpdate()
        msg.goal_status = UiSituationGoalStatus.COMPLETED
        msg.situation_id = self.id
        self._set_major_goal_data(pet, sickness, msg.major_goal)
        self._set_minor_goals_data(pet, msg.goals)
        self._handle_completed_goal(resolver, sickness, msg)
        return msg

    def _handle_completed_goal(self, resolver, sickness, msg):
        recently_discovered_sickness = None if resolver is None else resolver.get_resolved_arg('discovered_sickness')
        if recently_discovered_sickness is sickness:
            msg.completed_goal_id = SICKNESS_MAJOR_GOAL_ID
            return msg
        else:
            recently_discovered_symptom = None if resolver is None else resolver.get_resolved_arg('discovered_symptom')
            if recently_discovered_symptom is not None:
                msg.completed_goal_id = SICKNESS_MINOR_GOAL_IDS[sickness.get_ordered_symptoms().index(recently_discovered_symptom)]
                return msg
        return msg

    def _set_major_goal_data(self, pet, sickness, major_goal_msg):
        is_sickness_discovered = False if sickness is None else pet.sim_info.sickness_tracker.has_discovered_sickness
        major_goal_name = sickness.display_name() if is_sickness_discovered else self.undiscovered_sickness_text()
        major_goal_msg.goal_id = SICKNESS_MAJOR_GOAL_ID
        major_goal_msg.goal_name = major_goal_name
        major_goal_msg.max_iterations = 1
        major_goal_msg.current_iterations = 1 if is_sickness_discovered else 0
        if self.main_goal_audio_sting is not None:
            major_goal_msg.audio_sting.type = self.main_goal_audio_sting.type
            major_goal_msg.audio_sting.group = self.main_goal_audio_sting.group
            major_goal_msg.audio_sting.instance = self.main_goal_audio_sting.instance

    def _set_minor_goals_data(self, pet, goals_msg):
        discovered_symptoms = pet.sim_info.sickness_tracker.discovered_symptoms
        while True:
            for i in range(0 if pet.sim_info.current_sickness is None else len(pet.sim_info.current_sickness.symptoms)):
                is_symptom_discovered = len(discovered_symptoms) > i and pet.sim_info.was_symptom_discovered(discovered_symptoms[i])
                symptom_goal_name = discovered_symptoms[i].display_name() if is_symptom_discovered else self.undiscovered_symptom_text()
                with ProtocolBufferRollback(goals_msg) as goal_msg:
                    goal_msg.goal_id = SICKNESS_MINOR_GOAL_IDS[i]
                    goal_msg.goal_name = symptom_goal_name
                    goal_msg.max_iterations = 1
                    goal_msg.current_iterations = 1 if is_symptom_discovered else 0
                    if self.audio_sting_on_symptom_discovery is not None:
                        goal_msg.audio_sting.type = self.audio_sting_on_symptom_discovery.type
                        goal_msg.audio_sting.group = self.audio_sting_on_symptom_discovery.group
                        goal_msg.audio_sting.instance = self.audio_sting_on_symptom_discovery.instance
lock_instance_tunables(VetClinicDiagnosisSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0)