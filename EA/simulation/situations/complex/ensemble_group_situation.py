from sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableInterval, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom situations.bouncer.bouncer_types import BouncerExclusivityCategory, RequestSpawningOption, BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationStateData, TunableSituationJobAndRoleState, SituationStatefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_types import SituationCreationUIOptionimport filtersimport servicesimport sims4.logINDIVIDUAL_SIM_SITUATIONS = 'individual_sim_situations'logger = sims4.log.Logger('EnsembleGroupSituation', default_owner='rmccord')
class _GroupState(SituationState):
    pass

class EnsembleGroupSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'individual_sim_situation': Situation.TunableReference(description='\n            The behavior situation for a Sim in this ensemble.\n            \n            Ex: A situation for a business partner at the cafe so they will\n            want to get coffee before chatting and hanging out with other Sims\n            in this situation.\n            '), 'sim_job_and_role': TunableSituationJobAndRoleState(description="\n            The default job for a Sim in this situation. The role shouldn't\n            actually matter much because the individual Situation will put the\n            Sim in its own behavior when they are added.\n            "), 'num_sims': TunableInterval(description='\n            The number of sims we want in the situation and ensemble.\n            ', tunable_type=int, default_lower=2, default_upper=3, minimum=2, maximum=6), 'group_filter': TunableReference(description='\n            The group filter for these Sims. This filter is what will\n            setup the Sims that need to spawn in. They will be added\n            to Individual Sim Situations.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=filters.tunable.TunableAggregateFilter, tuning_group=GroupNames.ROLES)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        reader = self._seed.custom_init_params_reader
        if reader is not None:
            self._individual_sim_situations = list(reader.read_uint32s(INDIVIDUAL_SIM_SITUATIONS, list()))
        else:
            self._individual_sim_situations = []

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _GroupState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.sim_job_and_role.job, cls.sim_job_and_role.role_state)]

    @classmethod
    def default_job(cls):
        return cls.sim_job_and_role.job

    @classmethod
    def get_predefined_guest_list(cls):
        guest_list = SituationGuestList(invite_only=True)
        worker_filter = cls.group_filter if cls.group_filter is not None else cls.default_job().filter
        filter_results = services.sim_filter_service().submit_matching_filter(sim_filter=worker_filter, allow_yielding=False, number_of_sims_to_find=cls.num_sims.random_int(), gsi_source_fn=cls.get_sim_filter_gsi_name)
        if not filter_results:
            logger.error('Failed to find/create any sims for {};', cls, owner='rmccord')
            return guest_list
        for result in filter_results:
            guest_list.add_guest_info(SituationGuestInfo(result.sim_info.sim_id, cls.default_job(), RequestSpawningOption.MUST_SPAWN, BouncerRequestPriority.BACKGROUND_MEDIUM))
        return guest_list

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        situation_manager = services.get_zone_situation_manager()
        guest_list = SituationGuestList(invite_only=True)
        guest_list.add_guest_info(SituationGuestInfo(sim.sim_id, self.individual_sim_situation.default_job(), RequestSpawningOption.CANNOT_SPAWN, BouncerRequestPriority.BACKGROUND_MEDIUM))
        situation_id = situation_manager.create_situation(self.individual_sim_situation, guest_list=guest_list, user_facing=False)
        self._individual_sim_situations.append(situation_id)

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self._individual_sim_situations:
            situation = situation_manager.get(situation_id)
            if not situation is None:
                if situation.is_sim_in_situation(sim):
                    self._individual_sim_situations.remove(situation_id)
            self._individual_sim_situations.remove(situation_id)

    def start_situation(self):
        super().start_situation()
        self._change_state(_GroupState())

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        writer.write_uint32s(INDIVIDUAL_SIM_SITUATIONS, self._individual_sim_situations)
lock_instance_tunables(EnsembleGroupSituation, exclusivity=BouncerExclusivityCategory.NEUTRAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)