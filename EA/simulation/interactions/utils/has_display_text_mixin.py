from sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableVariant
class HasDisplayTextMixin:
    TEXT_USE_DEFAULT = 0
    TEXT_NONE = 1
    FACTORY_TUNABLES = {'text': TunableVariant(description="\n            Specify the display text to use for this tunable. This tuning\n            structure may be shared across multiple tunables. It is up to the\n            system consuming the tunable to determine in which ways the tuned\n            display text is used.\n            \n            e.g. Loot Operations\n             The adventure system auto-generates notifications based on the loot\n             that was awarded from a chance card. A loot's display text, if\n             used, will be an item in the generated bulleted list. The ability\n             to override display text allows tuners to set custom next in such\n             notifications.\n             \n            e.g. Reward Tuning\n             Rewards have display text so that, similarly to adventures, a\n             bulleted list of entries can be auto-generated when obtained by a\n             Sim. Use this tunable to control the text of such entries.\n            ", override=TunableLocalizedStringFactory(description='\n                Specify a string override. The tokens are different depending on\n                the type of tunable.\n                '), locked_args={'use_default': TEXT_USE_DEFAULT, 'no_text': TEXT_NONE}, default='use_default')}

    def __init__(self, *args, text=None, **kwargs):
        super().__init__(*args, **kwargs)
        if text is None and hasattr(self, 'text'):
            self._HasDisplayTextMixin__display_text = self.text
        else:
            self._HasDisplayTextMixin__display_text = text

    def get_display_text(self, resolver=None):
        if self._HasDisplayTextMixin__display_text == self.TEXT_USE_DEFAULT:
            return self._get_display_text(resolver=resolver)
        if self._HasDisplayTextMixin__display_text == self.TEXT_NONE:
            return
        return self._HasDisplayTextMixin__display_text(*self._get_display_text_tokens(resolver=resolver))

    def _get_display_text(self, resolver=None):
        pass

    def _get_display_text_tokens(self, resolver=None):
        return ()
