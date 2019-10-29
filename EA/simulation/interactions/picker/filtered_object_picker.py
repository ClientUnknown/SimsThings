from interactions.base.picker_interaction import ObjectPickerInteractionfrom interactions.utils.object_definition_or_tags import ObjectDefinitonsOrTagsVariantfrom sims4.tuning.tunable import TunableVariantfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodimport servicesimport sims4.loglogger = sims4.log.Logger('FilteredObjectPickerInteraction', default_owner='jdimailig')
class FilteredObjectPickerInteraction(ObjectPickerInteraction):
    ON_LOT_ONLY = 'on_lot'
    OFF_LOT_ONLY = 'off_lot'
    ANYWHERE = 'anywhere'
    INSTANCE_TUNABLES = {'object_filter': ObjectDefinitonsOrTagsVariant(description='\n            Filter to use to find an object.\n            ', tuning_group=GroupNames.PICKERTUNING), 'on_off_lot_requirement': TunableVariant(description='\n            Whether to accept objects on the active lot.\n            ', default=ON_LOT_ONLY, locked_args={ANYWHERE: ANYWHERE, OFF_LOT_ONLY: OFF_LOT_ONLY, ON_LOT_ONLY: ON_LOT_ONLY}, tuning_group=GroupNames.PICKERTUNING)}

    @flexmethod
    def _get_objects_gen(cls, inst, target, context, **kwargs):
        object_manager = services.object_manager()
        if cls.on_off_lot_requirement == cls.ANYWHERE:
            yield from object_manager.get_objects_with_filter_gen(cls.object_filter)
        elif cls.on_off_lot_requirement == cls.ON_LOT_ONLY:
            for obj in object_manager.get_objects_with_filter_gen(cls.object_filter):
                if obj.is_on_active_lot():
                    yield obj
        else:
            for obj in object_manager.get_objects_with_filter_gen(cls.object_filter):
                if not obj.is_on_active_lot():
                    yield obj
