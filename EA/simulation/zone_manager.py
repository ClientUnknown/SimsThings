from indexed_manager import IndexedManagerfrom sims4.utils import classpropertyfrom uninstantiated_zone import UninstantiatedZoneimport persistence_error_typesimport servicesimport sims4.gsi.dispatcherimport sims4.zone_utilsimport zonelogger = sims4.log.Logger('ZoneManager', default_owner='manus')
class ZoneManager(IndexedManager):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_zone = None

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_ZONE_MANAGER

    def get(self, zone_id, allow_uninstantiated_zones=False):
        zone = super().get(zone_id)
        if allow_uninstantiated_zones:
            if zone is None:
                self.load_uninstantiated_zone_data(zone_id)
                return super().get(zone_id)
            return zone
        elif zone is not None and zone.is_instantiated:
            return zone

    def create_zone(self, zone_id, gameplay_zone_data, save_slot_data):
        if sims4.zone_utils.zone_id is not None:
            raise RuntimeError('Attempting to set _zone_id to {} when its already set {}.'.format(zone_id, sims4.zone_utils.zone_id))
        if save_slot_data is not None:
            save_slot_data_id = save_slot_data.slot_id
        else:
            save_slot_data_id = None
        new_zone = zone.Zone(zone_id, save_slot_data_id)
        logger.info('Created new zone {} with id {}.', new_zone, zone_id)
        self.add(new_zone)
        return new_zone

    def remove_id(self, obj_id):
        logger.info('Remove {}.', obj_id)
        super().remove_id(obj_id)
        if sims4.zone_utils.zone_id == obj_id:
            sims4.zone_utils.set_current_zone_id(None)

    def shutdown(self):
        logger.info('Shutdown')
        sims4.zone_utils.register_zone_change_callback(None)
        key_list = list(self._objects.keys())
        for k in key_list:
            self.remove_id(k)

    def _update_current_zone(self, zone_id):
        if zone_id is None:
            self.current_zone = None
        else:
            self.current_zone = self.get(zone_id)
        logger.info('Updated current zone to {}. zone_utils.zone_id: {}.', self.current_zone, zone_id)

    def start(self):
        logger.info('Started')
        super().start()
        sims4.zone_utils.register_zone_change_callback(self._update_current_zone)
        sims4.gsi.dispatcher.register_zone_manager(self)

    def stop(self):
        logger.info('Stopped')
        super().stop()
        sims4.gsi.dispatcher.register_zone_manager(None)

    def save(self, save_slot_data=None):
        for zone in self.values():
            zone.save_zone(save_slot_data=save_slot_data)

    def load_uninstantiated_zone_data(self, zone_id):
        if zone_id == 0:
            logger.error('Attempting to load an uninstantiated zone with 0 ID. Shameful!', owner='manus')
            return
        if zone_id in self:
            return
        new_uninstantiated_zone = UninstantiatedZone(zone_id)
        self.add(new_uninstantiated_zone)
        new_uninstantiated_zone.load()

    def cleanup_uninstantiated_zones(self):
        for (zone_id, zone) in tuple(self.items()):
            if not zone.is_instantiated:
                self.remove_id(zone_id)

    def clear_lot_ownership(self, zone_id):
        zone_data_proto = services.get_persistence_service().get_zone_proto_buff(zone_id)
        if zone_data_proto is not None:
            zone_data_proto.household_id = 0
            lot_decoration_service = services.lot_decoration_service()
            neighborhood_proto = services.get_persistence_service().get_neighborhood_proto_buff(zone_data_proto.neighborhood_id)
            for lot_owner_info in neighborhood_proto.lots:
                if lot_owner_info.zone_instance_id == zone_id:
                    lot_owner_info.ClearField('lot_owner')
                    if lot_decoration_service is not None:
                        lot_decoration_service.handle_lot_owner_changed(zone_id, None)
                    break
