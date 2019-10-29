from sims.sim_dialogs import SimPersonalityAssignmentDialogfrom sims.sim_info_types import Speciesfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableMapping, TunableEnumEntryfrom snippets import define_snippetfrom ui.ui_dialog_generic import TEXT_INPUT_FIRST_NAME, TEXT_INPUT_LAST_NAME
class PregnancyData(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'dialog': SimPersonalityAssignmentDialog.TunableFactory(description="\n            The dialog that is displayed when an offspring is created. It allows\n            the player to enter a first and last name for the Sim. An additional\n            token is passed in: the offspring's Sim data.\n            ", text_inputs=(TEXT_INPUT_FIRST_NAME, TEXT_INPUT_LAST_NAME))}
(TunablePregnancyDataReference, _) = define_snippet('Pregnancy', PregnancyData.TunableFactory())
class PregnancyTuning:
    PREGNANCY_DATA = TunableMapping(description='\n        A mapping of species to pregnancy data.\n        ', key_type=TunableEnumEntry(description="\n            The newborn's species.\n            ", tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)), value_type=TunablePregnancyDataReference(pack_safe=True))

    @classmethod
    def get_pregnancy_data(cls, sim_info):
        return cls.PREGNANCY_DATA.get(sim_info.species)
