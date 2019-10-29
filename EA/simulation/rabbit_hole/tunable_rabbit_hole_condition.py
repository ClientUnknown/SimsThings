from sims4.tuning.tunable import TunableVariantfrom statistics.statistic_conditions import TunableStatisticCondition
class TunableRabbitHoleCondition(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, stat_based=TunableStatisticCondition(description='\n                A condition based on the status of a statistic.\n                '), default='stat_based', **kwargs)
