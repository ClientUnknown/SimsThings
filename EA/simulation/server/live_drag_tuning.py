from interactions import ParticipantTypefrom interactions.inventory_loot import InventoryLootfrom interactions.money_payout import MoneyChangefrom interactions.utils.loot import LootActionsfrom interactions.utils.loot_ops import CollectibleShelveItem, StateChangeLootOp, SlotObjectsfrom interactions.utils.success_chance import SuccessChancefrom sims4.tuning.tunable import TunableVariant, TunableListfrom statistics.statistic_ops import TunableStatisticChangefrom ui.ui_dialog import UiDialogOkCancelimport enumimport event_testingimport objects.object_tests
class LiveDragTuning:
    LIVE_DRAG_SELL_DIALOG = UiDialogOkCancel.TunableFactory(description='\n        The dialog to show when the user tries to sell an object via Live Drag.\n        ')
    LIVE_DRAG_SELL_STACK_DIALOG = UiDialogOkCancel.TunableFactory(description='\n        The dialog to show when the user tries to sell a stack via Live Drag.\n        ')

class LiveDragState(enum.Int, export=False):
    NOT_LIVE_DRAGGING = ...
    LIVE_DRAGGING = ...

class LiveDragLocation(enum.Int, export=False):
    INVALID = 0
    GAMEPLAY_UI = 1
    BUILD_BUY = 2
    GAMEPLAY_SCRIPT = 3

class LiveDragPermission(enum.Int, export=False):
    NOT_IN_USE = ...
    HOUSEHOLD = ...
    STATE = ...

class TunableLiveDragTestVariant(TunableVariant):

    def __init__(self, description='A single tunable test for Live Dragged objects and their potential targets.', test_excluded=(), **kwargs):
        super().__init__(description=description, state=event_testing.state_tests.TunableStateTest(locked_args={'tooltip': None}), statistic=event_testing.statistic_tests.StatThresholdTest.TunableFactory(locked_args={'tooltip': None}), object_has_no_children=objects.object_tests.ObjectHasNoChildrenTest.TunableFactory(locked_args={'tooltip': None}), **kwargs)

class TunableLiveDragTestSet(event_testing.tests.TestListLoadingMixin):
    DEFAULT_LIST = event_testing.tests.TestList()

    def __init__(self, description=None, **kwargs):
        if description is None:
            description = 'A list of tests.  All tests must succeed to pass the TestSet.'
        super().__init__(description=description, tunable=TunableLiveDragTestVariant(), **kwargs)

class LiveDragLootActions(LootActions):
    INSTANCE_TUNABLES = {'loot_actions': TunableList(TunableVariant(statistics=TunableStatisticChange(locked_args={'advertise': False, 'chance': SuccessChance.ONE, 'tests': None}, include_relationship_ops=False), collectible_shelve_item=CollectibleShelveItem.TunableFactory(), inventory_loot=InventoryLoot.TunableFactory(subject_participant_type_options={'description': '\n                            The participant type who has the inventory that the\n                            object goes into during this loot.\n                            ', 'optional': False}, target_participant_type_options={'description': '\n                            The participant type of the object which gets to\n                            switch inventories in the loot.\n                            ', 'default_participant': ParticipantType.LiveDragActor}), state_change=StateChangeLootOp.TunableFactory(), money_loot=MoneyChange.TunableFactory(), slot_objects=SlotObjects.TunableFactory()))}

    def __iter__(self):
        return iter(self.loot_actions)
