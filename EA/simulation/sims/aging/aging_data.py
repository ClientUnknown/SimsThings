from sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableMapping, TunableEnumEntry, TunableTuple, TunableRange, TunableReference, Tunablefrom sims4.tuning.tunable_base import ExportModes, EnumBinaryExportTypeimport sims4.resourcesfrom interactions.utils.death import DeathTypefrom interactions.utils.tunable_icon import TunableIconfrom sims.aging.aging_transition import TunableAgingTransitionReferencefrom sims.sim_info_types import Ageimport serviceslogger = sims4.log.Logger('AgingData')
class AgingData(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'ages': TunableMapping(description='\n            All available ages for this Sim, and any data associated with that\n            specific age.\n            ', key_type=TunableEnumEntry(description='\n                The available age for the Sim.\n                ', tunable_type=Age, default=Age.ADULT, binary_type=EnumBinaryExportType.EnumUint32), value_type=TunableTuple(description='\n                Any further data associated with this age.\n                ', transition=TunableAgingTransitionReference(description='\n                    The transition data associated with this age, such as\n                    dialogs, notifications, durations, etc...\n                    ', pack_safe=True), personality_trait_count=TunableRange(description='\n                    The number of traits available to a Sim of this age.\n                    ', tunable_type=int, default=3, minimum=0, export_modes=ExportModes.All), cas_icon=TunableIcon(description='\n                    Icon to be displayed in the ui for the age.\n                    ', export_modes=ExportModes.ClientBinary), cas_icon_selected=TunableIcon(description='\n                    Icon to be displayed in the UI for the age when buttons are\n                    selected.\n                    ', export_modes=ExportModes.ClientBinary), cas_name=TunableLocalizedStringFactory(description='\n                    The name to be displayed in the UI for the age.\n                    ', export_modes=ExportModes.ClientBinary), export_class_name='AvailableAgeDataTuple'), minlength=1, tuple_name='AvailableAgeDataMapping'), 'age_up_interaction': TunableReference(description='\n            The default interaction that ages Sims up. This is called when Sims\n            auto-age or when the "Age Up" cheat is invoked.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True), 'old_age_interaction': TunableReference(description='\n            The default interaction that transitions a Sim from old age to\n            death.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True), 'old_age_npc_death_type_fallback': TunableEnumEntry(description="\n            Used if the Old Age Interaction is not a death interaction.  In that\n            case, the non-instanced NPCs are not running the interaction but also\n            can't get their death type from the interaction's tuning.  This value\n            is used as a fallback.  The NPC's death type set to this value, and \n            it will effectively become a ghost.\n            ", tunable_type=DeathType, default=DeathType.NONE, pack_safe=True), 'bonus_days': TunableMapping(description='\n            Specify how much bonus time is added to elder Sims\n            possessing these traits.\n            ', key_type=TunableReference(description='\n                The trait associated with this modifier.\n                ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), pack_safe=True), value_type=Tunable(description='\n                The modifier associated with this trait.\n                ', tunable_type=float, default=0))}

    def get_age_transition_data(self, age):
        return self.ages[age].transition

    def get_birth_age(self):
        return min(self.ages)

    def get_lifetime_duration(self, sim_info):
        total_lifetime = sum(age_data.transition.get_age_duration(sim_info) for age_data in self.ages.values())
        aging_service = services.get_aging_service()
        total_lifetime /= aging_service.get_speed_multiple(aging_service.aging_speed)
        return total_lifetime

    def get_lifetime_bonus(self, sim_info):
        lifetime_duration = self.get_lifetime_duration(sim_info)
        bonus_multiplier = sum(modifier for (trait, modifier) in self.bonus_days.items() if sim_info.has_trait(trait))
        return lifetime_duration*bonus_multiplier

    def get_personality_trait_count(self, age):
        age_data = self.ages.get(age, None)
        if age_data is None:
            raise ValueError('{} is not in {}'.format(age, self.ages))
        return age_data.personality_trait_count

    def get_next_age(self, age):
        ages = tuple(sorted(self.ages))
        for (current_age, next_age) in zip(ages, ages[1:]):
            if current_age <= age and age < next_age:
                return next_age
        raise ValueError('There is no age after {}'.format(age))

    def get_previous_age(self, age):
        ages = tuple(sorted(self.ages))
        for (previous_age, current_age) in zip(ages, ages[1:]):
            if previous_age < age and age <= current_age:
                return previous_age
