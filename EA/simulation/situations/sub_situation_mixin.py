from situations.situation_types import SituationCallbackOption
class SubSituationMixin:

    def __init__(self, seed, **kwargs):
        super().__init__(seed, **kwargs)
        self._owner_situation = seed.extra_kwargs.get('owner_situation', None)

    def _destroy(self):
        super()._destroy()
        self._owner_situation = None

    @property
    def owner_situation(self):
        return self._owner_situation

class SubSituationOwnerMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sub_situation_ids = []

    def _on_sub_situation_end(self, sub_situation_id):
        pass

    def _destroy(self):
        super()._destroy()
        self._destroy_sub_situations()

    def _create_sub_situation(self, sub_situation_type, **kwargs):
        sub_situation_id = self.manager.create_situation(sub_situation_type, owner_situation=self, **kwargs)
        if sub_situation_id is not None:
            self._sub_situation_ids.append(sub_situation_id)
            self.manager.register_for_callback(sub_situation_id, SituationCallbackOption.END_OF_SITUATION, self._on_sub_situation_end_callback)
            self.manager.disable_save_to_situation_manager(sub_situation_id)
        return sub_situation_id

    def _on_sub_situation_end_callback(self, sub_situation_id, situation_callback_option, data):
        if sub_situation_id in self._sub_situation_ids:
            self._sub_situation_ids.remove(sub_situation_id)
            self._on_sub_situation_end(sub_situation_id)

    def _destroy_sub_situation(self, sub_situation_id):
        if sub_situation_id in self._sub_situation_ids:
            self._sub_situation_ids.remove(sub_situation_id)
            self.manager.destroy_situation_by_id(sub_situation_id)

    def _destroy_sub_situations(self):
        for sub_situation_id in tuple(self._sub_situation_ids):
            self.manager.destroy_situation_by_id(sub_situation_id)
        self._sub_situation_ids.clear()

    def _get_sub_situation_by_id(self, sub_situation_id):
        sub_situation = self.manager.get(sub_situation_id)
        return sub_situation

    def _get_sub_situations(self):
        return tuple(self.manager[sub_situation_id] for sub_situation_id in self._sub_situation_ids if sub_situation_id in self.manager)
