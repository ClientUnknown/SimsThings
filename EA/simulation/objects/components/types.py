from objects.components import component_definitionimport objects.componentsANIMATION_COMPONENT = component_definition('Animation', 'animation_component')AUDIO_COMPONENT = component_definition('Audio', 'audio_component')EFFECTS_COMPONENT = component_definition('Effects', 'effects_component')FOOTPRINT_COMPONENT = component_definition('Footprint', 'footprint_component')GAMEPLAY_COMPONENT = component_definition('Gameplay', 'gameplay_component')LIVE_DRAG_COMPONENT = component_definition('LiveDrag', 'live_drag_component')POSITION_COMPONENT = component_definition('Position', 'position_component')RENDER_COMPONENT = component_definition('Render', 'render_component')ROUTING_COMPONENT = component_definition('Routing', 'routing_component')SIM_COMPONENT = component_definition('Sim', 'sim_component')VIDEO_COMPONENT = component_definition('Video', 'video_component')AFFORDANCE_TUNING_COMPONENT = component_definition('AffordanceTuning', 'affordancetuning_component')ANIMATION_OVERLAY_COMPONENT = component_definition('AnimationOverlay', 'animationoverlay_component')AUTONOMY_COMPONENT = component_definition('Autonomy', 'autonomy_component')AWARENESS_COMPONENT = component_definition('Awareness', 'awareness_component')BUFF_COMPONENT = component_definition('Buffs', 'buffs_component')CAMERA_VIEW_COMPONENT = component_definition('camera_view', 'camera_view_component')CANVAS_COMPONENT = component_definition('Canvas', 'canvas_component')CARRYABLE_COMPONENT = component_definition('Carryable', 'carryable_component')CARRYING_COMPONENT = component_definition('Carrying', 'carrying_component')CHANNEL_COMPONENT = component_definition('Channel', 'channel_component')CENSOR_GRID_COMPONENT = component_definition('CensorGrid', 'censorgrid_component')COLLECTABLE_COMPONENT = component_definition('CollectableComponent', 'collectable_component')CONSUMABLE_COMPONENT = component_definition('ConsumableComponent', 'consumable_component')CRAFTING_COMPONENT = component_definition('Crafting', 'crafting_component')CRAFTING_STATION_COMPONENT = component_definition('CraftingStationComponent', 'craftingstation_component')CURFEW_COMPONENT = component_definition('curfew', 'curfew_component')DISPLAY_COMPONENT = component_definition('Display', 'display_component')ENSEMBLE_COMPONENT = component_definition('EnsembleComponent', 'ensemble_component')ENVIRONMENT_SCORE_COMPONENT = component_definition('EnvironmentScoreComponent', 'environmentscore_component')EXAMPLE_COMPONENT = component_definition('Example', 'example_component')FISHING_LOCATION_COMPONENT = component_definition('FishingLocation', 'fishing_location_component')FLOWING_PUDDLE_COMPONENT = component_definition('FlowingPuddle', 'flowingpuddle_component')FOCUS_COMPONENT = component_definition('FocusComponent', 'focus_component')GAME_COMPONENT = component_definition('Game', 'game_component')GARDENING_COMPONENT = component_definition('Gardening', 'gardening_component')IDLE_COMPONENT = component_definition('Idle', 'idle_component')INVENTORY_COMPONENT = component_definition('Inventory', 'inventory_component')INVENTORY_ITEM_COMPONENT = component_definition('InventoryItem', 'inventoryitem_component')LIGHTING_COMPONENT = component_definition('Lighting', 'lighting_component')LINE_OF_SIGHT_COMPONENT = component_definition('LineOfSight', 'lineofsight_component')LINKED_OBJECT_COMPONENT = component_definition('LinkedObject', 'linked_object_component')LIVE_DRAG_TARGET_COMPONENT = component_definition('LiveDragTarget', 'live_drag_target_component')MANNEQUIN_COMPONENT = component_definition('Mannequin', 'mannequin_component')NAME_COMPONENT = component_definition('Name', 'name_component')NARRATIVE_AWARE_COMPONENT = component_definition('NarrativeAware', 'narrative_aware_component')NEW_OBJECT_COMPONENT = component_definition('NewObject', 'newobject_component')OBJECT_AGE_COMPONENT = component_definition('ObjectAge', 'objectage_component')OBJECT_CLAIM_COMPONENT = component_definition('ObjectClaim', 'object_claim_component')OBJECT_RELATIONSHIP_COMPONENT = component_definition('ObjectRelationship', 'objectrelationship_component')OBJECT_ROUTING_COMPONENT = component_definition('ObjectRouting', 'objectrouting_component')OBJECT_TELEPORTATION_COMPONENT = component_definition('ObjectTeleportation', 'objectteleportation_component')OWNABLE_COMPONENT = component_definition('Ownable', 'ownable_component')OWNING_HOUSEOLD_COMPONENT = component_definition('OwningHousehold', 'owning_household_component')PARENT_TO_SIM_HEAD_COMPONENT = component_definition('ParentToSimHead', 'parenttosimhead_component')PORTAL_COMPONENT = component_definition('Portal', 'portal_component')PORTAL_ANIMATION_COMPONENT = component_definition('PortalAnimation', 'portal_animation_component')PORTAL_LOCKING_COMPONENT = component_definition('PortalLocking', 'portal_locking_component')PRIVACY_COMPONENT = component_definition('Privacy', 'privacy_component')PROXIMITY_COMPONENT = component_definition('Proximity', 'proximity_component')RETAIL_COMPONENT = component_definition('Retail', 'retail_component')ROUTING_COMPONENT = component_definition('Routing', 'routing_component')SEASON_AWARE_COMPONENT = component_definition('SeasonAware', 'season_aware_component')SITUATION_SCHEDULER_COMPONENT = component_definition('SituationScheduler', 'situation_scheduler_component')SLOT_COMPONENT = component_definition('Slot', 'slot_component')SPAWN_POINT_COMPONENT = component_definition('SpawnPoint', 'spawn_point_component')SPAWNER_COMPONENT = component_definition('Spawner', 'spawner_component')STAGE_MARK_COMPONENT = component_definition('StageMark', 'stage_mark_component')STATE_COMPONENT = component_definition('State', 'state_component')STATISTIC_COMPONENT = component_definition('Statistic', 'statistic_component')STOLEN_COMPONENT = component_definition('Stolen', 'stolen_component')STORED_OBJECT_INFO_COMPONENT = component_definition('StoredObjectInfo', 'storedobjectinfo_component')STORED_AUDIO_COMPONENT = component_definition('StoredAudio', 'storedaudio_component')STORED_SIM_INFO_COMPONENT = component_definition('StoredSimInfo', 'storedsiminfo_component')TIME_OF_DAY_COMPONENT = component_definition('TimeOfDay', 'timeofday_component')TOOLTIP_COMPONENT = component_definition('Tooltip', 'tooltip_component')TOPIC_COMPONENT = component_definition('Topic', 'topic_component')VEHICLE_COMPONENT = component_definition('Vehicle', 'vehicle_component')WAITING_LINE_COMPONENT = component_definition('WaitingLine', 'waiting_line_component')WEATHER_AWARE_COMPONENT = component_definition('WeatherAware', 'weather_aware_component')WHIM_COMPONENT = component_definition('Whim', 'whim_component')
class NativeComponent(objects.components.Component, use_owner=False):

    @classmethod
    def create_component(cls, owner):
        return cls(owner)

    @classmethod
    def has_server_component(cls):
        return True

class ClientOnlyComponent(NativeComponent):

    @classmethod
    def has_server_component(cls):
        return False

class PositionComponent(ClientOnlyComponent, component_name=POSITION_COMPONENT, key=1578750580):
    pass

class RenderComponent(ClientOnlyComponent, component_name=RENDER_COMPONENT, key=573464449):
    pass

class AnimationComponent(ClientOnlyComponent, component_name=ANIMATION_COMPONENT, key=3994535597):
    pass

class RoutingComponent(ClientOnlyComponent, component_name=ROUTING_COMPONENT, key=2561111181):
    pass

class SimComponent(ClientOnlyComponent, component_name=SIM_COMPONENT, key=577793786):
    pass

class AudioComponent(ClientOnlyComponent, component_name=AUDIO_COMPONENT, key=1069811801):
    pass

class EffectsComponent(ClientOnlyComponent, component_name=EFFECTS_COMPONENT, key=1942696649):
    pass

class GameplayComponent(ClientOnlyComponent, component_name=GAMEPLAY_COMPONENT, key=89505537):
    pass
