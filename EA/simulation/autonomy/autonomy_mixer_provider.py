from interactions import DEFAULT_MIXER_GROUP_SETimport autonomy.content_setsimport enumimport sims4.loglogger = sims4.log.Logger('Autonomy', default_owner='msantander')
class _MixerProviderType(enum.Int, export=False):
    INVALID = 0
    SI = 1
    BUFF = 2

class _MixerProvider:

    def __init__(self, mixer_provider, mixer_provider_type):
        self._mixer_provider = mixer_provider
        self._type = mixer_provider_type

    def __str__(self):
        return str(self._mixer_provider)

    @property
    def is_social(self):
        if self._type == _MixerProviderType.SI:
            return self._mixer_provider.is_social
        return False

    def mixer_interaction_groups(self):
        if self._type == _MixerProviderType.SI:
            return self._mixer_provider.content_set_mixer_interaction_groups()
        return DEFAULT_MIXER_GROUP_SET

    @property
    def target_string(self):
        return str(getattr(self._mixer_provider, 'target', 'None'))

    def get_scored_commodity(self, motive_scores):
        if self._type == _MixerProviderType.SI:
            best_score = None
            best_stat_type = None
            for stat_type in self._mixer_provider.commodity_flags:
                score = motive_scores.get(stat_type)
                if not best_score is None:
                    if score.score > best_score:
                        best_score = score.score
                        best_stat_type = stat_type
                best_score = score.score
                best_stat_type = stat_type
            return best_stat_type
        elif self._type == _MixerProviderType.BUFF:
            if self._mixer_provider.interactions.scored_commodity:
                return self._mixer_provider.interactions.scored_commodity
            return
        else:
            logger.error('Unknown type in _MixerProvider.get_commodity_score()')
            return
        return
        logger.error('Unknown type in _MixerProvider.get_commodity_score()')
        return

    def get_subaction_weight(self):
        if self._type == _MixerProviderType.SI:
            return self._mixer_provider.subaction_selection_weight
        if self._type == _MixerProviderType.BUFF:
            return self._mixer_provider.interactions.weight
        else:
            logger.error('Unknown type in _MixerProvider.get_subaction_weight()')
            return 0

    def has_mixers(self):
        if self._type == _MixerProviderType.SI:
            return self._mixer_provider.has_affordances()
        if self._type == _MixerProviderType.BUFF:
            return bool(self._mixer_provider.interactions)
        else:
            logger.error('Unknown type of _MixerProvider.has_mixers')
            return False

    def get_mixers(self, request, mixer_interaction_group):
        mixer_aops = None
        if self._type == _MixerProviderType.SI:
            potential_targets = self._mixer_provider.get_potential_mixer_targets()
            mixer_aops = autonomy.content_sets.generate_content_set(request.sim, self._mixer_provider.super_affordance, self._mixer_provider, request.context, potential_targets=potential_targets, push_super_on_prepare=request.push_super_on_prepare, mixer_interaction_group=mixer_interaction_group)
        elif self._type == _MixerProviderType.BUFF:
            source_interaction = request.sim.posture.source_interaction
            if source_interaction:
                potential_targets = source_interaction.get_potential_mixer_targets()
                mixer_aop_dict = autonomy.content_sets.get_buff_aops(request.sim, self._mixer_provider, source_interaction, request.context, potential_targets=potential_targets)
                if mixer_aop_dict:
                    mixer_aops = [scored_aop for (_, scored_aop_list) in mixer_aop_dict.items() for scored_aop in scored_aop_list]
        else:
            logger.error('Unknown type in _MixerProvider.get_mixers()')
            return
        return mixer_aops
