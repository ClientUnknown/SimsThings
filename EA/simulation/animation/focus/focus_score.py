from animation.focus.focus_tuning import FocusScore, FocusTuningfrom distributor.rollback import ProtocolBufferRollbackfrom sims.sim_info_types import Speciesfrom sims4 import resourcesfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, TunableMapping, TunableReference, TunableRange, TunableVariantimport services
class _FocusScoreGlobal(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'base': TunableEnumEntry(description='\n            The base focus score, with no multipliers applied.\n            ', tunable_type=FocusScore, default=FocusScore.NONE, needs_tuning=True), 'multipliers': TunableMapping(description="\n            A mapping of traits that increase or decrease a Sim's interest\n            towards an object. The multiplier is applied to the tuned\n            associate value of the focus score.\n            ", key_type=TunableReference(description='\n                The trait that triggers the multiplier.\n                ', manager=services.get_instance_manager(resources.Types.TRAIT), pack_safe=True), value_type=TunableRange(description='\n                The score multiplier to apply if the Sim has the specified\n                trait.\n                ', tunable_type=float, minimum=0, default=1))}

    def populate_focus_score_entry_msg(self, focus_score_entry_msg):
        focus_score_entry_msg.base = FocusTuning.FOCUS_SCORE_VALUES[self.base]
        for (trait, multiplier) in self.multipliers.items():
            with ProtocolBufferRollback(focus_score_entry_msg.multipliers) as focus_score_entry_multiplier_msg:
                focus_score_entry_multiplier_msg.trait_id = trait.guid64
                focus_score_entry_multiplier_msg.multiplier = multiplier

    def populate_focus_score_msg(self, focus_score_msg):
        self.populate_focus_score_entry_msg(focus_score_msg.global_score)

class _FocusScoreSpecies(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'scores': TunableMapping(description='\n            A mapping of species to the focus score specific to that\n            species.\n            ', key_type=TunableEnumEntry(description='\n                The species associated with this score.\n                ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)), value_type=_FocusScoreGlobal.TunableFactory())}

    def populate_focus_score_msg(self, focus_score_msg):
        for (species, focus_score) in self.scores.items():
            with ProtocolBufferRollback(focus_score_msg.specific_scores) as focus_score_entry_msg:
                focus_score_entry_msg.species = species
                focus_score.populate_focus_score_entry_msg(focus_score_entry_msg.score)

class TunableFocusScoreVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, description='\n            Define how focus score is determined for this object.\n            ', globally=_FocusScoreGlobal.TunableFactory(), species_specific=_FocusScoreSpecies.TunableFactory(), default='globally', **kwargs)
