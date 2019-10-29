from protocolbuffers import InteractionOps_pb2 as interaction_protocol, Sims_pb2 as protocols, Consts_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom clubs import club_tuningfrom clubs.club_enums import ClubRuleEncouragementStatusfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import create_icon_info_msg, IconInfoDatafrom distributor.system import Distributorfrom event_testing.resolver import SingleSimResolver, SingleActorAndObjectResolver, InteractionResolverfrom gsi_handlers import posture_graph_handlersfrom interactions.choices import ChoiceMenu, toggle_show_interaction_failure_reasonfrom interactions.context import InteractionContextfrom interactions.priority import Priorityfrom interactions.utils.enum_utils import FlagFieldfrom objects import ALL_HIDDEN_REASONSfrom objects.pools import pool_utilsfrom postures import posture_graphfrom server.config_service import ContentModesfrom server.pick_info import PickInfo, PickType, PICK_USE_TERRAIN_OBJECT, PICK_NEVER_USE_POOLfrom server_commands.argument_helpers import get_optional_target, OptionalTargetParam, RequiredTargetParam, TunableInstanceParamfrom sims.phone_tuning import PhoneTuningfrom sims4.commands import Outputfrom sims4.localization import TunableLocalizedStringFactory, create_tokensfrom sims4.tuning.tunable import TunableResourceKeyfrom terrain import get_water_depthfrom world.ocean_tuning import OceanTuningimport autonomy.content_setsimport build_buyimport enumimport interactions.social.social_mixer_interactionimport interactions.utils.outcomeimport objects.terrainimport postures.transition_sequenceimport routingimport servicesimport sims4.commandsimport sims4.logimport sims4.reloadimport telemetry_helperlogger = sims4.log.Logger('Interactions')TELEMETRY_GROUP_PIE_MENU = 'PIEM'TELEMETRY_HOOK_CREATE_PIE_MENU = 'PIEM'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_PIE_MENU)with sims4.reload.protected(globals()):
    _show_interaction_tuning_name = False
    _show_front_page_score = False
class InteractionCommandsTuning:
    INTERACTION_TUNING_NAME = TunableLocalizedStringFactory(description='\n        The localized string used to create interaction choice names and\n        display the tuning name next to it.\n        ')
    INTERACTION_FRONT_PAGE_SCORING = TunableLocalizedStringFactory(description='\n        The localized string used to create interaction choice names and\n        front page scoring.\n        ')

def _active_sim(client):
    if client:
        return client.active_sim

@sims4.commands.Command('interactions.posture_graph_build', 'posture_graph.build')
def build_posture_graph(_connection=None):
    services.current_zone().posture_graph_service.rebuild()

@sims4.commands.Command('interactions.posture_graph_export', 'posture_graph.export')
def export_posture_graph(_connection=None):
    services.current_zone().posture_graph_service.export()

@sims4.commands.Command('interactions.posture_graph_gsi_min_progress', 'posture_graph.gsi_min_progress')
def posture_graph_min_gsi_progress(min_progress:int=0, _connection=None):
    posture_graph_handlers.gsi_min_progress = min_progress

@sims4.commands.Command('interactions.show_interaction_tuning_name', command_type=sims4.commands.CommandType.DebugOnly)
def show_interaction_tuning_name(enable:bool=None, _connection=None):
    global _show_interaction_tuning_name
    if enable is None:
        enable = not _show_interaction_tuning_name
    _show_interaction_tuning_name = enable

@sims4.commands.Command('interactions.show_front_page_score', command_type=sims4.commands.CommandType.DebugOnly)
def show_front_page_score(enable:bool=None, _connection=None):
    global _show_front_page_score
    if enable is None:
        enable = not _show_front_page_score
    _show_front_page_score = enable
    sims4.commands.output('show_front_page_score: {}.'.format(_show_front_page_score), _connection)

@sims4.commands.Command('interactions.show_failure_reason')
def show_interaction_failure_reason(enable:bool=None, _connection=None):
    toggle_show_interaction_failure_reason(enable=enable)

@sims4.commands.Command('interactions.has_choices', command_type=sims4.commands.CommandType.Live)
def has_choices(target_id:int=None, pick_type:PickType=PickType.PICK_TERRAIN, x:float=0.0, y:float=0.0, z:float=0.0, lot_id:int=0, level:int=0, control:int=0, alt:int=0, shift:int=0, reference_id:int=0, is_routable:bool=True, _connection=None):
    if target_id is None:
        return
    zone = services.current_zone()
    client = services.client_manager().get(_connection)
    if client is None:
        return
    sim = _active_sim(client)
    shift_held = bool(shift)
    if shift_held:
        cheat_service = services.get_cheat_service()
        if False or cheat_service.cheats_enabled:
            _send_interactable_message(client, target_id, True, interactable_flags=interaction_protocol.Interactable.INTERACTABLE)
        else:
            _send_interactable_message(client, target_id, False)
        return
    position = sims4.math.Vector3(x, y, z)
    pick_target = zone.find_object(target_id)
    (pick_target, pick_type, potential_targets) = _get_targets_from_pick(sim, pick_target, pick_type, position, level, zone.id, lot_id, is_routable, preferred_objects=set())
    is_interactable = False
    if pick_target is not None:
        tutorial_service = services.get_tutorial_service()
        for (potential_target, routing_surface) in potential_targets:
            pick = PickInfo(pick_type=pick_type, target=potential_target, location=position, routing_surface=routing_surface, lot_id=lot_id, level=level, alt=bool(alt), control=bool(control), shift=shift_held)
            context = client.create_interaction_context(sim, pick=pick)
            for aop in potential_target.potential_interactions(context):
                if tutorial_service is not None and not tutorial_service.is_affordance_visible(aop.affordance):
                    pass
                else:
                    result = ChoiceMenu.is_valid_aop(aop, context, user_pick_target=potential_target)
                    if result or not result.tooltip:
                        pass
                    else:
                        is_interactable = aop.affordance.allow_user_directed
                        if not is_interactable:
                            is_interactable = aop.affordance.has_pie_menu_sub_interactions(aop.target, context, **aop.interaction_parameters)
                        if is_interactable:
                            break
            if sim is not None:
                for si in sim.si_state:
                    potential_mixer_targets = si.get_potential_mixer_targets()
                    for potential_mixer_target in potential_mixer_targets:
                        if potential_target is potential_mixer_target:
                            break
                        if potential_mixer_target.is_part and potential_mixer_target.part_owner is potential_target:
                            break
                    if autonomy.content_sets.any_content_set_available(sim, si.super_affordance, si, context, potential_targets=(potential_target,), include_failed_aops_with_tooltip=True):
                        is_interactable = True
                        break
    interactable_flags = _get_interactable_flags(pick_target, is_interactable)
    _send_interactable_message(client, target_id, is_interactable, True, interactable_flags=interactable_flags)

def _send_interactable_message(client, target_id, is_interactable, immediate=False, interactable_flags=0):
    msg = interaction_protocol.Interactable()
    msg.object_id = target_id
    msg.is_interactable = is_interactable
    msg.interactable_flags = interactable_flags
    distributor = Distributor.instance()
    distributor.add_event(Consts_pb2.MSG_OBJECT_IS_INTERACTABLE, msg, immediate)

def _get_interactable_flags(target, is_interactable):
    if target is None:
        return 0
    if is_interactable:
        interactable_flag_field = FlagField(interaction_protocol.Interactable.INTERACTABLE)
    else:
        interactable_flag_field = FlagField()
    target.modify_interactable_flags(interactable_flag_field)
    return interactable_flag_field.flags

class PieMenuActions(enum.Int, export=False):
    SHOW_PIE_MENU = 0
    SHOW_DEBUG_PIE_MENU = 1
    INTERACTION_QUEUE_FULL_TOOLTIP = 2
    INTERACTION_QUEUE_FULL_STR = TunableLocalizedStringFactory(description="\n        Tooltip string shown to the user instead of a pie menu when the Sim's queue\n        is full of interactions.\n        ")
    POSTURE_INCOMPATIBLE_ICON = TunableResourceKey(description='\n        Icon to be displayed when pie menu option is not compatible with\n        current posture of the sim.\n        ', resource_types=sims4.resources.CompoundTypes.IMAGE)

def should_generate_pie_menu(client, sim, shift_held):
    can_queue_interactions = sim is None or (sim.queue is None or sim.queue.can_queue_visible_interaction())
    if shift_held:
        cheat_service = services.get_cheat_service()
        if False or cheat_service.cheats_enabled:
            return PieMenuActions.SHOW_DEBUG_PIE_MENU
        if can_queue_interactions:
            return PieMenuActions.SHOW_PIE_MENU
        return PieMenuActions.INTERACTION_QUEUE_FULL_TOOLTIP
    elif can_queue_interactions:
        return PieMenuActions.SHOW_PIE_MENU
    else:
        return PieMenuActions.INTERACTION_QUEUE_FULL_TOOLTIP

def _get_targets_from_pick(sim, pick_target, pick_type:PickType, position, level:int, zone_id:int, lot_id:int, is_routable:bool, *, preferred_objects):
    potential_targets = []
    pool_block_id = 0
    if pick_type not in PICK_NEVER_USE_POOL and build_buy.is_location_pool(zone_id, position, level):
        routing_surface = routing.SurfaceIdentifier(zone_id, level, routing.SurfaceType.SURFACETYPE_POOL)
        pool_block_id = build_buy.get_block_id(sim.zone_id, position, level - 1)
    else:
        routing_surface = routing.SurfaceIdentifier(zone_id, level, routing.SurfaceType.SURFACETYPE_WORLD)
    if pick_type in PICK_USE_TERRAIN_OBJECT:
        location = sims4.math.Location(sims4.math.Transform(position), routing_surface)
        terrain_point = objects.terrain.TerrainPoint(location)
        pick_target = terrain_point
        water_height = get_water_depth(position.x, position.z, level)
        if lot_id and lot_id != services.active_lot_id():
            pick_type = PickType.PICK_TERRAIN
            potential_targets.append((pick_target, routing_surface))
        elif pool_block_id:
            pool = pool_utils.get_pool_by_block_id(pool_block_id)
            if pool is not None:
                pool_point = objects.terrain.PoolPoint(location, pool)
                pick_target = pool_point
                potential_targets.append((pool_point, routing_surface))
        elif water_height > 0:
            if services.terrain_service.ocean_object() is not None:
                if not is_routable:
                    return (None, None, ())
                wading_interval = OceanTuning.get_actor_wading_interval(sim)
                if wading_interval is not None and water_height > wading_interval.upper_bound:
                    ocean_surface = routing.SurfaceIdentifier(zone_id, level, routing.SurfaceType.SURFACETYPE_POOL)
                    ocean_location = location.clone(routing_surface=ocean_surface)
                    ocean_point = objects.terrain.OceanPoint(ocean_location)
                    potential_targets.append((ocean_point, ocean_surface))
                    pick_target = ocean_point
                else:
                    potential_targets.append((terrain_point, routing_surface))
            else:
                water_terrain_object_cache = services.object_manager().water_terrain_object_cache
                nearest_obj = water_terrain_object_cache.get_nearest_object(position)
                if nearest_obj is not None:
                    pick_target = nearest_obj
                    potential_targets.append((pick_target, pick_target.routing_surface))
        else:
            potential_targets.append((terrain_point, routing_surface))
    else:
        if lot_id and lot_id != services.active_lot_id():
            location = sims4.math.Location(sims4.math.Transform(position), routing_surface)
            pick_target = objects.terrain.TerrainPoint(location)
            pick_type = PickType.PICK_TERRAIN
            potential_targets.append((pick_target, routing_surface))
        elif pick_target is not None and pick_target.provided_routing_surface is not None and not pick_target.is_routing_surface_overlapped_at_position(position):
            potential_targets.append((pick_target, routing_surface))
            new_routing_surface = pick_target.provided_routing_surface
            location = sims4.math.Location(sims4.math.Transform(position), new_routing_surface)
            if sim is not None and (posture_graph.is_object_mobile_posture_compatible(pick_target) or routing.test_connectivity_math_locations(sim.location, location, sim.routing_context)):
                pick_target = objects.terrain.TerrainPoint(location)
                potential_targets.append((pick_target, new_routing_surface))
        else:
            preferred_objects.add(pick_target)
            potential_targets.append((pick_target, routing_surface))
        if pick_target is None:
            return (None, None, ())
        if pick_target.provides_terrain_interactions:
            location = sims4.math.Location(sims4.math.Transform(position), routing_surface)
            terrain_target = objects.terrain.TerrainPoint(location)
            potential_targets.append((terrain_target, routing_surface))
        if pick_target.provides_ocean_interactions:
            location = sims4.math.Location(sims4.math.Transform(position), routing_surface)
            ocean_surface = routing.SurfaceIdentifier(zone_id, level, routing.SurfaceType.SURFACETYPE_POOL)
            ocean_location = location.clone(routing_surface=ocean_surface)
            ocean_point = objects.terrain.OceanPoint(ocean_location)
            potential_targets.append((ocean_point, ocean_surface))
    return (pick_target, pick_type, tuple(potential_targets))

@sims4.commands.Command('interactions.choices', command_type=sims4.commands.CommandType.Live)
def generate_choices(target_id:int=None, pick_type:PickType=PickType.PICK_TERRAIN, x:float=0.0, y:float=0.0, z:float=0.0, lot_id:int=0, level:int=0, control:int=0, alt:int=0, shift:int=0, reference_id:int=0, referred_object_id:int=0, preferred_object_id:int=0, is_routable:bool=True, _connection=None):
    if alt or control:
        return 0
    if target_id is None:
        return 0
    zone = services.current_zone()
    client = services.client_manager().get(_connection)
    sim = _active_sim(client)
    shift_held = bool(shift)
    context = None
    choice_menu = ChoiceMenu(sim)
    pick_target = zone.find_object(target_id)
    preferred_object = None
    if preferred_object_id is not None:
        preferred_object = services.object_manager().get(preferred_object_id)
    preferred_objects = set() if preferred_object is None else {preferred_object}
    pie_menu_action = should_generate_pie_menu(client, sim, shift_held)
    show_pie_menu = pie_menu_action == PieMenuActions.SHOW_PIE_MENU
    show_debug_pie_menu = pie_menu_action == PieMenuActions.SHOW_DEBUG_PIE_MENU
    suppress_social_front_page = False
    if show_pie_menu or show_debug_pie_menu:
        if pick_type == PickType.PICK_PORTRAIT or pick_type == PickType.PICK_CLUB_PANEL:
            sim_info = services.sim_info_manager().get(target_id)
            if sim_info is None:
                return 0
            if sim is None:
                return 0
            picked_item_ids = set([target_id])
            context = client.create_interaction_context(sim, target_sim_id=target_id)
            context.add_preferred_objects(preferred_objects)
            potential_interactions = list(sim.potential_relation_panel_interactions(context, picked_item_ids=picked_item_ids))
            choice_menu.add_potential_aops(sim_info, context, potential_interactions)
            client.set_choices(choice_menu)
        elif pick_type == PickType.PICK_SKEWER:
            sim_info = services.sim_info_manager().get(target_id)
            skewer_sim = None
            if sim_info is None:
                return 0
            skewer_sim = sim_info.get_sim_instance()
            context = client.create_interaction_context(skewer_sim)
            context.add_preferred_objects(preferred_objects)
            potential_interactions = list(sim_info.sim_skewer_affordance_gen(context))
            choice_menu.add_potential_aops(pick_target, context, potential_interactions)
            client.set_choices(choice_menu)
        elif pick_type == PickType.PICK_MANAGE_OUTFITS:
            context = client.create_interaction_context(sim)
            retail_manager = services.business_service().get_retail_manager_for_zone()
            potential_interactions = []
            if retail_manager is not None:
                potential_interactions = list(retail_manager.potential_manage_outfit_interactions_gen(context))
            choice_menu.add_potential_aops(pick_target, context, potential_interactions)
            client.set_choices(choice_menu)
        else:
            if show_pie_menu:
                shift_held = False
            position = sims4.math.Vector3(x, y, z)
            (pick_target, pick_type, potential_targets) = _get_targets_from_pick(sim, pick_target, pick_type, position, level, zone.id, lot_id, is_routable, preferred_objects=preferred_objects)
            if pick_target is None:
                return
            interaction_parameters = client.get_interaction_parameters()
            if potential_targets:
                for (potential_target, routing_surface) in potential_targets:
                    if potential_target.is_sim:
                        suppress_social_front_page |= potential_target.should_suppress_social_front_page_when_targeted()
                    pick = PickInfo(pick_type=pick_type, target=potential_target, location=position, routing_surface=routing_surface, lot_id=lot_id, level=level, alt=bool(alt), control=bool(control), shift=shift_held)
                    context = client.create_interaction_context(sim, pick=pick, shift_held=shift_held)
                    context.add_preferred_objects(preferred_objects)
                    potential_aops = list(potential_target.potential_interactions(context, **interaction_parameters))
                    choice_menu.add_potential_aops(potential_target, context, potential_aops)
                if shift_held or sim is not None:
                    context = client.create_interaction_context(sim, pick=pick, shift_held=shift_held)
                    context.add_preferred_objects(preferred_objects)
                    sim.fill_choices_menu_with_si_state_aops(pick_target, context, choice_menu)
                client.set_choices(choice_menu)
    msg = create_pie_menu_message(sim, choice_menu, reference_id, pie_menu_action, target=pick_target, suppress_front_page=suppress_social_front_page)
    distributor = Distributor.instance()
    distributor.add_event(Consts_pb2.MSG_PIE_MENU_CREATE, msg, True)
    num_choices = len(msg.items)
    if num_choices > 0:
        if pick_type in (PickType.PICK_PORTRAIT, PickType.PICK_SIM, PickType.PICK_CLUB_PANEL):
            with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_CREATE_PIE_MENU, sim=sim) as hook:
                hook.write_int('piid', reference_id)
                hook.write_enum('kind', pick_type)
                hook.write_int('tsim', target_id)
        else:
            with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_CREATE_PIE_MENU, sim=sim) as hook:
                hook.write_int('piid', reference_id)
                if pick_target is not None and getattr(pick_target, 'definition'):
                    hook.write_guid('tobj', pick_target.definition.id)
                else:
                    hook.write_int('tobj', 0)
                hook.write_enum('kind', pick_type)
    return num_choices

@sims4.commands.Command('interactions.phone_choices', command_type=sims4.commands.CommandType.Live)
def generate_phone_choices(control:int=0, alt:int=0, shift:int=0, reference_id:int=0, _connection=None):
    client = services.client_manager().get(_connection)
    sim = _active_sim(client)
    if sim is None:
        return 0
    msg = None
    phone_disabled_tooltip = None
    resolver = SingleSimResolver(sim.sim_info)
    for phone_test in PhoneTuning.DISABLE_PHONE_TESTS:
        test_result = resolver(phone_test.test)
        if test_result:
            phone_disabled_tooltip = phone_test.tooltip
            msg = create_pie_menu_message(sim, None, reference_id, None, failure_tooltip=phone_disabled_tooltip(sim))
            break
    if msg is None:
        shift_held = bool(shift)
        context = client.create_interaction_context(sim, shift_held=shift_held)
        can_queue_interactions = sim.queue is None or sim.queue.can_queue_visible_interaction()
        if can_queue_interactions:
            pie_menu_action = PieMenuActions.SHOW_PIE_MENU
            choice_menu = ChoiceMenu(sim)
            choice_menu.add_potential_aops(None, context, sim.potential_phone_interactions(context))
            client.set_choices(choice_menu)
        else:
            pie_menu_action = PieMenuActions.INTERACTION_QUEUE_FULL_TOOLTIP
            choice_menu = None
        msg = create_pie_menu_message(sim, choice_menu, reference_id, pie_menu_action)
    distributor = Distributor.instance()
    distributor.add_event(Consts_pb2.MSG_PHONE_MENU_CREATE, msg, True)
    with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_CREATE_PIE_MENU, sim=sim) as hook:
        hook.write_int('piid', reference_id)
        hook.write_string('kind', 'phone')
    return len(msg.items)

def create_pie_menu_message(sim, choice_menu, reference_id, pie_menu_action, target=None, failure_tooltip=None, suppress_front_page=False):
    msg = interaction_protocol.PieMenuCreate()
    msg.sim = sim.id if sim is not None else 0
    msg.client_reference_id = reference_id
    msg.server_reference_id = 0
    msg.supress_social_front_page = suppress_front_page
    if failure_tooltip is not None:
        msg.disabled_tooltip = failure_tooltip
        return msg
    if not choice_menu:
        fire_service = services.get_fire_service()
        if fire_service.fire_is_active:
            msg.disabled_tooltip = fire_service.INTERACTION_UNAVAILABLE_DUE_TO_FIRE_TOOLTIP()
            return msg
    if pie_menu_action == PieMenuActions.INTERACTION_QUEUE_FULL_TOOLTIP:
        msg.disabled_tooltip = PieMenuActions.INTERACTION_QUEUE_FULL_STR(sim)
        return msg
    create_tokens(msg.category_tokens, sim, target, None if target is None else target.get_stored_sim_info())
    if choice_menu:
        resolver = InteractionResolver(None, None, target, next(iter(choice_menu))[1].context)
    else:
        resolver = SingleActorAndObjectResolver(sim, target, source='create_pie_menu_message')
    if sim is not None:
        (icon_override, parent_override, blacklist_icon_tags, blacklist_parent_tags) = sim.get_actor_new_pie_menu_icon_and_parent_name(None, resolver)
    else:
        icon_override = None
        parent_override = None
        blacklist_icon_tags = set()
        blacklist_parent_tags = set()
    if choice_menu is not None:
        msg.server_reference_id = choice_menu.revision
        club_service = services.get_club_service()
        tutorial_service = services.get_tutorial_service()
        for (option_id, item) in choice_menu:
            aop = item.aop
            aop_affordance = aop.affordance
            if tutorial_service is not None and not tutorial_service.is_affordance_visible(aop_affordance):
                pass
            else:
                if sim is None:
                    modifier_tooltip = None
                else:
                    (modifier_visibility, modifier_tooltip) = sim.test_pie_menu_modifiers(aop_affordance)
                    if not modifier_visibility:
                        pass
                    else:
                        with ProtocolBufferRollback(msg.items) as item_msg:
                            item_msg.id = aop.aop_id
                            context = item.context
                            allow_global_icon_overrides = not blacklist_icon_tags & aop_affordance.interaction_category_tags
                            allow_global_parent_overrides = not blacklist_parent_tags & aop_affordance.interaction_category_tags
                            logger.debug('%3d: %s' % (option_id, aop))
                            name = aop_affordance.get_name(aop.target, context, **aop.interaction_parameters)
                            (name_override_tunable, name_override_result) = aop_affordance.get_name_override_tunable_and_result(target=aop.target, context=context)
                            if allow_global_parent_overrides:
                                name = parent_override(sim, name)
                            pie_menu_icon = aop_affordance.get_pie_menu_icon_info(context=context, **aop.interaction_parameters) if parent_override is not None and icon_override is None else None
                            category_key = item.category_key
                            ignore_pie_menu_icon_override = aop_affordance.is_rally_interaction and pie_menu_icon is not None
                            if name_override_tunable is not None:
                                if not ignore_pie_menu_icon_override:
                                    pie_menu_icon = name_override_tunable.new_pie_menu_icon(resolver)
                                if name_override_tunable.new_pie_menu_icon is not None and name_override_tunable.new_pie_menu_category is not None:
                                    category_key = name_override_tunable.new_pie_menu_category.guid64
                                if not (parent_override is None or allow_global_parent_overrides):
                                    name = name_override_tunable.parent_name(sim, name)
                            if _show_interaction_tuning_name:
                                affordance_tuning_name = str(aop_affordance.__name__)
                                name = InteractionCommandsTuning.INTERACTION_TUNING_NAME(name, affordance_tuning_name)
                            item_msg.score = aop.content_score if aop.content_score is not None else 0
                            if _show_front_page_score:
                                name = InteractionCommandsTuning.INTERACTION_FRONT_PAGE_SCORING(name, str(item_msg.score))
                            item_msg.loc_string = name
                            tooltip = modifier_tooltip or item.result.tooltip
                            if tooltip is not None:
                                tooltip = aop_affordance.create_localized_string(tooltip, context=context, target=aop.target, **aop.interaction_parameters)
                                item_msg.disabled_text = tooltip
                            else:
                                if tutorial_service is not None:
                                    tooltip = tutorial_service.get_disabled_affordance_tooltip(aop_affordance)
                                if tooltip is not None:
                                    tooltip = aop_affordance.create_localized_string(tooltip, context=context, target=aop.target, **aop.interaction_parameters)
                                    item_msg.disabled_text = tooltip
                                else:
                                    success_tooltip = aop_affordance.get_display_tooltip(override=name_override_tunable, context=context, target=aop.target, **aop.interaction_parameters)
                                    if success_tooltip is not None:
                                        item_msg.success_tooltip = success_tooltip
                            if icon_override is not None and allow_global_icon_overrides:
                                item_msg.icon_infos.append(create_icon_info_msg(IconInfoData(icon_resource=icon_override)))
                            elif pie_menu_icon is not None:
                                item_msg.icon_infos.append(create_icon_info_msg(pie_menu_icon))
                            if category_key is not None:
                                item_msg.category_key = category_key
                            if item.result.icon is not None:
                                item_msg.icon_infos.append(create_icon_info_msg(IconInfoData(icon_resource=item.result.icon)))
                            if aop.show_posture_incompatible_icon:
                                item_msg.icon_infos.append(create_icon_info_msg(IconInfoData(icon_resource=PieMenuActions.POSTURE_INCOMPATIBLE_ICON)))
                            if club_service is not None and sim is not None:
                                (encouragement, _) = club_service.get_interaction_encouragement_status_and_rules_for_sim_info(sim.sim_info, aop)
                                if encouragement == ClubRuleEncouragementStatus.ENCOURAGED:
                                    item_msg.icon_infos.append(create_icon_info_msg(IconInfoData(icon_resource=club_tuning.ClubTunables.PIE_MENU_INTERACTION_ENCOURAGED_ICON)))
                                elif encouragement == ClubRuleEncouragementStatus.DISCOURAGED:
                                    item_msg.icon_infos.append(create_icon_info_msg(IconInfoData(icon_resource=club_tuning.ClubTunables.PIE_MENU_INTERACTION_DISCOURAGED_ICON)))
                            handle_pie_menu_item_coloring(item_msg, item, sim, aop, name_override_result)
                            for visual_target in aop_affordance.visual_targets_gen(aop.target, context, **aop.interaction_parameters):
                                if visual_target is not None:
                                    item_msg.target_ids.append(visual_target.id)
                            item_msg.pie_menu_priority = aop_affordance.pie_menu_priority
                with ProtocolBufferRollback(msg.items) as item_msg:
                    item_msg.id = aop.aop_id
                    context = item.context
                    allow_global_icon_overrides = not blacklist_icon_tags & aop_affordance.interaction_category_tags
                    allow_global_parent_overrides = not blacklist_parent_tags & aop_affordance.interaction_category_tags
                    logger.debug('%3d: %s' % (option_id, aop))
                    name = aop_affordance.get_name(aop.target, context, **aop.interaction_parameters)
                    (name_override_tunable, name_override_result) = aop_affordance.get_name_override_tunable_and_result(target=aop.target, context=context)
                    if allow_global_parent_overrides:
                        name = parent_override(sim, name)
                    pie_menu_icon = aop_affordance.get_pie_menu_icon_info(context=context, **aop.interaction_parameters) if parent_override is not None and icon_override is None else None
                    category_key = item.category_key
                    ignore_pie_menu_icon_override = aop_affordance.is_rally_interaction and pie_menu_icon is not None
                    if name_override_tunable is not None:
                        if not ignore_pie_menu_icon_override:
                            pie_menu_icon = name_override_tunable.new_pie_menu_icon(resolver)
                        if name_override_tunable.new_pie_menu_icon is not None and name_override_tunable.new_pie_menu_category is not None:
                            category_key = name_override_tunable.new_pie_menu_category.guid64
                        if not (parent_override is None or allow_global_parent_overrides):
                            name = name_override_tunable.parent_name(sim, name)
                    if _show_interaction_tuning_name:
                        affordance_tuning_name = str(aop_affordance.__name__)
                        name = InteractionCommandsTuning.INTERACTION_TUNING_NAME(name, affordance_tuning_name)
                    item_msg.score = aop.content_score if aop.content_score is not None else 0
                    if _show_front_page_score:
                        name = InteractionCommandsTuning.INTERACTION_FRONT_PAGE_SCORING(name, str(item_msg.score))
                    item_msg.loc_string = name
                    tooltip = modifier_tooltip or item.result.tooltip
                    if tooltip is not None:
                        tooltip = aop_affordance.create_localized_string(tooltip, context=context, target=aop.target, **aop.interaction_parameters)
                        item_msg.disabled_text = tooltip
                    else:
                        if tutorial_service is not None:
                            tooltip = tutorial_service.get_disabled_affordance_tooltip(aop_affordance)
                        if tooltip is not None:
                            tooltip = aop_affordance.create_localized_string(tooltip, context=context, target=aop.target, **aop.interaction_parameters)
                            item_msg.disabled_text = tooltip
                        else:
                            success_tooltip = aop_affordance.get_display_tooltip(override=name_override_tunable, context=context, target=aop.target, **aop.interaction_parameters)
                            if success_tooltip is not None:
                                item_msg.success_tooltip = success_tooltip
                    if icon_override is not None and allow_global_icon_overrides:
                        item_msg.icon_infos.append(create_icon_info_msg(IconInfoData(icon_resource=icon_override)))
                    elif pie_menu_icon is not None:
                        item_msg.icon_infos.append(create_icon_info_msg(pie_menu_icon))
                    if category_key is not None:
                        item_msg.category_key = category_key
                    if item.result.icon is not None:
                        item_msg.icon_infos.append(create_icon_info_msg(IconInfoData(icon_resource=item.result.icon)))
                    if aop.show_posture_incompatible_icon:
                        item_msg.icon_infos.append(create_icon_info_msg(IconInfoData(icon_resource=PieMenuActions.POSTURE_INCOMPATIBLE_ICON)))
                    if club_service is not None and sim is not None:
                        (encouragement, _) = club_service.get_interaction_encouragement_status_and_rules_for_sim_info(sim.sim_info, aop)
                        if encouragement == ClubRuleEncouragementStatus.ENCOURAGED:
                            item_msg.icon_infos.append(create_icon_info_msg(IconInfoData(icon_resource=club_tuning.ClubTunables.PIE_MENU_INTERACTION_ENCOURAGED_ICON)))
                        elif encouragement == ClubRuleEncouragementStatus.DISCOURAGED:
                            item_msg.icon_infos.append(create_icon_info_msg(IconInfoData(icon_resource=club_tuning.ClubTunables.PIE_MENU_INTERACTION_DISCOURAGED_ICON)))
                    handle_pie_menu_item_coloring(item_msg, item, sim, aop, name_override_result)
                    for visual_target in aop_affordance.visual_targets_gen(aop.target, context, **aop.interaction_parameters):
                        if visual_target is not None:
                            item_msg.target_ids.append(visual_target.id)
                    item_msg.pie_menu_priority = aop_affordance.pie_menu_priority
    return msg

def handle_pie_menu_item_coloring(item_msg, item, sim, choice, name_override_result):
    mood_result = None
    mood_intensity_result = None
    away_action = choice.interaction_parameters.get('away_action')
    away_action_sim_info = choice.interaction_parameters.get('away_action_sim_info')
    if away_action is not None:
        away_action_sim_current_mood = away_action_sim_info.get_mood()
        if away_action_sim_current_mood in away_action.mood_list:
            mood_result = away_action_sim_current_mood
            mood_intensity_result = away_action_sim_info.get_mood_intensity()
    elif item.result.influence_by_active_mood or name_override_result.influence_by_active_mood:
        mood_result = sim.get_mood()
        mood_intensity_result = sim.get_mood_intensity()
    if mood_result is not None:
        item_msg.mood = mood_result.guid64
        item_msg.mood_intensity = mood_intensity_result

@sims4.commands.Command('interactions.select', command_type=sims4.commands.CommandType.Live)
def select_choice(choice_id:int, reference_id:int=0, _connection=None):
    client = services.client_manager().get(_connection)
    return client.select_interaction(choice_id, reference_id)

@sims4.commands.Command('interactions.queue')
def display_queue(sim_id:int=None, _connection=None):
    output = Output(_connection)
    if sim_id is None:
        client = services.client_manager().get(_connection)
        sim = _active_sim(client)
    else:
        sim_info = services.sim_info_manager().get(sim_id)
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) if sim_info is not None else None
        if sim is None:
            output('Invalid Sim id {0:08x}'.format(sim_id))
            return False
    output('Super Interaction State: (num = {0})'.format(len(sim.si_state)))
    for si in sim.si_state.sis_actor_gen():
        output(' * {}'.format(str(si)))
        for subi in si.queued_sub_interactions_gen():
            output('    - {}'.format(str(subi)))
    output('Interaction Queue State: (num = {0})'.format(len(sim.queue)))
    for si in sim.queue:
        output(' * {}'.format(str(si)))
    output('Running: %s' % sim.queue.running)

@sims4.commands.Command('qa.interactions.list', command_type=sims4.commands.CommandType.Automation)
def display_queue_automation(sim_id:int=None, _connection=None):
    output = sims4.commands.AutomationOutput(_connection)
    if sim_id is None:
        client = services.client_manager().get(_connection)
        sim = _active_sim(client)
    else:
        sim_info = services.sim_info_manager().get(sim_id)
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) if sim_info is not None else None
    if sim is None:
        output('SimInteractionData; SimId:None')
        return False
    if sim.queue.running is None:
        output('SimInteractionData; SimId:%d, SICount:%d, RunningId:None' % (sim.id, len(sim.si_state)))
    else:
        output('SimInteractionData; SimId:%d, SICount:%d, RunningId:%d, RunningClass:%s' % (sim.id, len(sim.si_state), sim.queue.running.id, sim.queue.running.__class__.__name__))
    for si in sim.si_state.sis_actor_gen():
        output('SimSuperInteractionData; Id:%d, Class:%s' % (si.id, si.__class__.__name__))

@sims4.commands.Command('interactions.reevaluate_head')
def reevaluate_head(sim_id:int=None, _connection=None):
    output = sims4.commands.AutomationOutput(_connection)
    if sim_id is None:
        client = services.client_manager().get(_connection)
        sim = _active_sim(client)
    else:
        sim_info = services.sim_info_manager().get(sim_id)
        sim = sim_info.get_sim_instance() if sim_info is not None else None
    if sim is None:
        output('SimInteractionData; SimId:None')
        return False
    for interaction in sim.queue:
        if interaction.is_super:
            interaction.transition = None
    sim.queue._get_head()

@sims4.commands.Command('qa.interactions.enable_sim_interaction_logging', command_type=sims4.commands.CommandType.Automation)
def enable_sim_interaction_logging(sim_id:int=None, _connection=None):
    output = sims4.commands.AutomationOutput(_connection)
    if sim_id is None:
        client = services.client_manager().get(_connection)
        sim = _active_sim(client)
    else:
        sim_info = services.sim_info_manager().get(sim_id)
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) if sim_info is not None else None
    if sim is None:
        output('SimInteractionToggleOn; SimId:None')
        return False
    sim.interaction_logging = True
    output('[AreaInstanceInteraction] SimInteractionToggleOn; SimId:%d, Logging:%d' % (sim.id, sim.interaction_logging))

@sims4.commands.Command('qa.interactions.disable_sim_interaction_logging', command_type=sims4.commands.CommandType.Automation)
def disable_sim_interaction_logging(sim_id:int=None, _connection=None):
    output = sims4.commands.AutomationOutput(_connection)
    if sim_id is None:
        client = services.client_manager().get(_connection)
        sim = _active_sim(client)
    else:
        sim_info = services.sim_info_manager().get(sim_id)
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) if sim_info is not None else None
    if sim is None:
        output('SimInteractionToggleOff; SimId:None')
        return False
    sim.interaction_logging = False
    output('[AreaInstanceInteraction] SimInteractionToggleOff; SimId:%d, Logging:%d' % (sim.id, sim.interaction_logging))

@sims4.commands.Command('qa.interactions.enable_sim_transition_path_logging', command_type=sims4.commands.CommandType.Automation)
def enable_sim_transition_path_logging(sim_id:int=None, _connection=None):
    output = sims4.commands.AutomationOutput(_connection)
    if sim_id is None:
        client = services.client_manager().get(_connection)
        sim = _active_sim(client)
    else:
        sim_info = services.sim_info_manager().get(sim_id)
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) if sim_info is not None else None
    if sim is None:
        output('SimTransitionPathToggleOn; SimId:None')
        return False
    sim.transition_path_logging = True
    output('[AreaInstanceInteraction] SimTransitionPathToggleOn; SimId:%d, Logging:%d' % (sim.id, sim.interaction_logging))

@sims4.commands.Command('qa.interactions.disable_sim_transition_path_logging', command_type=sims4.commands.CommandType.Automation)
def disable_sim_transition_path_logging(sim_id:int=None, _connection=None):
    output = sims4.commands.AutomationOutput(_connection)
    if sim_id is None:
        client = services.client_manager().get(_connection)
        sim = _active_sim(client)
    else:
        sim_info = services.sim_info_manager().get(sim_id)
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) if sim_info is not None else None
    if sim is None:
        output('SimTransitionPathToggleOff; SimId:None')
        return False
    sim.transition_path_logging = False
    output('[AreaInstanceInteraction] SimTransitionPathToggleOff; SimId:%d, Logging:%d' % (sim.id, sim.interaction_logging))

@sims4.commands.Command('interactions.display_outcomes')
def display_outcomes(sim_id:int=None, _connection=None):
    sim_info = services.sim_info_manager().get(sim_id)
    sim = sim_info.get_sim_instance() if sim_info is not None else None
    client = services.client_manager().get(_connection)
    if sim is None:
        sim = _active_sim(client)
    for si in sim.si_state.sis_actor_gen():
        sims4.commands.output('Outcome for {} = {}'.format(si.affordance, si.global_outcome_result), _connection)

def send_reject_response(client, sim, context_handle, cancel_reason):
    reject_msg = protocols.ServerResponseFailed()
    reject_msg.handle = context_handle
    reject_msg.reason = cancel_reason
    distributor = Distributor.instance()
    distributor.add_op_with_no_owner(GenericProtocolBufferOp(Operation.SIM_SERVER_RESPONSE_FAILED, reject_msg))
    logger.debug('    sending reject msg')

def cancel_common(interaction_id:int, context_handle:int=None, _connection=None, user_canceled=False):
    client = services.client_manager().get(_connection)
    sim = _active_sim(client)
    interaction = sim.find_interaction_by_id(interaction_id)
    if interaction is None:
        continuation = sim.find_continuation_by_id(interaction_id)
        if continuation is not None:
            continuation.cancel_user(cancel_reason_msg='User canceled the interaction.')
        return True
    if interaction.cancel_user(cancel_reason_msg='Command interactions.cancel_si'):
        return True
    if context_handle is not None:
        send_reject_response(client, sim, context_handle, protocols.ServerResponseFailed.REJECT_CLIENT_CANCEL_SUPERINTERACTION)
    return False

@sims4.commands.Command('interactions.force_inertial', command_type=sims4.commands.CommandType.Automation)
def interaction_force_inertial(opt_target:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_target, _connection)
    if sim is None:
        return False
    for si in sim.si_state:
        si.force_inertial = True

@sims4.commands.Command('interactions.cancel', command_type=sims4.commands.CommandType.Live)
def cancel_mixer_interaction(interaction_id:int, mixer_id:int, server_ref:int, context_handle:int=None, _connection=None):
    logger.debug('cancel_sub_interaction {0}', interaction_id)
    client = services.client_manager().get(_connection)
    sim = _active_sim(client)
    interaction = sim.find_sub_interaction_by_aop_id(interaction_id, mixer_id)
    if interaction is not None and sim.queue.running != interaction:
        return interaction.cancel_user(cancel_reason_msg='Command interactions.cancel')
    return False

@sims4.commands.Command('interactions.cancel_si', command_type=sims4.commands.CommandType.Live)
def cancel_super_interaction(super_interaction_id:int, context_handle:int=None, _connection=None):
    logger.debug('cancel_super_interaction {0}', super_interaction_id)
    if False and _mixer_lock:
        return False
    return cancel_common(super_interaction_id, context_handle, _connection, user_canceled=True)

@sims4.commands.Command('interactions.run_first')
def first_interaction(target_id:int=None, _connection=None):
    target = None
    if target_id is not None:
        target = services.object_manager().get(target_id)
    client = services.client_manager().get(_connection)
    sim = _active_sim(client)
    if target is None:
        target = sim
    context = client.create_interaction_context(sim)
    affordances = list(target.potential_interactions(context))
    if affordances:
        logger.debug('Running affordance: {0}', affordances[0])
        return affordances[0].test_and_execute(context)
    return False

@sims4.commands.Command('interactions.push', command_type=sims4.commands.CommandType.Live)
def push_interaction(affordance:TunableInstanceParam(sims4.resources.Types.INTERACTION), opt_target:RequiredTargetParam=None, opt_sim:OptionalTargetParam=None, priority=Priority.High, _connection=None):
    target = opt_target.get_target() if opt_target is not None else None
    sim = get_optional_target(opt_sim, _connection)
    client = services.client_manager().get(_connection)
    priority = Priority(priority)
    if not sim.queue.can_queue_visible_interaction():
        sims4.commands.output('Interaction queue is full, cannot add anymore interactions.', _connection)
        return False
    else:
        context = InteractionContext(sim, InteractionContext.SOURCE_PIE_MENU, priority, client=client, pick=None)
        result = sim.push_super_affordance(affordance, target, context)
        if not result:
            output = sims4.commands.Output(_connection)
            output('Failed to push: {}'.format(result))
            return False
    return True

@sims4.commands.Command('interactions.push_all_sims')
def push_interaction_on_all_sims(affordance:TunableInstanceParam(sims4.resources.Types.INTERACTION), opt_target:RequiredTargetParam=None, _connection=None):
    target = opt_target.get_target() if opt_target is not None else None
    client = services.client_manager().get(_connection)
    for sim_info in client.selectable_sims:
        sim = sim_info.get_sim_instance()
        if sim is not None:
            context = InteractionContext(sim, InteractionContext.SOURCE_PIE_MENU, Priority.High, client=client, pick=None)
            sim.push_super_affordance(affordance, target, context)
    return True

@sims4.commands.Command('interactions.content_mode')
def set_content_mode(mode=None, _connection=None):
    output = sims4.commands.Output(_connection)
    if mode is None:
        output('No mode specified. Please use one of: {}'.format(', '.join(ContentModes.names)))
        return False
    try:
        valid_mode = ContentModes[mode.upper()]
    except AttributeError:
        output('Invalid mode specified. Please use one of: {}'.format(', '.join(ContentModes.names)))
        return False
    services.config_service().content_mode = valid_mode
    output('Mode set to {}'.format(valid_mode.name))
    return True

@sims4.commands.Command('demo.mixer_lock')
def demo_mixer_lock(enabled=None, _connection=None):
    output = sims4.commands.Output(_connection)
    output('Mixer lock is not supported in optimized python builds.')

class InteractionModes(enum.Int, export=False):
    default = 0
    autonomous = 1

@sims4.commands.Command('interactions.set_interaction_mode')
def set_interaction_mode(mode:InteractionModes=None, source:int=None, priority:interactions.priority.Priority=None, _connection=None):
    output = sims4.commands.Output(_connection)
    client = services.client_manager().get(_connection)
    if client is None:
        return 0
    sources = {}
    for (key, val) in vars(interactions.context.InteractionContext).items():
        if key.startswith('SOURCE'):
            sources[val] = key
    if priority is None:
        output('Source options:')
        for val in sources.values():
            output('    {}'.format(val))
        output('Priority options:')
        for val in interactions.priority.Priority:
            output('    {}'.format(val.name))
    if mode is None and source is None and mode is InteractionModes.default:
        client.interaction_source = None
        client.interaction_priority = None
    elif mode is InteractionModes.autonomous:
        client.interaction_source = interactions.context.InteractionContext.SOURCE_AUTONOMY
        client.interaction_priority = interactions.priority.Priority.Low
    if source is not None:
        client.interaction_source = source
    if priority is not None:
        client.interaction_priority = priority
    source = sources.get(client.interaction_source, client.interaction_source)
    output('Client interaction mode: source={} priority={}'.format(source, client.interaction_priority.name))
    return 1

@sims4.commands.Command('interactions.debug_outcome_print', command_type=sims4.commands.CommandType.Automation)
def debug_outcome_index_print(affordance:TunableInstanceParam(sims4.resources.Types.INTERACTION), mode=None, _connection=None):
    sims4.commands.output(affordance.outcome.print_outcome_index(), _connection)

@sims4.commands.Command('interactions.debug_outcome_index_set', command_type=sims4.commands.CommandType.Automation)
def debug_outcome_index_set(affordance:TunableInstanceParam(sims4.resources.Types.INTERACTION), debug_outcome_index, mode=None, _connection=None):
    interactions.utils.outcome.update_debug_outcome_index_mapping(affordance, debug_outcome_index)
    sims4.commands.output(interactions.utils.outcome.debug_outcome_index_mapping.__str__(), _connection)

@sims4.commands.Command('interactions.debug_outcome_index_table_clear', command_type=sims4.commands.CommandType.Automation)
def debug_outcome_index_table_clear(mode=None, _connection=None):
    interactions.utils.outcome.debug_outcome_index_mapping = None

@sims4.commands.Command('interactions.debug_outcome_index_table_print', command_type=sims4.commands.CommandType.Automation)
def debug_outcome_index_table_print(mode=None, _connection=None):
    sims4.commands.output(interactions.utils.outcome.debug_outcome_index_mapping.__str__(), _connection)

@sims4.commands.Command('interactions.debug_outcome_style_set', command_type=sims4.commands.CommandType.Automation)
def set_debug_outcome_style(debug_style, mode=None, _connection=None):
    interactions.utils.outcome.debug_outcome_style = _parse_debug_outcome_style(debug_style)

@sims4.commands.Command('interactions.debug_outcome_style_current')
def print_current_debug_outcome_style(mode=None, _connection=None):
    sims4.commands.output(interactions.utils.outcome.debug_outcome_style.__str__(), _connection)

@sims4.commands.Command('interactions.print_content_set')
def print_current_content_set(_connection=None):
    client = services.client_manager().get(_connection)
    if client is None:
        return
    sim = _active_sim(client)
    if sim is None:
        sims4.commands.output('There is no active sim.', _connection)
    else:
        has_printed = False
        context = client.create_interaction_context(sim)
        for si in sim.si_state:
            potential_targets = si.get_potential_mixer_targets()
            content_set = autonomy.content_sets.generate_content_set(sim, si.super_affordance, si, context, potential_targets=potential_targets)
            for (weight, aop, test_result) in content_set:
                affordance_name = aop.affordance.__name__ + ' '
                sims4.commands.output('affordance:{} weight:{} result:{}'.format(affordance_name, weight, test_result), _connection)
                has_printed = True
        if not has_printed:
            sims4.commands.output('Could not find an active content set.', _connection)

def _parse_debug_outcome_style(debug_outcome_style):
    input_lower = debug_outcome_style.lower()
    style = interactions.utils.outcome.DebugOutcomeStyle.NONE
    if input_lower == 'auto_succeed' or input_lower == 'success':
        style = interactions.utils.outcome.DebugOutcomeStyle.AUTO_SUCCEED
    elif input_lower == 'auto_fail' or input_lower == 'fail':
        style = interactions.utils.outcome.DebugOutcomeStyle.AUTO_FAIL
    elif input_lower == 'rotate' or input_lower == 'alternate':
        style = interactions.utils.outcome.DebugOutcomeStyle.ROTATE
    elif input_lower == 'none' or input_lower == 'off':
        style = interactions.utils.outcome.DebugOutcomeStyle.NONE
    return style

@sims4.commands.Command('interactions.lock_content_set', command_type=sims4.commands.CommandType.Automation)
def lock_content_set(*mixer_interactions, _connection=None):
    try:
        autonomy.content_sets.lock_content_sets(mixer_interactions)
    except Exception as e:
        sims4.commands.output('Content set lock failed: {}'.format(e), _connection)

@sims4.commands.Command('interactions.regenerate', command_type=sims4.commands.CommandType.Automation)
def regenerate(_connection=None):
    client = services.client_manager().get(_connection)
    sim = _active_sim(client)
    if sim is not None:
        sims4.commands.output('Regenerate Content set currently disabled.', _connection)

@sims4.commands.Command('interactions.set_social_mixer_tests_enabled')
def toggle_social_tests(enabled:bool=None):
    current = interactions.social.social_mixer_interaction.tunable_tests_enabled
    if enabled is None:
        interactions.social.social_mixer_interaction.tunable_tests_enabled = not current
    else:
        interactions.social.social_mixer_interaction.tunable_tests_enabled = enabled

@sims4.commands.Command('interactions.toggle_interactions_in_callstack', command_type=sims4.commands.CommandType.Automation)
def toggle_interactions_in_callstack(enabled:bool=None, _connection=None):
    value = postures.transition_sequence.inject_interaction_name_in_callstack
    value = not value
    postures.transition_sequence.inject_interaction_name_in_callstack = value
    sims4.commands.output('Inject interaction names: {}'.format(value), _connection)
