from build_buy import FloorFeatureTypefrom interactions import ParticipantTypefrom interactions.base.super_interaction import SuperInteractionfrom interactions.constraints import create_constraint_set, TunableCircle, TunableFacing, Nowherefrom sims4.tuning.geometric import TunableDistanceSquaredfrom sims4.tuning.tunable import Tunable, TunableEnumEntry, OptionalTunable, TunableTuplefrom sims4.utils import flexmethodimport build_buyimport routingimport servicesimport sims4.loglogger = sims4.log.Logger('FloorFeatureInteractions')
class GoToNearestFloorFeatureInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'terrain_feature': TunableEnumEntry(description='\n            The type of floor feature the sim should route to\n            ', tunable_type=FloorFeatureType, default=FloorFeatureType.BURNT), 'routing_circle_constraint': TunableCircle(1.5, description='\n            Circle constraint around the floor feature\n            '), 'routing_facing_constraint': TunableFacing(description='\n                Controls how a Sim must face the terrain feature\n                '), 'indoors_only': Tunable(description='\n            Indoors Only\n            ', tunable_type=bool, default=False), 'radius_filter': OptionalTunable(description='\n            If enabled, floor features will be filtered out unless they are \n            within a radius of the radius_actor.\n            \n            The purpose of the radius filter is to constrain the set of\n            found floor features only to those within a radius of a tuned\n            participant. For example, this interaction could allow Sims only\n            to route to leaves within the radius of a targeted leaf pile.\n            ', tunable=TunableTuple(radius=TunableDistanceSquared(description="\n                    The radius, with the Saved Actor 1's position, that defines the area\n                    within which the floor feature is valid.\n                    ", default=5.0), radius_actor=TunableEnumEntry(description='\n                    The Actor within whose radius the tuned floor feature must be in\n                    for consideration.\n                    ', tunable_type=ParticipantType, default=ParticipantType.Actor)))}

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        inst_or_cls = inst if inst is not None else cls
        yield from super(SuperInteraction, inst_or_cls)._constraint_gen(sim, target, participant_type=participant_type)
        floor_feature_constraint = inst_or_cls._create_floor_feature_constraint_set(sim)
        yield floor_feature_constraint

    @flexmethod
    def _create_floor_feature_constraint_set(cls, inst, sim):
        inst_or_cls = inst if inst is not None else cls
        floor_feature_contraints = []
        floor_features_and_surfaces = []
        zone_id = services.current_zone_id()
        floor_features = build_buy.list_floor_features(zone_id, inst_or_cls.terrain_feature)
        if floor_features is None:
            return Nowhere('No found floor features.')
        radius_object = None
        if inst_or_cls.radius_filter is not None:
            radius_object = inst_or_cls.get_participant(inst_or_cls.radius_filter.radius_actor)
        if inst_or_cls.radius_filter is not None and radius_object is None:
            return Nowhere('Radius filter is enabled but the radius actor has a None value.')
        for floor_feature in floor_features:
            if inst_or_cls.indoors_only and build_buy.is_location_natural_ground(zone_id, floor_feature[0], floor_feature[1]):
                pass
            else:
                routing_surface = routing.SurfaceIdentifier(zone_id, floor_feature[1], routing.SurfaceType.SURFACETYPE_WORLD)
                floor_feature_location = floor_feature[0]
                if inst_or_cls.radius_filter is not None:
                    if (radius_object.position - floor_feature_location).magnitude_squared() <= inst_or_cls.radius_filter.radius:
                        floor_features_and_surfaces.append((floor_feature_location, routing_surface))
                        floor_features_and_surfaces.append((floor_feature_location, routing_surface))
                else:
                    floor_features_and_surfaces.append((floor_feature_location, routing_surface))
        if floor_features_and_surfaces:
            for floor_feature_and_surface in floor_features_and_surfaces:
                circle_constraint = inst_or_cls.routing_circle_constraint.create_constraint(sim, None, target_position=floor_feature_and_surface[0], routing_surface=floor_feature_and_surface[1])
                facing_constraint = inst_or_cls.routing_facing_constraint.create_constraint(sim, None, target_position=floor_feature_and_surface[0], routing_surface=floor_feature_and_surface[1])
                constraint = circle_constraint.intersect(facing_constraint)
                floor_feature_contraints.append(constraint)
            return create_constraint_set(floor_feature_contraints)
        return Nowhere('With radius filter enabled, no found floor features are within range.')
