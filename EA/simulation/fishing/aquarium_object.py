import collectionsfrom sims4 import hash_utilimport broadcasters.environment_scoreimport objects.game_objectimport sims4.tuning.tunableimport sims4.tuning.tunable_baseimport vfx
class Aquarium(objects.game_object.GameObject):
    VFX_SLOT_NAME = '_FX_fish_'
    INSTANCE_TUNABLES = {'fish_vfx_prefix': sims4.tuning.tunable.Tunable(description='\n            prefix gets added to beginning of every effect. This way we can\n            swap out effects if we need to for different aquariums.\n            i.e. if the effect on the fish is "trout_vfx" and we put "ep04" here, it will\n            change it to "ep04_trout_vfx". This will apply to every fish object\n            in this aquarium.\n            ', tunable_type=str, default=None, tuning_group=sims4.tuning.tunable_base.GroupNames.FISHING)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fish_vfx_handles = []

    def on_object_added_to_inventory(self, obj):
        for _ in range(obj.stack_count()):
            self._add_fish_effect(obj)
        self.add_dynamic_component(objects.components.types.ENVIRONMENT_SCORE_COMPONENT)

    def on_object_removed_from_inventory(self, obj):
        for _ in range(obj.stack_count()):
            self._remove_fish_effect(obj.id)
        if len(self.inventory_component) == 0:
            self._fish_vfx_handles.clear()
            self.remove_component(objects.components.types.ENVIRONMENT_SCORE_COMPONENT)

    def on_object_stack_id_updated(self, obj, old_obj_id, old_stack_count):
        for (i, fish_vfx_handle) in enumerate(self._fish_vfx_handles):
            if fish_vfx_handle is not None and fish_vfx_handle[0] == old_obj_id:
                self._fish_vfx_handles[i] = (obj.id, fish_vfx_handle[1])
        stack_delta = obj.stack_count() - old_stack_count
        if stack_delta > 0:
            for _ in range(stack_delta):
                self._add_fish_effect(obj)
        elif stack_delta < 0:
            for _ in range(-stack_delta):
                self._remove_fish_effect(obj.id)

    def get_environment_score(self, sim, ignore_disabled_state=False):
        if len(self.inventory_component) > 0:
            total_mood_scores = collections.Counter()
            total_positive_score = 0
            total_negative_score = 0
            total_contributions = []
            for fish in self.inventory_component:
                (mood_scores, negative_score, positive_score, contributions) = fish.get_environment_score(sim=sim, ignore_disabled_state=ignore_disabled_state)
                total_mood_scores.update(mood_scores)
                total_positive_score += positive_score
                total_negative_score += negative_score
                total_contributions.extend(contributions)
            return (total_mood_scores, total_negative_score, total_positive_score, total_contributions)
        else:
            return broadcasters.environment_score.environment_score_component.EnvironmentScoreComponent.ENVIRONMENT_SCORE_ZERO

    def _add_fish_effect(self, fish):
        if None in self._fish_vfx_handles:
            index = self._fish_vfx_handles.index(None)
        else:
            index = len(self._fish_vfx_handles)
            self._fish_vfx_handles.append(None)
        vfx_data = fish.inventory_to_fish_vfx.get(self.inventory_component.inventory_type, None)
        if vfx_data is not None:
            vfx_index = index + 1
            if self.fish_vfx_prefix is not None:
                vfx_name = '{}_{}_{}'.format(self.fish_vfx_prefix, vfx_data.vfx_name, vfx_index)
            else:
                vfx_name = '{}_{}'.format(vfx_data.vfx_name, vfx_index)
            vfx_slot_name = '{}{}'.format(vfx_data.vfx_base_bone_name, vfx_index)
        else:
            vfx_name = fish.fishbowl_vfx
            vfx_slot_name = self.VFX_SLOT_NAME
        vfx_slot = hash_util.hash32(vfx_slot_name)
        play_effect_handle = vfx.PlayEffect(self, vfx_name, joint_name=vfx_slot)
        play_effect_handle.start()
        self._fish_vfx_handles[index] = (fish.id, play_effect_handle)

    def _remove_fish_effect(self, fish_obj_id):
        for (i, fish_vfx_handle) in enumerate(self._fish_vfx_handles):
            if fish_vfx_handle is not None and fish_vfx_handle[0] == fish_obj_id:
                fish_vfx_handle[1].stop()
                self._fish_vfx_handles[i] = None
                break
