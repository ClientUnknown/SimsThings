from bucks.bucks_enums import BucksTypefrom bucks.bucks_utils import BucksUtilsfrom interactions import ParticipantTypeSingleSimfrom interactions.base.picker_interaction import PickerSuperInteractionfrom sims4.localization import LocalizationHelperTuningfrom sims4.tuning.tunable import Tunable, TunableEnumEntry, TunableListfrom sims4.utils import flexmethodfrom ui.ui_dialog_picker import ObjectPickerRowfrom interactions.utils.tunable import TunableContinuationfrom sims4.tuning.tunable_base import GroupNames
class BucksPerkPickerSuperInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'is_add': Tunable(description='\n            If this interaction is trying to add a bucks perk to the sim or to\n            remove a bucks perk from the sim.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.PICKERTUNING), 'bucks_type': TunableEnumEntry(description='\n            The type of Bucks required to unlock/lock this perk.\n            ', tunable_type=BucksType, default=BucksType.INVALID, pack_safe=True, invalid_enums=(BucksType.INVALID,), tuning_group=GroupNames.PICKERTUNING), 'continuations': TunableList(description='\n            List of continuations to push if a buff is actually selected.\n            ', tunable=TunableContinuation(), tuning_group=GroupNames.PICKERTUNING), 'subject': TunableEnumEntry(description='\n            From whom the BucksPerks should be added/removed.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.TargetSim, tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        participant = self.get_participant(self.subject)
        self._show_picker_dialog(participant, target_sim=participant)
        return True

    @classmethod
    def _bucks_perk_selection_gen(cls, participant):
        bucks_perk_tracker = BucksUtils.get_tracker_for_bucks_type(cls.bucks_type, participant.id, add_if_none=True)
        get_unlocked = not cls.is_add
        for perk in bucks_perk_tracker.all_perks_of_type_with_lock_state_gen(cls.bucks_type, get_unlocked):
            yield perk

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        participant = inst_or_cls.get_participant(inst_or_cls.subject, sim=context.sim, target=target)
        for perk in cls._bucks_perk_selection_gen(participant):
            if perk.display_name:
                display_name = perk.display_name(participant)
                row = ObjectPickerRow(name=display_name, row_description=perk.perk_description(participant), icon=perk.icon.key, tag=perk)
                yield row

    def on_choice_selected(self, choice_tag, **kwargs):
        perk = choice_tag
        if perk is None:
            return
        participant = self.get_participant(self.subject)
        bucks_perk_tracker = BucksUtils.get_tracker_for_bucks_type(self.bucks_type, participant.id)
        if self.is_add:
            bucks_perk_tracker.pay_for_and_unlock_perk(perk)
        else:
            bucks_perk_tracker.lock_perk(perk, True)
        for continuation in self.continuations:
            self.push_tunable_continuation(continuation)
