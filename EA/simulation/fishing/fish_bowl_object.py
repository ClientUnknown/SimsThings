from protocolbuffers import UI_pb2 as ui_protocolsfrom event_testing.tests import CompoundTestListimport broadcasters.environment_score.environment_score_componentimport objects.game_objectimport sims4.logimport vfxlogger = sims4.log.Logger('Fishing', default_owner='TrevorLindsey')
class FishBowl(objects.game_object.GameObject):
    VFX_SLOT_HASH = sims4.hash_util.hash32('_FX_')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fish_vfx = None
        self.add_component(FishBowlTooltipComponent(self, custom_tooltips=(), state_value_numbers=(), state_value_strings=(), tooltip_tests=CompoundTestList(), update_if_stat_changes=False))
        self._disable_tooltip()

    def get_fish(self):
        for obj in self.inventory_component:
            return obj

    def on_object_added_to_inventory(self, fish):
        current_fish = self.get_fish()
        if current_fish and current_fish is not fish:
            logger.error("The fish_added function was called but there is\n            either no fish in this fish bowl or the fish in it doesn't match\n            the fish making the function called.")
            return
        if current_fish.fishbowl_vfx is not None:
            self._fish_vfx = vfx.PlayEffect(self, current_fish.fishbowl_vfx, self.VFX_SLOT_HASH)
            self._fish_vfx.start()
        self._enable_tooltip()
        self.add_dynamic_component(objects.components.types.ENVIRONMENT_SCORE_COMPONENT)

    def on_object_removed_from_inventory(self, fish):
        if self._fish_vfx is not None:
            self._fish_vfx.stop()
            self._fish_vfx = None
        self._disable_tooltip()
        self.remove_component(objects.components.types.ENVIRONMENT_SCORE_COMPONENT)

    def _ui_metadata_gen(self):
        fish = self.get_fish()
        if fish is not None:
            yield from fish._ui_metadata_gen()
        else:
            return

    def get_environment_score(self, sim, ignore_disabled_state=False):
        fish = self.get_fish()
        if fish is None:
            return broadcasters.environment_score.environment_score_component.EnvironmentScoreComponent.ENVIRONMENT_SCORE_ZERO
        else:
            return fish.get_environment_score(sim, ignore_disabled_state=ignore_disabled_state)

    def potential_interactions(self, *args, **kwargs):
        fish = self.get_fish()
        if fish is not None:
            yield from fish.potential_interactions(*args, **kwargs)
        yield from super().potential_interactions(*args, **kwargs)

    def _enable_tooltip(self):
        self.hover_tip = ui_protocols.UiObjectMetadata.HOVER_TIP_CUSTOM_OBJECT
        self.update_object_tooltip()

    def _disable_tooltip(self):
        self.hover_tip = ui_protocols.UiObjectMetadata.HOVER_TIP_DISABLED
        self.update_object_tooltip()

class FishBowlTooltipComponent(objects.components.tooltip_component.TooltipComponent):

    def _ui_metadata_gen(self):
        fish = self.owner.get_fish()
        if fish is None:
            return
        yield from fish._ui_metadata_gen()
