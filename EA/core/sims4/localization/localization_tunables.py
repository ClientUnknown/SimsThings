from sims4.localization import TunableLocalizedStringFactoryVariant, LocalizationHelperTuningfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, OptionalTunable, TunableTuplefrom singletons import DEFAULTimport sims4.loglogger = sims4.log.Logger('Localization', default_owner='epanero')
class LocalizedStringHouseholdNameSelector(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'empty_household': OptionalTunable(description='\n            When enabled, this string will be used if the provided household\n            does not have any members.\n            ', tunable=TunableLocalizedStringFactoryVariant(description='\n                The string to use if the provided household has no members. This\n                string is provided the same tokens as the original string.\n                ')), 'single_sim': OptionalTunable(description='\n            When enabled, this string will be used if the Sim is the only member\n            of the household. If disabled, this check will be ignored.\n            ', tunable=TunableLocalizedStringFactoryVariant(description='\n                The string to use if the Sim is the only member of the\n                household. The first token is the only Sim of the household. It\n                might differ from the original Sim if the provided household is\n                different. The original Sim is the last token.\n                ')), 'single_family': OptionalTunable(description='\n            When enabled, this string will be used if the Sim is part of a\n            household where all Sims share the same last name. If disabled, this\n            check will be ignored.\n            ', tunable=TunableLocalizedStringFactoryVariant(description='\n                The string to use if all Sims in the household share the same\n                last name. The first token is a string containing the household\n                name. The original Sim is the last token.\n                ')), 'fallback': TunableLocalizedStringFactoryVariant(description='\n            The string to use of no other rule applies. The first token is a\n            string containing the household name.\n            '), 'pets': OptionalTunable(description='\n            If enabled, pet specific text is appended to the string.\n            ', tunable=TunableTuple(description='\n                The various strings that apply specifically to pets.\n                ', single_pet=TunableLocalizedStringFactoryVariant(description='\n                    The string to use if there is only one pet in the household.\n                    The first token is the pet.\n                    '), multiple_pets=TunableLocalizedStringFactoryVariant(description='\n                    The string to use if there is more than one pet in the\n                    household. The first token is the list of pets.\n                    ')))}

    def _get_string_for_humans(self, sim, household, *args, **kwargs):
        humans = tuple(household.get_humans_gen()) if household is not None else ()
        if not (self.empty_household is not None and (household is None or humans)):
            return self.empty_household(sim, *args, **kwargs)
        if household is None:
            logger.error("LocalizedStringHouseholdNameSelector is being provided a None household, but 'empty_household' text is unset.")
            return LocalizationHelperTuning.get_raw_text('')
        if self.single_sim is not None and len(humans) == 1:
            return self.single_sim(humans[0], args + (sim,), **kwargs)
        if self.single_family is not None and all(sim_info.last_name == sim.last_name for sim_info in humans) and sim.last_name == household.name:
            return self.single_family(sim.last_name, args + (sim,), **kwargs)
        return self.fallback(household.name, args + (sim,), **kwargs)

    def _get_string_for_pets(self, sim, household, *args, **kwargs):
        if self.pets is None:
            return
        pets = tuple(household.get_pets_gen()) if household is not None else ()
        if len(pets) == 1:
            return self.pets.single_pet(pets[0], *args, **kwargs)
        elif pets:
            return self.pets.multiple_pets(pets, *args, **kwargs)

    def __call__(self, sim, *args, household=DEFAULT, **kwargs):
        household = sim.household if household is DEFAULT else household
        string = self._get_string_for_humans(sim, household, *args, **kwargs)
        pets_string = self._get_string_for_pets(sim, household, *args, **kwargs)
        if pets_string is not None:
            string = LocalizationHelperTuning.NEW_LINE_LIST_STRUCTURE(string, pets_string)
        return string
