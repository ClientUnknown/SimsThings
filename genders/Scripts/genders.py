import sims4.commands

@sims4.commands.Command('genders', command_type=sims4.commands.CommandType.Live)
def get_gender(_connection=None):
    #sim_info = sim_obj.SimInfoNameData.DESCRIPTOR.gender
    #genders = EA.simulation.sims.sim_info_types.Gender()
    
    #setattr(genders, 'OTHER', 16384)

    output = sims4.commands.CheatOutput(_connection)
    output("Hello World")
    #output(genders)