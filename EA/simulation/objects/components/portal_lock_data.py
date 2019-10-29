from functools import total_orderingimport operatorfrom event_testing.resolver import SingleSimResolverfrom event_testing.test_events import TestEventfrom event_testing.test_variants import SituationJobTestfrom interactions import ParticipantTypefrom objects.components.portal_locking_enums import LockPriority, LockSide, LockTypefrom sims.sim_info_tests import SimInfoTest, MatchTypefrom sims.sim_info_types import Age, Gender, Speciesfrom sims4 import resourcesfrom sims4.math import Operator, Thresholdfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableEnumEntry, Tunable, TunableList, TunableReference, OptionalTunable, TunableEnumSet, TunableThreshold, TunableRangeimport servicesimport sims4logger = sims4.log.Logger('PortalLockData', default_owner='nsavalani')
class LockResult:
    NONE = None

    def __init__(self, is_locked, lock_type=None, lock_priority=None, lock_sides=LockSide.LOCK_BOTH, lock_reason=None):
        self.is_locked = is_locked
        self.lock_priority = lock_priority
        self.lock_type = lock_type
        self.lock_sides = lock_sides
        self.lock_reason = lock_reason

    def __bool__(self):
        return self.is_locked

    def __eq__(self, other):
        return self.is_locked == other.is_locked and (self.lock_priority == other.lock_priority and self.lock_sides == other.lock_sides)

    def __repr__(self):
        return '{}, LockType:{}, LockSides:{}'.format(self.is_locked, self.lock_type, self.lock_sides)

    def is_locking_both(self):
        return self.lock_sides == LockSide.LOCK_BOTH

    def is_player_lock(self):
        return self.lock_priority == LockPriority.PLAYER_LOCK
LockResult.NONE = LockResult(False)
class LockData(HasTunableFactory, AutoFactoryInit):
    REFRESH_EVENTS = ()
    FACTORY_TUNABLES = {'lock_priority': TunableEnumEntry(description='\n            The priority of this lock data. Used in comparison between multiple\n            lock datas on the lock component test.\n            ', tunable_type=LockPriority, default=LockPriority.SYSTEM_LOCK), 'lock_sides': TunableEnumEntry(description='\n            Which side or both this lock data will lock.\n            ', tunable_type=LockSide, default=LockSide.LOCK_BOTH), 'should_persist': Tunable(description='\n            If checked, this lock data will be persisted.\n            ', tunable_type=bool, default=True)}

    def __init__(self, lock_type=None, **kwargs):
        super().__init__(**kwargs)
        self.lock_type = lock_type

    def test_lock(self, sim):
        raise NotImplementedError

    def setup_data(self, subject, target, resolver):
        pass

    def update(self, other_data):
        if self.lock_type != other_data.lock_type:
            logger.error('Attempting to update mismatched lock types. Current: {}. Request: {}', self.lock_type, other_data.lock_type)
            return
        self.lock_priority = max(self.lock_priority, other_data.lock_priority)

    def get_exception_data(self):
        return repr(self)

    def save(self, save_data):
        save_data.priority = self.lock_priority
        save_data.sides = self.lock_sides

    def load(self, load_data):
        pass

class LockSimInfoData(LockData):
    FACTORY_TUNABLES = {'siminfo_test': SimInfoTest.TunableFactory(description='\n            The test to determine whether this sim can pass or not.\n            '), 'locked_args': {'lock_priority': LockPriority.SYSTEM_LOCK}}

    def __init__(self, **kwargs):
        super().__init__(lock_type=LockType.LOCK_SIMINFO, **kwargs)

    def test_lock(self, sim):
        single_sim_resolver = SingleSimResolver(sim.sim_info)
        if single_sim_resolver(self.siminfo_test):
            return LockResult(False, 'siminfo_lock', self.lock_priority, self.lock_sides)
        return LockResult(True, 'siminfo_lock', self.lock_priority, self.lock_sides)

class LockRankedStatisticData(LockData):
    REFRESH_EVENTS = (TestEvent.RankedStatisticChange,)
    FACTORY_TUNABLES = {'ranked_stat': TunableReference(description="\n            The ranked statistic we are operating on. Sims won't be allowed to\n            traverse if they don't have this statistic.\n            ", manager=services.statistic_manager(), class_restrictions=('RankedStatistic',)), 'rank_threshold': TunableThreshold(description="\n            Sims that have ranked statistic's value inside the threshold are \n            allowed to traverse the portal.\n            ", value=TunableRange(description='\n                The number that describes the threshold.\n                ', tunable_type=int, default=1, minimum=0), default=sims4.math.Threshold(1, operator.ge))}

    def __init__(self, **kwargs):
        super().__init__(lock_type=LockType.LOCK_RANK_STATISTIC, **kwargs)

    def __repr__(self):
        return 'Ranked Stat: {}, Threshold: {}'.format(self.ranked_stat, self.rank_threshold)

    def test_lock(self, sim):
        tracker = sim.sim_info.get_tracker(self.ranked_stat)
        if tracker is not None:
            ranked_stat_inst = tracker.get_statistic(self.ranked_stat)
            if ranked_stat_inst is not None and self.rank_threshold.compare(ranked_stat_inst.rank_level):
                return LockResult(False, self.lock_type, self.lock_priority, self.lock_sides)
        return LockResult(True, self.lock_type, self.lock_priority, self.lock_sides)

    def save(self, save_data):
        super().save(save_data)
        save_data.ranked_stat_id = self.ranked_stat.guid64
        save_data.threshold_value = self.rank_threshold.value
        save_data.threshold_comparison = Operator.from_function(self.rank_threshold.comparison)

    def load(self, load_data):
        super().load(load_data)
        self.ranked_stat = services.statistic_manager().get(load_data.ranked_stat_id)
        self.rank_threshold = Threshold(value=load_data.threshold_value, comparison=Operator(load_data.threshold_comparison).function)

class LockAllWithSimIdExceptionData(LockData):
    FACTORY_TUNABLES = {'except_actor': Tunable(description='\n            If we want this lock data to have this actor as exception sim.\n            ', tunable_type=bool, default=False), 'except_household': Tunable(description="\n            If we want this lock data to have actor's household as exception sims.\n            ", tunable_type=bool, default=False)}

    def __init__(self, **kwargs):
        super().__init__(lock_type=LockType.LOCK_ALL_WITH_SIMID_EXCEPTION, **kwargs)
        self.except_sim_ids = set()

    def __repr__(self):
        return 'Except sims {}'.format(self.except_sim_ids)

    def setup_data(self, subject, target, resolver):
        if self.except_actor and subject.id not in self.except_sim_ids:
            self.except_sim_ids.add(subject.id)

    def update(self, other_data):
        super().update(other_data)
        self.except_sim_ids.update(other_data.except_sim_ids)

    def test_lock(self, sim):
        if self.except_household and services.active_lot().get_household() is sim.household:
            return LockResult(False, 'all_lock', self.lock_priority, self.lock_sides)
        if self.except_sim_ids and sim.id in self.except_sim_ids:
            return LockResult(False, 'all_lock', self.lock_priority, self.lock_sides)
        return LockResult(True, 'all_lock', self.lock_priority, self.lock_sides)

    def get_exception_data(self):
        except_sim_names = []
        sim_info_mgr = services.sim_info_manager()
        for sim_id in self.except_sim_ids:
            sim_info = sim_info_mgr.get(sim_id)
            if sim_info is not None:
                except_sim_names.append(sim_info.full_name)
            else:
                except_sim_names.append(str(sim_id))
        return ','.join(except_sim_names)

    def save(self, save_data):
        super().save(save_data)
        save_data.except_actor = self.except_actor
        save_data.except_household = self.except_household
        if self.except_sim_ids:
            save_data.exception_sim_ids.extend(self.except_sim_ids)

    def load(self, load_data):
        super().load(load_data)
        for sim_id in load_data.exception_sim_ids:
            self.except_sim_ids.add(sim_id)

class LockAllWithClubException(LockData):
    REFRESH_EVENTS = (TestEvent.ClubMemberAdded, TestEvent.ClubMemberRemoved)
    FACTORY_TUNABLES = {'except_club_seeds': TunableList(description='\n            Sims that are members of these Clubs are allowed to traverse the\n            portal.\n            ', tunable=TunableReference(manager=services.get_instance_manager(resources.Types.CLUB_SEED), pack_safe=True))}

    def __init__(self, **kwargs):
        super().__init__(lock_type=LockType.LOCK_ALL_WITH_CLUBID_EXCEPTION, **kwargs)
        self.except_club_ids = set()

    def __repr__(self):
        club_service = services.get_club_service()
        if club_service is None:
            return 'No Club Service'
        return 'Except: {}, {}'.format(','.join(str(club_seed) for club_seed in self.except_club_seeds), ','.join(str(club_service.get_club_by_id(club_id)) for club_id in self.except_club_ids))

    def setup_data(self, subject, target, resolver):
        club = resolver.get_participant(ParticipantType.AssociatedClub)
        if club is not None:
            self.except_club_ids.add(club.club_id)

    def update(self, other_data):
        super().update(other_data)
        self.except_club_ids.update(other_data.except_club_ids)

    def save(self, save_data):
        club_service = services.get_club_service()
        if club_service is not None:
            for club_seed in self.except_club_seeds:
                club = club_service.get_club_by_seed(club_seed)
                if club is not None:
                    save_data.exception_sim_ids.append(club.club_id)
        save_data.exception_sim_ids.extend(self.except_club_ids)
        return super().save(save_data)

    def load(self, load_data):
        self.except_club_ids.update(load_data.exception_sim_ids)
        return super().load(load_data)

    def test_lock(self, sim):
        club_service = services.get_club_service()
        if club_service is not None and not any(club.club_id in self.except_club_ids or club.club_seed in self.except_club_seeds for club in club_service.get_clubs_for_sim_info(sim.sim_info)):
            return LockResult(True, 'club_lock', self.lock_priority, self.lock_sides)
        return LockResult(False, 'club_lock', self.lock_priority, self.lock_sides)

class LockAllWithSituationJobExceptionData(LockData):
    from event_testing.test_variants import TunableSituationJobTest
    FACTORY_TUNABLES = {'situation_job_test': TunableSituationJobTest(description='\n            The test to determine whether this sim can pass or not.\n            '), 'except_business_employee': Tunable(description='\n            If true, the business store employee will have exception to the door.\n            ', tunable_type=bool, default=False)}

    def __init__(self, **kwargs):
        super().__init__(lock_type=LockType.LOCK_ALL_WITH_SITUATION_JOB_EXCEPTION, **kwargs)

    def __repr__(self):
        return 'Except SituationJobs:{}, RoleTags:{}, Except retail employee: {}'.format(self.situation_job_test.situation_jobs, self.situation_job_test.role_tags, self.except_business_employee)

    def test_lock(self, sim):
        single_sim_resolver = SingleSimResolver(sim.sim_info)
        if single_sim_resolver(self.situation_job_test):
            return LockResult(False, 'situation_job_lock', self.lock_priority, self.lock_sides)
        if self.except_business_employee:
            business_manager = services.business_service().get_business_manager_for_zone()
            if business_manager is not None:
                if business_manager.is_household_owner(sim.sim_info.household_id):
                    return LockResult(False, 'situation_job_lock', self.lock_priority, self.lock_sides)
                if business_manager.is_employee(sim.sim_info):
                    return LockResult(False, 'situation_job_lock', self.lock_priority, self.lock_sides)
        return LockResult(True, 'situation_job_lock', self.lock_priority, self.lock_sides)

    def get_exception_data(self):
        return 'SituationJobs:{}, RoleTags:{}, Except retail employee: {}'.format(self.situation_job_test.situation_jobs, self.situation_job_test.role_tags, self.except_business_employee)

    def save(self, save_data):
        super().save(save_data)
        situation_job_test = self.situation_job_test
        save_data.participant_enum = situation_job_test.participant
        save_data.negate = situation_job_test.negate
        if situation_job_test.situation_jobs:
            job_list = [job.guid64 for job in situation_job_test.situation_jobs]
            save_data.situation_jobs.extend(job_list)
        if situation_job_test.role_tags:
            save_data.role_tags.extend(situation_job_test.role_tags)
        save_data.except_retail_employee = self.except_business_employee

    def load(self, load_data):
        super().load(load_data)
        situation_jobs = set()
        situation_job_manager = services.situation_job_manager()
        if load_data.situation_jobs:
            for job_id in load_data.situation_jobs:
                job_type = situation_job_manager.get(job_id)
                if job_type is not None:
                    situation_jobs.add(job_type)
        role_tags = frozenset(load_data.role_tags)
        self.situation_job_test = SituationJobTest(participant=load_data.participant_enum, negate=load_data.negate, situation_jobs=frozenset(situation_jobs), role_tags=role_tags)

class LockAllWithGenusException(LockData):
    FACTORY_TUNABLES = {'ages': OptionalTunable(tunable=TunableEnumSet(description='\n                The Sim must be one of the specified ages.\n                ', enum_type=Age, enum_default=Age.ADULT, default_enum_list=[Age.TEEN, Age.YOUNGADULT, Age.ADULT, Age.ELDER]), disabled_name='unspecified', enabled_name='specified'), 'gender': OptionalTunable(tunable=TunableEnumEntry(description='\n                The Sim must be of the specified gender.\n                ', tunable_type=Gender, default=None), enabled_name='specified', disabled_name='unspecified', disabled_value=0), 'species': OptionalTunable(tunable=TunableEnumSet(description='\n                The Sim must be one of the specified species.\n                ', enum_type=Species, enum_default=Species.HUMAN, invalid_enums=(Species.INVALID,)), disabled_name='unspecified', enabled_name='specified'), 'match_type': TunableEnumEntry(description='\n            If MATCH_ALL is set, test will pass if Sim matches with all \n            enabled tuned genus.\n             \n            If MATCH_ANY is set, test will pass if Sim matches with one of the \n            enabled tuned genus.\n            ', tunable_type=MatchType, default=MatchType.MATCH_ALL)}

    def __init__(self, **kwargs):
        super().__init__(lock_type=LockType.LOCK_ALL_WITH_GENUS_EXCEPTION, **kwargs)

    def __repr__(self):
        return 'Except Ages:{}, Gender:{}, Species:{}'.format(self.ages, self.gender, self.species)

    def test_lock(self, sim):
        match_results = []
        if self.gender != 0:
            match_results.append(sim.sim_info.gender == self.gender)
        if self.ages is not None:
            match_results.append(sim.sim_info.age in self.ages)
        if self.species is not None:
            match_results.append(sim.sim_info.species in self.species)
        if self.match_type == MatchType.MATCH_ANY:
            if not any(match_results):
                return LockResult(True, self.lock_type, self.lock_priority, self.lock_sides)
        elif not all(match_results):
            return LockResult(True, self.lock_type, self.lock_priority, self.lock_sides)
        return LockResult(False, self.lock_type, self.lock_priority, self.lock_sides)

    def save(self, save_data):
        super().save(save_data)
        save_data.gender = self.gender
        save_data.match_type = self.match_type
        if self.ages:
            save_data.ages.extend(self.ages)
        if self.species:
            save_data.species.extend(self.species)

    def load(self, load_data):
        super().load(load_data)
        self.gender = load_data.gender
        if load_data.HasField('match_type'):
            self.match_type = MatchType(load_data.match_type)
        for age in load_data.ages:
            if self.ages is None:
                self.ages = set()
            self.ages.add(age)
        for species in load_data.species:
            if self.species is None:
                self.species = set()
            self.species.add(species)

class LockAllWithBuffExceptionData(LockData):

    @staticmethod
    def _on_tunable_loaded_callback(source, *_, except_buffs, **__):
        for buff in except_buffs:
            buff.refresh_portal_lock = True

    REFRESH_EVENTS = (TestEvent.BuffBeganEvent, TestEvent.BuffEndedEvent)
    FACTORY_TUNABLES = {'except_buffs': TunableList(description='\n            Sims that have one of these buffs are allowed to traverse the\n            portal.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.BUFF), pack_safe=True), unique_entries=True), 'callback': _on_tunable_loaded_callback}

    def __init__(self, **kwargs):
        super().__init__(lock_type=LockType.LOCK_ALL_WITH_BUFF_EXCEPTION, **kwargs)

    def __repr__(self):
        return 'Except: {}'.format(','.join(buff.buff_type.__name__ for buff in self.except_buffs))

    def test_lock(self, sim):
        if any(sim.has_buff(buff) for buff in self.except_buffs):
            return LockResult(False, self.lock_type, self.lock_priority, self.lock_sides)
        return LockResult(True, self.lock_type, self.lock_priority, self.lock_sides)

    def save(self, save_data):
        super().save(save_data)
        buff_ids = [buff.guid64 for buff in self.except_buffs]
        save_data.buff_ids.extend(buff_ids)

    def load(self, load_data):
        super().load(load_data)
        self.except_buffs = []
        buff_manager = services.get_instance_manager(sims4.resources.Types.BUFF)
        for buff_id in load_data.buff_ids:
            buff = buff_manager.get(buff_id)
            if buff is not None:
                self.except_buffs.append(buff)

class IndividualSimDoorLockData(LockData):

    def __init__(self, lock_sim=None, unlock_sim=None, **kwargs):
        super().__init__(lock_type=LockType.INDIVIDUAL_SIM, **kwargs)
        self.locked_sim_ids = set((lock_sim.id,)) if lock_sim is not None else set()
        self.except_sim_ids = set((unlock_sim.id,)) if unlock_sim is not None else set()

    def __repr__(self):
        return 'Locked Sims:{}, Except Sims:{}'.format(self.locked_sim_ids, self.except_sim_ids)

    def test_lock(self, sim):
        if sim.id in self.locked_sim_ids:
            return LockResult(True, self.lock_type, self.lock_priority, self.lock_sides)
        elif sim.id in self.except_sim_ids:
            return LockResult(False, self.lock_type, self.lock_priority, self.lock_sides)

    def update(self, other_data):
        super().update(other_data)
        if self.except_sim_ids:
            other_data.locked_sim_ids -= self.except_sim_ids
        else:
            other_data.except_sim_ids -= self.locked_sim_ids
        self.locked_sim_ids.update(other_data.locked_sim_ids)
        self.except_sim_ids.update(other_data.except_sim_ids)

    def save(self, save_data):
        super().save(save_data)
        if self.except_sim_ids:
            save_data.exception_sim_ids.extend(self.except_sim_ids)
        if self.locked_sim_ids:
            save_data.locked_sim_ids.extend(self.locked_sim_ids)

    def load(self, load_data):
        super().load(load_data)
        for sim_id in load_data.exception_sim_ids:
            self.except_sim_ids.add(sim_id)
        for sim_id in load_data.locked_sim_ids:
            self.locked_sim_ids.add(sim_id)
