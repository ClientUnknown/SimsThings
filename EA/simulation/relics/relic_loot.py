from interactions.utils.loot_basic_op import BaseLootOperationfrom relics.relic_tuning import RelicComboIdfrom sims4.tuning.tunable import TunableEnumEntry
class AddRelicCombo(BaseLootOperation):
    FACTORY_TUNABLES = {'relic_combo_id': TunableEnumEntry(description="\n            The relic combo ID to add to the Sim's Relic Tracker.\n            ", tunable_type=RelicComboId, default=RelicComboId.INVALID, invalid_enums=(RelicComboId.INVALID,))}

    def __init__(self, *args, relic_combo_id, **kwargs):
        super().__init__(*args, **kwargs)
        self._relic_combo_id = relic_combo_id

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            return
        relic_tracker = subject.relic_tracker
        relic_tracker.add_relic_combo(self._relic_combo_id)
