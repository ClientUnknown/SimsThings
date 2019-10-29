from _weakrefset import WeakSetfrom build_buy import get_object_has_tagfrom interactions import ParticipantTypefrom interactions.liability import Liabilityfrom objects.components.lighting_component import LightingComponentfrom sims4.tuning.geometric import TunableDistanceSquaredfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableEnumEntryimport objects.components.typesimport services
class LightingLiability(Liability, HasTunableFactory, AutoFactoryInit):
    LIABILITY_TOKEN = 'LightingLiability'
    FACTORY_TUNABLES = {'radius_squared': TunableDistanceSquared(description='\n            The distance away from the specified participant that lights will\n            be turned off.\n            ', default=1, display_name='Radius'), 'participant': TunableEnumEntry(description='\n            The participant of the interaction that we will be used as the\n            center of the radius to turn lights off.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor)}

    def __init__(self, interaction, **kwargs):
        super().__init__(**kwargs)
        self._interaction = interaction
        self._lights = WeakSet()
        self._automated_lights = WeakSet()

    def on_run(self):
        if self._lights:
            return
        participant = self._interaction.get_participant(self.participant)
        position = participant.position
        for obj in services.object_manager().get_all_objects_with_component_gen(objects.components.types.LIGHTING_COMPONENT):
            if get_object_has_tag(obj.definition.id, LightingComponent.MANUAL_LIGHT_TAG):
                pass
            else:
                distance_from_pos = obj.position - position
                if distance_from_pos.magnitude_squared() > self.radius_squared:
                    pass
                else:
                    if obj.get_light_dimmer_value() == LightingComponent.LIGHT_AUTOMATION_DIMMER_VALUE:
                        self._automated_lights.add(obj)
                    else:
                        self._lights.add(obj)
                    obj.set_light_dimmer_value(LightingComponent.LIGHT_DIMMER_VALUE_OFF)

    def release(self):
        for obj in self._lights:
            obj.set_light_dimmer_value(LightingComponent.LIGHT_DIMMER_VALUE_MAX_INTENSITY)
        self._lights.clear()
        for obj in self._automated_lights:
            obj.set_light_dimmer_value(LightingComponent.LIGHT_AUTOMATION_DIMMER_VALUE)
        self._automated_lights.clear()
