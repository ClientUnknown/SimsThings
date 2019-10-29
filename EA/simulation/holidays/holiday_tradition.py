from _collections import defaultdictfrom buffs.tunable import TunableBuffReferencefrom business.business_enums import BusinessTypefrom event_testing.resolver import SingleSimResolver, GlobalResolverfrom holidays.holiday_globals import HolidayState, TraditionPreferencefrom interactions import ParticipantTypefrom interactions.utils.display_mixin import get_display_mixinfrom relationships.relationship_tests import TunableRelationshipTestfrom sims.sim_info_tests import SimInfoTest, TraitTestfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableReference, TunableList, Tunable, TunableTuple, TunableEnumEntry, TunableVariant, OptionalTunable, AutoFactoryInit, HasTunableSingletonFactory, TunableEnumSet, TunableSingletonFactory, TunableMapping, TunableRangefrom sims4.tuning.tunable_base import GroupNames, ExportModesfrom situations.service_npcs.modify_lot_items_tuning import ModifyAllLotItemsfrom situations.situation_curve import SituationCurvefrom situations.situation_guest_list import SituationGuestListfrom situations.tunable import DestroySituationsByTagsMixinfrom tag import TunableTagsfrom tunable_time import TunableTimeOfDayimport alarmsimport elementsimport enumimport event_testingimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('Holiday', default_owner='jjacobson')
class TraditionActivationEvent(enum.Int):
    HOLIDAY_ACTIVATE = 0
    HOLIDAY_DEACTIVATE = 1
    TRADITION_ADD = 2
    TRADITION_REMOVE = 3

class TunablePreferenceTestVariant(TunableVariant):

    def __init__(self, description='A single tunable test.', **kwargs):
        super().__init__(relationship=TunableRelationshipTest(locked_args={'subject': ParticipantType.Actor, 'target_sim': ParticipantType.AllRelationships, 'test_event': 0, 'tooltip': None}), sim_info=SimInfoTest.TunableFactory(locked_args={'tooltip': None}), trait=TraitTest.TunableFactory(locked_args={'tooltip': None}), default='sim_info', description=description, **kwargs)

class TunablePreferenceTestList(event_testing.tests.TestListLoadingMixin):
    DEFAULT_LIST = event_testing.tests.TestList()

    def __init__(self, description=None):
        if description is None:
            description = 'A list of tests.  All tests must succeed to pass the TestSet.'
        super().__init__(description=description, tunable=TunablePreferenceTestVariant())

class _StartSituation(AutoFactoryInit):
    FACTORY_TUNABLES = {'situation': TunableReference(description='\n            The situation to start.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION))}

    def perform(self, resolver):
        guest_list = self.situation.get_predefined_guest_list()
        if guest_list is None:
            guest_list = SituationGuestList(invite_only=True)
        services.get_zone_situation_manager().create_situation(self.situation, guest_list=guest_list, user_facing=False)
StartSituation = TunableSingletonFactory.create_auto_factory(_StartSituation, 'StartSituation')
class _ModifyAllItems(AutoFactoryInit):
    FACTORY_TUNABLES = {'item_modifications': ModifyAllLotItems.TunableFactory(description='\n            Modify objects on the active lot.\n            ')}

    def perform(self, resolver):
        self.item_modifications().modify_objects()
ModifyAllItems = TunableSingletonFactory.create_auto_factory(_ModifyAllItems, 'ModifyAllItems')
class _DestroySituations(DestroySituationsByTagsMixin, AutoFactoryInit):

    def perform(self, resolver):
        self._destroy_situations_by_tags(resolver)
DestroySituations = TunableSingletonFactory.create_auto_factory(_DestroySituations, 'DestroySituations')
class TraditionActionVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(start_situation=StartSituation(), destroy_situations=DestroySituations(), default='start_situation', **kwargs)

class TraditionActions(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'trigger_on_events': TunableEnumSet(description='\n            Event that would trigger these actions.\n            ', enum_type=TraditionActivationEvent, enum_default=TraditionActivationEvent.HOLIDAY_ACTIVATE), 'actions_to_apply': TunableList(description='\n            Actions to apply for this event.\n            ', tunable=TraditionActionVariant())}

    def try_perform(self, resolver, activation_event):
        if activation_event in self.trigger_on_events:
            for action in self.actions_to_apply:
                action.perform(resolver)
HolidayTraditionDisplayMixin = get_display_mixin(has_description=True, has_icon=True, export_modes=ExportModes.All)START_SITUATION = 0MODIFY_ITEMS = 1
class HolidayTradition(HasTunableReference, HolidayTraditionDisplayMixin, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.HOLIDAY_TRADITION)):
    INSTANCE_TUNABLES = {'situation_goal': TunableReference(description='\n            This is the situation goal that will be offered when this tradition\n            is active.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_GOAL)), 'pre_holiday_buffs': TunableList(description='\n            A list of buffs that will be given out to all of the player Sims\n            during the pre-holiday period of each holiday.\n            ', tunable=TunableReference(description='\n                A buff that is given to all of the player Sims when it is the\n                pre-holiday period.\n                ', manager=services.get_instance_manager(sims4.resources.Types.BUFF)), unique_entries=True), 'pre_holiday_buff_reason': OptionalTunable(description='\n            If set, specify a reason why the buff was added.\n            ', tunable=TunableLocalizedString(description='\n                The reason the buff was added. This will be displayed in the\n                buff tooltip.\n                ')), 'holiday_buffs': TunableList(description='\n            A list of buffs that will be given out to all Sims during each\n            holiday.\n            ', tunable=TunableReference(description='\n                A buff that is given to all Sims during the holiday.\n                ', manager=services.get_instance_manager(sims4.resources.Types.BUFF)), unique_entries=True), 'holiday_buff_reason': OptionalTunable(description='\n            If set, specify a reason why the buff was added.\n            ', tunable=TunableLocalizedString(description='\n                The reason the buff was added. This will be displayed in the\n                buff tooltip.\n                ')), 'drama_nodes_to_score': TunableList(description='\n            Drama nodes that we will attempt to schedule and score when this\n            tradition becomes active.\n            ', tunable=TunableReference(description='\n                A drama node that we will put in the scoring pass when this\n                tradition becomes active.\n                ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE)), unique_entries=True), 'drama_nodes_to_run': TunableList(description='\n            Drama nodes that will be run when the tradition is activated.\n            ', tunable=TunableReference(description='\n                A drama node that we will run when the holiday becomes active.\n                ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE)), unique_entries=True), 'additional_walkbys': SituationCurve.TunableFactory(description='\n            An additional walkby schedule that will be added onto the walkby\n            schedule when the tradition is active.\n            ', get_create_params={'user_facing': False}), 'preference': TunableList(description='\n            A list of pairs of preference categories and tests.  To determine\n            what a Sim feels about a tradition each set of tests in this list\n            will be run in order.  When one of the test sets passes then we\n            will set that as the preference.  If none of them pass we will\n            default to LIKES.\n            ', tunable=TunableTuple(description='\n                A pair of preference and test set.\n                ', preference=TunableEnumEntry(description='\n                    The preference that the Sim will have to this tradition if\n                    the test set passes.\n                    ', tunable_type=TraditionPreference, default=TraditionPreference.LIKES), tests=TunablePreferenceTestList(description='\n                    A set of tests that need to pass for the Sim to have the\n                    tuned preference.\n                    '), reason=OptionalTunable(description='\n                    If enabled then we will also give this reason as to why the\n                    preference is the way it is.\n                    ', tunable=TunableLocalizedString(description='\n                        The reason that the Sim has this preference.\n                        ')))), 'preference_reward_buff': OptionalTunable(description='\n            If enabled then if the Sim loves this tradition when the holiday is\n            completed they will get a special buff if they completed the\n            tradition.\n            ', tunable=TunableBuffReference(description='\n                The buff given if this Sim loves the tradition and has completed\n                it at the end of the holiday.\n                ')), 'selectable': Tunable(description='\n            If checked then this tradition will appear in the tradition\n            selection.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.UI, export_modes=ExportModes.All), 'lifecycle_actions': TunableList(description='\n            Actions that occur as a result of the tradition activation/de-activation.\n            ', tunable=TraditionActions.TunableFactory()), 'events': TunableList(description='\n            A list of times and things we want to happen at that time.\n            ', tunable=TunableTuple(description='\n                A pair of a time of day and event of something that we want\n                to occur.\n                ', time=TunableTimeOfDay(description='\n                    The time of day this event will occur.\n                    '), event=TunableVariant(description='\n                    What we want to occur at this time.\n                    ', modify_items=ModifyAllItems(), start_situation=StartSituation(), default='start_situation'))), 'core_object_tags': TunableTags(description='\n            Tags of all the core objects used in this tradition.\n            ', filter_prefixes=('func',), tuning_group=GroupNames.UI, export_modes=ExportModes.All), 'deco_object_tags': TunableTags(description='\n            Tags of all the deco objects used in this tradition.\n            ', filter_prefixes=('func',), tuning_group=GroupNames.UI, export_modes=ExportModes.All), 'business_cost_multiplier': TunableMapping(description='\n            A mapping between the business type and the cost multiplier that\n            we want to use if this tradition is active.\n            ', key_type=TunableEnumEntry(description='\n                The type of business that we want to apply this price modifier\n                on.\n                ', tunable_type=BusinessType, default=BusinessType.INVALID, invalid_enums=(BusinessType.INVALID,)), value_type=TunableRange(description='\n                The value of the multiplier to use.\n                ', tunable_type=float, default=1.0, minimum=0.0))}

    @classmethod
    def _verify_tuning_callback(cls):
        if cls._display_data.instance_display_description is None:
            logger.error('Tradition {} missing display description', cls)
        if cls._display_data.instance_display_icon is None:
            logger.error('Tradition {} missing display icon', cls)
        if cls._display_data.instance_display_name is None:
            logger.error('Tradition {} missing display name', cls)

    def __init__(self):
        self._state = HolidayState.INITIALIZED
        self._buffs_added = defaultdict(list)
        self._event_alarm_handles = {}
        self._drama_node_processor = None

    @property
    def state(self):
        return self._state

    @classmethod
    def get_buiness_multiplier(cls, business_type):
        return cls.business_cost_multiplier.get(business_type, 1.0)

    @classmethod
    def get_sim_preference(cls, sim_info):
        resolver = SingleSimResolver(sim_info)
        for possible_preference in cls.preference:
            if possible_preference.tests.run_tests(resolver):
                return (possible_preference.preference, possible_preference.reason)
        return (TraditionPreference.LIKES, None)

    def on_sim_spawned(self, sim):
        if self._state == HolidayState.PRE_DAY:
            if sim.is_npc:
                return
            for buff in self.pre_holiday_buffs:
                buff_handle = sim.add_buff(buff, buff_reason=self.pre_holiday_buff_reason)
                if buff_handle is not None:
                    self._buffs_added[sim.sim_id].append(buff_handle)
        elif self._state == HolidayState.RUNNING:
            for buff in self.holiday_buffs:
                buff_handle = sim.add_buff(buff, buff_reason=self.holiday_buff_reason)
                if buff_handle is not None:
                    self._buffs_added[sim.sim_id].append(buff_handle)

    def activate_pre_holiday(self):
        if self._state >= HolidayState.PRE_DAY:
            logger.error('Tradition {} is trying to be put into the pre_holiday, but is already in {} which is farther along.', self, self._state)
            return
        self._state = HolidayState.PRE_DAY
        if self.pre_holiday_buffs:
            services.sim_spawner_service().register_sim_spawned_callback(self.on_sim_spawned)
            for sim_info in services.active_household().instanced_sims_gen():
                for buff in self.pre_holiday_buffs:
                    buff_handle = sim_info.add_buff(buff, buff_reason=self.pre_holiday_buff_reason)
                    if buff_handle is not None:
                        self._buffs_added[sim_info.sim_id].append(buff_handle)

    def _remove_all_buffs(self):
        sim_info_manager = services.sim_info_manager()
        for (sim_id, buff_handles) in self._buffs_added.items():
            sim_info = sim_info_manager.get(sim_id)
            if sim_info is None:
                pass
            elif sim_info.Buffs is None:
                pass
            else:
                for buff_handle in buff_handles:
                    sim_info.remove_buff(buff_handle)
        self._buffs_added.clear()

    def _deactivate_pre_holiday(self):
        if self.pre_holiday_buffs:
            services.sim_spawner_service().unregister_sim_spawned_callback(self.on_sim_spawned)
            self._remove_all_buffs()

    def deactivate_pre_holiday(self):
        if self._state != HolidayState.PRE_DAY:
            logger.error('Tradition {} is trying to deactivate the preday, but it is in the {} state, not that one.', self, self._state)
        self._state = HolidayState.SHUTDOWN
        self._deactivate_pre_holiday()

    def _create_event_alarm(self, key, event):

        def callback(_):
            event.event.perform(GlobalResolver())
            del self._event_alarm_handles[key]

        now = services.time_service().sim_now
        time_to_event = now.time_till_next_day_time(event.time)
        if key in self._event_alarm_handles:
            alarms.cancel_alarm(self._event_alarm_handles[key])
        self._event_alarm_handles[key] = alarms.add_alarm(self, time_to_event, callback)

    def _process_scoring_gen(self, timeline):
        try:
            yield from services.drama_scheduler_service().score_and_schedule_nodes_gen(self.drama_nodes_to_score, 1, timeline=timeline)
        except GeneratorExit:
            raise
        except Exception as exception:
            logger.exception('Exception while scoring DramaNodes: ', exc=exception, level=sims4.log.LEVEL_ERROR)
        finally:
            self._drama_node_processor = None

    def activate_holiday(self, from_load=False, from_customization=False):
        if self._state >= HolidayState.RUNNING:
            logger.error('Tradition {} is trying to be put into the Running state, but is already in {} which is farther along.', self, self._state)
            return
        self._deactivate_pre_holiday()
        self._state = HolidayState.RUNNING
        if self.holiday_buffs:
            services.sim_spawner_service().register_sim_spawned_callback(self.on_sim_spawned)
            for sim_info in services.sim_info_manager().instanced_sims_gen():
                for buff in self.holiday_buffs:
                    buff_handle = sim_info.add_buff(buff, buff_reason=self.holiday_buff_reason)
                    if buff_handle is not None:
                        self._buffs_added[sim_info.sim_id].append(buff_handle)
        for (key, event) in enumerate(self.events):
            self._create_event_alarm(key, event)
        if not from_load:
            resolver = GlobalResolver()
            for actions in self.lifecycle_actions:
                actions.try_perform(resolver, TraditionActivationEvent.TRADITION_ADD if from_customization else TraditionActivationEvent.HOLIDAY_ACTIVATE)
            if self.drama_nodes_to_score:
                sim_timeline = services.time_service().sim_timeline
                self._drama_node_processor = sim_timeline.schedule(elements.GeneratorElement(self._process_scoring_gen))
            drama_scheduler = services.drama_scheduler_service()
            for drama_node in self.drama_nodes_to_run:
                drama_scheduler.run_node(drama_node, resolver)

    def deactivate_holiday(self, from_customization=False):
        if self._state != HolidayState.RUNNING:
            logger.error('Tradition {} is trying to deactivate the tradition, but it is in the {} state, not that one.', self, self._state)
        self._state = HolidayState.SHUTDOWN
        if self.holiday_buffs:
            services.sim_spawner_service().unregister_sim_spawned_callback(self.on_sim_spawned)
            self._remove_all_buffs()
        for alarm in self._event_alarm_handles.values():
            alarms.cancel_alarm(alarm)
        self._event_alarm_handles.clear()
        resolver = GlobalResolver()
        for actions in self.lifecycle_actions:
            actions.try_perform(resolver, TraditionActivationEvent.TRADITION_REMOVE if from_customization else TraditionActivationEvent.HOLIDAY_DEACTIVATE)

    def get_additional_walkbys(self, predicate=lambda _: True):
        weighted_situations = self.additional_walkbys.get_weighted_situations(predicate=predicate)
        if weighted_situations is None:
            return ()
        return weighted_situations
