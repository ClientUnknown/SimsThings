from _sims4_collections import frozendictimport randomfrom protocolbuffers import FileSerialization_pb2 as serializationfrom cas.cas import generate_householdfrom sims import sim_info_typesfrom sims.baby.baby_utils import run_baby_spawn_behaviorfrom sims.outfits.outfit_enums import OutfitCategoryfrom sims.pets import breed_tuningfrom sims.sim_info_types import Gender, Species, SpeciesExtendedfrom sims.sim_spawner_enums import SimNameType, SimInfoCreationSourcefrom sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.tunable import TunableList, TunableMapping, TunableEnumEntry, TunableTuple, Tunable, TunableSetfrom sims4.tuning.tunable_base import ExportModes, EnumBinaryExportTypefrom singletons import DEFAULT, UNSETfrom tag import Tagfrom world.spawn_point import SpawnPointOptionimport gsi_handlersimport profanityimport serverimport servicesimport simsimport sims4.logimport sims4.mathimport terrainlogger = sims4.log.Logger('Sim Spawner')disable_spawning_non_selectable_sims = FalseOUTFITS_TO_POPULATE_ON_SPAWN = frozendict({Species.HUMAN: (OutfitCategory.SWIMWEAR, OutfitCategory.HOTWEATHER, OutfitCategory.COLDWEATHER)})
class SimCreator:

    def __init__(self, gender=None, age=None, species=None, first_name='', last_name='', breed_name='', first_name_key=0, last_name_key=0, full_name_key=0, breed_name_key=0, tunable_tag_set=None, weighted_tag_lists=None, additional_tags=(), resource_key=None, traits=(), sim_name_type=SimNameType.DEFAULT, filter_flag=None, body_type_chance_overrides={}, body_type_match_not_found_policy={}):
        self.gender = random.choice(list(sim_info_types.Gender)) if gender is None else gender
        self.age = sim_info_types.Age.ADULT if age is None else age
        self.species = sim_info_types.Species.HUMAN if species is None else species
        self.first_name = first_name
        self.last_name = last_name
        self.breed_name = breed_name
        self.first_name_key = first_name_key
        self.last_name_key = last_name_key
        self.full_name_key = full_name_key
        self.breed_name_key = breed_name_key
        self.resource_key = resource_key
        self.tag_set = set(tag for tag in tunable_tag_set.tags) if tunable_tag_set is not None else set()
        if additional_tags:
            self.tag_set.update(additional_tags)
        if weighted_tag_lists:
            for weighted_tag_list in weighted_tag_lists:
                weighted_tags = [(entry.weight, entry.tag) for entry in weighted_tag_list.weighted_tags]
                picked_tag = sims4.random.weighted_random_item(weighted_tags)
                self.tag_set.add(picked_tag)
        self.traits = set(traits)
        self.sim_name_type = sim_name_type
        self.randomization_mode = None
        self.filter_flags = filter_flag
        self.body_type_chance_overrides = body_type_chance_overrides
        self.body_type_match_not_found_policy = body_type_match_not_found_policy

    def __repr__(self):
        return '<{} {} {} - {} {}>'.format(self.age, self.gender, self.species, ','.join(str(t.__name__) for t in self.traits), ','.join(str(t) for t in self.tag_set))

    def build_creation_dictionary(self):
        sim_builder_dictionary = {}
        sim_builder_dictionary['age'] = self.age
        sim_builder_dictionary['gender'] = self.gender
        sim_builder_dictionary['tagSet'] = self.tag_set
        sim_builder_dictionary['species'] = self.species
        sim_builder_dictionary['trait_ids'] = [t.guid64 for t in self.traits]
        if self.randomization_mode is not None:
            sim_builder_dictionary['randomization_mode'] = self.randomization_mode
        if self.filter_flags is not None:
            sim_builder_dictionary['filter_flags'] = self.filter_flags
        if self.body_type_chance_overrides:
            sim_builder_dictionary['body_type_chance_overrides'] = self.body_type_chance_overrides
        if self.body_type_match_not_found_policy:
            sim_builder_dictionary['body_type_match_not_found_policy'] = self.body_type_match_not_found_policy
        return sim_builder_dictionary

class Language(DynamicEnum):
    ENGLISH = 0
DEFAULT_LOCALE = 'en-us'
def verify_random_name_tuning(instance_class, tunable_name, source, value):
    try:
        for (language, name_tuning) in value.items():
            for name in name_tuning.female_first_names:
                if profanity.scan(name):
                    logger.error('Female first name {} in {} is profane', name, language)
            for name in name_tuning.male_first_names:
                if profanity.scan(name):
                    logger.error('Male first name {} in {} is profane', name, language)
            for name in name_tuning.last_names:
                if profanity.scan(name):
                    logger.error('Last name {} in {} is profane', name, language)
    except:
        pass

class SimSpawner:
    SYSTEM_ACCOUNT_ID = 1
    LOCALE_MAPPING = TunableMapping(description="\n        A mapping of locale in terms of string to a sim name language in the\n        Language enum. This allows us to use the same random sim name\n        list for multiple locales. You can add new Language enum entries\n        in sims.sim_spawner's Language\n        ", key_name='locale_string', value_name='language', key_type=str, value_type=TunableEnumEntry(Language, Language.ENGLISH, export_modes=ExportModes.All), tuple_name='TunableLocaleMappingTuple', export_modes=ExportModes.All)

    class TunableRandomNamesForLanguage(TunableTuple):

        def __init__(self):
            super().__init__(description='\n                A list of random names to be used for a specific language.\n                ', last_names=TunableList(description='\n                    A list of the random last names that can be assigned in CAS or\n                    to randomly generated NPCs.\n                    ', tunable=Tunable(description='\n                        A random last name.\n                        ', tunable_type=str, default=''), unique_entries=True), female_last_names=TunableList(description="\n                    If the specified languages differentiate last names\n                    according to gender, this list has to be non-empty. For\n                    every last name specified in the 'last_names' list, there\n                    must be a corresponding last name in this list.\n                    \n                    Randomly generated NPCs and NPC offspring will select the\n                    corresponding female version if necessary.\n                    ", tunable=Tunable(description="\n                        The female version of the last name at the corresponding\n                        index in the 'last_name' list.\n                        ", tunable_type=str, default=''), unique_entries=True), female_first_names=TunableList(description='\n                    A list of the random female first names that can be assigned\n                    in CAS or to randomly generated NPCs.\n                    ', tunable=Tunable(description='\n                        A random female first name.\n                        ', tunable_type=str, default=''), unique_entries=True), male_first_names=TunableList(description='\n                    A list of the random male first names that can be assigned\n                    in CAS or to randomly generated NPCs.\n                    ', tunable=Tunable(description='\n                        A random male first name.\n                        ', tunable_type=str, default=''), unique_entries=True))

    RANDOM_NAME_TUNING = TunableMapping(description="\n        A mapping of sim name language to lists of random family name and first\n        names appropriate for that language. This is used to generate random sim\n        names appropriate for each account's specified locale.\n        ", key_name='language', value_name='random_name_tuning', key_type=TunableEnumEntry(Language, Language.ENGLISH, export_modes=ExportModes.All), value_type=TunableRandomNamesForLanguage(), tuple_name='TunableRandomNameMappingTuple', verify_tunable_callback=verify_random_name_tuning, export_modes=ExportModes.All)
    SIM_NAME_TYPE_TO_LOCALE_NAMES = TunableMapping(description='\n        A mapping of SimNameType to locale-specific names. Normally, Sims pull\n        from Random Name Tuning. But if specified with a SimNameType, they will\n        instead pull from this mapping of names.\n        ', key_name='name_type', value_name='name_type_random_names', key_type=TunableEnumEntry(tunable_type=SimNameType, default=SimNameType.DEFAULT, invalid_enums=(SimNameType.DEFAULT,), binary_type=EnumBinaryExportType.EnumUint32), value_type=TunableMapping(key_name='language', value_name='random_name_tuning', key_type=TunableEnumEntry(tunable_type=Language, default=Language.ENGLISH), value_type=TunableRandomNamesForLanguage(), tuple_name='TunableRandomNameMappingTuple', verify_tunable_callback=verify_random_name_tuning), tuple_name='TunableNameTypeToRandomNamesMappingTuple', export_modes=ExportModes.All)
    SPECIES_TO_NAME_TYPE = TunableMapping(description='\n        A mapping of species type to the type of names to use for that species. \n        ', key_name='species', value_name='species_name_type', key_type=TunableEnumEntry(tunable_type=SpeciesExtended, default=SpeciesExtended.HUMAN, invalid_enums=(SpeciesExtended.INVALID,), binary_type=EnumBinaryExportType.EnumUint32), value_type=TunableEnumEntry(tunable_type=SimNameType, default=SimNameType.DEFAULT, binary_type=EnumBinaryExportType.EnumUint32), tuple_name='TunableSpeciesToNameTypeMappingTuple', export_modes=ExportModes.All)
    NAME_TYPES_WITH_OPTIONAL_NAMES = TunableSet(description='\n        A set of name types with optional last names. \n        ', tunable=TunableEnumEntry(tunable_type=SimNameType, default=SimNameType.DEFAULT, binary_type=EnumBinaryExportType.EnumUint32), export_modes=ExportModes.All)

    @classmethod
    def _get_random_name_tuning(cls, language, sim_name_type=SimNameType.DEFAULT):
        language_mapping = SimSpawner.SIM_NAME_TYPE_TO_LOCALE_NAMES.get(sim_name_type, SimSpawner.RANDOM_NAME_TUNING)
        tuning = language_mapping.get(language)
        if tuning is None:
            tuning = language_mapping.get(Language.ENGLISH)
        return tuning

    @classmethod
    def get_random_first_name(cls, gender, species=Species.HUMAN, sim_name_type_override=None) -> str:
        species = SpeciesExtended.get_species(species)
        sim_name_type = SimNameType.DEFAULT
        if sim_name_type_override is not None:
            sim_name_type = sim_name_type_override
        elif species in cls.SPECIES_TO_NAME_TYPE:
            sim_name_type = cls.SPECIES_TO_NAME_TYPE[species]
        return cls._get_random_first_name(cls._get_language_for_locale(services.get_locale()), gender == Gender.FEMALE, sim_name_type=sim_name_type)

    @classmethod
    def _get_random_first_name(cls, language, is_female, sim_name_type=SimNameType.DEFAULT) -> int:
        tuning = cls._get_random_name_tuning(language, sim_name_type=sim_name_type)
        name_list = tuning.female_first_names if is_female else tuning.male_first_names
        return random.choice(name_list)

    @classmethod
    def _get_random_last_name(cls, language, sim_name_type=SimNameType.DEFAULT) -> int:
        tuning = cls._get_random_name_tuning(language, sim_name_type=sim_name_type)
        return random.choice(tuning.last_names)

    @classmethod
    def get_last_name(cls, last_name, gender, species=Species.HUMAN) -> str:
        species = SpeciesExtended.get_species(species)
        sim_name_type = SimNameType.DEFAULT
        if species in cls.SPECIES_TO_NAME_TYPE:
            sim_name_type = cls.SPECIES_TO_NAME_TYPE[species]
        return cls._get_family_name_for_gender(cls._get_language_for_locale(services.get_locale()), last_name, gender == Gender.FEMALE, sim_name_type=sim_name_type)

    @classmethod
    def _get_family_name_for_gender(cls, language, family_name, is_female, sim_name_type=SimNameType.DEFAULT) -> str:
        if sim_name_type in cls.NAME_TYPES_WITH_OPTIONAL_NAMES:
            return ''
        tuning = cls._get_random_name_tuning(language, sim_name_type=sim_name_type)
        if tuning.female_last_names:
            if family_name in tuning.female_last_names:
                if is_female:
                    return family_name
                index = tuning.female_last_names.index(family_name)
                return tuning.last_names[index]
            if family_name in tuning.last_names:
                if not is_female:
                    return family_name
                else:
                    index = tuning.last_names.index(family_name)
                    return tuning.female_last_names[index]
        return family_name

    @classmethod
    def _get_language_for_locale(cls, locale) -> Language:
        language = SimSpawner.LOCALE_MAPPING.get(locale, Language.ENGLISH)
        return language

    @classmethod
    def spawn_sim(cls, sim_info, sim_position:sims4.math.Vector3=None, sim_location=None, sim_spawner_tags=None, spawn_point_option=None, saved_spawner_tags=None, spawn_action=None, additional_fgl_search_flags=None, from_load=False, is_debug=False, use_fgl=True, spawn_point=None, spawn_at_lot=True, update_skewer=True, **kwargs):
        if is_debug or not (disable_spawning_non_selectable_sims and sim_info.is_selectable):
            return False
        try:
            sim_info.set_zone_on_spawn()
            if sim_info.species in OUTFITS_TO_POPULATE_ON_SPAWN:
                sim_info.generate_unpopulated_outfits(OUTFITS_TO_POPULATE_ON_SPAWN[sim_info.species])
            if not from_load:
                sim_info.spawn_point_option = spawn_point_option if spawn_point_option is not None else SpawnPointOption.SPAWN_ANY_POINT_WITH_CONSTRAINT_TAGS
            services.sim_info_manager().add_sim_info_if_not_in_manager(sim_info)
            success = sim_info.create_sim_instance(sim_position, sim_spawner_tags=sim_spawner_tags, saved_spawner_tags=saved_spawner_tags, spawn_action=spawn_action, sim_location=sim_location, additional_fgl_search_flags=additional_fgl_search_flags, from_load=from_load, use_fgl=use_fgl, spawn_point_override=spawn_point, spawn_at_lot=spawn_at_lot, **kwargs)
            if update_skewer and success and sim_info.is_selectable:
                client = services.client_manager().get_client_by_household_id(sim_info.household.id)
                if client is not None:
                    client.selectable_sims.notify_dirty()
            return success
        except Exception:
            logger.exception('Exception while creating sims, sim_id={}; failed', sim_info.id)
            return False

    @classmethod
    def load_sim(cls, sim_id, startup_location=DEFAULT):
        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None:
            return False
        if sim_info.is_baby:
            run_baby_spawn_behavior(sim_info)
            return False
        if startup_location is DEFAULT:
            startup_location = sim_info.startup_sim_location
        return cls.spawn_sim(sim_info, sim_location=startup_location, from_load=True)

    @classmethod
    def _get_default_account(cls):
        client = services.client_manager().get_first_client()
        if client is not None:
            account = client.account
            if account is not None:
                return account
        account = services.account_service().get_account_by_id(cls.SYSTEM_ACCOUNT_ID)
        if account is not None:
            return account
        account = server.account.Account(cls.SYSTEM_ACCOUNT_ID, 'SystemAccount')
        return account

    @classmethod
    def create_sim_infos(cls, sim_creators, household=None, starting_funds=DEFAULT, tgt_client=None, account=None, generate_deterministic_sim=False, zone_id=None, sim_name_type=SimNameType.DEFAULT, creation_source:str='Unknown - create_sim_infos', skip_adding_to_household=False, is_debug=False):
        sim_info_list = []
        if account is None:
            account = cls._get_default_account()
        if not skip_adding_to_household:
            household = sims.household.Household(account, starting_funds=starting_funds)
        sim_creation_dictionaries = tuple(sim_creator.build_creation_dictionary() for sim_creator in sim_creators)
        new_sim_data = generate_household(sim_creation_dictionaries=sim_creation_dictionaries, household_name=household.name, generate_deterministic_sim=generate_deterministic_sim)
        zone = services.current_zone()
        world_id = zone.world_id
        if household is None and zone_id is None:
            zone_id = zone.id
        elif zone_id != 0:
            world_id = services.get_persistence_service().get_world_id_from_zone(zone_id)
        language = cls._get_language_for_locale(account.locale)
        family_name = cls._get_random_last_name(language, sim_name_type=sim_name_type)
        if not skip_adding_to_household:
            household.id = new_sim_data['id']
            services.household_manager().add(household)
            household.name = family_name
        for (index, sim_data) in enumerate(new_sim_data['sims']):
            sim_proto = serialization.SimData()
            sim_proto.ParseFromString(sim_data)
            first_name = sim_creators[index].first_name
            if not sim_creators[index].full_name_key:
                if sim_name_type == SimNameType.DEFAULT:
                    first_name = cls.get_random_first_name(sim_proto.gender, sim_proto.extended_species)
                else:
                    first_name = cls._get_random_first_name(language, sim_proto.gender == Gender.FEMALE, sim_name_type=sim_name_type)
            last_name = sim_creators[index].last_name
            last_name_key = sim_creators[index].last_name_key
            if not sim_creators[index].full_name_key:
                if sim_name_type == SimNameType.DEFAULT:
                    last_name = cls.get_last_name(family_name, sim_proto.gender, sim_proto.extended_species)
                else:
                    last_name = cls._get_family_name_for_gender(language, family_name, sim_proto.gender == Gender.FEMALE, sim_name_type=sim_name_type)
            sim_proto.first_name = first_name
            sim_proto.last_name = last_name
            sim_proto.first_name_key = sim_creators[index].first_name_key
            if first_name or sim_creators[index].first_name_key or last_name or last_name_key or last_name_key is not UNSET and last_name_key is not UNSET:
                sim_proto.last_name_key = last_name_key
            sim_proto.full_name_key = sim_creators[index].full_name_key
            sim_proto.age = sim_creators[index].age
            sim_proto.extended_species = sim_creators[index].species
            sim_proto.breed_name_key = sim_creators[index].breed_name_key
            sim_proto.zone_id = zone_id
            sim_proto.world_id = world_id
            sim_proto.household_id = household.id
            SimInfoCreationSource.save_creation_source(creation_source, sim_proto)
            trait_ids = [trait.guid64 for trait in sim_creators[index].traits if trait.persistable]
            sim_proto.attributes.trait_tracker.trait_ids.extend(trait_ids)
            sim_info = sims.sim_info.SimInfo(sim_id=sim_proto.sim_id, account=account)
            sim_info.load_sim_info(sim_proto)
            breed_tag = breed_tuning.get_breed_tag_from_tag_set(sim_creators[index].tag_set)
            if breed_tag != Tag.INVALID:
                breed_tuning.try_conform_sim_info_to_breed(sim_info, breed_tag)
            if sim_creators[index].resource_key:
                sim_info.load_from_resource(sim_creators[index].resource_key)
                if not sim_info.first_name:
                    sim_info.first_name = sim_proto.first_name
                if not sim_info.last_name:
                    sim_info.last_name = sim_proto.last_name
                if not sim_info.first_name_key:
                    sim_info.first_name_key = sim_proto.first_name_key
                if not sim_info.last_name_key:
                    sim_info.last_name_key = sim_proto.last_name_key
                if not sim_info.full_name_key:
                    sim_info.full_name_key = sim_proto.full_name_key
                if not sim_info.breed_name_key:
                    sim_info.breed_name_key = sim_proto.breed_name_key
            if not skip_adding_to_household:
                sim_info.assign_to_household(household)
                sim_info.save_sim()
                household.add_sim_info(sim_info)
                if tgt_client is not None and household is tgt_client.household:
                    logger.info('Added {} Sims to the current client', len(sim_creators))
                    if tgt_client.active_sim is None:
                        tgt_client.set_next_sim()
                else:
                    logger.info('Added {} Sims to household ID {}.', len(sim_creators), household.id)
            logger.info('Create Sims, sim_number={}; succeeded', len(sim_creators))
            sim_info.push_to_relgraph()
            if gsi_handlers.sim_info_lifetime_handlers.archiver.enabled:
                gsi_handlers.sim_info_lifetime_handlers.archive_sim_info_event(sim_info, 'new sim info')
            services.sim_info_manager().on_sim_info_created()
            sim_info_list.append(sim_info)
        if not (household.id == 0 and skip_adding_to_household):
            household.save_data()
        if is_debug:
            services.get_zone_situation_manager().add_debug_sim_id(sim_info.id)
        return (sim_info_list, household)

    @classmethod
    def create_sims(cls, sim_creators, household=None, tgt_client=None, generate_deterministic_sim=False, sim_position:sims4.math.Vector3=None, sim_spawner_tags=None, account=None, is_debug=False, skip_offset=False, additional_fgl_search_flags=None, instantiate=True, creation_source:str='Unknown - create_sims'):
        (sim_info_list, _) = cls.create_sim_infos(sim_creators, household=household, starting_funds=DEFAULT, tgt_client=tgt_client, account=account, generate_deterministic_sim=generate_deterministic_sim, zone_id=0, creation_source=creation_source)
        if not instantiate:
            return
        offset = 0.0
        for sim_info in sim_info_list:
            if sim_position is not None:
                sim_position = sims4.math.Vector3(*sim_position)
                sim_position.x += offset
                if not skip_offset:
                    offset = 2.0
                sim_position.y = terrain.get_terrain_height(sim_position.x, sim_position.z)
            if is_debug:
                services.get_zone_situation_manager().add_debug_sim_id(sim_info.id)
            cls.spawn_sim(sim_info, sim_position, sim_spawner_tags=sim_spawner_tags, additional_fgl_search_flags=additional_fgl_search_flags, is_debug=is_debug)
            client = services.client_manager().get_client_by_household_id(sim_info.household_id)
            if client is not None:
                client.add_selectable_sim_info(sim_info)
