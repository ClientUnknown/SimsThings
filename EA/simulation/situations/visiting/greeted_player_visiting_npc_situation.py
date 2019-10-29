from animation.posture_manifest_constants import STAND_CONSTRAINTfrom distributor.shared_messages import IconInfoDatafrom event_testing.test_events import TestEventfrom interactions.context import InteractionContextfrom interactions.priority import Priorityfrom interactions.utils.satisfy_constraint_interaction import ForceSatisfyConstraintSuperInteractionfrom objects.components.line_of_sight_component import TunableLineOfSightFactoryfrom sims.sim_info_types import Speciesfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import Tunable, TunableThreshold, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom situations.base_situation import _RequestUserDatafrom situations.bouncer.bouncer_request import SelectableSimRequestFactoryfrom situations.situation_complex import SituationStateData, CommonInteractionCompletedSituationState, SituationComplexCommon, TunableInteractionOfInterest, CommonSituationStatefrom situations.situation_types import SituationCreationUIOptionfrom situations.visiting.ungreeted_player_visiting_npc_situation import UngreetedPlayerVisitingNPCSituationfrom situations.visiting.visiting_situation_common import VisitingNPCSituationfrom ui.ui_dialog_notification import UiDialogNotificationimport interactionsimport role.role_stateimport servicesimport sims4.tuning.tunableimport situations.bouncer.bouncer_typesSCOLD_COUNT_TOKEN = 'scold_count'
class _GreetedPlayerVisitingNPCState(CommonSituationState):
    FACTORY_TUNABLES = {'scolding_interactions': TunableInteractionOfInterest(description='\n                 The interaction, when run increases your scold count.\n                 '), 'scolding_notification': UiDialogNotification.TunableFactory(description='\n            The notification to display after scolding a greeted player.\n            '), 'inappropriate_behavior_threshold': TunableThreshold(description='\n            Threshold for times a Sim may be scolded for inappropriate behavior.\n            When leaving this threshold, they will be sent away. \n            '), 'send_away_notification': UiDialogNotification.TunableFactory(description='\n            Notification to be triggered when sending away the sim.\n            '), 'send_away_inappropriate_sim_interaction': TunableReference(description='\n            The affordance that the reacting NPC will run to tell \n            the inappropriate Sim to leave. \n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))}

    def __init__(self, scolding_interactions, scolding_notification, inappropriate_behavior_threshold, send_away_notification, send_away_inappropriate_sim_interaction, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scolding_interactions = scolding_interactions
        self.scolding_notification = scolding_notification
        self.inappropriate_behavior_threshold = inappropriate_behavior_threshold
        self.send_away_notification = send_away_notification
        self.send_away_inappropriate_sim_interaction = send_away_inappropriate_sim_interaction
        self._scold_count = 0

    def on_activate(self, reader=None):
        super().on_activate(reader)
        if reader is None:
            self._scold_count = 0
        else:
            self._scold_count = reader.read_uint32(SCOLD_COUNT_TOKEN, 0)
        for custom_key in self.scolding_interactions.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)

    def save_state(self, writer):
        super().save_state(writer)
        writer.write_uint32(SCOLD_COUNT_TOKEN, self._scold_count)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionComplete and resolver(self.scolding_interactions):
            self._handle_scolding_interaction(sim_info, event, resolver)

    def _handle_scolding_interaction(self, sim_info, event, resolver):
        target = resolver.interaction.target
        if resolver.interaction.sim.sim_info is not sim_info:
            return
        if not self.owner.is_sim_in_situation(target):
            return
        self._scold_count += 1
        if self.inappropriate_behavior_threshold.compare(self._scold_count):
            dialog = self.scolding_notification(sim_info)
            dialog.show_dialog(secondary_icon_override=IconInfoData(obj_instance=sim_info))
        else:
            dialog = self.send_away_notification(sim_info)
            dialog.show_dialog(secondary_icon_override=IconInfoData(obj_instance=sim_info))
            sim = sim_info.get_sim_instance()
            context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.Critical)
            execute_result = sim.push_super_affordance(self.send_away_inappropriate_sim_interaction, target, context)
            if execute_result:
                execute_result.interaction.register_on_finishing_callback(self._sent_away_finished_callback)

    def _sent_away_finished_callback(self, interaction):
        if not interaction.is_finishing_naturally:
            return
        self.owner._change_state(self.owner.leave_npc_house_state())

class _LeaveNPCHouseState(CommonInteractionCompletedSituationState):

    def _additional_tests(self, sim_info, event, resolver):
        return self.owner.is_sim_info_in_situation(sim_info)

    def _on_interaction_of_interest_complete(self, sim_info=None, **kwargs):
        self.owner._handle_sim_left_home(sim_info)

    def timer_expired(self):
        self.owner._switch_to_ungreeted_situation()
SIMS_WHO_LEFT = 'sims_who_left'
class GreetedPlayerVisitingNPCSituation(VisitingNPCSituation):
    INSTANCE_TUNABLES = {'greeted_player_sims': sims4.tuning.tunable.TunableTuple(situation_job=situations.situation_job.SituationJob.TunableReference(description='\n                    The job given to player sims in the visiting situation.\n                    '), role_state=role.role_state.RoleState.TunableReference(description='\n                    The role state given to player sims in the visiting situation.\n                    '), tuning_group=GroupNames.ROLES), '_line_of_sight_factory': TunableLineOfSightFactory(description='\n                Tuning to generate a light of sight constraint in front of the\n                sim who rang the doorbell in order to make the sims in this\n                situation move into the house.\n                '), '_line_of_sight_generation_distance': Tunable(description='\n                The distance in front of the sim that rang the doorbell that we\n                generate the line of sight constraint.\n                ', tunable_type=float, default=2.0), 'greeted_player_visiting_npc_state': _GreetedPlayerVisitingNPCState.TunableFactory(description='\n            The state in which a greeted player is visiting an NPC. \n            ', display_name='1. Greeted Player Visiting NPC State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, locked_args={'time_out': None}), 'leave_npc_house_state': _LeaveNPCHouseState.TunableFactory(description='\n            The state in which an ungreeted household leaves the npc\n            house.   \n            ', display_name='2. Leave NPC House State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'ungreeted_player_visiting_npc_situation': TunableReference(description='\n            The situation that will be created after a previously greeted\n            player sim is kicked out by a npc. \n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), class_restrictions=(UngreetedPlayerVisitingNPCSituation,))}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _GreetedPlayerVisitingNPCState, factory=cls.greeted_player_visiting_npc_state), SituationStateData(2, _LeaveNPCHouseState, factory=cls.leave_npc_house_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.greeted_player_sims.situation_job, cls.greeted_player_sims.role_state)]

    @classmethod
    def default_job(cls):
        return cls.greeted_player_sims.situation_job

    def start_situation(self):
        super().start_situation()
        self._change_state(self.greeted_player_visiting_npc_state())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._line_of_sight = None
        reader = self._seed.custom_init_params_reader
        if reader is None:
            self._sims_who_left_house = set()
        else:
            self._sims_who_left_house = set(reader.read_uint64s(SIMS_WHO_LEFT, set()))
        if self._seed.is_loadable or self.initiating_sim_info is not None:
            sim = self.initiating_sim_info.get_sim_instance()
            if sim is not None:
                self._line_of_sight = self._line_of_sight_factory()
                position = sim.position
                position += sim.forward*self._line_of_sight_generation_distance
                self._line_of_sight.generate(position, sim.routing_surface)

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self._sims_who_left_house:
            writer.write_uint64s(SIMS_WHO_LEFT, self._sims_who_left_house)

    def _issue_requests(self):
        request = SelectableSimRequestFactory(self, callback_data=_RequestUserData(role_state_type=self.greeted_player_sims.role_state), job_type=self.greeted_player_sims.situation_job, exclusivity=self.exclusivity)
        self.manager.bouncer.submit_request(request)

    def _on_add_sim_to_situation(self, sim, job_type, role_state_type_override=None):
        super()._on_add_sim_to_situation(sim, job_type, role_state_type_override=role_state_type_override)
        if self._line_of_sight is not None and sim.species == Species.HUMAN:
            context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.High)
            constraint_to_satisfy = STAND_CONSTRAINT.intersect(self._line_of_sight.constraint)
            sim.push_super_affordance(ForceSatisfyConstraintSuperInteraction, None, context, constraint_to_satisfy=constraint_to_satisfy, name_override='MoveInsideHouseFromGreetedSituation')

    def _handle_sim_left_home(self, sim_info):
        self._sims_who_left_house.add(sim_info.sim_id)
        if len(self._sims_who_left_house) < self.num_of_sims:
            return
        self._switch_to_ungreeted_situation()

    def _switch_to_ungreeted_situation(self):
        services.get_zone_situation_manager().create_situation(self.ungreeted_player_visiting_npc_situation, user_facing=False)
        self._self_destruct()
lock_instance_tunables(GreetedPlayerVisitingNPCSituation, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.VISIT, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0, _implies_greeted_status=True)