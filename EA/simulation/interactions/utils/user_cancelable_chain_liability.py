from interactions.liability import ReplaceableLiabilityfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactoryimport sims4logger = sims4.log.Logger('UserCancelableChainLiability')
class UserCancel:

    def __init__(self):
        self.requested = False

class UserCancelableChainLiability(ReplaceableLiability, HasTunableFactory, AutoFactoryInit):
    LIABILITY_TOKEN = 'UserCancelableChainLiability'

    def __init__(self, interaction, **kwargs):
        super().__init__(**kwargs)
        self._user_cancel = UserCancel()

    def merge(self, interaction, key, new_liability):
        interaction.remove_liability(key)
        new_liability._user_cancel = self._user_cancel
        return new_liability

    @property
    def was_user_cancel_requested(self):
        return self._user_cancel.requested

    def set_user_cancel_requested(self):
        self._user_cancel.requested = True

    def gsi_text(self):
        return str.format('{} : user_cancel.requested={}', super().gsi_text(), self._user_cancel.requested)
