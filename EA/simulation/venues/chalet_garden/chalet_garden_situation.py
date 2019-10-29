from sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriority, BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import TunableSituationJobAndRoleState, SituationComplexCommon, SituationState, SituationStateDatafrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_types import SituationCreationUIOptionimport filtersimport servicesimport sims4logger = sims4.log.Logger('ChaletGardenSituation', default_owner='trevor')
class _GroupState(SituationState):
    pass

class ChaletGardenSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'man_job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role state for the man on the Chalet Garden lot.\n            '), 'woman_job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role state for the man on the Chalet Garden lot.\n            '), 'group_filter': TunableReference(description='\n            The group filter for these Sims. This filter is what will\n            setup the Sims that need to spawn in. They will be added\n            to Individual Sim Situations.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=filters.tunable.TunableAggregateFilter, tuning_group=GroupNames.ROLES)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _GroupState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.man_job_and_role.job, cls.man_job_and_role.role_state), (cls.woman_job_and_role.job, cls.woman_job_and_role.role_state)]

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def get_predefined_guest_list(cls):
        guest_list = SituationGuestList(invite_only=True)
        worker_filter = cls.group_filter if cls.group_filter is not None else cls.default_job().filter
        filter_results = services.sim_filter_service().submit_matching_filter(sim_filter=worker_filter, allow_yielding=False, gsi_source_fn=cls.get_sim_filter_gsi_name)
        if not filter_results:
            logger.error('Failed to find/create any sims for {};', cls)
            return guest_list
        for result in filter_results:
            job = cls.man_job_and_role.job if result.sim_info.is_male else cls.woman_job_and_role.job
            guest_list.add_guest_info(SituationGuestInfo(result.sim_info.sim_id, job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.BACKGROUND_MEDIUM))
        return guest_list

    def start_situation(self):
        super().start_situation()
        self._change_state(_GroupState())
lock_instance_tunables(ChaletGardenSituation, exclusivity=BouncerExclusivityCategory.VENUE_EMPLOYEE, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)