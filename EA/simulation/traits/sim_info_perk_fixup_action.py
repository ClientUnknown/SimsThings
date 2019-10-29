from event_testing.tests import TunableTestSetfrom sims4.tuning.tunable import TunableRange, TunableList, TunableReferencefrom traits.sim_info_fixup_action import _SimInfoFixupActionimport servicesimport sims4.resourcesimport random
class _SimInfoPerkFixupAction(_SimInfoFixupAction):
    FACTORY_TUNABLES = {'potential_perks_to_grant': TunableList(description='\n            Bucks perks to grant.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.BUCKS_PERK))), 'number_of_perks_to_grant': TunableRange(description='\n            The number of perks that should be granted to the Sim. This is limited\n            to a maximum now since we might have performance issue otherwise.\n            ', tunable_type=int, default=1, minimum=1, maximum=50), 'tests': TunableTestSet(description='\n            A set of tests that must pass for this action to be applied.\n            ')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, sim_info):
        if self.tests:
            resolver = sim_info.get_resolver()
            if not self.tests.run_tests(resolver):
                return

        def perk_can_be_unlocked(perk):
            if bucks_tracker.is_perk_unlocked(perk):
                return False
            if perk.required_unlocks is not None:
                for required_perk in perk.required_unlocks:
                    if not bucks_tracker.is_perk_unlocked(required_perk):
                        return False
            return True

        bucks_tracker = sim_info.get_bucks_tracker(add_if_none=True)
        potential_perks_list = list(self.potential_perks_to_grant)
        available_bucks_perks = [perk for perk in potential_perks_list if perk_can_be_unlocked(perk)]
        num_unlocks_remaining = self.number_of_perks_to_grant
        while num_unlocks_remaining > 0 and available_bucks_perks:
            perk = random.choice(available_bucks_perks)
            bucks_tracker.unlock_perk(perk)
            num_unlocks_remaining -= 1
            potential_perks_list.remove(perk)
            available_bucks_perks = [perk for perk in potential_perks_list if perk_can_be_unlocked(perk)]
