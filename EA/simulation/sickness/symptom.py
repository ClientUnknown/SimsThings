from sims4.localization import TunableLocalizedStringFactoryfrom sims4.resources import Typesfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableReference, TunableSetfrom sims4.tuning.tunable_base import GroupNamesimport services
class Symptom(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(Types.SICKNESS)):
    INSTANCE_TUNABLES = {'display_name': TunableLocalizedStringFactory(description="\n            The symptom's display name. This string is provided with the owning\n            Sim as its only token.\n            ", tuning_group=GroupNames.UI), 'associated_buffs': TunableSet(description='\n            The associated buffs that will be added to the Sim when the symptom\n            is applied, and removed when the symptom is removed.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.BUFF), pack_safe=True)), 'associated_statistics': TunableSet(description="\n            The associated stats that will be added to the Sim when the symptom\n            is applied, and removed when the symptom is removed.\n            \n            These are added at the statistic's default value.\n            ", tunable=TunableReference(manager=services.get_instance_manager(Types.STATISTIC), pack_safe=True))}

    @classmethod
    def apply_to_sim_info(cls, sim_info):
        if sim_info is None:
            return
        for buff in cls.associated_buffs:
            if buff.can_add(sim_info) and not sim_info.has_buff(buff):
                sim_info.add_buff(buff, buff_reason=cls.display_name)
        for stat in cls.associated_statistics:
            if not sim_info.get_tracker(stat).has_statistic(stat):
                sim_info.add_statistic(stat, stat.default_value)

    @classmethod
    def remove_from_sim_info(cls, sim_info):
        if sim_info is None:
            return
        for buff in cls.associated_buffs:
            sim_info.remove_buff_by_type(buff)
        for stat in cls.associated_statistics:
            sim_info.remove_statistic(stat)
