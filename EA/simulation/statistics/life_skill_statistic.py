from protocolbuffers import Commodities_pb2, SimObjectAttributes_pb2 as protocolsfrom buffs.tunable import TunableBuffReferencefrom event_testing.resolver import SingleSimResolverfrom event_testing.tests import TunableTestSetfrom interactions.utils.display_mixin import get_display_mixinfrom objects import ALL_HIDDEN_REASONSfrom sims.sim_info_types import Agefrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableList, TunableTuple, TunableInterval, OptionalTunable, TunableEnumEntry, Tunable, TunableLiteralOrRandomValue, TunableReferencefrom sims4.tuning.tunable_base import ExportModes, GroupNamesfrom sims4.utils import classproperty, constpropertyfrom statistics.base_statistic import GalleryLoadBehaviorfrom statistics.commodity_messages import send_sim_life_skill_update_message, send_sim_life_skill_delete_messagefrom statistics.continuous_statistic_tuning import TunedContinuousStatisticfrom traits.traits import Traitfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetfrom vfx import TunablePlayEffectVariantimport servicesimport sims4.loglogger = sims4.log.Logger('LifeSkillStatistic', default_owner='bosee')LifeSkillDisplayMixin = get_display_mixin(has_description=True, has_icon=True, has_tooltip=False, use_string_tokens=False, export_modes=ExportModes.All)
class LifeSkillStatistic(HasTunableReference, LifeSkillDisplayMixin, TunedContinuousStatistic, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)):
    REMOVE_INSTANCE_TUNABLES = ('initial_value',)
    INSTANCE_TUNABLES = {'min_value_tuning': Tunable(description='\n            The minimum value for this stat.\n            ', tunable_type=float, default=-100, export_modes=ExportModes.All), 'max_value_tuning': Tunable(description='\n            The maximum value for this stat.\n            ', tunable_type=float, default=100, export_modes=ExportModes.All), 'initial_tuning': TunableLiteralOrRandomValue(description='\n            The initial value of this stat.  Can be a single value or range.\n            ', tunable_type=float, default=0, minimum=-100), 'initial_test_based_modifiers': TunableList(description='\n            List of tuples containing test and a random value. If the test passes,\n            a random value is added to the already random initial value. \n            ', tunable=TunableTuple(description='\n                A container for test and the corresponding random value.\n                ', initial_value_test=TunableTestSet(description='\n                    If test passes, then the random value tuned will be applied\n                    to the initial value. \n                    '), initial_modified_value=TunableLiteralOrRandomValue(description='\n                    The initial value of this stat.  Can be a single value or range.\n                    ', tunable_type=float, default=0, minimum=-100))), 'age_to_remove_stat': TunableEnumEntry(description='\n            When sim reaches this age, this stat will be removed permanently. \n            ', tunable_type=Age, default=Age.YOUNGADULT), 'missing_career_decay_rate': Tunable(description='\n            How much this life skill decay by if sim is late for school/work.\n            ', tunable_type=float, default=0.0), 'trait_on_age_up_list': TunableList(description='\n            A list of trait that will be applied on age up if this commodity \n            falls within the range specified in this tuple.\n            It also contains other visual information like VFX and notification.\n            ', tunable=TunableTuple(description='\n                A container for the range and corresponding information.\n                ', export_class_name='TunableTraitOnAgeUpTuple', life_skill_range=TunableInterval(description='\n                    If the commodity is in this range on age up, the trait\n                    will be applied. \n                    The vfx and notification will be played every time the \n                    range is crossed.\n                    ', tunable_type=float, default_lower=0, default_upper=100, export_modes=ExportModes.All), age_up_info=OptionalTunable(description="\n                    If enabled, this trait will be added on age up given the specified age. \n                    Otherwise, no trait will be added.\n                    We don't use loot because UI needs this trait exported for display.\n                    ", enabled_name='enabled_age_up_info', tunable=TunableTuple(export_class_name='TunableAgeUpInfoTuple', age_to_apply_trait=TunableEnumEntry(description='\n                            When sim reaches this age, this trait will be added on age up.\n                            ', tunable_type=Age, default=Age.YOUNGADULT), life_skill_trait=Trait.TunableReference(description='\n                            Trait that is added on age up.\n                            ', pack_safe=True)), export_modes=ExportModes.All), in_range_notification=OptionalTunable(tunable=TunableUiDialogNotificationSnippet(description='\n                        Notification that is sent when the commodity reaches this range.\n                        ')), out_of_range_notification=OptionalTunable(tunable=TunableUiDialogNotificationSnippet(description='\n                        Notification that is sent when the commodity exits this range.\n                        ')), vfx_triggered=TunablePlayEffectVariant(description='\n                    Vfx to play on the sim when commodity enters this threshold.\n                    ', tuning_group=GroupNames.ANIMATION), in_range_buff=OptionalTunable(tunable=TunableBuffReference(description='\n                        Buff that is added when sim enters this threshold.\n                        ')))), 'headline': TunableReference(description='\n            The headline that we want to send down when this life skill updates.\n            ', manager=services.get_instance_manager(sims4.resources.Types.HEADLINE), tuning_group=GroupNames.UI)}

    def __init__(self, tracker):
        self._vfx = None
        super().__init__(tracker, self.get_initial_value())
        self._last_update_value = None
        if not tracker.load_in_progress:
            self._apply_initial_value_modifier()

    @classproperty
    def persists_across_gallery_for_state(cls):
        if cls.gallery_load_behavior == GalleryLoadBehavior.LOAD_FOR_ALL or cls.gallery_load_behavior == GalleryLoadBehavior.LOAD_ONLY_FOR_OBJECT:
            return True
        return False

    @classmethod
    def get_initial_value(cls):
        return cls.initial_tuning.random_int()

    def _apply_initial_value_modifier(self):
        initial_value = self._value
        resolver = SingleSimResolver(self.tracker.owner)
        for initial_modifier in self.initial_test_based_modifiers:
            if initial_modifier.initial_value_test.run_tests(resolver):
                initial_value += initial_modifier.initial_modified_value.random_float()
        self.set_value(initial_value, from_add=True)

    def _update_value(self):
        old_value = self._value
        super()._update_value()
        new_value = self._value
        self._evaluate_threshold(old_value=old_value, new_value=new_value)

    def _evaluate_threshold(self, old_value=0, new_value=0, from_load=False):
        old_infos = []
        new_infos = []
        for range_info in self.trait_on_age_up_list:
            if old_value in range_info.life_skill_range:
                old_infos.append(range_info)
            if new_value in range_info.life_skill_range:
                new_infos.append(range_info)
        old_infos_set = set(old_infos)
        new_infos_set = set(new_infos)
        out_ranges = old_infos_set - new_infos_set
        in_ranges = new_infos_set - old_infos_set
        owner = self.tracker.owner
        is_household_sim = owner.is_selectable and owner.valid_for_distribution
        if not from_load:
            for out_range in out_ranges:
                if out_range.out_of_range_notification is not None and is_household_sim:
                    dialog = out_range.out_of_range_notification(owner, resolver=SingleSimResolver(owner))
                    dialog.show_dialog(additional_tokens=(owner,))
                if out_range.in_range_buff is not None:
                    owner.Buffs.remove_buff_by_type(out_range.in_range_buff.buff_type)
        for in_range in in_ranges:
            if in_range.in_range_notification is not None and (from_load or is_household_sim):
                dialog = in_range.in_range_notification(owner, resolver=SingleSimResolver(owner))
                dialog.show_dialog(additional_tokens=(owner,))
            if in_range.vfx_triggered is not None and (from_load or is_household_sim):
                if self._vfx is not None:
                    self._vfx.stop(immediate=True)
                    self._vfx = None
                sim = owner.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                if sim is not None:
                    self._vfx = in_range.vfx_triggered(sim)
                    self._vfx.start()
            if in_range.in_range_buff is not None:
                owner.Buffs.add_buff(in_range.in_range_buff.buff_type, buff_reason=in_range.in_range_buff.buff_reason)

    def _on_statistic_modifier_changed(self, notify_watcher=True):
        super()._on_statistic_modifier_changed(notify_watcher=notify_watcher)
        self.create_and_send_commodity_update_msg(is_rate_change=False)

    @constproperty
    def remove_on_convergence():
        return False

    def set_value(self, value, *args, from_load=False, interaction=None, **kwargs):
        old_value = self._value
        super().set_value(value, *args, from_load=from_load, interaction=interaction, **kwargs)
        new_value = self._value
        self._evaluate_threshold(old_value=old_value, new_value=new_value, from_load=from_load)
        if from_load:
            return
        self.create_and_send_commodity_update_msg(is_rate_change=False, from_add=kwargs.get('from_add', False))

    def on_remove(self, on_destroy=False):
        super().on_remove(on_destroy=on_destroy)
        if self._vfx is not None:
            self._vfx.stop(immediate=True)
            self._vfx = None

    def save_statistic(self, commodities, skills, ranked_statistics, tracker):
        message = protocols.Commodity()
        message.name_hash = self.guid64
        message.value = self.get_saved_value()
        if self._time_of_last_value_change:
            message.time_of_last_value_change = self._time_of_last_value_change.absolute_ticks()
        commodities.append(message)

    def create_and_send_commodity_update_msg(self, is_rate_change=True, allow_npc=False, from_add=False):
        current_value = self.get_value()
        change_rate = self.get_change_rate()
        life_skill_msg = Commodities_pb2.LifeSkillUpdate()
        life_skill_msg.sim_id = self.tracker.owner.id
        life_skill_msg.life_skill_id = self.guid64
        life_skill_msg.curr_value = current_value
        life_skill_msg.rate_of_change = change_rate
        life_skill_msg.is_from_add = from_add
        send_sim_life_skill_update_message(self.tracker.owner, life_skill_msg)
        if self._last_update_value is None:
            value_to_send = change_rate
        else:
            value_to_send = current_value - self._last_update_value
        self._last_update_value = current_value
        if value_to_send != 0 and not from_add:
            self.headline.send_headline_message(self.tracker.owner, value_to_send)

    def create_and_send_life_skill_delete_msg(self):
        life_skill_msg = Commodities_pb2.LifeSkillDelete()
        life_skill_msg.sim_id = self.tracker.owner.id
        life_skill_msg.life_skill_id = self.guid64
        send_sim_life_skill_delete_message(self.tracker.owner, life_skill_msg)
