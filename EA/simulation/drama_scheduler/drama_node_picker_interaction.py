from collections import defaultdictimport telemetry_helperfrom drama_scheduler.drama_node import DramaNodeScoringBucketfrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing.resolver import SingleSimResolverfrom interactions.base.picker_interaction import PickerSuperInteractionfrom interactions.utils.loot import LootActionsfrom sims4.tuning.tunable import OptionalTunable, TunableEnumEntry, TunableList, Tunable, TunableEnumSetfrom sims4.utils import flexmethodimport servicesimport sims4.loglogger = sims4.log.Logger('DramaNodePickerInteraction', default_owner='bosee')TELEMETRY_GROUP_DRAMA_NODE_PICKER = 'DPCK'TELEMETRY_HOOK_DRAMA_PICKER_NODE_SELECTED = 'DSEL'TELEMETRY_HOOK_DRAMA_PICKER_NODE_PRESENTED = 'DSHW'TELEMETRY_PICKER_INSTANCE_ID = 'piid'TELEMETRY_PICKER_DRAMA_NODE_ID = 'dnid'TELEMETRY_PICKER_DRAMA_NODE_ENABLED = 'dnen'telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_DRAMA_NODE_PICKER)
class DramaNodePickerInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'buckets': OptionalTunable(description='\n            If enabled, we only return nodes from these buckets.\n            Drama nodes with no buckets are rejected. The order in which\n            buckets are tuned here will determine the order in which buckets\n            are shown in the picker. Gigs from the first bucket will appear\n            at the top of the picker and so on.\n            ', tunable=TunableList(tunable=TunableEnumEntry(description='\n                    Bucket to test against.\n                    ', tunable_type=DramaNodeScoringBucket, default=DramaNodeScoringBucket.DEFAULT), unique_entries=True)), 'loot_when_empty': OptionalTunable(description="\n            If enabled, we run this loot when picker is empty and don't display\n            the empty picker.\n            If disabled, picker will appear empty.\n            ", tunable=TunableList(description='\n                Loot applied if the picker is going to be empty.\n                ', tunable=LootActions.TunableReference(pack_safe=True))), 'use_only_scheduled': Tunable(description='\n            If checked, this picker will only consider drama nodes that have\n            been scheduled by the drama scheduler service. This is usually the\n            desired behavior except in special circumstances like debugging.\n            ', tunable_type=bool, default=True), 'disable_row_if_visibily_tests_fail': Tunable(description="\n            If checked, we will grey out any row if the corresponding drama\n            node failed its visibility testing. If not checked, the row won't\n            be shown.\n            ", tunable_type=bool, default=False), 'run_visibility_tests': Tunable(description='\n            If checked, This picker will run visibility tests on a drama node\n            to decide whether it should be shown. Otherwise, all picker drama\n            nodes will be available.\n            ', tunable_type=bool, default=True)}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.target, target_sim=self.target)
        return True

    def _show_picker_dialog(self, owner, **kwargs):
        if self.use_pie_menu():
            return
        dialog = self._create_dialog(owner, **kwargs)
        if self.loot_when_empty is not None and len(dialog.picker_rows) == 0:
            resolver = SingleSimResolver(owner.sim_info)
            for loot in self.loot_when_empty:
                loot.apply_to_resolver(resolver)
        else:
            for picker_row in dialog.picker_rows:
                self.send_telemetry(TELEMETRY_HOOK_DRAMA_PICKER_NODE_PRESENTED, picker_row.tag, picker_row.is_enable)
            dialog.show_dialog()

    def send_telemetry(self, hook_tag, drama_node, is_enabled=None):
        with telemetry_helper.begin_hook(telemetry_writer, hook_tag, sim_info=self.sim.sim_info) as hook:
            hook.write_int(TELEMETRY_PICKER_INSTANCE_ID, self.aop_id)
            hook.write_int(TELEMETRY_PICKER_DRAMA_NODE_ID, drama_node.guid64)
            if is_enabled is not None:
                hook.write_bool(TELEMETRY_PICKER_DRAMA_NODE_ENABLED, is_enabled)

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        if inst_or_cls.use_only_scheduled:
            drama_nodes = iter(services.drama_scheduler_service().all_nodes_gen())
        else:
            drama_node_manager = services.get_instance_manager(sims4.resources.Types.DRAMA_NODE)
            drama_nodes = (drama_node() for drama_node in drama_node_manager.get_ordered_types())
        if inst_or_cls.buckets:
            picker_rows_by_bucket = defaultdict(list)
        else:
            picker_rows = list()
        for drama_node in drama_nodes:
            if drama_node.drama_node_type == DramaNodeType.PICKER:
                if inst_or_cls.buckets and drama_node.scoring and drama_node.scoring.bucket not in inst_or_cls.buckets:
                    pass
                else:
                    result = drama_node.create_picker_row(owner=target, run_visibility_tests=inst_or_cls.run_visibility_tests, disable_row_if_visibily_tests_fail=inst_or_cls.disable_row_if_visibily_tests_fail)
                    if result is not None:
                        if inst_or_cls.buckets:
                            picker_rows_by_bucket[drama_node.scoring.bucket].append(result)
                        else:
                            picker_rows.append(result)
        if inst_or_cls.buckets:
            for bucket in inst_or_cls.buckets:
                yield from picker_rows_by_bucket[bucket]
        else:
            yield from picker_rows

    def on_choice_selected(self, choice_tag, **kwargs):
        if choice_tag is None:
            return
        self.send_telemetry(TELEMETRY_HOOK_DRAMA_PICKER_NODE_SELECTED, choice_tag)
        choice_tag.on_picker_choice(owner=self.sim.sim_info)
