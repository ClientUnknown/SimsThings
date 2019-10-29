import itertoolsimport situationsfrom filters.tunable import FilterTermTag, TunableAggregateFilterfrom role.role_state import RoleStatefrom sims4.tuning.tunable import TunableTuple, TunableReference, TunableMapping, TunableEnumEntry, Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import RequestSpawningOptionfrom situations.complex.favorite_object_situation_mixin import FavoriteObjectSituationMixinfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationState, SituationStateData, CommonInteractionCompletedSituationStatefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_job import SituationJobimport filters.tunableimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('WalkbyMagicDuelSituation', default_owner='asantos')SIMS_RAN_INTERACTION = 'sims_ran_interaction'
class GoToDuelingGroundSituationState(CommonInteractionCompletedSituationState):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sims_ran_interaction = set()

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        if reader is not None:
            self._sims_ran_interaction = set(reader.read_uint64s(SIMS_RAN_INTERACTION, ()))

    def save_state(self, writer):
        super().save_state(writer)
        writer.write_uint64s(SIMS_RAN_INTERACTION, self._sims_ran_interaction)

    def _additional_tests(self, sim_info, event, resolver):
        return self.owner.is_sim_info_in_situation(sim_info)

    def _on_interaction_of_interest_complete(self, sim_info=None, **kwargs):
        self._sims_ran_interaction.add(sim_info.sim_id)
        if len(self._sims_ran_interaction) >= self.owner.get_sims_expected_to_be_in_situation():
            self._change_state(self.owner.duel_state())

class DuelSituationState(CommonInteractionCompletedSituationState):

    def _additional_tests(self, sim_info, event, resolver):
        return self.owner.is_sim_info_in_situation(sim_info)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._self_destruct()

class WalkbyMagicDuelSituation(FavoriteObjectSituationMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'go_to_dueling_ground_state': GoToDuelingGroundSituationState.TunableFactory(locked_args={'time_out': None, 'allow_join_situation': True}, tuning_group=GroupNames.STATE), 'duel_state': DuelSituationState.TunableFactory(locked_args={'time_out': None, 'allow_join_situation': True}, tuning_group=GroupNames.STATE)}

    @classmethod
    def _states(cls):
        return (SituationStateData.from_auto_factory(1, cls.go_to_dueling_ground_state), SituationStateData.from_auto_factory(2, cls.duel_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.go_to_dueling_ground_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def default_job(cls):
        pass

    @classproperty
    def situation_serialization_option(cls):
        return situations.situation_types.SituationSerializationOption.OPEN_STREETS

    def start_situation(self):
        super().start_situation()
        self._change_state(self.go_to_dueling_ground_state())

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        expected_sims = 0
        for job in cls.go_to_dueling_ground_state._tuned_values.job_and_role_changes.keys():
            expected_sims += job.sim_auto_invite.upper_bound
        return expected_sims
sims4.tuning.instances.lock_instance_tunables(WalkbyMagicDuelSituation, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE, duration=0, _implies_greeted_status=False)