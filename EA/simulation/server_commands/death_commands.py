from interactions.utils.death import DeathTypeimport interactions.utils.deathimport servicesimport sims4.commandsfrom objects import ALL_HIDDEN_REASONS
@sims4.commands.Command('death.toggle', command_type=sims4.commands.CommandType.Cheat)
def death_toggle(enabled:bool=None, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    interactions.utils.death.toggle_death(enabled=enabled)
    output('Toggling death, Enabled: {}'.format(interactions.utils.death._is_death_enabled))

@sims4.commands.Command('death.kill_many_npcs')
def death_kill_npcs(_connection=None):
    household_manager = services.household_manager()
    for household in tuple(household_manager.get_all()):
        if not household.home_zone_id:
            pass
        elif household is services.active_household():
            pass
        else:
            for sim_info in household:
                if len(tuple(household.can_live_alone_info_gen())) <= 1:
                    break
                if sim_info.can_live_alone and sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
                    pass
                elif sim_info.is_toddler_or_younger:
                    pass
                elif sim_info.death_type:
                    pass
                else:
                    death_type = DeathType.get_random_death_type()
                    sim_info.death_tracker.set_death_type(death_type, is_off_lot_death=True)
    return True
