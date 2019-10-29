import randomfrom balloon.balloon_enums import BALLOON_TYPE_LOOKUPfrom balloon.balloon_request import BalloonRequestfrom balloon.tunable_balloon import TunableBalloonfrom date_and_time import create_time_spanfrom event_testing.resolver import SingleSimResolverfrom sims4.tuning.tunable import Tunable, TunableList, TunableTupleimport gsi_handlersimport servicesimport sims4.loglogger = sims4.log.Logger('Balloons')
class PassiveBalloons:

    @staticmethod
    def _validate_tuning(instance_class, tunable_name, source, value):
        if PassiveBalloons.BALLOON_LOCKOUT + PassiveBalloons.BALLOON_RANDOM >= PassiveBalloons.BALLOON_LONG_LOCKOUT:
            logger.error('PassiveBalloons tuning value error! BALLOON_LONG_LOCKOUT must be tuned to be greater than BALLOON_LOCKOUT + BALLOON_RANDOM')

    BALLOON_LOCKOUT = Tunable(description='\n        The duration, in minutes, for the lockout time between displaying passive balloons.\n        ', tunable_type=int, default=10)
    BALLOON_RANDOM = Tunable(description='\n        The duration, in minutes, for a random amount to be added to the lockout\n        time between displaying passive balloons.\n        ', tunable_type=int, default=20)
    BALLOON_LONG_LOCKOUT = Tunable(description='\n        The duration, in minutes, to indicate that a long enough time has passed\n        since the last balloon, to trigger a delay of the next balloon by the\n        random amount of time from BALLOON_RANDOM. The reason for this is so\n        that newly spawned walkby sims that begin routing do not display their\n        first routing balloon immediately. Make sure that this is always higher\n        than the tuned values in BALLOON_LOCKOUT + BALLOON_RANDOM, or it will\n        not work as intended.\n        ', tunable_type=int, default=120, callback=_validate_tuning)
    MAX_NUM_BALLOONS = Tunable(description='\n        The maximum number of passive balloon tuning data entries to process per\n        balloon display attempt\n        ', tunable_type=int, default=25)
    ROUTING_BALLOONS = TunableList(description='\n        A weighted list of passive routing balloons.\n        ', tunable=TunableTuple(balloon=TunableBalloon(locked_args={'balloon_delay': 0, 'balloon_delay_random_offset': 0, 'balloon_chance': 100, 'balloon_target': None}), weight=Tunable(tunable_type=int, default=1)))

    @staticmethod
    def request_routing_to_object_balloon(sim, interaction):
        balloon_tuning = interaction.route_start_balloon
        if balloon_tuning is None:
            return
        if interaction.is_user_directed and not balloon_tuning.also_show_user_directed:
            return
        balloon_requests = balloon_tuning.balloon(interaction)
        if balloon_requests:
            choosen_balloon = random.choice(balloon_requests)
            if choosen_balloon is not None:
                choosen_balloon.distribute()

    @staticmethod
    def create_passive_ballon_request(sim, balloon_data):
        if gsi_handlers.balloon_handlers.archiver.enabled:
            gsi_entries = []
        else:
            gsi_entries = None
        resolver = SingleSimResolver(sim.sim_info)
        balloon_icon = TunableBalloon.select_balloon_icon(balloon_data.balloon_choices, resolver, gsi_entries=gsi_entries, gsi_interaction=None, gsi_balloon_target_override=None)
        category_icon = None
        if balloon_icon is not None:
            icon_info = balloon_icon.icon(resolver, balloon_target_override=None)
            if balloon_icon.category_icon is not None:
                category_icon = balloon_icon.category_icon(resolver, balloon_target_override=None)
        else:
            icon_info = None
        if gsi_handlers.balloon_handlers.archiver.enabled:
            gsi_handlers.balloon_handlers.archive_balloon_data(sim, None, balloon_icon, icon_info, gsi_entries)
        if balloon_icon is not None and (icon_info[0] is not None or icon_info[1] is not None):
            (balloon_type, priority) = BALLOON_TYPE_LOOKUP[balloon_icon.balloon_type]
            balloon_overlay = balloon_icon.overlay
            request = BalloonRequest(sim, icon_info[0], icon_info[1], balloon_overlay, balloon_type, priority, TunableBalloon.BALLOON_DURATION, balloon_data.balloon_delay, balloon_data.balloon_delay_random_offset, category_icon)
            return request

    @staticmethod
    def request_passive_balloon(sim, time_now):
        if time_now - sim.next_passive_balloon_unlock_time > create_time_span(minutes=PassiveBalloons.BALLOON_LONG_LOCKOUT):
            lockout_time = random.randint(0, PassiveBalloons.BALLOON_RANDOM)
            sim.next_passive_balloon_unlock_time = services.time_service().sim_now + create_time_span(minutes=lockout_time)
            return
        balloon_requests = []
        if len(PassiveBalloons.ROUTING_BALLOONS) > PassiveBalloons.MAX_NUM_BALLOONS:
            sampled_balloon_tuning = random.sample(PassiveBalloons.ROUTING_BALLOONS, PassiveBalloons.MAX_NUM_BALLOONS)
        else:
            sampled_balloon_tuning = PassiveBalloons.ROUTING_BALLOONS
        for balloon_weight_pair in sampled_balloon_tuning:
            balloon_request = PassiveBalloons.create_passive_ballon_request(sim, balloon_weight_pair.balloon)
            if balloon_request is not None:
                balloon_requests.append((balloon_weight_pair.weight, balloon_request))
        if len(balloon_requests) > 0:
            choosen_balloon = sims4.random.weighted_random_item(balloon_requests)
            if choosen_balloon is not None:
                choosen_balloon.distribute()
        lockout_time = PassiveBalloons.BALLOON_LOCKOUT + random.randint(0, PassiveBalloons.BALLOON_RANDOM)
        sim.next_passive_balloon_unlock_time = time_now + create_time_span(minutes=lockout_time)
