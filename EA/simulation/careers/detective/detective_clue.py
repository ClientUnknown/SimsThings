from filters.tunable import FilterTermVariantfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import TunableReference, HasTunableReference, TunableRangefrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport servicesimport sims4.resources
class RelaxedFilterTermProxy:

    def __init__(self, filter_term, min_filter_score):
        self._filter_term = filter_term
        self._min_filter_score = min_filter_score

    @property
    def minimum_filter_score(self):
        return self._min_filter_score

    def __getattr__(self, name):
        return getattr(self._filter_term, name)

class Clue(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.DETECTIVE_CLUE)):
    INSTANCE_TUNABLES = {'filter_term': FilterTermVariant(description='\n            The filter that will be used to spawn Sims (including the criminal)\n            that match this clue.\n            '), 'notebook_entry': TunableReference(description="\n            The entry that will be added to the player's notebook when they\n            discover this clue.\n            ", manager=services.get_instance_manager(sims4.resources.Types.NOTEBOOK_ENTRY)), 'notification': TunableUiDialogNotificationSnippet(description='\n            The notification that will be displayed to the player when this clue\n            is discovered.\n            '), 'decoy_importance': TunableRange(description='\n            This controls which Sims are chosen as decoys. 1 means the decoy\n            must match the clue. Anything less allows non-matching Sims to be\n            decoys, but Sims that match clues with higher importance are\n            preferentially chosen.\n            ', tunable_type=float, default=1, minimum=0, maximum=1)}

    @classmethod
    def get_decoy_filter_term(cls):
        min_filter_score = 1 - cls.decoy_importance
        return RelaxedFilterTermProxy(cls.filter_term, min_filter_score)
