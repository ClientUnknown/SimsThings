from interactions.base.picker_interaction import PickerSuperInteractionfrom sims import sim_spawnerfrom sims.pets.breed_tuning import all_breeds_genfrom sims.sim_info_types import SpeciesExtendedfrom sims4.localization import TunableLocalizedString, LocalizationHelperTuningfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntryfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom ui.ui_dialog_picker import TunablePickerDialogVariant, ObjectPickerTuningFlags, BasePickerRowimport sims4logger = sims4.log.Logger('BreedPickerSuperInteraction')
class BreedPickerSuperInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': TunablePickerDialogVariant(description='\n            The item picker dialog.\n            ', available_picker_flags=ObjectPickerTuningFlags.ITEM, default='item_picker', tuning_group=GroupNames.PICKERTUNING), 'species_name': TunableMapping(description="\n            If specified, for a particular species, include this text in the\n            breed's name.\n            ", key_type=TunableEnumEntry(tunable_type=SpeciesExtended, default=SpeciesExtended.HUMAN, invalid_enums=(SpeciesExtended.INVALID,)), value_type=TunableLocalizedString(), tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        if inst is not None:
            breed_species = []
            species = inst.interaction_parameters['species']
            for species_extended in SpeciesExtended:
                if species_extended == SpeciesExtended.INVALID:
                    pass
                elif SpeciesExtended.get_species(species_extended) == species:
                    breed_species.append(species_extended)
        else:
            breed_species = (None,)
        for _breed_species in breed_species:
            for breed in all_breeds_gen(species=_breed_species):
                name = breed.breed_display_name
                name = LocalizationHelperTuning.NAME_VALUE_PARENTHESIS_PAIR_STRUCTURE(name, cls.species_name[_breed_species])
                row = BasePickerRow(name=name, row_description=breed.breed_description, tag=breed)
                yield row

    def on_choice_selected(self, choice_tag, **kwargs):
        breed = choice_tag
        if breed is not None:
            position = self.context.pick.location
            actor_sim_info = self.sim.sim_info
            params = self.interaction_parameters
            age = params['age']
            gender = params['gender']
            species = breed.breed_species
            sim_creator = sim_spawner.SimCreator(age=age, gender=gender, species=species, additional_tags=(breed.breed_tag,))
            (sim_info_list, _) = sim_spawner.SimSpawner.create_sim_infos((sim_creator,), account=actor_sim_info.account, zone_id=actor_sim_info.zone_id, creation_source='cheat: BreedPickerSuperInteraction')
            sim_info = sim_info_list[0]
            sim_spawner.SimSpawner.spawn_sim(sim_info, sim_position=position, is_debug=True)
