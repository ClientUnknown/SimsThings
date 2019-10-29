import randomfrom date_and_time import create_time_spanfrom interactions.constraints import Anywhere, create_constraint_setfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableEnumEntry, TunableSet, TunableSimMinute, TunableIntervalfrom socials.group import SocialGroupfrom socials.social_scoring import PetGroupCostFunctionfrom tag import Tagimport alarmsimport clockimport servicesimport sims4logger = sims4.log.Logger('Social Group')
class PetSocialGroup(SocialGroup):
    INSTANCE_TUNABLES = {'main_social_lockout_time': TunableSimMinute(description='\n            Amount of time main socials are locked out after one executes.\n            ', default=10), 'main_social_tags': TunableSet(description="\n            If any of these Tags are found on mixers run in the social group it\n            is considered to be a main social for the social group.\n            \n            In a Pet Group you're only allowed to have one of these running at a\n            time.\n            ", tunable=TunableEnumEntry(description="\n                An individual Tag that's considered a main social by the social group.\n                ", tunable_type=Tag, default=Tag.INVALID, pack_safe=True)), 'adjustment_interval': TunableInterval(description='\n            How long Sims wait before adjusting positions.\n            ', tunable_type=TunableSimMinute, default_lower=2, default_upper=5), 'scoring_function': PetGroupCostFunction.TunableFactory(description='\n            The scoring function for this group.\n            ')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock_side_group_until = None

    def _pick_worst_placed_sim(self):
        available_sims = list(self._adjustable_sims_gen())
        if available_sims:
            num_pets = len(available_sims)
            random_pet = random.randint(0, sims4.math.MAX_INT32) % num_pets
            return available_sims[random_pet]

    def _can_sim_be_adjusted(self, sim, initial=False):
        if any(self._is_main_pet_social(interaction) for interaction in sim.si_state) or any(self._is_main_pet_social(interaction) for interaction in sim.queue):
            return False
        for group_sim in sim.get_main_group():
            if not any(self._is_main_pet_social(interaction) and interaction.target is sim for interaction in group_sim.si_state):
                if any(self._is_main_pet_social(interaction) and interaction.target is sim for interaction in group_sim.queue):
                    return False
            return False
        return super()._can_sim_be_adjusted(sim, initial=initial)

    def _create_adjustment_alarm(self):
        if self._adjustment_alarm is not None:
            alarms.cancel_alarm(self._adjustment_alarm)
        alarm_delay = self.adjustment_interval.random_float()
        self._adjustment_alarm = alarms.add_alarm(self, clock.interval_in_sim_minutes(alarm_delay), self._adjustment_alarm_callback)

    def _get_constraint(self, sim):
        if self._focus is None:
            logger.error('Attempt to get a constraint for a Sim before the group constraint is initialized: {} for {}', self, sim, owner='maxr')
            return Anywhere()
        geometric_constraint = self._constraint
        if geometric_constraint is None:
            raise RuntimeError('Attempt to get the constraint from a Social group before it has been initialized. Social Group is {}, Size of group is {}, and minimum number allowed for group is {}'.format(self, len(self), self.minimum_sim_count))
        scoring_constraints = []
        for other_sim in self:
            if other_sim is sim:
                pass
            else:
                scoring_constraint = self.facing_restriction.create_constraint(sim, other_sim, scoring_functions=(self.scoring_function(sim, other_sim),))
                scoring_constraints.append(scoring_constraint)
        scoring_constraints = create_constraint_set(scoring_constraints)
        geometric_constraint = geometric_constraint.intersect(scoring_constraints)
        return geometric_constraint

    def is_locked_out(self, affordance):
        if self._is_main_pet_social(affordance) and self._lock_side_group_until is not None:
            return self._lock_side_group_until >= services.time_service().sim_now
        return False

    def _is_main_pet_social(self, interaction):
        return any(tag in self.main_social_tags for tag in interaction.get_category_tags())

    def _on_interaction_start(self, interaction):
        if self._is_main_pet_social(interaction):
            now = services.time_service().sim_now
            lock_out_time = now + create_time_span(minutes=self.main_social_lockout_time)
            self._lock_side_group_until = lock_out_time
lock_instance_tunables(PetSocialGroup, include_default_facing_constraint=False)