from interactions.liability import SharedLiabilityDELETE_OBJECT_LIABILITY = 'DeleteObjectLiability'
class DeleteObjectLiability(SharedLiability):

    def __init__(self, obj_list, source_liability=None):
        super().__init__(source_liability=source_liability)
        self._delete_objects = obj_list

    def shared_release(self):
        for obj in self._delete_objects:
            obj.schedule_destroy_asap()
        self._delete_objects.clear()

    def merge(self, interaction, key, new_liability):
        new_liability._delete_objects.update(self._delete_objects)
        return new_liability

    def create_new_liability(self, interaction):
        return self.__class__(self._delete_objects, source_liability=self)
