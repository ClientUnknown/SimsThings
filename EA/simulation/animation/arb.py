from native.animation import arbClipEventType = arb.ClipEventTypeset_tag_functions = arb.set_tag_functions
class Arb(arb.NativeArb):

    def __init__(self, additional_blockers=()):
        super().__init__()
        self.additional_blockers = set(additional_blockers)

    @property
    def actor_ids(self):
        return self._actors()

    @property
    def request_info(self):
        return self._request_info

    def append(self, arb, safe_mode=True, force_sync=False):
        result = super().append(arb, safe_mode=safe_mode, force_sync=force_sync)
        self.additional_blockers.update(arb.additional_blockers)
        return result

    def add_request_info(self, animation_context, asm, state):
        pass

    def log_request_history(self, log_fn):
        pass
