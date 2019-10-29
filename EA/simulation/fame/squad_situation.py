from interactions.context import InteractionContext, QueueInsertStrategyfrom sims.outfits.outfit_enums import OutfitCategory, BodyTypeFlagfrom sims4.tuning.tunable import TunableReferencefrom situations.base_situation import _RequestUserDatafrom situations.bouncer.bouncer_request import BouncerRequestfrom situations.bouncer.bouncer_types import BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonSituationState, SituationStateDataimport interactions.priorityimport servicesimport sims4.resources
class _BeInSquadState(CommonSituationState):
    pass

class SquadSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'_be_in_squad_state': _BeInSquadState.TunableFactory(description='\n            The situation state used for sims in this situation.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_be_in_squad_state'), 'leader_job': TunableReference(description='\n            The job that the leader will have. This will be used to identify\n            the leader.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), 'squad_member_job': TunableReference(description='\n            The job that each member of the squad will get when they are added\n            to this situation.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), 'ensemble_type': TunableReference(description='    \n            The type of ensemble you want the squad to start.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ENSEMBLE))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ensemble = None

    @classmethod
    def _states(cls):
        return [SituationStateData(1, _BeInSquadState, factory=cls._be_in_squad_state)]

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls._be_in_squad_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def default_job(cls):
        pass

    def start_situation(self):
        super().start_situation()
        self._change_state(self._be_in_squad_state())

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        if job_type is self.leader_job:
            for sim_info_id in sim.sim_info.squad_members:
                request = BouncerRequest(self, callback_data=_RequestUserData(), requested_sim_id=sim_info_id, job_type=self.squad_member_job, request_priority=BouncerRequestPriority.BACKGROUND_HIGH, user_facing=False, exclusivity=self.exclusivity)
                self.manager.bouncer.submit_request(request)
        else:
            if self._ensemble is None:
                services.ensemble_service().create_ensemble(self.ensemble_type, self._situation_sims.keys())
                self._ensemble = services.ensemble_service().get_ensemble_for_sim(self.ensemble_type, sim)
            else:
                self._ensemble.add_sim_to_ensemble(sim)
            if job_type.job_uniform is None:
                self._fixup_sims_outfit(sim)

    def _fixup_sims_outfit(self, sim):
        sim_info = sim.sim_info
        if sim_info.is_child_or_younger:
            return
        leader_sim_info = self.requesting_sim_info
        if sim_info.species != leader_sim_info.species or sim_info.clothing_preference_gender != leader_sim_info.clothing_preference_gender:
            return
        leader_current_outfit = leader_sim_info.get_current_outfit()
        if leader_current_outfit[0] == OutfitCategory.BATHING:
            leader_current_outfit = (OutfitCategory.EVERYDAY, 0)
        with leader_sim_info.set_temporary_outfit_flags(leader_current_outfit[0], leader_current_outfit[1], BodyTypeFlag.CLOTHING_ALL):
            sim_info.generate_merged_outfit(leader_sim_info, (OutfitCategory.SITUATION, 0), sim_info.get_current_outfit(), leader_current_outfit, preserve_outfit_flags=True)
        if self.manager.sim_being_created is sim or not services.current_zone().is_zone_running:
            sim.set_current_outfit((OutfitCategory.SITUATION, 0))
        else:
            context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.High, insert_strategy=QueueInsertStrategy.NEXT, bucket=interactions.context.InteractionBucketType.DEFAULT)
            sim.push_super_affordance(self.CHANGE_TO_SITUATION_OUTFIT, None, context)

    def on_remove(self):
        super().on_remove()
        if self._ensemble is not None:
            self._ensemble.end_ensemble()
            self._ensemble = None
