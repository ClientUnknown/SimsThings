import randomimport servicesfrom sims.favorites.favorites_tuning import FavoritesTuning
def get_favorite_in_sim_inventory(sim, favorite_type):
    favorites_tracker = sim.sim_info.favorites_tracker
    if favorites_tracker is None:
        return
    sim_inventory = sim.inventory_component
    (favorite_obj_id, favorite_def_id) = favorites_tracker.get_favorite(favorite_type)
    if favorite_obj_id is not None:
        favorite_object = services.current_zone().find_object(favorite_obj_id)
        if favorite_object is not None and favorite_object in sim_inventory:
            return favorite_object.definition
    elif favorite_def_id is not None:
        return services.definition_manager().get(favorite_def_id)
    other_objects = sim_inventory.get_objects_by_tag(favorite_type)
    found_obj_def = random.choice(other_objects).definition if other_objects else None
    return found_obj_def

def get_animation_override_for_prop_def(definition):
    for overrides in FavoritesTuning.FAVORITES_ANIMATION_OVERRIDES:
        if definition in overrides.favorite_definitions:
            return overrides.animation_overrides
