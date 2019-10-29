from sims4.tuning.tunable import TunableReferenceimport servicesimport sims4
class FishingContestTuning:
    WEIGHT_STATISTIC = TunableReference(description="\n        Statistic that describes the weight of the fish for the fishing contest. The \n        value of the statistic is used as the sim's score in the fishing contest\n        ", manager=services.statistic_manager())
    FISHING_CONTEST = TunableReference(description='\n        The drama node to add to the score of in the FishingContestSubmitElement\n        and to get the rewards from in the FishingContestAwardWinners\n        ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE), pack_safe=True)
