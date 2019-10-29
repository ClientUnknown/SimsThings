from _collections import defaultdictimport itertoolsimport refrom gsi_handlers.gameplay_archiver import GameplayArchiverfrom gsi_handlers.gsi_utils import parse_filter_to_listfrom objects.game_object import GameObjectfrom routing.portals.portal_tuning import PortalFlagsfrom server.live_drag_tuning import LiveDragPermissionfrom sims4.common import Pack, get_pack_enumfrom sims4.gsi.dispatcher import GsiHandler, add_cheat_schemafrom sims4.gsi.schema import GsiGridSchema, GSIGlobalCheatSchema, GsiFieldVisualizersimport build_buyimport gsi_handlers.gsi_utilsimport objects.components.typesimport servicesimport sims4import tagglobal_object_cheats_schema = GSIGlobalCheatSchema()global_object_cheats_schema.add_cheat('objects.clear_lot', label='Clear Lot')add_cheat_schema('global_object_cheats', global_object_cheats_schema)object_manager_schema = GsiGridSchema(label='Object Manager')object_manager_schema.add_field('mgr', label='Manager', width=1, hidden=True)object_manager_schema.add_field('objId', label='Object Id', width=3, unique_field=True)object_manager_schema.add_field('classStr', label='Class', width=3)object_manager_schema.add_field('definitionStr', label='Definition', width=3)object_manager_schema.add_field('modelStr', label='Model', width=3)object_manager_schema.add_field('locX', label='X', width=1)object_manager_schema.add_field('locY', label='Y', width=1)object_manager_schema.add_field('locZ', label='Z', width=1)object_manager_schema.add_field('on_active_lot', label='On Active Lot', width=1, hidden=True)object_manager_schema.add_field('current_value', label='Value', width=1)object_manager_schema.add_field('isSurface', label='Surface', width=1)object_manager_schema.add_field('parent', label='Parent', width=2)object_manager_schema.add_field('bb_parent', label='BB_Parent', width=2)object_manager_schema.add_field('lockouts', label='Lockouts', width=2)object_manager_schema.add_field('transient', label='Transient', width=1, hidden=True)object_manager_schema.add_field('is_interactable', label='Interactable', width=1, hidden=True)object_manager_schema.add_field('footprint', label='Footprint', width=1, hidden=True)object_manager_schema.add_field('inventory_owner_id', label='inventory owner id', width=2, hidden=True)object_manager_schema.add_filter('on_active_lot')object_manager_schema.add_filter('open_street')object_manager_schema.add_filter('inventory')object_manager_schema.add_filter('game_objects')object_manager_schema.add_filter('prototype_objects')object_manager_schema.add_filter('sim_objects')with object_manager_schema.add_view_cheat('objects.destroy', label='Delete') as cheat:
    cheat.add_token_param('objId')with object_manager_schema.add_view_cheat('objects.reset', label='Reset') as cheat:
    cheat.add_token_param('objId')with object_manager_schema.add_view_cheat('objects.focus_camera_on_object', label='Focus On Selected Object') as cheat:
    cheat.add_token_param('objId')with object_manager_schema.add_has_many('commodities', GsiGridSchema) as sub_schema:
    sub_schema.add_field('commodity', label='Commodity')
    sub_schema.add_field('value', label='value')
    sub_schema.add_field('convergence_value', label='convergence value')
    sub_schema.add_field('decay_rate', label='decay')
    sub_schema.add_field('change_rate', label='change rate')with object_manager_schema.add_has_many('postures', GsiGridSchema) as sub_schema:
    sub_schema.add_field('interactionName', label='Interaction Name')
    sub_schema.add_field('providedPosture', label='Provided Posture')with object_manager_schema.add_has_many('states', GsiGridSchema) as sub_schema:
    sub_schema.add_field('state_type', label='State')
    sub_schema.add_field('state_value', label='Value')with object_manager_schema.add_has_many('reservations', GsiGridSchema) as sub_schema:
    sub_schema.add_field('reservation_sim', label='Owner', width=1)
    sub_schema.add_field('reservation_target', label='Target', width=1)
    sub_schema.add_field('reservation_type', label='Type', width=1)
    sub_schema.add_field('reservation_interaction', label='Interaction', width=1)with object_manager_schema.add_has_many('parts', GsiGridSchema) as sub_schema:
    sub_schema.add_field('part_group_index', label='Part Group Index', width=0.5)
    sub_schema.add_field('part_suffix', label='Part Suffix', width=0.5)
    sub_schema.add_field('subroot_index', label='SubRoot', width=0.5)
    sub_schema.add_field('is_mirrored', label='Mirrored', width=0.5)with object_manager_schema.add_has_many('slots', GsiGridSchema) as sub_schema:
    sub_schema.add_field('slot', label='Slot')
    sub_schema.add_field('children', label='Children')with object_manager_schema.add_has_many('inventory', GsiGridSchema) as sub_schema:
    sub_schema.add_field('objId', label='Object Id', width=2, unique_field=True)
    sub_schema.add_field('classStr', label='Class', width=2)
    sub_schema.add_field('stack_count', label='Stack Count', width=1, type=GsiFieldVisualizers.INT)
    sub_schema.add_field('stack_sort_order', label='Stack Sort Order', width=1, type=GsiFieldVisualizers.INT)
    sub_schema.add_field('hidden', label='In Hidden', width=1)with object_manager_schema.add_has_many('additional_data', GsiGridSchema) as sub_schema:
    sub_schema.add_field('dataId', label='Data', unique_field=True)
    sub_schema.add_field('dataValue', label='Value')with object_manager_schema.add_has_many('object_relationships', GsiGridSchema) as sub_schema:
    sub_schema.add_field('relationshipNumber', label='Relationship Number', width=0.5)
    sub_schema.add_field('simValue', label='Sim', width=0.25, unique_field=True)
    sub_schema.add_field('relationshipValue', label='Relationship Value', width=0.25)
    sub_schema.add_field('relationshipStatInfo', label='Relationship Stat Info')with object_manager_schema.add_has_many('portal_lock', GsiGridSchema) as sub_schema:
    sub_schema.add_field('lock_type', label='Lock Type', width=0.5)
    sub_schema.add_field('lock_priority', label='Lock Priority', width=0.25)
    sub_schema.add_field('lock_side', label='Lock Side', width=0.25)
    sub_schema.add_field('should_persist', label='Should Persist', width=0.25)
    sub_schema.add_field('exceptions', label='Exceptions')with object_manager_schema.add_has_many('awareness', GsiGridSchema) as sub_schema:
    sub_schema.add_field('awareness_role', label='Role', width=0.25)
    sub_schema.add_field('awareness_channel', label='Channel', width=0.25)
    sub_schema.add_field('awareness_data', label='Data', width=2)with object_manager_schema.add_has_many('component', GsiGridSchema) as sub_schema:
    sub_schema.add_field('component_name', label='Name', width=0.25)with object_manager_schema.add_has_many('live_drag', GsiGridSchema) as sub_schema:
    sub_schema.add_field('live_drag_data_name', label='Data', unique_field=True)
    sub_schema.add_field('live_drag_data_value', label='Value')with object_manager_schema.add_has_many('ownership', GsiGridSchema) as sub_schema:
    sub_schema.add_field('ownership_household_owner', label='Household Owner')
    sub_schema.add_field('ownership_sim_owner', label='Sim Owner')
    sub_schema.add_field('ownership_crafter_sim', label='Crafter Sim')
    sub_schema.add_field('ownership_preference_sim', label='Preference Sims')with object_manager_schema.add_has_many('walkstyles', GsiGridSchema, label='Walkstyles') as sub_schema:
    sub_schema.add_field('walkstyle_priority', label='Priority', width=0.5)
    sub_schema.add_field('walkstyle_type', label='Style', width=0.75)
    sub_schema.add_field('walkstyle_short', label='Short Replacement', width=0.75)
    sub_schema.add_field('walkstyle_combo_replacement', label='Combo replacement', width=1)
    sub_schema.add_field('walkstyle_is_current', label='Is Current', width=0.25)
    sub_schema.add_field('walkstyle_is_default', label='Is Default', width=0.25)with object_manager_schema.add_has_many('portals', GsiGridSchema, label='Routable Portal Flags') as sub_schema:
    sub_schema.add_field('portal_flag', label='Flags')