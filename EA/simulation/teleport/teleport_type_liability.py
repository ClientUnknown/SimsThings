from interactions.base.interaction_constants import InteractionQueuePreparationStatusfrom interactions.liability import Liability, PreparationLiabilityfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableEnumEntryfrom teleport.teleport_enums import TeleportStyle, TeleportStyleSource
class TeleportStyleLiability(Liability, HasTunableFactory, AutoFactoryInit):
    LIABILITY_TOKEN = 'TeleportStyleLiability'
    FACTORY_TUNABLES = {'teleport_style': TunableEnumEntry(description='\n            Style to be used while the liability is active.\n            ', tunable_type=TeleportStyle, default=TeleportStyle.NONE, invalid_enums=(TeleportStyle.NONE,), pack_safe=True)}

    def __init__(self, interaction, source=TeleportStyleSource.TUNED_LIABILITY, **kwargs):
        super().__init__(**kwargs)
        self._sim_info = interaction.sim.sim_info
        self._source = source
        self._sim_info.add_teleport_style(self._source, self.teleport_style)

    def release(self):
        self._sim_info.remove_teleport_style(self._source, self.teleport_style)

class TeleportStyleInjectionLiability(Liability):
    LIABILITY_TOKEN = 'TeleportStyleInjectionLiability'

    def should_transfer(self, continuation):
        return False
