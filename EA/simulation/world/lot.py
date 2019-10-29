from collections import defaultdictimport randomimport weakreffrom protocolbuffers import Consts_pb2, UI_pb2from protocolbuffers.Localization_pb2 import LocalizedStringTokenfrom distributor.shared_messages import create_icon_info_msg, IconInfoDatafrom distributor.system import Distributorfrom objects.components import ComponentContainerfrom objects.components.inventory_enums import InventoryTypefrom objects.components.inventory_type_tuning import InventoryTypeTuningfrom objects.components.shared_inventory_component import SharedInventoryContainerfrom objects.components.statistic_component import HasStatisticComponentfrom objects.object_enums import ItemLocationfrom objects.system import create_objectfrom plex.plex_enums import PlexBuildingTypefrom sims4.math import vector_normalizefrom sims4.utils import constpropertyfrom terrain import get_water_depthfrom world.lot_enums import LotPositionStrategyfrom world.lot_tuning import GlobalLotTuningAndCleanup, LotTuningMapsfrom world.premade_lot_status import PremadeLotStatusimport distributorimport objects.components.typesimport servicesimport sims4.logtry:
    import _lot
except ImportError:

    class _lot:

        @staticmethod
        def get_lot_id_from_instance_id(*_, **__):
            return 0

        class Lot:
            pass
get_lot_id_from_instance_id = _lot.get_lot_id_from_instance_idlogger = sims4.log.Logger('Lot')
class Lot(ComponentContainer, HasStatisticComponent, _lot.Lot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inventory_owners = defaultdict(weakref.WeakSet)
        self._shared_inventory_containers = {}

    @constproperty
    def is_sim():
        return False

    @property
    def is_downloaded(self):
        return False

    @property
    def center(self):
        return self.position

    def get_random_point(self):
        pos = sims4.math.Vector3(0, 0, 0)
        pos.x = (random.random() - 0.5)*self.size_x
        pos.z = (random.random() - 0.5)*self.size_z
        rot = self.orientation
        pos = rot.transform_vector(pos)
        pos += self.position
        return pos

    def get_uniform_sampling_of_points(self, samples_x, samples_z):
        samples = []
        step_x = 1/samples_x
        step_z = 1/samples_z
        for z in range(samples_z):
            for x in range(samples_x):
                pos = sims4.math.Vector3(-0.5 + step_x/2, 0, -0.5 + step_z/2)
                pos.x += x*step_x
                pos.z += z*step_z
                pos.x *= self.size_x
                pos.z *= self.size_z
                pos = self.orientation.transform_vector(pos)
                pos += self.center
                samples.append(pos)
        return samples

    def get_edge_polygons(self, width=5.0, depth=2.0):
        corners = self.corners
        polygons = []
        half_edge_width = 0.5*width
        for i in range(len(corners)):
            j = i + 1 if i < len(corners) - 1 else 0
            corner_a = corners[i]
            corner_b = corners[j]
            diff = corner_b - corner_a
            edge_center = 0.5*diff + corner_a
            cross = sims4.math.vector_normalize(self.center - edge_center)
            width_edge = half_edge_width*sims4.math.vector_normalize(diff)
            depth_edge = cross*depth
            vertices = []
            vertices.append(edge_center - width_edge)
            vertices.append(edge_center - width_edge + depth_edge)
            vertices.append(edge_center + width_edge + depth_edge)
            vertices.append(edge_center + width_edge)
            polygons.append(sims4.geometry.Polygon(vertices))
        return polygons

    def get_front_door(self):
        if self._front_door_id:
            return services.object_manager().get(self._front_door_id)

    def get_default_position(self, position=None):
        front_door = services.get_door_service().get_front_door()
        if front_door is not None:
            default_position = front_door.position
        elif position is not None:
            default_position = min(self.corners, key=lambda p: (p - position).magnitude_squared())
        else:
            plex_service = services.get_plex_service()
            if plex_service.get_plex_building_type(services.current_zone_id()) == PlexBuildingType.COASTAL:
                for corner_position in self.corners:
                    if get_water_depth(corner_position.x, corner_position.z) <= 0:
                        default_position = corner_position
                        break
                logger.error("Couldn't find a corner that was not below water on the current lot. This is probably an error case. We need a place to put down things like the mailbox, etc.")
                default_position = self.corners[0]
            else:
                default_position = self.corners[0]
        delta = self.position - default_position
        if not sims4.math.vector3_almost_equal(delta, sims4.math.Vector3.ZERO()):
            default_position += vector_normalize(delta)
        if front_door is not None:
            plex_service = services.get_plex_service()
            if plex_service.is_active_zone_a_plex():
                (front_position, back_position) = front_door.get_door_positions()
                front_zone_id = plex_service.get_plex_zone_at_position(front_position, front_door.level)
                if front_zone_id is not None:
                    default_position = front_position
                else:
                    back_zone_id = plex_service.get_plex_zone_at_position(back_position, front_door.level)
                    if back_zone_id is not None:
                        default_position = back_position
        return default_position

    def get_hidden_inventory(self):
        return self.get_object_inventories(InventoryType.HIDDEN)[0]

    def create_object_in_hidden_inventory(self, definition_id, household_id=None):
        inventory = self.get_hidden_inventory()
        obj = create_object(definition_id, loc_type=ItemLocation.OBJECT_INVENTORY)
        if household_id is not None:
            obj.set_household_owner_id(household_id)
        try:
            inventory.system_add_object(obj)
            return obj
        except:
            obj.destroy(source=self, cause='Failed to place object in hidden inventory.')

    def get_mailbox_inventory(self, household_id):
        if InventoryTypeTuning.is_shared_between_objects(InventoryType.MAILBOX):
            return self.get_object_inventories(InventoryType.MAILBOX)[0]
        for inventory in self.get_object_inventories(InventoryType.MAILBOX):
            if inventory.owner.get_household_owner_id() == household_id:
                return inventory

    def create_object_in_mailbox(self, definition_id, household_id):
        inventory = self.get_mailbox_inventory(household_id)
        if inventory is None:
            return
        obj = create_object(definition_id, loc_type=ItemLocation.OBJECT_INVENTORY)
        if household_id is not None:
            obj.set_household_owner_id(household_id)
        try:
            inventory.system_add_object(obj)
            return obj
        except:
            obj.destroy(source=self, cause='Failed to place object in mailbox.')

    def get_object_inventories(self, inv_type):
        inventory_owners = self.inventory_owners[inv_type]
        if inventory_owners or InventoryTypeTuning.is_shared_between_objects(inv_type):
            owner = SharedInventoryContainer(inv_type)
            self._shared_inventory_containers[inv_type] = owner
            inventory_owners.add(owner)
        return [inventory_owner.inventory_component for inventory_owner in inventory_owners]

    def get_all_object_inventories_gen(self, shared_only=False):
        for (inventory_type, inventory_owners) in self.inventory_owners.items():
            if not shared_only or not InventoryTypeTuning.is_shared_between_objects(inventory_type):
                pass
            else:
                for inventory_owner in inventory_owners:
                    yield (inventory_type, inventory_owner.inventory_component)

    def on_hit_their_marks(self):
        for (inventory_type, inventory_owners) in self.inventory_owners.items():
            if inventory_type == InventoryType.HIDDEN:
                pass
            else:
                for inventory_owner in inventory_owners:
                    inventory_owner.inventory_component.publish_inventory_items(items_own_ops=True)

    def populate_localization_token(self, token):
        token.type = LocalizedStringToken.RAW_TEXT
        token.raw_text = self.get_lot_name() or ''

    def get_lot_name(self):
        persistence = services.get_persistence_service()
        lot_name = None
        zone_data = persistence.get_zone_proto_buff(self.zone_id)
        if zone_data is not None:
            lot_name = zone_data.name
        return lot_name

    def send_lot_display_info(self):
        lot_name = self.get_lot_name()
        household = self.get_household()
        if household is not None:
            owner_household_name = household.name
        else:
            owner_household_name = None
        msg = UI_pb2.LotDisplayInfo()
        if lot_name is not None:
            msg.lot_name = lot_name
        if owner_household_name is not None:
            msg.household_name = owner_household_name
        zone_modifier_display_infos = services.get_zone_modifier_service().get_zone_modifier_display_infos(self.zone_id)
        for display_info in zone_modifier_display_infos:
            msg.icon_infos.append(create_icon_info_msg(IconInfoData(icon_resource=display_info.zone_modifier_icon)))
        op = distributor.shared_messages.create_message_op(msg, Consts_pb2.MSG_UI_LOT_DISPLAY_INFO)
        Distributor.instance().add_op_with_no_owner(op)

    def get_household(self):
        return services.household_manager().get(self.owner_household_id)

    def _should_track_premade_status(self):
        lot_tuning = LotTuningMaps.get_lot_tuning()
        if lot_tuning is None:
            return False
        return lot_tuning.track_premade_status

    def get_premade_status(self):
        if self._should_track_premade_status():
            save_game_data = services.get_persistence_service().get_save_game_data_proto()
            premade_lot_status = save_game_data.gameplay_data.premade_lot_status
            for lot_data in premade_lot_status:
                if lot_data.lot_id == self.lot_id:
                    if lot_data.is_premade:
                        return PremadeLotStatus.IS_PREMADE
                    return PremadeLotStatus.NOT_PREMADE
        return PremadeLotStatus.NOT_TRACKED

    def flag_as_premade(self, is_premade):
        if not self._should_track_premade_status():
            return
        save_game_data = services.get_persistence_service().get_save_game_data_proto()
        premade_lot_status = save_game_data.gameplay_data.premade_lot_status
        for lot_data in premade_lot_status:
            if lot_data.lot_id == self.lot_id:
                if lot_data.is_premade == False:
                    return
                lot_data.is_premade = is_premade
                return
        lot_data = premade_lot_status.add()
        lot_data.lot_id = self.lot_id
        lot_data.is_premade = is_premade

    def get_lot_position(self, position_strategy):
        if position_strategy == LotPositionStrategy.DEFAULT:
            return self.get_default_position()
        if position_strategy == LotPositionStrategy.RANDOM:
            return self.get_random_point()
        else:
            logger.error('Invalid LotPositionStrategy: {}, returning default lot position', position_strategy, self, owner='bnguyen')
            return self.get_default_position()

    def on_teardown(self):
        statistic_component = self.get_component(objects.components.types.STATISTIC_COMPONENT)
        if statistic_component is not None:
            statistic_component.on_remove()

    def save(self, gameplay_zone_data, is_instantiated=True):
        gameplay_zone_data.ClearField('commodity_tracker')
        gameplay_zone_data.ClearField('statistics_tracker')
        gameplay_zone_data.ClearField('skill_tracker')
        if is_instantiated:
            GlobalLotTuningAndCleanup.calculate_object_quantity_statistic_values(self)
        self.update_all_commodities()
        (commodites, skill_statistics, ranked_statistics) = self.commodity_tracker.save()
        gameplay_zone_data.commodity_tracker.commodities.extend(commodites)
        regular_statistics = self.statistic_tracker.save()
        gameplay_zone_data.statistics_tracker.statistics.extend(regular_statistics)
        gameplay_zone_data.skill_tracker.skills.extend(skill_statistics)
        gameplay_zone_data.ranked_statistic_tracker.ranked_statistics.extend(ranked_statistics)

    def load(self, gameplay_zone_data):
        self.commodity_tracker.load(gameplay_zone_data.commodity_tracker.commodities)
        self.statistic_tracker.load(gameplay_zone_data.statistics_tracker.statistics)
        self.commodity_tracker.load(gameplay_zone_data.skill_tracker.skills)
        self.commodity_tracker.load(gameplay_zone_data.ranked_statistic_tracker.ranked_statistics)
