import enumimport sims4.callback_utils
class FinishingType(enum.Int, export=False):
    KILLED = ...
    AUTO_EXIT = ...
    DISPLACED = ...
    NATURAL = ...
    RESET = ...
    USER_CANCEL = ...
    SI_FINISHED = ...
    TARGET_DELETED = ...
    FAILED_TESTS = ...
    TRANSITION_FAILURE = ...
    INTERACTION_INCOMPATIBILITY = ...
    INTERACTION_QUEUE = ...
    PRIORITY = ...
    SOCIALS = ...
    WAIT_IN_LINE = ...
    OBJECT_CHANGED = ...
    SITUATIONS = ...
    CRAFTING = ...
    LIABILITY = ...
    DIALOG = ...
    CONDITIONAL_EXIT = ...
    FIRE = ...
    WEDDING = ...
    ROUTING_FORMATION = ...
    UNKNOWN = ...

class InteractionFinisher:
    CANCELED = frozenset([FinishingType.USER_CANCEL, FinishingType.SI_FINISHED, FinishingType.TARGET_DELETED, FinishingType.FAILED_TESTS, FinishingType.TRANSITION_FAILURE, FinishingType.INTERACTION_INCOMPATIBILITY, FinishingType.INTERACTION_QUEUE, FinishingType.PRIORITY, FinishingType.SOCIALS, FinishingType.WAIT_IN_LINE, FinishingType.OBJECT_CHANGED, FinishingType.SITUATIONS, FinishingType.CRAFTING, FinishingType.LIABILITY, FinishingType.DIALOG, FinishingType.CONDITIONAL_EXIT, FinishingType.FIRE, FinishingType.WEDDING, FinishingType.ROUTING_FORMATION])

    def __init__(self):
        self._history = []
        self._pending = []
        self._on_finishing_callbacks = sims4.callback_utils.CallableList()

    def on_finishing_move(self, move, interaction):
        self._pending.append(move)
        for pending_move in self._pending:
            if pending_move not in self._history:
                self._history.append(pending_move)
        self._on_finishing_callbacks(interaction)
        self._pending.clear()

    def on_pending_finishing_move(self, move, interaction):
        if self.is_finishing:
            self.on_finishing_move(move, interaction)
        else:
            self._pending.append(move)

    def register_callback(self, callback):
        self._on_finishing_callbacks.append(callback)

    def unregister_callback(self, callback):
        if callback in self._on_finishing_callbacks:
            self._on_finishing_callbacks.remove(callback)

    def can_run_subinteraction(self):
        return not self.is_finishing and not self._pending

    @property
    def is_finishing(self):
        return bool(self._history)

    @property
    def has_been_killed(self):
        for move in self._history:
            if move == FinishingType.KILLED:
                return True
        return False

    @property
    def has_been_canceled(self):
        for move in self._history:
            if move in self.CANCELED:
                return True
        return False

    @property
    def has_been_user_canceled(self):
        for move in self._history:
            if move == FinishingType.USER_CANCEL:
                return True
        return False

    @property
    def has_been_reset(self):
        for move in self._history:
            if move == FinishingType.RESET:
                return True
        return False

    @property
    def transition_failed(self):
        return any(move == FinishingType.TRANSITION_FAILURE for move in self._history)

    @property
    def is_finishing_naturally(self):
        return self._history and self._history[0] == FinishingType.NATURAL

    @property
    def finishing_type(self):
        if self._history:
            return self._history[0]

    @property
    def was_initially_displaced(self):
        return self._history and self._history[0] == FinishingType.DISPLACED

    @property
    def has_pending_natural_finisher(self):
        if not self._pending:
            return True
        for pending_move in self._pending:
            if pending_move == FinishingType.NATURAL:
                return True
        return False

    def get_pending_finishing_move_debug_string(self):
        return ','.join([str(move) for move in self._pending])

    def __repr__(self):
        if not self._history:
            return 'Not Finishing'
        else:
            return ','.join([str(move) for move in self._history])
