from interactions import ParticipantTypeObject, PipelineProgressfrom interactions.constraints import Anywherefrom interactions.interaction_finisher import FinishingTypefrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableEnumEntryfrom socials.group import SocialGroup
class SideGroup(SocialGroup):
    INSTANCE_SUBCLASSES_ONLY = True

    def _create_social_geometry(self, sim, call_on_changed=True):
        pass

    def _clear_social_geometry(self, sim, call_on_changed=True):
        pass

    def _group_geometry_changed(self):
        pass

    def _create_adjustment_alarm(self):
        pass

    def try_relocate_around_focus(self, *args, **kwargs):
        return True
lock_instance_tunables(SideGroup, adjust_sim_positions_dynamically=True, is_side_group=True, include_default_facing_constraint=False)
class GameGroup(SideGroup):
    INSTANCE_TUNABLES = {'social_anchor_object': TunableEnumEntry(description='\n            The participant type used to find an object with the game component.\n            This object will also be used as the social anchor for your social\n            group to ensure the players of the game are around the object.\n            ', tunable_type=ParticipantTypeObject, default=ParticipantTypeObject.ActorSurface)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry = None

    @classmethod
    def make_constraint_default(cls, *args, **kwargs):
        return Anywhere()

    @property
    def _los_constraint(self):
        return Anywhere()

    def get_potential_mixer_targets(self, sim):
        return set()

    def get_constraint(self, sim):
        return Anywhere()

    def _remove(self, sim, interaction=None, **kwargs):

        def _remove_sim(interaction):
            if interaction.pipeline_progress != PipelineProgress.EXITED:
                return
            if self._anchor_object is not None:
                game = self._anchor_object.game_component
                if game is not None:
                    game.remove_player(sim)
                    if game.current_game is None:
                        self.shutdown(finishing_type=FinishingType.NATURAL)

        interaction.on_pipeline_change_callbacks.append(_remove_sim)
        super()._remove(sim, **kwargs)

class InObjectGroup(SideGroup):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry = None

    @classmethod
    def make_constraint_default(cls, *args, **kwargs):
        return Anywhere()

    def get_constraint(self, sim):
        return Anywhere()
