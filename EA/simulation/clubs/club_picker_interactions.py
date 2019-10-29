import itertoolsimport mathfrom clubs.club_tuning import ClubSuperInteractionfrom interactions import ParticipantTypefrom interactions.base.picker_interaction import PickerSuperInteraction, _TunablePieMenuOptionTuplefrom interactions.base.super_interaction import SuperInteractionfrom interactions.context import QueueInsertStrategyfrom interactions.social.social_super_interaction import SocialSuperInteractionfrom interactions.utils.tunable import TunableContinuationfrom objects.components.game.game_transition_liability import GameTransitionDestinationNodeValidatorfrom objects.components.game_component import GameRulesfrom objects.components.portal_lock_data import LockAllWithClubExceptionfrom objects.components.portal_locking_enums import ClearLockfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableList, TunableVariant, TunableEnumEntry, OptionalTunable, Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom ui.ui_dialog_picker import BasePickerRowfrom venues.venue_constants import NPCSummoningPurposeimport services
class ClubPickerSuperInteraction(PickerSuperInteraction):

    class _ClubGenerateFromParticipant(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'subject': TunableEnumEntry(description="\n                All Clubs this Sim is a member of will be generated, provided\n                they don't conflict with the tuned blacklist.\n                ", tunable_type=ParticipantType, default=ParticipantType.TargetSim), 'subject_blacklist': OptionalTunable(description='\n                If specified, some Clubs will not be generated.\n                ', tunable=TunableEnumEntry(description='\n                    No Clubs this Sim is a member of will be generated, even if\n                    the specified subject is a member.\n                    ', tunable_type=ParticipantType, default=ParticipantType.Actor))}

        def get_clubs_gen(self, cls, inst, target, context, **kwargs):
            club_service = services.get_club_service()
            if club_service is None:
                return
            inst_or_cls = inst if inst is not None else cls
            resolver = inst_or_cls.get_resolver(target=target, context=context, **kwargs)
            clubs = {club for sim_info in resolver.get_participants(self.subject) for club in club_service.get_clubs_for_sim_info(sim_info)}
            if self.subject_blacklist is not None:
                clubs -= {club for sim_info in resolver.get_participants(self.subject_blacklist) for club in club_service.get_clubs_for_sim_info(sim_info)}
            yield from clubs

    class _ClubGeneratorFromGatherings(HasTunableSingletonFactory, AutoFactoryInit):

        def get_clubs_gen(self, cls, inst, target, context, **kwargs):
            club_service = services.get_club_service()
            if club_service is None:
                return
            sim = context.sim if context is not None else inst.sim
            club_gathering = club_service.sims_to_gatherings_map.get(sim)
            if club_gathering is None:
                return
            for club in club_service.clubs_to_gatherings_map:
                if club is club_gathering.associated_club:
                    pass
                else:
                    yield club

    class _ClubPickerActionChallenge(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'challenge_game': GameRules.TunableReference(description='\n                The game that the club is being challenged at. This is used to\n                determine how many Sims are required, per team.\n                '), 'challenge_social_interaction': SocialSuperInteraction.TunableReference(description='\n                Specify an interaction that the challenging Sim runs on a Sim in\n                the challenged club (usually the leader). Once this interaction\n                completes, the challenge executes.\n                '), 'challenge_interaction': SuperInteraction.TunableReference(description='\n                The interaction to push on the Sims being challenged.\n                ')}

        def on_choice_selected(self, interaction, picked_items, **kwargs):
            club_service = services.get_club_service()
            if club_service is None:
                return
            actor_club_gathering = club_service.sims_to_gatherings_map.get(interaction.sim)
            if actor_club_gathering is None:
                return

            def _on_challenge_social_interaction_finished(challenge_social_interaction):
                if not challenge_social_interaction.is_finishing_naturally:
                    return
                minimum_players_per_team = math.ceil(self.challenge_game.players_per_game.lower_bound/self.challenge_game.teams_per_game.lower_bound)
                maximum_players_per_team = math.floor(self.challenge_game.players_per_game.upper_bound/self.challenge_game.teams_per_game.upper_bound)
                teams = []
                for (_, club) in zip(range(self.challenge_game.teams_per_game.upper_bound), itertools.chain((actor_club_gathering.associated_club,), picked_items)):
                    club_gathering = club_service.clubs_to_gatherings_map.get(club)
                    if club_gathering is None:
                        pass
                    else:
                        club_team = set()
                        challenger_sims = (interaction.sim,) if actor_club_gathering.associated_club is club else ()
                        for club_member in itertools.chain(challenger_sims, sorted(club_gathering.all_sims_in_situation_gen(), key=lambda sim: sim.sim_info is not club.leader)):
                            club_team.add(club_member)
                            if len(club_team) >= maximum_players_per_team:
                                break
                        if len(club_team) >= minimum_players_per_team:
                            teams.append(club_team)
                if len(teams) < self.challenge_game.teams_per_game.lower_bound:
                    return
                all_sims = tuple(itertools.chain.from_iterable(teams))
                game_transition_destination_node_validator = GameTransitionDestinationNodeValidator(self.challenge_game, teams=teams)
                for sim in all_sims:
                    context = challenge_social_interaction.context.clone_for_sim(sim, group_id=challenge_social_interaction.group_id, source_interaction_id=challenge_social_interaction.id, source_interaction_sim_id=challenge_social_interaction.sim.sim_id, insert_strategy=QueueInsertStrategy.NEXT)
                    sim.push_super_affordance(self.challenge_interaction, interaction.target, context, game_transition_destination_node_validator=game_transition_destination_node_validator)

            for club in picked_items:
                club_gathering = club_service.clubs_to_gatherings_map.get(club)
                if club_gathering is None:
                    pass
                else:
                    for club_member in sorted(club_gathering.all_sims_in_situation_gen(), key=lambda sim: sim.sim_info is not club.leader):
                        context = interaction.context.clone_from_immediate_context(interaction)
                        execute_result = interaction.sim.push_super_affordance(self.challenge_social_interaction, club_member, context)
                        if execute_result:
                            challenge_social_interaction = execute_result.interaction
                            challenge_social_interaction.register_on_finishing_callback(_on_challenge_social_interaction_finished)
                            break

    class _ClubPickerActionSummon(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'purpose': TunableEnumEntry(description='\n                The purpose/reason the NPC is being summoned.\n                ', tunable_type=NPCSummoningPurpose, default=NPCSummoningPurpose.DEFAULT)}

        def on_choice_selected(self, interaction, picked_items, **kwargs):
            venue = services.get_current_venue()
            if venue is None:
                return
            sim_infos = {sim_info for club in picked_items for sim_info in club.members if sim_info.is_npc}
            venue.summon_npcs(sim_infos, self.purpose, interaction.sim.sim_info)

    class _ClubPickerActionLockPortal(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'club_lock': LockAllWithClubException.TunableFactory(description='\n                The Club lock to apply to the target portal.\n                '), 'replace_lock_type': Tunable(description='\n                If checked, then the specified Club lock replaces any existing\n                Club lock, i.e. the only allowed Club is the new Club. If\n                unchecked, then the operation is additive: any Clubs specified\n                for this lock are also allowed, alongside any Clubs previously\n                allowed.\n                ', tunable_type=bool, default=True), 'clear_existing_locks': TunableEnumEntry(description='\n                Which existing locks should be cleared before adding the new \n                Club lock.\n                ', tunable_type=ClearLock, default=ClearLock.CLEAR_ALL)}

        def on_choice_selected(self, interaction, picked_items, **kwargs):
            for club in picked_items:
                lock_data = self.club_lock()
                lock_data.setup_data(None, None, interaction.get_resolver(associated_club=club))
                interaction.target.add_lock_data(lock_data, replace_same_lock_type=self.replace_lock_type, clear_existing_locks=self.clear_existing_locks)

    class _ClubPickerActionPushInteraction(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'continuation': TunableContinuation(description='\n                The interaction to push.\n                ', class_restrictions=(ClubSuperInteraction,))}

        def on_choice_selected(self, interaction, picked_items, **kwargs):
            for club in picked_items:
                interaction.push_tunable_continuation(self.continuation, associated_club=club)

    INSTANCE_TUNABLES = {'pie_menu_option': _TunablePieMenuOptionTuple(tuning_group=GroupNames.PICKERTUNING), 'club_generator': TunableVariant(description='\n            Define which Clubs are generated for this picker interaction.\n            ', from_participant=_ClubGenerateFromParticipant.TunableFactory(), from_gatherings=_ClubGeneratorFromGatherings.TunableFactory(), default='from_participant', tuning_group=GroupNames.PICKERTUNING), 'club_actions': TunableList(description='\n            A list of actions to perform, in order, on the selected Club.\n            ', tunable=TunableVariant(description='\n                An action to execute on the specified club.\n                ', challenge=_ClubPickerActionChallenge.TunableFactory(), npc_summon=_ClubPickerActionSummon.TunableFactory(), lock_portal=_ClubPickerActionLockPortal.TunableFactory(), push_interaction=_ClubPickerActionPushInteraction.TunableFactory(), default='challenge'), tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim, target=self.target)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        for club in cls.club_generator.get_clubs_gen(cls, inst, target, context, **kwargs):
            yield BasePickerRow(name=club.name, tag=club)

    def on_choice_selected(self, picked_item, **kwargs):
        for club_action in self.club_actions:
            club_action.on_choice_selected(self, (picked_item,))
lock_instance_tunables(ClubPickerSuperInteraction, picker_dialog=None)