from debugvis import Contextfrom interactions.constraints import WaterDepthIntervalsfrom routing import SurfaceTypefrom sims.sim_info_types import Species, Agefrom sims4.color import Colorfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, Tunableimport servicesimport sims4.loglogger = sims4.log.Logger('Debugvis')
class LocatorVisualizer:
    LOCATOR_COLORS = TunableMapping(description="\n        Debug Locator Color mapping. This way we can map locator types\n        to colors. When the user types the |debugvis.locators.start\n        command, they will be able to see which locator belongs to it's\n        appropriate color, even if the catalog side changes.\n        ", key_type=Tunable(description='\n            The ID of the Locator from the Catalog under Locators.\n            ', tunable_type=int, default=8890), value_type=TunableEnumEntry(description='\n            The debug Color this Locator will appear in the world.\n            ', tunable_type=Color, default=Color.WHITE), key_name='Locator ID', value_name='Locator Color')

    def __init__(self, layer):
        self.layer = layer
        self._start()

    def _start(self):
        locator_manager = services.locator_manager()
        locator_manager.register_locators_changed_callback(self._draw_locators)
        self._draw_locators()

    def stop(self):
        locator_manager = services.locator_manager()
        locator_manager.unregister_locators_changed_callback(self._draw_locators)

    def _draw_locators(self):
        locator_manager = services.locator_manager()
        ocean = services.terrain_service.ocean_object()
        with Context(self.layer) as layer:
            for (obj_def_guid, locators) in locator_manager.items():
                point_color = LocatorVisualizer.LOCATOR_COLORS.get(obj_def_guid, Color.WHITE)
                for locator in locators:
                    layer.add_arrow_for_transform(locator.transform, length=locator.scale, color=point_color, altitude=0.1)
                    layer.set_color(Color.WHITE)
                    layer.add_text_world(locator.transform.translation, 'Locator: {}'.format(obj_def_guid))
            if ocean is not None:
                species = [Species.HUMAN, Species.DOG]
                age = [Age.TODDLER, Age.CHILD, Age.ADULT]
                interval = {WaterDepthIntervals.SWIM: Color.RED, WaterDepthIntervals.WADE: Color.YELLOW, WaterDepthIntervals.WET: Color.BLUE}
                for s in species:
                    for a in age:
                        for (i, c) in interval.items():
                            key = (s, a, i)
                            if key not in ocean._constraint_starts:
                                pass
                            else:
                                transforms = ocean._constraint_starts[(s, a, i)]
                                for transform in transforms:
                                    layer.add_circle(transform.translation, radius=0.1, num_points=6, color=c, altitude=0.1)
