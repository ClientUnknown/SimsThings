import randomfrom sims.outfits.outfit_enums import OutfitCategoryfrom sims.sim_info_base_wrapper import SimInfoBaseWrapperfrom sims.sim_info_types import SpeciesExtendedfrom sims4.localization import TunableLocalizedStringfrom sims4.resources import Typesfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import TunableReference, TunableTuple, TunableSet, TunableEnumEntry, TunableList, TunableResourceKey, TunableInterval, Tunable, HasTunableReferencefrom sims4.tuning.tunable_base import ExportModes, EnumBinaryExportTypefrom tag import TunableTag, Tagimport servicesimport sims4.resourceslogger = sims4.log.Logger('BreedTuning')BREED_TAG_FILTER_PREFIXES = ('breed',)with sims4.reload.protected(globals()):
    BREED_TAG_TO_TUNING_ID_MAP = {}
class Breed(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.BREED)):
    INSTANCE_TUNABLES = {'breed_display_name': TunableLocalizedString(description='\n            The breed display name.\n            ', export_modes=ExportModes.All), 'breed_description': TunableLocalizedString(description='\n            The breed description.\n            ', export_modes=ExportModes.All), 'breed_species': TunableEnumEntry(description='\n            This breed is restricted to this species.\n            ', tunable_type=SpeciesExtended, default=SpeciesExtended.HUMAN, invalid_enums=(SpeciesExtended.HUMAN, SpeciesExtended.INVALID), binary_type=EnumBinaryExportType.EnumUint32, export_modes=ExportModes.All), 'breed_tag': TunableTag(description='\n            The tag associated with this breed.\n            ', filter_prefixes=BREED_TAG_FILTER_PREFIXES, pack_safe=False, export_modes=ExportModes.All), 'breed_traits': TunableSet(description='\n            Traits that are by default associated with this breed.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.TRAIT)), export_modes=ExportModes.All), 'breed_voices': TunableList(description='\n            A list valid voice actors and pitch ranges that this breed can have\n            when randomly generated.\n            ', tunable=TunableTuple(breed_voice_actor_index=Tunable(description="\n                    The breed's default voice actor is a combination of its species\n                    and index. In general, 0-3 is mapped to A-D, though not all\n                    species have all four.\n                    \n                    (The mapping of species+index to voice actor is maintained in\n                    CASSharedUtils.cpp.)\n        \n                    Dogs and small dogs share the same voice actors, and have four:\n                    Index 0 - DogA (Generic Dog)\n                    Index 1 - DogB (Small Yappy Dog)\n                    Index 2 - DogC (Tough Dog)\n                    Index 3 - DogD (Big Dumb Hound Dog)\n                    \n                    Cats have two:\n                    Index 0 - CatA (Generic Cat)\n                    Index 1 - CatB (Scratchy Alley Cat)\n                    ", tunable_type=int, default=0), breed_voice_pitch=TunableInterval(description='\n                    Min/max voice pitch that the breed will have.\n                    ', tunable_type=float, default_lower=-1, default_upper=1, minimum=-1, maximum=1), export_class_name='BreedVoiceTuple'), export_modes=ExportModes.All), 'sim_info_resources': TunableSet(description='\n            A list of YA resources for the breed. CAS will attempt to age down \n            or up when they are generating the sim info with the age we pass in\n            through the SimInfo. \n            ', tunable=TunableResourceKey(resource_types=(sims4.resources.Types.SIMINFO,)))}

    @classmethod
    def _tuning_loaded_callback(cls):
        BREED_TAG_TO_TUNING_ID_MAP[cls.breed_tag] = cls.guid64

def all_breeds_gen(species=None):
    yield from (breed for breed in services.get_instance_manager(sims4.resources.Types.BREED).types.values() if species is None or breed.breed_species == species)

def get_random_breed_tag(species):
    breed_tags = tuple(breed.breed_tag for breed in all_breeds_gen(species=species))
    if not breed_tags:
        return
    return random.choice(breed_tags)

def get_breed_tag_from_tag_set(tags):
    breed_tags = tuple(tag for tag in tags if tag in BREED_TAG_TO_TUNING_ID_MAP)
    if len(breed_tags) != 1:
        return Tag.INVALID
    return breed_tags[0]

def try_conform_sim_info_to_breed(sim_info, breed_tag):
    breed = get_breed_from_tag(breed_tag)
    if breed is not None:
        sim_info.breed_name_key = breed.breed_display_name.hash
    resource_key = get_resource_key_for_breed(sim_info.species, sim_info.age, breed_tag)
    if resource_key is None:
        return
    model_sim_info = SimInfoBaseWrapper(age=sim_info.age, gender=sim_info.gender, species=sim_info.species)
    model_sim_info.load_from_resource(resource_key, sim_info.age, resend_physical_attributes=False)
    model_sim_info.add_random_variation_to_modifiers()
    SimInfoBaseWrapper.copy_physical_attributes(sim_info, model_sim_info)
    for outfit in sim_info.get_all_outfit_entries():
        sim_info.generate_merged_outfit(model_sim_info, outfit, outfit, (OutfitCategory.EVERYDAY, 0))

def get_breed_from_tag(breed_tag):
    tuning_id = BREED_TAG_TO_TUNING_ID_MAP.get(breed_tag, None)
    manager = services.get_instance_manager(sims4.resources.Types.BREED)
    breed = manager.get(tuning_id)
    if breed is None:
        logger.warn('Could not find breed tuning for breed with tag {}', breed_tag)
    return breed

def get_resource_key_for_breed(species, age, breed_tag):
    breed = get_breed_from_tag(breed_tag)
    if breed is None:
        return
    resource_keys = breed.sim_info_resources
    if not resource_keys:
        return
    return random.choice(list(resource_keys))
