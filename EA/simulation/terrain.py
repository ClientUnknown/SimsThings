import servicesfrom routing import SurfaceTypetry:
    import _terrain
    get_lot_level_height = _terrain.get_lot_level_height
    get_lot_level_height_and_surface_object = _terrain.get_lot_level_height_and_surface_object
    get_snowmask_value = _terrain.get_snowmask_value
    TERRAIN_TAG_REQUIRED_STRENGTH = 0.75

    def is_terrain_tag_at_position(x, z, terrain_tags, level=0, required_strength=TERRAIN_TAG_REQUIRED_STRENGTH):
        zone_id = services.current_zone().id
        terrain_tag_values = [terrain_tag.value for terrain_tag in terrain_tags]
        return _terrain.is_terrain_tag_at_position(x, z, zone_id, terrain_tag_values, level, required_strength)

    def get_terrain_size(zone_id=None):
        if zone_id is None or zone_id == 0:
            zone_id = services.current_zone().id
        return _terrain.get_size(zone_id)

    def get_terrain_center(zone_id=None):
        if zone_id is None or zone_id == 0:
            zone_id = services.current_zone().id
        return _terrain.get_center(zone_id)

    def get_terrain_height(x, z, routing_surface=None):
        zone = services.current_zone()
        level = 0 if routing_surface is None else routing_surface.secondary_id
        surface_type = SurfaceType.SURFACETYPE_UNKNOWN if routing_surface is None else routing_surface.type
        val = get_lot_level_height(x, z, level, zone.id, surface_type)
        return val

    def get_water_depth(x, z, level=0):
        zone_id = services.current_zone_id()
        val = _terrain.get_water_depth(x, z, zone_id, level)
        return val

    def get_water_depth_at_location(location):
        level = 0 if location.routing_surface is None else location.routing_surface.secondary_id
        return get_water_depth(location.transform.translation.x, location.transform.translation.z, level)

    def adjust_locations_for_target_water_depth(target_depth, error, initial_transforms):
        zone_id = services.current_zone_id()
        transforms = _terrain.adjust_locations_for_target_water_depth(zone_id, target_depth, error, initial_transforms)
        return transforms

    def adjust_locations_for_coastline(initial_transforms):
        zone_id = services.current_zone_id()
        transforms = _terrain.adjust_locations_for_coastline(zone_id, initial_transforms)
        return transforms

    def is_position_in_bounds(x, z, zone_id=None):
        if zone_id is None or zone_id == 0:
            zone_id = services.current_zone().id
        return _terrain.is_position_in_bounds(x, z, zone_id)

    def is_position_in_street(position):
        return _terrain.is_position_in_markup_region(position)

except ImportError:

    def get_terrain_size(*args, **kwargs):
        pass

    def get_terrain_center(*args, **kwargs):
        pass

    def get_lot_level_height(*args, **kwargs):
        return 0

    def get_lot_level_height_and_surface_object(*args, **kwargs):
        pass

    def get_terrain_height(*args, **kwargs):
        return 0

    def is_position_in_bounds(*args, **kwargs):
        return False

    def is_position_in_street(*args, **kwargs):
        return False

    def get_snowmask_value(*args, **kwargs):
        return 0

    def get_water_depth(*args, **kwargs):
        return 0

    def get_water_depth_at_location(*args, **kwargs):
        return 0

    def adjust_locations_for_target_water_depth(*args, **kwargs):
        pass

    def adjust_locations_for_coastline(*args, **kwargs):
        pass

    def is_terrain_tag_at_position(*args, **kwargs):
        return False
