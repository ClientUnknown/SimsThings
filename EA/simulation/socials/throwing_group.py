from collections import Counterfrom interactions.base.mixer_interaction import MixerInteractionfrom interactions.constraints import Anywhere, create_constraint_setfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableSimMinute, TunableInterval, TunableListfrom socials.group import SocialGroupfrom socials.social_scoring import ThrowingGroupCostFunctionimport alarmsimport clockimport objectsimport sims4logger = sims4.log.Logger('Throwing Group')
class ThrowingSocialGroup(SocialGroup):
    INSTANCE_TUNABLES = {'adjustment_interval': TunableInterval(description='\n            How long Sims wait before adjusting positions.\n            ', tunable_type=TunableSimMinute, default_lower=2, default_upper=5), 'scoring_function': ThrowingGroupCostFunction.TunableFactory(description='\n            The scoring function for this group.\n            '), 'adjustment_mixers': TunableList(description='\n            List of mixers that we push as possible adustment options.  Sims\n            should not try to adjust right after running these mixers.\n            ', tunable=MixerInteraction.TunableReference(description='\n                Adjustment mixer reference.\n                ', pack_safe=True))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._adjustment_score = Counter()
        self._pending_adjustments = set()

    def validate_anchor(self, target):
        return self._anchor_object is not None

    @classmethod
    def _get_social_anchor_object(cls, si, target_sim):
        if cls.social_anchor_object is None:
            return objects.terrain.TerrainPoint(si.sim.location)
        return super()._get_social_anchor_object(si, target_sim)

    def _can_sim_be_adjusted(self, sim, initial=False):
        for interaction in sim.get_all_running_and_queued_interactions():
            if interaction.affordance in self.adjustment_mixers:
                return False
        return super()._can_sim_be_adjusted(sim, initial=initial)

    def _pick_worst_placed_sim(self):
        weighted_sims = []
        for sim in self._adjustable_sims_gen():
            if sim.id in self._adjustment_score:
                weighted_sims.append((self._adjustment_score[sim.id], sim))
            else:
                weighted_sims.append((1, sim))
        if weighted_sims:
            random_sim = sims4.random.weighted_random_item(weighted_sims)
            self._adjustment_score[sim.id] = 1
            self._pending_adjustments.add(sim.id)
            return random_sim

    def _create_adjustment_alarm(self):
        if self._adjustment_alarm is not None:
            alarms.cancel_alarm(self._adjustment_alarm)
        alarm_delay = self.adjustment_interval.random_float()
        self._adjustment_alarm = alarms.add_alarm(self, clock.interval_in_sim_minutes(alarm_delay), self._adjustment_alarm_callback)

    def _get_constraint(self, sim):
        if self._focus is None:
            logger.error('Attempt to get a constraint for a Sim before the group constraint is initialized: {} for {}', self, sim, owner='camilogarcia')
            return Anywhere()
        geometric_constraint = self._constraint
        if geometric_constraint is None:
            logger.error('Attempt to get the constraint from a Social group before it has been initialized. Social Group is {}, Size of group is {}, and minimum number allowed for group is {}', self, len(self), self.minimum_sim_count, owner='camilogarcia')
            return Anywhere()
        scoring_constraints = []
        for other_sim in self:
            if other_sim is sim:
                pass
            else:
                facing_anchor = self._anchor_object if self._anchor_object is not None else other_sim
                force_readjustment = sim.id in self._pending_adjustments
                if force_readjustment:
                    self._pending_adjustments.remove(sim.id)
                scoring_constraint = self.facing_restriction.create_constraint(sim, facing_anchor, scoring_functions=(self.scoring_function(sim, other_sim, force_readjustment),))
                scoring_constraints.append(scoring_constraint)
        scoring_constraints = create_constraint_set(scoring_constraints)
        geometric_constraint = geometric_constraint.intersect(scoring_constraints)
        return geometric_constraint

    def update_adjustment_scoring(self, sim_id, action_score):
        self._adjustment_score[sim_id] += action_score
lock_instance_tunables(ThrowingSocialGroup, include_default_facing_constraint=False)