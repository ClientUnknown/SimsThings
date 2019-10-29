from event_testing.resolver import SingleSimResolverfrom narrative.narrative_enums import NarrativeEventfrom server_commands.argument_helpers import TunableInstanceParamfrom sims4.common import Packfrom sims4.tuning.tunable import TunablePackSafeReferenceimport servicesimport sims4.commands
@sims4.commands.Command('narrative.trigger_event', command_type=sims4.commands.CommandType.Automation)
def trigger_narrative_event(event:NarrativeEvent, _connection=None):
    services.narrative_service().handle_narrative_event(event)

@sims4.commands.Command('narrative.start_narrative', command_type=sims4.commands.CommandType.Automation)
def start_narrative(narrative:TunableInstanceParam(sims4.resources.Types.NARRATIVE), _connection=None):
    services.narrative_service().start_narrative(narrative)

@sims4.commands.Command('narrative.end_narrative', command_type=sims4.commands.CommandType.Automation)
def end_narrative(narrative:TunableInstanceParam(sims4.resources.Types.NARRATIVE), _connection=None):
    services.narrative_service().end_narrative(narrative)

@sims4.commands.Command('narrative.reset_completion', command_type=sims4.commands.CommandType.Automation)
def reset_narrative_completion(narrative:TunableInstanceParam(sims4.resources.Types.NARRATIVE), _connection=None):
    services.narrative_service().reset_completion(narrative)

@sims4.commands.Command('narrative.get_active_narratives', command_type=sims4.commands.CommandType.DebugOnly)
def get_active_narratives(_connection=None):
    for active_narrative in services.narrative_service().active_narratives:
        sims4.commands.cheat_output('{}'.format(active_narrative.guid64), _connection)
    return True

@sims4.commands.Command('narrative.has_narrative', command_type=sims4.commands.CommandType.Automation)
def has_narrative(narrative_id:int, _connection=None):
    found_narrative = False
    for active_narrative in services.narrative_service().active_narratives:
        if active_narrative.guid64 == narrative_id:
            found_narrative = True
            break
    sims4.commands.automation_output('NarrativeInfo; NarrativeIsActive:{}'.format(found_narrative), _connection)
    return True

class EP07NarrativeCommands:
    CONSERVATION_START_STAGE_LOOT = TunablePackSafeReference(description='\n        The loot we will apply if the player runs the\n        narrative.restart_conservation_narrative cheat.\n        ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',))
    CONSERVATION_INTERMEDIATE_STAGE_LOOT = TunablePackSafeReference(description='\n        The loot we will apply if the player runs the\n        narrative.set_stage_intermediate_conservation_narrative cheat.\n        ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',))
    CONSERVATION_FINAL_STAGE_LOOT = TunablePackSafeReference(description='\n        The loot we will apply if the player runs the\n        narrative.set_stage_final_conservation_narrative cheat.\n        ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',))
    CONSERVATION_NARRATIVE_START_STAGE = TunablePackSafeReference(description='\n        The least conserved island narrative stage. Used for locking narrative\n        stages based on cheats.\n        ', manager=services.get_instance_manager(sims4.resources.Types.NARRATIVE))
    CONSERVATION_NARRATIVE_INTERMEDIATE_STAGE = TunablePackSafeReference(description='\n        The intermediate island narrative stage. Used for locking narrative\n        stages based on cheats.\n        ', manager=services.get_instance_manager(sims4.resources.Types.NARRATIVE))
    CONSERVATION_NARRATIVE_FINAL_STAGE = TunablePackSafeReference(description='\n        The final island narrative stage. Used for locking narrative\n        stages based on cheats.\n        ', manager=services.get_instance_manager(sims4.resources.Types.NARRATIVE))

@sims4.commands.Command('narrative.restart_conservation_narrative', command_type=sims4.commands.CommandType.Cheat, pack=Pack.EP07)
def restart_conservation_narrative(_connection=None):
    if services.narrative_service().is_narrative_locked(EP07NarrativeCommands.CONSERVATION_NARRATIVE_START_STAGE):
        sims4.commands.output('Island Conservation Narrative stage locked. Please unlock to set.', _connection)
    resolver = SingleSimResolver(services.active_sim_info())
    loot = EP07NarrativeCommands.CONSERVATION_START_STAGE_LOOT
    if loot is None:
        return
    loot.apply_to_resolver(resolver)

@sims4.commands.Command('narrative.set_stage_intermediate_conservation_narrative', command_type=sims4.commands.CommandType.Cheat, pack=Pack.EP07)
def set_stage_intermediate_conservation_narrative(_connection=None):
    if services.narrative_service().is_narrative_locked(EP07NarrativeCommands.CONSERVATION_NARRATIVE_INTERMEDIATE_STAGE):
        sims4.commands.output('Island Conservation Narrative stage locked. Please unlock to set.', _connection)
    resolver = SingleSimResolver(services.active_sim_info())
    loot = EP07NarrativeCommands.CONSERVATION_INTERMEDIATE_STAGE_LOOT
    if loot is None:
        return
    loot.apply_to_resolver(resolver)

@sims4.commands.Command('narrative.set_stage_final_conservation_narrative', command_type=sims4.commands.CommandType.Cheat, pack=Pack.EP07)
def set_stage_final_conservation_narrative(_connection=None):
    if services.narrative_service().is_narrative_locked(EP07NarrativeCommands.CONSERVATION_NARRATIVE_FINAL_STAGE):
        sims4.commands.output('Island Conservation Narrative stage locked. Please unlock to set.', _connection)
    resolver = SingleSimResolver(services.active_sim_info())
    loot = EP07NarrativeCommands.CONSERVATION_FINAL_STAGE_LOOT
    if loot is None:
        return
    loot.apply_to_resolver(resolver)

@sims4.commands.Command('narrative.toggle_island_conservation_narrative_lock', command_type=sims4.commands.CommandType.Cheat, pack=Pack.EP07)
def toggle_island_conservation_narrative_lock(_connection=None):
    narrative_service = services.narrative_service()
    did_lock = False
    for narrative in (EP07NarrativeCommands.CONSERVATION_NARRATIVE_START_STAGE, EP07NarrativeCommands.CONSERVATION_NARRATIVE_INTERMEDIATE_STAGE, EP07NarrativeCommands.CONSERVATION_NARRATIVE_FINAL_STAGE):
        if narrative_service.is_narrative_locked(narrative):
            narrative_service.unlock_narrative(narrative)
        else:
            narrative_service.lock_narrative(narrative)
            did_lock = True
    if did_lock:
        sims4.commands.output('Island Conservation Narrative locked', _connection)
    else:
        sims4.commands.output('Island Conservation Narrative unlocked', _connection)
