from event_testing.test_events import TestEventfrom fishing.fishing_tuning import FishingTuningfrom notebook.notebook_entry import SubEntryDatafrom sims4.tuning.tunable import TunableMapping, TunableReference, TunablePercentimport buffs.tunableimport event_testingimport fishing.fish_bowl_objectimport interactionsimport objects.components.inventory_enumsimport objects.components.stateimport objects.game_objectimport objects.game_object_propertiesimport servicesimport sims4.localizationimport sims4.tuning.tunableimport sims4.tuning.tunable_baselogger = sims4.log.Logger('Fishing', default_owner='TrevorLindsey')
class Fish(objects.game_object.GameObject):
    INSTANCE_TUNABLES = {'fishbowl_vfx': sims4.tuning.tunable.Tunable(description='\n            The name of the VFX to use when this fish is dropped in a fish bowl.\n            ', tunable_type=str, default=None, tuning_group=sims4.tuning.tunable_base.GroupNames.FISHING), 'inventory_to_fish_vfx': sims4.tuning.tunable.TunableMapping(description='\n            The inventory type to fish vfx to play when fish is placed in\n            inventory type.  If inventory type does not exist in mapping, use\n            fishbowl_vfx as fallback vfx to play.\n            ', key_type=sims4.tuning.tunable.TunableEnumEntry(tunable_type=objects.components.inventory_enums.InventoryType, default=objects.components.inventory_enums.InventoryType.UNDEFINED), value_type=sims4.tuning.tunable.TunableTuple(vfx_name=sims4.tuning.tunable.Tunable(tunable_type=str, default=''), vfx_base_bone_name=sims4.tuning.tunable.Tunable(tunable_type=str, default='_FX_fish_')), key_name='inventory_type', value_name='base vfx name', tuning_group=sims4.tuning.tunable_base.GroupNames.FISHING), 'fishing_hole_vfx': sims4.tuning.tunable.Tunable(description='\n            The name of the VFX to use at the fishing hole (pond) where this\n            fish can be caught.\n            ', tunable_type=str, default=None, tuning_group=sims4.tuning.tunable_base.GroupNames.FISHING), 'fishing_spot_vfx': sims4.tuning.tunable.Tunable(description='\n            The name of the VFX to use at the fishing spot (sign) where this\n            fish can be caught.\n            ', tunable_type=str, default=None, tuning_group=sims4.tuning.tunable_base.GroupNames.FISHING), 'wall_mounted_object': sims4.tuning.tunable.TunableReference(description='\n            When this fish is mounted to the wall, this is the object it will turn in to.\n            ', manager=services.definition_manager(), tuning_group=sims4.tuning.tunable_base.GroupNames.FISHING), 'catchable_tests': event_testing.tests.TunableTestSet(description="\n            If these tests pass, the Sim can catch this fish.\n            If these tests fail, the Sim can not catch this fish.\n            This doesn't stop the Sim from trying to catch these fish, but it\n            will never happen.\n            \n            DO NOT add bait buffs here. Those should be added to the Required Bait tunable field.\n            \n            When testing on fishing skill be sure to enable 'Use Effective\n            Skill Level' since baits can change it.\n            ", tuning_group=sims4.tuning.tunable_base.GroupNames.FISHING), 'required_bait_buff': sims4.tuning.tunable.OptionalTunable(description='\n            The bait buff that is required to catch this fish.\n            \n            If this is tuned, this fish can not be caught without the required bait.\n            If this is not tuned, this fish can be caught with or without bait.\n            \n            Note: Bait buffs are the only buffs that should be tuned here.\n            If you want to gate this fish on a non-bait buff, use the Catchable Tests.\n            ', tunable=sims4.tuning.tunable.TunableReference(manager=services.buff_manager()), tuning_group=sims4.tuning.tunable_base.GroupNames.FISHING), 'fish_type': sims4.tuning.tunable.Tunable(description="\n            The asm parameter for the size of the fish. If you're unsure what\n            this should be set to, talk to the animator or modeler and ask what\n            fish type this fish should be.\n            ", tunable_type=str, default=None, source_query=sims4.tuning.tunable_base.SourceQueries.SwingEnumNamePattern.format('fishType'), tuning_group=sims4.tuning.tunable_base.GroupNames.FISHING), 'skill_weight_curve': sims4.tuning.geometric.TunableCurve(description="\n            This curve represents the mean weight in kg of the fish based on the Sims's fishing skill level.\n            The X axis is the Sim's effective fishing skill level.\n            The Y axis is the mean weight, in kg, of the fish.\n            The mean weight will be modified by the Mean Weight Deviation field.\n            ", x_axis_name='Effective Fishing Skill Level', y_axis_name='Mean Weight (kg)', tuning_group=sims4.tuning.tunable_base.GroupNames.FISHING), 'mean_weight_deviation': sims4.tuning.tunable.Tunable(description='\n            This is the amount of deviation from the mean the weight can be.\n            The mean weight is first decided then multiplied by this number.\n            The result is both added and subtracted from the mean weight to get\n            the min/max possible weight of the fish. We then pick a random\n            number between the min and max to determine the final weight of the\n            fish.\n            \n            Example: Assume Mean Weight = 2 and Mean Weight Deviation = 0.2\n            2 x 0.2 = 0.4\n            min = 2 - 0.4 = 1.6\n            max = 2 + 0.4 = 2.4\n            A random number is chosen between 1.6 and 2.4, inclusively.\n            ', tunable_type=float, default=1, tuning_group=sims4.tuning.tunable_base.GroupNames.FISHING), 'weight_money_multiplier': sims4.tuning.tunable.Tunable(description='\n            The weight of the fish will be multiplied by this number then the\n            result of that multiplication will be added to the base value of\n            the fish.\n            ', tunable_type=float, default=1, tuning_group=sims4.tuning.tunable_base.GroupNames.FISHING), 'global_policy_value_mapping': TunableMapping(description='\n            The mapping of global policies that when enacted are used to\n            increment the base value of the fish by a percent of its original value.\n            ', key_type=TunableReference(description='\n                The global policy that when completed updates the cost of the\n                fish by the paired percent.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('GlobalPolicy',), pack_safe=True), value_type=TunablePercent(description="\n                The percent of the fish's value to increment the base value.\n                ", default=50), tuning_group=sims4.tuning.tunable_base.GroupNames.FISHING), 'buffs_on_catch': sims4.tuning.tunable.TunableList(description='\n            A list of buffs to award the Sim when they catch this fish.\n            ', tunable=buffs.tunable.TunableBuffReference(), tuning_group=sims4.tuning.tunable_base.GroupNames.FISHING)}
    FISHING_SKILL_STATISTIC = sims4.tuning.tunable.TunableReference(description='\n        The fishing skill stat. This just makes lookups on the fishing skill easier.\n        ', manager=services.statistic_manager())
    FISH_FRESHNESS_STATE = objects.components.state.ObjectState.TunableReference(description='\n        The statistic used for fish freshness.\n        ')
    WEIGHT_STATISTIC = sims4.tuning.tunable.TunableReference(description='\n        The weight statistic that will be added to the fish and set as they\n        are caught.\n        ', manager=services.statistic_manager())
    LOCALIZED_WEIGHT = sims4.localization.TunableLocalizedStringFactory(description="\n        How the weight should appear when used in other strings, like the\n        'catch fish' notification. i.e. '2.2 kg'\n        {0.Number} = weight value\n        ")
    MINIMUM_FISH_WEIGHT = 0.1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._active_global_policy_modifiers = None

    @sims4.utils.flexmethod
    def can_catch(cls, inst, resolver, require_bait=False):
        inst_or_cls = inst if inst is not None else cls
        if require_bait:
            sim = resolver.get_participant(interactions.ParticipantType.Actor)
            if inst_or_cls.required_bait_buff and not sim.has_buff(inst_or_cls.required_bait_buff):
                return False
        return inst_or_cls.catchable_tests.run_tests(resolver)

    def on_add(self):
        super().on_add()
        self.add_state_changed_callback(self._on_state_or_name_changed)
        self.add_name_changed_callback(self._on_state_or_name_changed)
        self._update_fish_cost(self.WEIGHT_STATISTIC.default_value)
        self._register_for_tuned_global_policy_events()

    def _update_fish_cost(self, new_cost):
        fish_stat_tracker = self.get_tracker(self.WEIGHT_STATISTIC)
        fish_stat_tracker.set_value(self.WEIGHT_STATISTIC, new_cost)
        self.base_value += int(new_cost*self.weight_money_multiplier)
        self.remove_global_policy_value_mod()
        self.add_global_policy_value_mod()
        self.update_object_tooltip()

    def _register_for_tuned_global_policy_events(self):
        active_global_policies = self._active_global_policy_modifiers is not None
        for policy in self.global_policy_value_mapping:
            if active_global_policies and policy in self._active_global_policy_modifiers:
                pass
            else:
                services.get_event_manager().register_with_custom_key(self, TestEvent.GlobalPolicyProgress, policy)

    def remove_global_policy_value_mod(self):
        if self._active_global_policy_modifiers is None:
            return
        global_policy_service = services.global_policy_service()
        if global_policy_service is None:
            return
        total_percent_decrease = 1.0
        policies_to_remove = []
        enacted_policies = global_policy_service.get_enacted_global_policies()
        for modifying_policy in self._active_global_policy_modifiers:
            if modifying_policy not in enacted_policies:
                total_percent_decrease += self.global_policy_value_mapping.get(type(modifying_policy))
                services.get_event_manager().register_with_custom_key(self, TestEvent.GlobalPolicyProgress, type(modifying_policy))
                policies_to_remove.append(modifying_policy)
        for policy_to_remove in policies_to_remove:
            self._active_global_policy_modifiers.remove(policy_to_remove)
        if total_percent_decrease != 0:
            self.base_value = int(self.base_value/total_percent_decrease)

    def add_global_policy_value_mod(self):
        if not self.global_policy_value_mapping:
            return
        global_policy_service = services.global_policy_service()
        if global_policy_service is None:
            return
        total_percent_increase = 0
        active_global_policy_modifiers = self._active_global_policy_modifiers is not None
        for enacted_policy in global_policy_service.get_enacted_global_policies():
            if active_global_policy_modifiers and enacted_policy in self._active_global_policy_modifiers:
                pass
            else:
                policy_percent_increase = self.global_policy_value_mapping.get(type(enacted_policy))
                if policy_percent_increase:
                    if not active_global_policy_modifiers:
                        self._active_global_policy_modifiers = [enacted_policy]
                    else:
                        self._active_global_policy_modifiers.append(enacted_policy)
                    services.get_event_manager().register_with_custom_key(self, TestEvent.GlobalPolicyProgress, type(enacted_policy))
                    total_percent_increase += policy_percent_increase
        self.base_value += int(self.base_value*total_percent_increase)

    def get_object_property(self, property_type):
        if property_type == objects.game_object_properties.GameObjectProperty.FISH_FRESHNESS:
            return self.get_state(self.FISH_FRESHNESS_STATE).display_name
        else:
            return super().get_object_property(property_type)

    def initialize_fish(self, sim):
        fishing_stat = sim.get_statistic(self.FISHING_SKILL_STATISTIC)
        skill_level = 1 if fishing_stat is None else sim.get_effective_skill_level(fishing_stat)
        mean_weight = self.skill_weight_curve.get(skill_level)
        deviation = mean_weight*self.mean_weight_deviation
        weight_min = max(mean_weight - deviation, self.MINIMUM_FISH_WEIGHT)
        weight_max = mean_weight + deviation
        actual_weight = sims4.random.uniform(weight_min, weight_max)
        self._update_fish_cost(actual_weight)
        self.update_ownership(sim)

    def get_catch_buffs_gen(self):
        yield from self.buffs_on_catch

    def get_localized_weight(self):
        stat_tracker = self.get_tracker(self.WEIGHT_STATISTIC)
        return self.LOCALIZED_WEIGHT(stat_tracker.get_user_value(self.WEIGHT_STATISTIC))

    def get_notebook_information(self, notebook_entry, notebook_sub_entries):
        sub_entries = None
        if notebook_sub_entries is not None:
            for sub_entry in notebook_sub_entries:
                bait_data = FishingTuning.get_fishing_bait_data(sub_entry.definition)
                if bait_data is not None:
                    if sub_entries is None:
                        sub_entries = []
                    sub_entries.append(SubEntryData(bait_data.guid64, True))
        return (notebook_entry(self.definition.id, sub_entries=sub_entries),)

    def _on_state_or_name_changed(self, *_, **__):
        fishbowl = self._try_get_fishbowl()
        if fishbowl is not None:
            fishbowl.update_object_tooltip()

    def handle_event(self, sim_info, event_type, resolver):
        if event_type == TestEvent.GlobalPolicyProgress:
            self._update_fish_cost(self.WEIGHT_STATISTIC.default_value)

    def on_remove(self):
        self.remove_state_changed_callback(self._on_state_or_name_changed)
        self.remove_name_changed_callback(self._on_state_or_name_changed)
        if self.global_policy_value_mapping:
            for policy in self.global_policy_value_mapping:
                services.get_event_manager().unregister_with_custom_key(self, TestEvent.GlobalPolicyProgress, policy)
            if self._active_global_policy_modifiers is not None:
                for modifying_policy in self._active_global_policy_modifiers:
                    services.get_event_manager().unregister_with_custom_key(self, TestEvent.GlobalPolicyProgress, type(modifying_policy))
        self._active_global_policy_modifiers = None
        super().on_remove()

    def _ui_metadata_gen(self):
        tooltip_component = self.get_component(objects.components.types.TOOLTIP_COMPONENT)
        yield from tooltip_component._ui_metadata_gen()

    def _try_get_fishbowl(self):
        inventory_owner = self.inventoryitem_component.last_inventory_owner
        if isinstance(inventory_owner, fishing.fish_bowl_object.FishBowl):
            return inventory_owner
