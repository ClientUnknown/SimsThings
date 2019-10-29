import operatorimport randomfrom objects.client_object_mixin import ClientObjectMixinfrom objects.definition_manager import TunableDefinitionListfrom objects.puddles import PuddleLiquid, PuddleSize, create_puddlefrom routing import SurfaceIdentifier, SurfaceTypefrom sims4.tuning.tunable import TunableTuple, TunableRange, TunableInterval, TunableSimMinute, Tunable, TunableEnumEntryfrom sims4.tuning.tunable_base import GroupNamesfrom singletons import DEFAULTfrom statistics.commodity import Commodityfrom statistics.statistic import Statisticimport build_buyimport objects.game_objectimport objects.systemimport placementimport sims4.logimport sims4.randomlogger = sims4.log.Logger('Puddles')
class Puddle(objects.game_object.GameObject):
    WEED_DEFINITIONS = TunableDefinitionList(description='\n        Possible weed objects which can be spawned by evaporation.')
    PLANT_DEFINITIONS = TunableDefinitionList(description='\n        Possible plant objects which can be spawned by evaporation.')
    INSTANCE_TUNABLES = {'indoor_evaporation_time': TunableInterval(description='\n            Number of SimMinutes this puddle should take to evaporate when \n            created indoors.\n            ', tunable_type=TunableSimMinute, default_lower=200, default_upper=300, minimum=1, tuning_group=GroupNames.DEPRECATED), 'outdoor_evaporation_time': TunableInterval(description='\n            Number of SimMinutes this puddle should take to evaporate when \n            created outdoors.\n            ', tunable_type=TunableSimMinute, default_lower=30, default_upper=60, minimum=1, tuning_group=GroupNames.DEPRECATED), 'evaporation_outcome': TunableTuple(nothing=TunableRange(int, 5, minimum=1, description='Relative chance of nothing.'), weeds=TunableRange(int, 2, minimum=0, description='Relative chance of weeds.'), plant=TunableRange(int, 1, minimum=0, description='Relative chance of plant.'), tuning_group=GroupNames.PUDDLES), 'intial_stat_value': TunableTuple(description='\n            This is the starting value for the stat specified.  This controls \n            how long it takes to mop this puddle.\n            ', stat=Statistic.TunableReference(description='\n                The stat used for mopping puddles.\n                '), value=Tunable(description='\n                The initial value this puddle should have for the mopping stat.\n                The lower the value (-100,100), the longer it takes to mop up.\n                ', tunable_type=int, default=-20), tuning_group=GroupNames.PUDDLES), 'evaporation_data': TunableTuple(description='\n            This is the information for evaporation.  This controls how long this\n            puddle takes to evaporate.\n            ', commodity=Commodity.TunableReference(description='\n                The commodity used for evaporation.\n                '), initial_value=TunableInterval(description='\n                Initial value of this commodity.  Time it takes to evaporate\n                will be based on how fast this commodity decays.\n                (Based on loot given in weather aware component)\n                ', tunable_type=float, default_lower=30, default_upper=60, minimum=1), tuning_group=GroupNames.PUDDLES), 'puddle_liquid': TunableEnumEntry(description='\n        The liquid that the puddle is made of.\n        ', tunable_type=PuddleLiquid, default=PuddleLiquid.INVALID, invalid_enums=(PuddleLiquid.INVALID,), tuning_group=GroupNames.PUDDLES), 'puddle_size': TunableEnumEntry(description='\n        The size of the puddle.\n        ', tunable_type=PuddleSize, default=PuddleSize.NoPuddle, invalid_enums=(PuddleSize.NoPuddle,), tuning_group=GroupNames.PUDDLES)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._evaporate_callback_handle = None
        self.statistic_tracker.set_value(self.intial_stat_value.stat, self.intial_stat_value.value)

    @property
    def size_count(self):
        if self.puddle_size == PuddleSize.SmallPuddle:
            return 1
        if self.puddle_size == PuddleSize.MediumPuddle:
            return 2
        elif self.puddle_size == PuddleSize.LargePuddle:
            return 3

    def place_puddle(self, target, max_distance, ids_to_ignore=DEFAULT):
        destroy_puddle = True
        try:
            if ids_to_ignore is DEFAULT:
                ids_to_ignore = (self.id,)
            else:
                ids_to_ignore.append(self.id)
            flags = placement.FGLSearchFlag.ALLOW_GOALS_IN_SIM_POSITIONS
            flags = flags | placement.FGLSearchFlag.ALLOW_GOALS_IN_SIM_INTENDED_POSITIONS
            flags = flags | placement.FGLSearchFlag.STAY_IN_SAME_CONNECTIVITY_GROUP
            if target.is_on_active_lot():
                flags = flags | placement.FGLSearchFlag.SHOULD_TEST_BUILDBUY
            else:
                flags = flags | placement.FGLSearchFlag.SHOULD_TEST_ROUTING
                flags = flags | placement.FGLSearchFlag.USE_SIM_FOOTPRINT
            flags = flags | placement.FGLSearchFlag.CALCULATE_RESULT_TERRAIN_HEIGHTS
            flags = flags | placement.FGLSearchFlag.DONE_ON_MAX_RESULTS
            radius_target = target
            while radius_target.parent is not None:
                radius_target = radius_target.parent
            if radius_target.is_part:
                radius_target = radius_target.part_owner
            routing_surface = target.routing_surface
            routing_surface = SurfaceIdentifier(routing_surface.primary_id, routing_surface.secondary_id, SurfaceType.SURFACETYPE_WORLD)
            starting_location = placement.create_starting_location(position=target.position + target.forward*radius_target.object_radius, orientation=sims4.random.random_orientation(), routing_surface=routing_surface)
            fgl_context = placement.create_fgl_context_for_object(starting_location, self, search_flags=flags, ignored_object_ids=ids_to_ignore, max_distance=max_distance)
            (position, orientation) = placement.find_good_location(fgl_context)
            if position is not None:
                destroy_puddle = False
                self.place_puddle_at(position, orientation, routing_surface)
                return True
            return False
        finally:
            if destroy_puddle:
                self.destroy(source=self, cause='Failed to place puddle.')

    def place_puddle_at(self, position, orientation, routing_surface):
        self.location = sims4.math.Location(sims4.math.Transform(position, orientation), routing_surface)
        self.fade_in()
        self.start_evaporation()

    def try_grow_puddle(self):
        if self.puddle_size == PuddleSize.LargePuddle:
            return
        else:
            if self.puddle_size == PuddleSize.MediumPuddle:
                puddle = create_puddle(PuddleSize.LargePuddle, puddle_liquid=self.puddle_liquid)
            else:
                puddle = create_puddle(PuddleSize.MediumPuddle, puddle_liquid=self.puddle_liquid)
            if puddle.place_puddle(self, 1, ids_to_ignore=[self.id]):
                if self._evaporate_callback_handle is not None:
                    self.commodity_tracker.remove_listener(self._evaporate_callback_handle)
                self.destroy(self, cause='Puddle is growing.', fade_duration=ClientObjectMixin.FADE_DURATION)
                return puddle

    def start_evaporation(self):
        tracker = self.commodity_tracker
        tracker.set_value(self.evaporation_data.commodity, self.evaporation_data.initial_value.random_float())
        if self._evaporate_callback_handle is not None:
            tracker.remove_listener(self._evaporate_callback_handle)
        threshold = sims4.math.Threshold(0.0, operator.le)
        self._evaporate_callback_handle = tracker.create_and_add_listener(self.evaporation_data.commodity, threshold, self.evaporate)

    def evaporate(self, stat_instance):
        if self.in_use:
            self.start_evaporation()
            return
        if self._evaporate_callback_handle is not None:
            self.commodity_tracker.remove_listener(self._evaporate_callback_handle)
            self._evaporate_callback_handle = None
        if self.is_on_natural_ground():
            defs_to_make = sims4.random.weighted_random_item([(self.evaporation_outcome.nothing, None), (self.evaporation_outcome.weeds, self.WEED_DEFINITIONS), (self.evaporation_outcome.plant, self.PLANT_DEFINITIONS)])
            if defs_to_make:
                def_to_make = random.choice(defs_to_make)
                obj_location = sims4.math.Location(sims4.math.Transform(self.position, sims4.random.random_orientation()), self.routing_surface)
                (result, _) = build_buy.test_location_for_object(None, def_to_make.id, obj_location, [self])
                if result:
                    obj = objects.system.create_object(def_to_make)
                    obj.opacity = 0
                    obj.location = self.location
                    obj.fade_in()
        self.destroy(self, cause='Puddle is evaporating.', fade_duration=ClientObjectMixin.FADE_DURATION)

    def load_object(self, object_data):
        super().load_object(object_data)
        self.start_evaporation()
