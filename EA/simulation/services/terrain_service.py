from objects.object_enums import ItemLocationfrom routing import SurfaceIdentifier, SurfaceTypefrom sims4.tuning.tunable import TunableReferencefrom world.ocean_tuning import OceanTuningimport servicesimport sims4.mathimport sims4.reloadimport sims4.service_managerwith sims4.reload.protected(globals()):
    _terrain_object = None
    _ocean_object = None
class TerrainService(sims4.service_manager.Service):
    TERRAIN_DEFINITION = TunableReference(description='\n        The definition used to instantiate the Terrain object.\n        ', manager=services.definition_manager(), class_restrictions='Terrain')
    OCEAN_DEFINITION = TunableReference(description='\n        The definition for the Ocean object.\n        ', manager=services.definition_manager(), class_restrictions='Ocean')

    def start(self):
        create_terrain_object()
        return True

    def on_zone_load(self):
        global _ocean_object
        if _ocean_object is None:
            beach_locator_def = OceanTuning.get_beach_locator_definition()
            if beach_locator_def is None:
                return
            locator_manager = services.locator_manager()
            locators = locator_manager.get(beach_locator_def.id)
            if not locators:
                return

            def move_ocean(ocean):
                zone = services.current_zone()
                terrain_center = zone.lot.center
                location = sims4.math.Location(sims4.math.Transform(translation=terrain_center, orientation=sims4.math.Quaternion.IDENTITY()), routing_surface=SurfaceIdentifier(zone.id, 0, SurfaceType.SURFACETYPE_WORLD))
                ocean.location = location

            from objects.system import create_object
            _ocean_object = create_object(TerrainService.OCEAN_DEFINITION, post_add=move_ocean, loc_type=ItemLocation.FROM_OPEN_STREET)

    def on_zone_unload(self):
        global _ocean_object
        if _ocean_object is not None:
            _ocean_object.destroy()
            _ocean_object = None

    def stop(self):
        destroy_terrain_object()

def terrain_object():
    if _terrain_object is None:
        raise RuntimeError('Attempting to access the terrain object before it is created.')
    return _terrain_object

def ocean_object():
    return _ocean_object

def create_terrain_object():
    global _terrain_object
    if _terrain_object is None:
        from objects.system import create_script_object
        _terrain_object = create_script_object(TerrainService.TERRAIN_DEFINITION)

def destroy_terrain_object():
    global _terrain_object
    _terrain_object = None
