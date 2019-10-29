import collectionsfrom sims.sim_info_types import Species, Age, SpeciesExtendedimport enumimport placementimport routingimport sims4.loglogger = sims4.log.Logger('Jig Utils')with sims4.reload.protected(globals()):
    on_jig_changed = sims4.callback_utils.CallableList()
class JigPositioning(enum.Int):
    RelativeToSimB = 0
    RelativeToSimA = 1
SIMS_3_DISTANCE_MATRIX = {(Species.CAT, Age.CHILD): {(Species.CAT, Age.CHILD): 0.3, Species.CAT: 0.5, (Species.DOG, Age.CHILD): 0.3, Species.DOG: 0.9, (Species.HUMAN, Age.CHILD): 0.6, Species.HUMAN: 0.7}, Species.CAT: {(Species.CAT, Age.CHILD): 0.5, Species.CAT: 0.6, (Species.DOG, Age.CHILD): 0.5, Species.DOG: 1, (Species.HUMAN, Age.CHILD): 0.7, Species.HUMAN: 1}, (Species.DOG, Age.CHILD): {(Species.CAT, Age.CHILD): 0.7, Species.CAT: 1, (Species.DOG, Age.CHILD): 0.7, Species.DOG: 1, (Species.HUMAN, Age.CHILD): 0.7, Species.HUMAN: 0.7}, Species.DOG: {(Species.CAT, Age.CHILD): 0.9, Species.CAT: 1, (Species.DOG, Age.CHILD): 0.9, Species.DOG: 1, (Species.HUMAN, Age.CHILD): 1, Species.HUMAN: 1}, (Species.HUMAN, Age.CHILD): {(Species.CAT, Age.CHILD): 0.6, Species.CAT: 0.7, (Species.DOG, Age.CHILD): 0.6, Species.DOG: 1, (Species.HUMAN, Age.CHILD): 0.7, Species.HUMAN: 0.7}, Species.HUMAN: {(Species.CAT, Age.CHILD): 0.7, Species.CAT: 1, (Species.DOG, Age.CHILD): 0.7, Species.DOG: 1, (Species.HUMAN, Age.CHILD): 0.7, Species.HUMAN: 0.7}}
def get_sims3_social_distance(sim_a_species, sim_a_age, sim_b_species, sim_b_age):
    sim_a_key = (sim_a_species, sim_a_age)
    sim_b_key = (sim_b_species, sim_b_age)
    if sim_a_key not in SIMS_3_DISTANCE_MATRIX:
        sim_a_key = sim_a_species
    if sim_b_key not in SIMS_3_DISTANCE_MATRIX:
        sim_b_key = sim_b_species
    return SIMS_3_DISTANCE_MATRIX[sim_a_key][sim_b_key]
ReserveSpace = collections.namedtuple('_ReserveSpace', ('front', 'back', 'left', 'right'))DEFAULT_RESERVE_SPACE = {(SpeciesExtended.SMALLDOG, Age.CHILD): ReserveSpace(0.4, 0.5, 0.3, 0.3), SpeciesExtended.SMALLDOG: ReserveSpace(0.4, 0.5, 0.3, 0.3), (Species.CAT, Age.CHILD): ReserveSpace(0.2, 0.3, 0.2, 0.2), Species.CAT: ReserveSpace(0.4, 0.5, 0.3, 0.3), (Species.DOG, Age.CHILD): ReserveSpace(0.4, 0.5, 0.3, 0.3), Species.DOG: ReserveSpace(0.75, 1.0, 0.3, 0.3), (Species.HUMAN, Age.CHILD): ReserveSpace(0.5, 0.5, 0.5, 0.5), Species.HUMAN: ReserveSpace(0.5, 0.5, 0.5, 0.5)}
def get_default_reserve_space(species, age):
    key = (species, age)
    if key not in DEFAULT_RESERVE_SPACE:
        key = species
    return DEFAULT_RESERVE_SPACE[key]

def _generate_poly_points(sim_a_translation, sim_a_fwd, sim_b_translation, sim_b_fwd, a_left, a_right, a_front, a_back, b_left, b_right, b_front, b_back):
    all_points = []
    sim_a_cross = sims4.math.vector_cross(sim_a_fwd, sims4.math.Vector3.Y_AXIS())
    all_points.append(sim_a_translation + sim_a_fwd*a_front)
    all_points.append(sim_a_translation + sim_a_cross*a_right)
    all_points.append(sim_a_translation - sim_a_fwd*a_back)
    all_points.append(sim_a_translation - sim_a_cross*a_left)
    sim_b_cross = sims4.math.vector_cross(sim_b_fwd, sims4.math.Vector3.Y_AXIS())
    all_points.append(sim_b_translation + sim_b_fwd*b_front)
    all_points.append(sim_b_translation + sim_b_cross*b_right)
    all_points.append(sim_b_translation - sim_b_fwd*b_back)
    all_points.append(sim_b_translation - sim_b_cross*b_left)
    polygon = sims4.geometry.Polygon(all_points)
    return polygon.get_convex_hull()

def _generate_single_poly_rectangle_points(sim_a_translation, sim_z_vector, sim_x_vector, a_left, a_right, a_front, a_back):
    all_points = [sim_a_translation + (sim_x_vector*-a_left + sim_z_vector*a_back), sim_a_translation + (sim_x_vector*a_right + sim_z_vector*a_back), sim_a_translation + (sim_x_vector*-a_left + sim_z_vector*-a_front), sim_a_translation + (sim_x_vector*a_right + sim_z_vector*-a_front)]
    polygon = sims4.geometry.Polygon(all_points)
    return polygon.get_convex_hull()

def generate_jig_polygon(loc_a, pos_a, rotation_a, loc_b, pos_b, rotation_b, a_left, a_right, a_front, a_back, b_left, b_right, b_front, b_back, positioning_type=JigPositioning.RelativeToSimB, fallback_routing_surface=None, reverse_nonreletive_sim_orientation=False, **fgl_kwargs):
    if isinstance(pos_a, sims4.math.Vector2):
        pos_a = sims4.math.Vector3(pos_a.x, 0, pos_a.y)
    if isinstance(pos_b, sims4.math.Vector2):
        pos_b = sims4.math.Vector3(pos_b.x, 0, pos_b.y)
    sim_a_radians = rotation_a
    sim_b_radians = rotation_b

    def _generate_polygon_params(relative_loc, fwd_vec, relative_vec, rot_relative, rot_other):
        polygon_fwd = relative_loc.transform.orientation.transform_vector(fwd_vec)
        abs_vec_to_relative_sim = relative_loc.transform.orientation.transform_vector(relative_vec)
        translation_relative = relative_loc.world_transform.translation
        fwd_relative = sims4.math.vector3_rotate_axis_angle(polygon_fwd, rot_relative, sims4.math.Vector3.Y_AXIS())
        translation_other = translation_relative - abs_vec_to_relative_sim
        fwd_other = sims4.math.vector3_rotate_axis_angle(polygon_fwd, rot_other, sims4.math.Vector3.Y_AXIS())
        routing_surface = relative_loc.routing_surface
        if relative_loc.parent is not None:
            routing_surface = relative_loc.parent.routing_surface
        start_location = routing.Location(relative_loc.world_transform.translation, relative_loc.world_transform.orientation, routing_surface)
        return (start_location, fwd_relative, translation_relative, fwd_other, translation_other, routing_surface)

    if positioning_type == JigPositioning.RelativeToSimB:
        vec_to_relative_sim = pos_b - pos_a
        (start_location, sim_b_fwd, sim_b_translation, sim_a_fwd, sim_a_translation, routing_surface) = _generate_polygon_params(loc_b, -1*sims4.math.Vector3.Z_AXIS(), vec_to_relative_sim, sim_b_radians, sim_a_radians)
    else:
        vec_to_relative_sim = pos_a - pos_b
        (start_location, sim_a_fwd, sim_a_translation, sim_b_fwd, sim_b_translation, routing_surface) = _generate_polygon_params(loc_a, sims4.math.Vector3.Z_AXIS(), vec_to_relative_sim, sim_a_radians, sim_b_radians)
    polygon = _generate_poly_points(sim_a_translation, sim_a_fwd, sim_b_translation, sim_b_fwd, a_left, a_right, a_front, a_back, b_left, b_right, b_front, b_back)
    context = placement.FindGoodLocationContext(start_location, object_polygons=(polygon,), **fgl_kwargs)
    (new_translation, new_orientation) = placement.find_good_location(context)
    if fallback_routing_surface is not None:
        start_location.routing_surface = fallback_routing_surface
        context = placement.FindGoodLocationContext(start_location, object_polygons=(polygon,), **fgl_kwargs)
        (new_translation, new_orientation) = placement.find_good_location(context)
    if new_translation is None and new_translation is None:
        return (None, None, None, None, None)
    if positioning_type == JigPositioning.RelativeToSimB:
        sim_b_translation = new_translation
        sim_b_orientation = sims4.math.Quaternion.concatenate(new_orientation, sims4.math.angle_to_yaw_quaternion(sim_b_radians))
        if reverse_nonreletive_sim_orientation:
            sim_a_fwd = new_orientation.transform_vector(vec_to_relative_sim)
        else:
            sim_a_fwd = new_orientation.transform_vector(-1*vec_to_relative_sim)
        sim_a_translation = new_translation + new_orientation.transform_vector(-1*vec_to_relative_sim)
        sim_a_orientation = sims4.math.Quaternion.from_forward_vector(sims4.math.vector3_rotate_axis_angle(sim_a_fwd, sim_a_radians, sims4.math.Vector3.Y_AXIS()))
    else:
        sim_a_translation = new_translation
        sim_a_orientation = sims4.math.Quaternion.concatenate(new_orientation, sims4.math.angle_to_yaw_quaternion(sim_a_radians))
        if reverse_nonreletive_sim_orientation:
            sim_b_fwd = new_orientation.transform_vector(vec_to_relative_sim)
        else:
            sim_b_fwd = new_orientation.transform_vector(-1*vec_to_relative_sim)
        sim_b_translation = new_translation + new_orientation.transform_vector(-1*vec_to_relative_sim)
        sim_b_orientation = sims4.math.Quaternion.concatenate(new_orientation, sims4.math.angle_to_yaw_quaternion(sim_b_radians))
    return (sim_a_translation, sim_a_orientation, sim_b_translation, sim_b_orientation, routing_surface)
