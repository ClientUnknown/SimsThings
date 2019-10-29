from build_buy import get_object_has_tag, get_object_all_tags, get_block_idfrom objects.components.lighting_component import LightingComponentfrom objects.components.types import LIGHTING_COMPONENTfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableSet, TunableEnumEntry, TunableVariant, TunableRange, TunableColor, Tunablefrom tag import Tagimport objects.components.typesimport servicesimport sims4.loglogger = sims4.log.Logger('Lighting')
def all_lights_gen(target):
    plex_service = services.get_plex_service()
    for obj in services.object_manager().get_all_objects_with_component_gen(LIGHTING_COMPONENT):
        if get_object_has_tag(obj.definition.id, LightingComponent.MANUAL_LIGHT_TAG):
            pass
        elif not plex_service.is_active_zone_a_plex() or plex_service.get_plex_zone_at_position(obj.position, obj.level) is None:
            pass
        else:
            yield obj

def lights_in_target_room_gen(target):
    zone_id = services.current_zone_id()
    target_block_id = get_block_id(zone_id, target.position, target.level)
    for obj in services.object_manager().get_all_objects_with_component_gen(LIGHTING_COMPONENT):
        if get_object_has_tag(obj.definition.id, LightingComponent.MANUAL_LIGHT_TAG):
            pass
        else:
            obj_block_id = get_block_id(zone_id, obj.position, obj.level)
            if obj_block_id != target_block_id:
                pass
            else:
                yield obj

class _LightTargetInteraction(HasTunableSingletonFactory):

    @property
    def is_multi_light(self):
        return False

    def get_light_target_gen(self, interaction):
        yield interaction.target

class _LightTargetAll(HasTunableSingletonFactory):

    @property
    def is_multi_light(self):
        return True

    def get_light_target_gen(self, interaction):
        yield from all_lights_gen(interaction.target)

class _LightTargetRoom(HasTunableSingletonFactory):

    @property
    def is_multi_light(self):
        return True

    def get_light_target_gen(self, interaction):
        target = interaction.target
        yield from lights_in_target_room_gen(target)

class _LightTargetFromTags(AutoFactoryInit, HasTunableSingletonFactory):
    FACTORY_TUNABLES = {'tags': TunableSet(description='\n            An object with any tag in this set is a potential target of this\n            interaction, provided it has a lighting component.\n            ', tunable=TunableEnumEntry(description='\n                A tag.\n                ', tunable_type=Tag, default=Tag.INVALID, pack_safe=True))}

    @property
    def is_multi_light(self):
        return True

    def get_light_target_gen(self, interaction):
        for obj in services.object_manager().get_all_objects_with_component_gen(objects.components.types.LIGHTING_COMPONENT):
            target_object_tags = set(get_object_all_tags(obj.definition.id))
            if self.tags & target_object_tags:
                yield obj

class TunableLightTargetVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, this_light=_LightTargetInteraction.TunableFactory(), all_lights=_LightTargetAll.TunableFactory(), room_lights=_LightTargetRoom.TunableFactory(), specific_lights=_LightTargetFromTags.TunableFactory(), default='this_light', **kwargs)

class _DimmerValueFromPreviousSetting(HasTunableSingletonFactory):

    def get_dimmer_value(self, obj):
        previous_light_dimmer = obj.get_previous_light_dimmer_value()
        if previous_light_dimmer is None:
            logger.warn('Previous light dimmer for {} is None, return current light dimmer instead.', obj, owner='mkartika')
            return obj.get_light_dimmer_value()
        return previous_light_dimmer

    def is_storing_previous_setting(self):
        return False

class _DimmerValueFromClient(HasTunableSingletonFactory):

    def get_dimmer_value(self, obj):
        return LightingComponent.LIGHT_AUTOMATION_DIMMER_VALUE

    def is_storing_previous_setting(self):
        return False

class _DimmerValueSpecified(AutoFactoryInit, HasTunableSingletonFactory):
    FACTORY_TUNABLES = {'dimmer_value': TunableRange(description='\n            This value should be a float between 0.0 and 1.0. A value of\n            0.0 is off and a value of 1.0 is completely on.\n            ', minimum=0, maximum=1, tunable_type=float, default=0), 'store_previous_setting': Tunable(description='\n            If enabled, current dimmer value will be stored in \n            previous setting before changing it to the new value..\n            ', tunable_type=bool, default=False)}

    def get_dimmer_value(self, obj):
        return self.dimmer_value

    def is_storing_previous_setting(self):
        return self.store_previous_setting

class TunableDimmerValueVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, use_previous_setting=_DimmerValueFromPreviousSetting.TunableFactory(), automated_by_client=_DimmerValueFromClient.TunableFactory(), specify_dimmer_value=_DimmerValueSpecified.TunableFactory(), default='automated_by_client', **kwargs)

class _LightColorFromPreviousSetting(HasTunableSingletonFactory):

    def get_light_color(self, obj):
        return obj.get_previous_light_color()

    def is_storing_previous_setting(self):
        return False

class _LightColorNoChange(HasTunableSingletonFactory):

    def get_light_color(self, obj):
        return obj.get_light_color()

    def is_storing_previous_setting(self):
        return False

class _LightColorSpecified(AutoFactoryInit, HasTunableSingletonFactory):
    FACTORY_TUNABLES = {'light_color': TunableColor(description='\n            The color of the lights.\n            '), 'store_previous_setting': Tunable(description='\n            If enabled, current color will be stored in \n            previous setting before changing it to the new color.\n            ', tunable_type=bool, default=False)}

    def get_light_color(self, obj):
        return self.light_color

    def is_storing_previous_setting(self):
        return self.store_previous_setting

class TunableLightColorVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, use_previous_setting=_LightColorFromPreviousSetting.TunableFactory(), do_not_change_light_color=_LightColorNoChange.TunableFactory(), specify_light_color=_LightColorSpecified.TunableFactory(), default='do_not_change_light_color', **kwargs)

class LightingHelper(AutoFactoryInit, HasTunableSingletonFactory):
    FACTORY_TUNABLES = {'light_target': TunableLightTargetVariant(description='\n            Define the set of lights that this interaction is applied to.\n            '), 'dimmer_value': TunableDimmerValueVariant(description='\n            Specify the intensity to be applied to the light.\n            '), 'light_color': TunableLightColorVariant(description='\n            Specify the color to be applied to the light.\n            ')}

    def execute_lighting_helper(self, interaction):
        for light_obj in self.light_target.get_light_target_gen(interaction):
            dimmer_value = self.dimmer_value.get_dimmer_value(light_obj)
            store_dimmer_prev_setting = self.dimmer_value.is_storing_previous_setting()
            light_obj.set_light_dimmer_value(dimmer_value, store_previous_value=store_dimmer_prev_setting)
            light_color = self.light_color.get_light_color(light_obj)
            store_color_prev_setting = self.light_color.is_storing_previous_setting()
            light_obj.set_light_color(light_color, store_previous_value=store_color_prev_setting)
