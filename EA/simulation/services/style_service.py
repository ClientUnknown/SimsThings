from _collections import defaultdictfrom protocolbuffers import GameplaySaveData_pb2import randomfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom sims.outfits.outfit_enums import OutfitCategoryfrom sims.sim_info_base_wrapper import SimInfoBaseWrapperfrom sims.sim_info_types import Genderfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunablePercent, TunableEnumEntry, TunableMapping, TunableResourceKeyfrom sims4.utils import classpropertyimport persistence_error_typesimport servicesimport sims4.loglogger = sims4.log.Logger('style', default_owner='nabaker')
class StyleService(Service):
    STYLE_OUTFIT_SELECTION_ODDS = TunablePercent(description='\n        Chance a situation sim will wear a styled outfit\n        ', default=20)
    STYLE_OUTFIT_DEFAULT = TunableMapping(description='\n        The mapping between gender and default outfit information\n        ', key_type=TunableEnumEntry(tunable_type=Gender, default=Gender.MALE), value_type=TunableResourceKey(description='\n            The SimInfo file to use when editing outfits.\n            ', default=None, resource_types=(sims4.resources.Types.SIMINFO,)), minlength=2)

    def __init__(self):
        self._style_outfit_data = {}

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_STYLE_SERVICE

    def save(self, save_slot_data=None, **kwargs):
        data = GameplaySaveData_pb2.PersistableStyleService()
        for (gender, outfit_data) in self._style_outfit_data.items():
            with ProtocolBufferRollback(data.outfit_infos) as outfit_info:
                outfit_info.outfit_info_data.mannequin_id = outfit_data.sim_id
                outfit_data.save_sim_info(outfit_info.outfit_info_data)
        save_slot_data.gameplay_data.style_service = data

    def load(self, **_):
        persistence_service = services.get_persistence_service()
        save_slot_data_msg = persistence_service.get_save_slot_proto_buff()
        data = save_slot_data_msg.gameplay_data.style_service
        for outfit_info in data.outfit_infos:
            outfit_info_data = outfit_info.outfit_info_data
            outfit_data = self.get_style_outfit_data(outfit_info_data.gender, sim_id=outfit_info_data.mannequin_id)
            if persistence_service is not None:
                persisted_data = persistence_service.get_mannequin_proto_buff(outfit_info_data.mannequin_id)
                if persisted_data is not None:
                    outfit_info_data = persisted_data
            outfit_data.load_sim_info(outfit_info_data)
            outfit_data.manager = services.sim_info_manager()
            Distributor.instance().add_object(outfit_data)
            persistence_service.del_mannequin_proto_buff(outfit_info.outfit_info_data.mannequin_id)

    def get_style_outfit_data(self, gender:Gender, sim_id=0):
        outfit_data = self._style_outfit_data.get(gender)
        if outfit_data is None:
            outfit_data = SimInfoBaseWrapper(sim_id=sim_id)
            self._style_outfit_data[gender] = outfit_data
            default_outfit = self.STYLE_OUTFIT_DEFAULT.get(gender)
            outfit_data.load_from_resource(default_outfit)
            if not sim_id:
                outfit_data.manager = services.sim_info_manager()
                Distributor.instance().add_object(outfit_data)
        return outfit_data

    def try_set_style_outfit(self, sim):
        if sim.is_human and sim.sim_info.is_teen_or_older and random.random() <= self.STYLE_OUTFIT_SELECTION_ODDS:
            outfit_sim_info = self._style_outfit_data.get(sim.gender, None)
            if outfit_sim_info is not None:
                outfit = outfit_sim_info.get_random_outfit(outfit_categories=(OutfitCategory.CAREER,))
                if outfit[0] == OutfitCategory.CAREER:
                    sim.sim_info.generate_merged_outfit(outfit_sim_info, (OutfitCategory.SITUATION, 0), sim.sim_info.get_current_outfit(), outfit)
                    sim.sim_info.set_current_outfit((OutfitCategory.SITUATION, 0))
                    return True
        return False
