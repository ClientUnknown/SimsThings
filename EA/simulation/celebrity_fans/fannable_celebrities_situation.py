from celebrity_fans.fan_tuning import FanTuningfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation_types import SituationCreationUIOption, SituationSerializationOptionimport sims4.logfrom situations.complex.sim_backgroud_situation import SimBackgroundSituationlogger = sims4.log.Logger('FannableCelebritySimsSituation', default_owner='jdimailig')
class FannableCelebritySimsSituation(SimBackgroundSituation):

    def _on_set_sim_job(self, sim, job):
        super()._on_set_sim_job(sim, job)
        sim.append_tags(set((FanTuning.FAN_TARGETTING_TAG,)))
lock_instance_tunables(FannableCelebritySimsSituation, exclusivity=BouncerExclusivityCategory.NON_WALKBY_BACKGROUND, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0, _implies_greeted_status=False)