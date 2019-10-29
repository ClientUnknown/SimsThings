from _collections import defaultdictfrom contextlib import contextmanagerimport itertoolsfrom protocolbuffers import GameplaySaveData_pb2from cas.cas import generate_random_siminfofrom date_and_time import DateAndTimefrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom sims.pets.breed_tuning import get_random_breed_tag, try_conform_sim_info_to_breedfrom sims.sim_info_base_wrapper import SimInfoBaseWrapperfrom sims.sim_spawner import SimSpawner, SimCreatorfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableSimMinute, TunableList, TunableTuple, Tunablefrom sims4.utils import classpropertyfrom traits.traits import Traitimport persistence_error_typesimport servicesimport sims4
class AdoptionService(Service):
    PET_ADOPTION_CATALOG_LIFETIME = TunableSimMinute(description='\n        The amount of time in Sim minutes before a pet Sim is removed from the adoption catalog.\n        ', default=60, minimum=0)
    PET_ADOPTION_GENDER_OPTION_TRAITS = TunableList(description='\n        List of gender option traits from which one will be applied to generated\n        Pets based on the tuned weights.\n        ', tunable=TunableTuple(description='\n            A weighted gender option trait that might be applied to the\n            generated Pet.\n            ', weight=Tunable(description='\n                The relative weight of this trait.\n                ', tunable_type=float, default=1), trait=Trait.TunableReference(description='\n                A gender option trait that might be applied to the generated\n                Pet.\n                ', pack_safe=True)))

    def __init__(self):
        self._sim_infos = defaultdict(list)
        self._real_sim_ids = None
        self._creation_times = {}

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_ADOPTION_SERVICE

    def timeout_real_sim_infos(self):
        sim_now = services.time_service().sim_now
        for sim_id in tuple(self._creation_times.keys()):
            elapsed_time = (sim_now - self._creation_times[sim_id]).in_minutes()
            if elapsed_time > self.PET_ADOPTION_CATALOG_LIFETIME:
                del self._creation_times[sim_id]

    def save(self, save_slot_data=None, **kwargs):
        self.timeout_real_sim_infos()
        adoption_service_proto = GameplaySaveData_pb2.PersistableAdoptionService()
        for (sim_id, creation_time) in self._creation_times.items():
            with ProtocolBufferRollback(adoption_service_proto.adoptable_sim_data) as msg:
                msg.adoptable_sim_id = sim_id
                msg.creation_time = creation_time.absolute_ticks()
        save_slot_data.gameplay_data.adoption_service = adoption_service_proto

    def on_all_households_and_sim_infos_loaded(self, _):
        save_slot_data = services.get_persistence_service().get_save_slot_proto_buff()
        sim_info_manager = services.sim_info_manager()
        for sim_data in save_slot_data.gameplay_data.adoption_service.adoptable_sim_data:
            sim_info = sim_info_manager.get(sim_data.adoptable_sim_id)
            if sim_info is None:
                pass
            else:
                self._creation_times[sim_data.adoptable_sim_id] = DateAndTime(sim_data.creation_time)

    def stop(self):
        self._sim_infos.clear()
        self._creation_times.clear()

    def add_sim_info(self, age, gender, species):
        key = (age, gender, species)
        sim_info = SimInfoBaseWrapper(age=age, gender=gender, species=species)
        generate_random_siminfo(sim_info._base)
        breed_tag = get_random_breed_tag(species)
        if breed_tag is not None:
            try_conform_sim_info_to_breed(sim_info, breed_tag)
        trait_manager = services.get_instance_manager(sims4.resources.Types.TRAIT)
        traits = {trait_manager.get(trait_id) for trait_id in sim_info.trait_ids}
        if sim_info.is_pet:
            gender_option_traits = [(entry.weight, entry.trait) for entry in self.PET_ADOPTION_GENDER_OPTION_TRAITS if entry.trait.is_valid_trait(sim_info)]
            selected_trait = sims4.random.weighted_random_item(gender_option_traits)
            if selected_trait is not None:
                traits.add(selected_trait)
        sim_info.set_trait_ids_on_base(trait_ids_override=list(t.guid64 for t in traits))
        sim_info.first_name = SimSpawner.get_random_first_name(gender, species)
        sim_info.manager = services.sim_info_manager()
        Distributor.instance().add_object(sim_info)
        self._sim_infos[key].append(sim_info)

    def add_real_sim_info(self, sim_info):
        self._creation_times[sim_info.sim_id] = services.time_service().sim_now

    def get_sim_info(self, sim_id):
        for sim_info in itertools.chain.from_iterable(self._sim_infos.values()):
            if sim_info.sim_id == sim_id:
                return sim_info
        for adoptable_sim_id in self._creation_times.keys():
            if sim_id == adoptable_sim_id:
                return services.sim_info_manager().get(adoptable_sim_id)

    @contextmanager
    def real_sim_info_cache(self):
        self.timeout_real_sim_infos()
        self._real_sim_ids = defaultdict(list)
        sim_info_manager = services.sim_info_manager()
        for sim_id in self._creation_times.keys():
            sim_info = sim_info_manager.get(sim_id)
            key = (sim_info.age, sim_info.gender, sim_info.species)
            self._real_sim_ids[key].append(sim_id)
        try:
            yield None
        finally:
            self._real_sim_ids.clear()
            self._real_sim_ids = None

    def get_sim_infos(self, interval, age, gender, species):
        key = (age, gender, species)
        real_sim_count = len(self._real_sim_ids[key]) if self._real_sim_ids is not None else 0
        entry_count = len(self._sim_infos[key]) + real_sim_count
        if entry_count < interval.lower_bound:
            while entry_count < interval.upper_bound:
                self.add_sim_info(age, gender, species)
                entry_count += 1
        real_sim_infos = []
        if self._real_sim_ids is not None:
            sim_info_manager = services.sim_info_manager()
            for sim_id in tuple(self._real_sim_ids[key]):
                sim_info = sim_info_manager.get(sim_id)
                if sim_info is not None:
                    real_sim_infos.append(sim_info)
        return tuple(itertools.chain(self._sim_infos[key], real_sim_infos))

    def remove_sim_info(self, sim_info):
        for sim_infos in self._sim_infos.values():
            if sim_info in sim_infos:
                sim_infos.remove(sim_info)
        if sim_info.sim_id in self._creation_times:
            del self._creation_times[sim_info.sim_id]

    def create_adoption_sim_info(self, sim_info, household=None, account=None, zone_id=None):
        sim_creator = SimCreator(age=sim_info.age, gender=sim_info.gender, species=sim_info.extended_species, first_name=sim_info.first_name, last_name=sim_info.last_name)
        (sim_info_list, new_household) = SimSpawner.create_sim_infos((sim_creator,), household=household, account=account, zone_id=0, creation_source='adoption')
        SimInfoBaseWrapper.copy_physical_attributes(sim_info_list[0], sim_info)
        sim_info_list[0].pelt_layers = sim_info.pelt_layers
        sim_info_list[0].breed_name_key = sim_info.breed_name_key
        sim_info_list[0].load_outfits(sim_info.save_outfits())
        sim_info_list[0].resend_physical_attributes()
        return (sim_info_list[0], new_household)

    def convert_base_sim_info_to_full(self, sim_id):
        current_sim_info = self.get_sim_info(sim_id)
        if current_sim_info is None:
            return
        (new_sim_info, new_household) = self.create_adoption_sim_info(current_sim_info)
        new_household.set_to_hidden()
        self.remove_sim_info(current_sim_info)
        self.add_real_sim_info(new_sim_info)
        return new_sim_info
