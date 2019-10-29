from build_buy import load_conditional_objectsfrom conditional_layers.conditional_layer_service import ConditionalLayerRequestSpeedTypefrom date_and_time import TimeSpan, create_time_spanfrom default_property_stream_reader import DefaultPropertyStreamReaderfrom objects.client_object_mixin import ClientObjectMixinfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableRange, TunableSimMinute, TunableMapping, TunableVariant, TunableEnumEntry, Tunable, OptionalTunable, TunableReferencefrom sims4.utils import classpropertyfrom situations.service_npcs.modify_lot_items_tuning import ModifyAllLotItemsfrom venues.npc_summoning import ResidentialLotArrivalBehavior, CreateAndAddToSituation, AddToBackgroundSituationimport alarmsimport enumimport objectsimport servicesimport sims4.resourcesimport venues.venue_constantsimport world.streetlogger = sims4.log.Logger('OpenStreetDirector', default_owner='jjacobson')
class OpenStreetDirectorPriority(enum.Int, export=False):
    DEFAULT = ...
    CART = ...
    FESTIVAL = ...

class OpenStreetDirectorBase(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.OPEN_STREET_DIRECTOR)):
    INSTANCE_SUBCLASSES_ONLY = True
    LAYER_OBJECTS_TO_LOAD = TunableRange(description='\n        The number of objects to load at a time when loading a layer.\n        Please consult a GPE before changing this value as it will impact\n        performance.\n        ', tunable_type=int, default=1, minimum=1)
    LAYER_OBJECTS_TO_DESTROY = TunableRange(description='\n        The number of objects to destroy at a time when destroying a layer.\n        Please consult a GPE before changing this value as it will impact\n        performance.\n        ', tunable_type=int, default=1, minimum=1)
    LAYER_OBJECTS_ALARM_TIME = TunableSimMinute(description='\n        The frequency that we will create or destroy objects in the festival.\n        Please consult a GPE before changing this value as it will impact\n        performance.\n        ', default=5, minimum=1)
    INSTANCE_TUNABLES = {'lot_cleanup': ModifyAllLotItems.TunableFactory(description='\n            A list of actions taken on objects on the lot when the open street\n            director is being shutdown or cleaned up.  Objects on the lot are\n            left untouched.\n            '), 'startup_actions': ModifyAllLotItems.TunableFactory(description='\n            A list of actions that are taken on objects on the open street\n            when the open street director is being started up.  Objects on\n            the lot are left untouched.\n            '), 'npc_summoning_behavior': TunableMapping(description='\n            Whenever an NPC is summoned to a lot by the player, determine\n            which action to take based on the summoning purpose. The purpose\n            is a dynamic enum: venues.venue_constants.NPCSummoningPurpose.\n            \n            The action will generally involve either adding a sim to an existing\n            situation or creating a situation then adding them to it.\n            \n            \\depot\\Sims4Projects\\Docs\\Design\\Open Streets\\Open Street Invite Matrix.xlsx\n            \n            residential: This is behavior pushed on the NPC if the venue is a residential lot.\n            create_situation: Place the NPC in the specified situation/job pair.\n            add_to_background_situation: Add the NPC the currently running background \n            situation on a venue.\n            ', key_type=TunableEnumEntry(venues.venue_constants.NPCSummoningPurpose, venues.venue_constants.NPCSummoningPurpose.DEFAULT), value_type=TunableVariant(locked_args={'disabled': None}, residential=ResidentialLotArrivalBehavior.TunableFactory(), create_situation=CreateAndAddToSituation.TunableFactory(), add_to_background_situation=AddToBackgroundSituation.TunableFactory(), default='disabled')), 'allow_loading_after_time_passes_elsewhere': Tunable(description='\n            When Checked this will allow an open street director to be loaded\n            even if time has passed on another neighborhood with a different,\n            or no, open street director.\n            \n            When Unchecked, if any time passes in another neighborhood then the\n            save data will not be loaded.\n            ', tunable_type=bool, default=False), 'whim_set': OptionalTunable(description='\n            If enabled then this open street director will offer a whim set to\n            the Sim when it is running.\n            ', tunable=TunableReference(description='\n                A whim set that is active when this open street director is\n                running.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions=('ObjectivelessWhimSet',)))}

    @classproperty
    def priority(cls):
        raise NotImplementedError

    def __init__(self):
        self.request = None
        self._cleanup_actions = []
        self.was_loaded = False
        self._loaded_layers = []
        self._being_cleaned_up = False
        self._ready_for_destruction = False
        self._prerolling = False
        self.did_preroll = False

    @property
    def ready_for_destruction(self):
        return self._ready_for_destruction

    def on_startup(self):
        startup_actions = self.startup_actions()

        def object_criteria(obj):
            if obj.is_on_active_lot():
                return False
            return True

        startup_actions.modify_objects(object_criteria=object_criteria)

    def on_shutdown(self):
        pass

    def _clean_up(self):
        pass

    def clean_up(self):
        if self._ready_for_destruction:
            self.request.on_open_director_shutdown()
            return
        self._being_cleaned_up = True
        self._clean_up()

    def create_situations_during_zone_spin_up(self):
        pass

    def self_destruct(self):
        if self._ready_for_destruction:
            self.request.on_open_director_shutdown()
        else:
            self.request.request_destruction()

    def _should_load_old_data(self, street_director_proto, reader):
        if not (services.current_zone().time_has_passed_in_world_since_open_street_save() and self.allow_loading_after_time_passes_elsewhere and street_director_proto.HasField('resource_key')):
            return False
        previous_resource_key = sims4.resources.get_key_from_protobuff(street_director_proto.resource_key)
        return previous_resource_key == self.resource_key

    def load(self, street_director_proto):
        if street_director_proto.HasField('custom_data'):
            reader = DefaultPropertyStreamReader(street_director_proto.custom_data)
        else:
            reader = None
        if self._should_load_old_data(street_director_proto, reader):
            self.was_loaded = True
            loaded_layers = set()
            conditional_layer_manager = services.get_instance_manager(sims4.resources.Types.CONDITIONAL_LAYER)
            loaded_layers = set(conditional_layer_manager.get(conditional_layer_guid) for conditional_layer_guid in street_director_proto.loaded_layer_guids)
            self._loaded_layers = list(loaded_layers)
            self._load_custom_open_street_director(street_director_proto, reader)
        else:
            self.request.manager.cleanup_old_open_street_director()

    def _load_custom_open_street_director(self, street_director_proto, reader):
        pass

    def save(self, street_director_proto):
        street_director_proto.resource_key = sims4.resources.get_protobuff_for_key(self.resource_key)
        street_director_proto.loaded_layer_guids.extend(loaded_layer.guid64 for loaded_layer in self._loaded_layers)
        writer = sims4.PropertyStreamWriter()
        self._save_custom_open_street_director(street_director_proto, writer)
        data = writer.close()
        if writer.count > 0:
            street_director_proto.custom_data = data

    def _save_custom_open_street_director(self, street_director_proto, writer):
        pass

    def has_conditional_layer(self, conditional_layer):
        current_zone_id = services.current_zone_id()
        street = world.street.get_street_instance_from_zone_id(current_zone_id)
        if street is None:
            return False
        return street.has_conditional_layer(conditional_layer)

    def load_layer_immediately(self, conditional_layer):
        if conditional_layer not in self._loaded_layers:
            self._loaded_layers.append(conditional_layer)
        services.conditional_layer_service().load_conditional_layer(conditional_layer, callback=self.on_layer_loaded, speed=ConditionalLayerRequestSpeedType.IMMEDIATELY)

    def load_layer_gradually(self, conditional_layer):
        if conditional_layer not in self._loaded_layers:
            self._loaded_layers.append(conditional_layer)
        services.conditional_layer_service().load_conditional_layer(conditional_layer, callback=self.on_layer_loaded, speed=ConditionalLayerRequestSpeedType.GRADUALLY, timer_interval=OpenStreetDirectorBase.LAYER_OBJECTS_ALARM_TIME, timer_object_count=OpenStreetDirectorBase.LAYER_OBJECTS_TO_LOAD)

    def on_layer_loaded(self, conditional_layer):
        layer_objects = services.conditional_layer_service().get_layer_objects(conditional_layer)
        for obj in layer_objects:
            if obj.environmentscore_component is not None:
                obj.remove_component(objects.components.types.ENVIRONMENT_SCORE_COMPONENT)

    def remove_layer_objects(self, conditional_layer):
        speed = ConditionalLayerRequestSpeedType.GRADUALLY if services.current_zone().is_zone_running else ConditionalLayerRequestSpeedType.IMMEDIATELY
        services.conditional_layer_service().destroy_conditional_layer(conditional_layer, callback=self.on_layer_objects_destroyed, speed=speed, timer_interval=OpenStreetDirectorBase.LAYER_OBJECTS_ALARM_TIME, timer_object_count=OpenStreetDirectorBase.LAYER_OBJECTS_TO_DESTROY)

    def on_layer_objects_destroyed(self, conditional_layer):
        if conditional_layer in self._loaded_layers:
            self._loaded_layers.remove(conditional_layer)

    def get_all_layer_created_objects(self):
        conditional_object_service = services.conditional_layer_service()
        objects = []
        for conditional_layer in self._loaded_layers:
            objects.extend(conditional_object_service.get_layer_objects(conditional_layer))
        return objects

    @classmethod
    def run_lot_cleanup(cls):
        cleanup = cls.lot_cleanup()

        def object_criteria(obj):
            if obj.in_use:
                return False
            elif obj.is_on_active_lot():
                return False
            return True

        cleanup.modify_objects(object_criteria=object_criteria)

    def summon_npcs(self, npc_infos, purpose, host_sim_info=None):
        summon_behavior = self.npc_summoning_behavior.get(purpose)
        if summon_behavior is None:
            summon_behavior = self.npc_summoning_behavior.get(venues.venue_constants.NPCSummoningPurpose.DEFAULT)
            if summon_behavior is None:
                return False
        summon_behavior(npc_infos, host_sim_info=host_sim_info)
        return True

    def _preroll(self, preroll_time):
        pass

    def preroll(self, preroll_time=None):
        if self.was_loaded:
            return
        self.did_preroll = True
        self._prerolling = True
        try:
            self._preroll(preroll_time)
        except Exception:
            logger.exception('Exception hit while prerolling for {}:', self)
        finally:
            self._prerolling = False
