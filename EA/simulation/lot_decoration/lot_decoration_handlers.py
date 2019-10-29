from sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemaimport servicesimport sims4.resourcesdecoratable_lots_schema = GsiGridSchema(label='Lot Decorations')decoratable_lots_schema.add_field('zone_id', label='Zone Id', width=1)decoratable_lots_schema.add_field('world_id', label='World Id', width=1)decoratable_lots_schema.add_field('deco_type_id', label='Decoration Type Id', width=1)decoratable_lots_schema.add_field('owned_by_active_household', label='Owned By Active HH?', width=1)decoratable_lots_schema.add_field('preset', label='Preset Used', width=3)decoratable_lots_schema.add_field('customized', label='Customized', width=1)decoratable_lots_schema.add_field('current_lot', label='Current Lot', width=1)
def get_presets():
    instance_manager = services.get_instance_manager(sims4.resources.Types.LOT_DECORATION_PRESET)
    if instance_manager.all_instances_loaded:
        return [cls.__name__ for cls in instance_manager.types.values()]
    return []
with decoratable_lots_schema.add_view_cheat('lot_decorations.apply_preset_to_neighbors', label='Apply Preset to Neighbors') as apply_neighborhood_decorations:
    apply_neighborhood_decorations.add_token_param('preset', dynamic_token_fn=get_presets)with decoratable_lots_schema.add_view_cheat('lot_decorations.apply_preset_to_zone', label='Apply Preset to Zone') as apply_zone_decorations:
    apply_zone_decorations.add_token_param('preset', dynamic_token_fn=get_presets)
    apply_zone_decorations.add_token_param('zone_id')with decoratable_lots_schema.add_has_many('Decorations', GsiGridSchema) as sub_schema:
    sub_schema.add_field('deco_location', label='Location')
    sub_schema.add_field('decoration', label='Decoration')
@GsiHandler('decoratable_lots_view', decoratable_lots_schema)
def generate_decoratable_lots_view():
    lot_decoration_service = services.lot_decoration_service()
    if lot_decoration_service is None:
        return []
    return lot_decoration_service.get_lot_decorations_gsi_data()
