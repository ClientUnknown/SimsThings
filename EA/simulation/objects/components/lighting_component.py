from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom build_buy import get_object_has_tagfrom objects.components import Component, componentmethodfrom objects.components.types import LIGHTING_COMPONENTfrom objects.object_enums import ResetReasonfrom sims.household_utilities.utility_types import Utilitiesfrom sims4.tuning.tunable import HasTunableFactory, TunableList, TunableReference, TunableEnumEntry, AutoFactoryInit, OptionalTunable, Tunable, TunableRangefrom singletons import DEFAULTfrom tag import Tagfrom vfx import PlayEffectimport distributor.opsimport servicesimport sims4.loglogger = sims4.log.Logger('Lighting')
class LightingComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=LIGHTING_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.LightingComponent):
    LIGHT_STATE_STAT = TunableReference(description="\n        The stat name used to manipulate the lights' on and off states that\n        control the effects they may or may not play\n        ", manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), deferred=True)
    MANUAL_LIGHT_TAG = TunableEnumEntry(description='\n        The tag that is used to mark lighting objects that do not have any\n        automatic behavior such as following auto-light interactions.\n        ', tunable_type=Tag, default=Tag.INVALID)
    NON_ELECTRIC_LIGHT_TAG = TunableEnumEntry(description='\n        The tag that is used to determine if the lights goes off when the power\n        is shut down.\n        ', tunable_type=Tag, default=Tag.INVALID)
    LIGHT_AUTOMATION_DIMMER_VALUE = -1
    LIGHT_DIMMER_STAT_MULTIPLIER = 100
    LIGHT_DIMMER_VALUE_OFF = 0.0
    LIGHT_DIMMER_VALUE_MAX_INTENSITY = 1.0
    FACTORY_TUNABLES = {'component_interactions': TunableList(description='\n            Each interaction in this list will be added to the owner of the\n            component.\n            ', tunable=TunableReference(manager=services.affordance_manager())), 'default_dimmer_value': TunableRange(description='\n            The default dimmer value for this light.\n            ', tunable_type=float, default=LIGHT_DIMMER_VALUE_MAX_INTENSITY, minimum=LIGHT_DIMMER_VALUE_OFF, maximum=LIGHT_DIMMER_VALUE_MAX_INTENSITY), 'material_state_on': OptionalTunable(description='\n            If enabled, specify the material state to apply when the light is\n            on.\n            ', tunable=Tunable(description='\n                The material state to apply when the light is on.\n                ', tunable_type=str, default='lightson')), 'material_state_off': OptionalTunable(description='\n            If enabled, specify the material state to apply when the light is\n            off.\n            ', tunable=Tunable(description='\n                The material state to apply when the light is off.\n                ', tunable_type=str, default='lightsoff')), 'visual_effect': OptionalTunable(description='\n            If enabled, specify the visual effect to apply when the light is on.\n            ', tunable=PlayEffect.TunableFactory())}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user_intensity_overrides = None
        self._light_dimmer = self.default_dimmer_value
        self._previous_light_dimmer = None
        self._owner_stat_tracker = self.owner.get_tracker(self.LIGHT_STATE_STAT)
        self._material_state_on = self.material_state_on
        self._material_state_off = self.material_state_off
        self._visual_effect = None
        self._pending_dimmer_value = None
        self._color = None
        self._previous_color = None
        if self.is_power_off():
            self.on_power_off()

    @distributor.fields.ComponentField(op=distributor.ops.SetLightDimmer)
    def light_dimmer(self):
        return self._light_dimmer

    _resend_lighting = light_dimmer.get_resend()

    @light_dimmer.setter
    def light_dimmer(self, value):
        if self.is_power_off():
            value = 0
        if value != self._light_dimmer:
            self.set_light_dimmer_value(value)

    @distributor.fields.ComponentField(op=distributor.ops.SetLightMaterialStates)
    def light_material_states(self):
        return (self._material_state_on, self._material_state_off)

    @light_material_states.setter
    def light_material_states(self, value):
        material_state_on = getattr(value, 'material_state_on')
        if material_state_on is not None:
            self._material_state_on = self.material_state_on if material_state_on is DEFAULT else material_state_on
        material_state_off = getattr(value, 'material_state_off')
        if material_state_off is not None:
            self._material_state_off = self.material_state_off if material_state_off is DEFAULT else material_state_off

    @distributor.fields.ComponentField(op=distributor.ops.SetLightColor)
    def light_color(self):
        return self._color

    _resend_color = light_color.get_resend()

    @componentmethod
    def get_light_dimmer_value(self):
        return self._light_dimmer

    @componentmethod
    def get_previous_light_dimmer_value(self):
        return self._previous_light_dimmer

    @componentmethod
    def get_overridden_dimmer_value(self, value):
        if value == self.LIGHT_AUTOMATION_DIMMER_VALUE:
            return self.LIGHT_AUTOMATION_DIMMER_VALUE
        if value == self.LIGHT_DIMMER_VALUE_OFF:
            return self.LIGHT_DIMMER_VALUE_OFF
        if self._user_intensity_overrides:
            value = self._user_intensity_overrides
        return sims4.math.clamp(self.LIGHT_DIMMER_VALUE_OFF, float(value), self.LIGHT_DIMMER_VALUE_MAX_INTENSITY)

    @componentmethod
    def set_light_dimmer_value(self, value, store_previous_value=False):
        if store_previous_value:
            self._previous_light_dimmer = self.get_light_dimmer_value()
        value = self.get_overridden_dimmer_value(value)
        self._light_dimmer = value
        self._update_visual_effect()
        stat = self._owner_stat_tracker.get_statistic(self.LIGHT_STATE_STAT)
        if stat is not None:
            self._owner_stat_tracker.set_value(self.LIGHT_STATE_STAT, value*self.LIGHT_DIMMER_STAT_MULTIPLIER)
        self._resend_lighting()

    def _update_visual_effect(self):
        if self.visual_effect is None:
            return
        if self._light_dimmer == 0:
            self._stop_visual_effect()
            return
        if self._light_dimmer == self.LIGHT_AUTOMATION_DIMMER_VALUE:
            auto_on_effect = True
        else:
            auto_on_effect = False
        if self._visual_effect is not None and self._visual_effect.auto_on_effect == auto_on_effect:
            return
        self._stop_visual_effect()
        self._visual_effect = self.visual_effect(self.owner, auto_on_effect=auto_on_effect)
        self._visual_effect.start()

    def _stop_visual_effect(self, immediate=False):
        if self._visual_effect is not None:
            self._visual_effect.stop(immediate=immediate)
            self._visual_effect = None

    @componentmethod
    def get_light_color(self):
        return self._color

    @componentmethod
    def get_previous_light_color(self):
        return self._previous_color

    @componentmethod
    def set_light_color(self, color, store_previous_value=False):
        if store_previous_value:
            self._previous_color = self._color
        self._color = color
        self._resend_color()

    @componentmethod
    def set_user_intensity_override(self, value):
        self._user_intensity_overrides = value
        self.set_light_dimmer_value(value)

    @componentmethod
    def set_automated(self):
        pass

    def is_power_off(self):
        household = services.owning_household_of_active_lot()
        if household is not None and not (services.utilities_manager(household.id).is_utility_active(Utilities.POWER) or get_object_has_tag(self.owner.definition.id, LightingComponent.NON_ELECTRIC_LIGHT_TAG)):
            return True
        return False

    def on_power_off(self, from_load=False):
        if not get_object_has_tag(self.owner.definition.id, LightingComponent.NON_ELECTRIC_LIGHT_TAG):
            if not from_load:
                self._pending_dimmer_value = self._light_dimmer
            self.set_light_dimmer_value(self.LIGHT_DIMMER_VALUE_OFF)

    def on_power_on(self):
        if self._pending_dimmer_value is not None:
            self._light_dimmer = self._pending_dimmer_value
            self._resend_lighting()
            self._pending_dimmer_value = None

    def component_super_affordances_gen(self, **kwargs):
        yield from self.component_interactions

    def component_interactable_gen(self):
        if self.component_interactions:
            yield self

    @componentmethod
    def get_user_intensity_overrides(self):
        if self._user_intensity_overrides is not None:
            return self._user_intensity_overrides
        return self.LIGHT_DIMMER_VALUE_MAX_INTENSITY

    def on_add(self):
        if self.owner.is_on_active_lot():
            self.set_light_dimmer_value(self._light_dimmer)
        else:
            self.set_light_dimmer_value(LightingComponent.LIGHT_AUTOMATION_DIMMER_VALUE)

    def on_finalize_load(self):
        if self.is_power_off():
            from_load = True if self._pending_dimmer_value else False
            self.on_power_off(from_load=from_load)
        else:
            self.on_power_on()

    def on_set_sold(self):
        self.on_power_off()

    def on_restock(self):
        self.on_power_on()

    def component_reset(self, reset_reason):
        if reset_reason == ResetReason.BEING_DESTROYED:
            self._stop_visual_effect(immediate=True)

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.LightingComponent
        lighting_save = persistable_data.Extensions[protocols.PersistableLightingComponent.persistable_data]
        lighting_save.dimmer_setting = self._light_dimmer
        if self._previous_light_dimmer is not None:
            lighting_save.previous_dimmer_setting = self._previous_light_dimmer
        if self._color is not None:
            lighting_save.color = self._color
        if self._previous_color is not None:
            lighting_save.previous_color = self._previous_color
        if self._pending_dimmer_value is not None:
            lighting_save.pending_dimmer_setting = self._pending_dimmer_value
        if self._user_intensity_overrides is not None:
            lighting_save.user_intensity = self._user_intensity_overrides
        persistence_master_message.data.extend([persistable_data])

    def load(self, lighting_component_message):
        lighting_component_data = lighting_component_message.Extensions[protocols.PersistableLightingComponent.persistable_data]
        if lighting_component_data.user_intensity:
            self._user_intensity_overrides = lighting_component_data.user_intensity
        self.set_light_dimmer_value(lighting_component_data.dimmer_setting)
        if lighting_component_data.previous_dimmer_setting:
            self._previous_light_dimmer = lighting_component_data.previous_dimmer_setting
        if lighting_component_data.color:
            self.set_light_color(lighting_component_data.color)
        if lighting_component_data.previous_color:
            self._previous_color = lighting_component_data.previous_color
        if lighting_component_data.pending_dimmer_setting:
            self._pending_dimmer_value = lighting_component_data.pending_dimmer_setting
