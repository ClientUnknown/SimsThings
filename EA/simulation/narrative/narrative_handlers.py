import operatorfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemafrom sims4.resources import Typesimport servicesnarratives_schema = GsiGridSchema(label='Narratives/Tuned Narratives', auto_refresh=False)narratives_schema.add_field('narrative', label='Narrative', width=0.2)narratives_schema.add_field('groups', label='Narrative Groups', width=1)narratives_schema.add_field('active', label='Is Active', width=0.1)narratives_schema.add_field('previously_completed', label='Previously Completed', width=0.1)with narratives_schema.add_has_many('Linked Narratives', GsiGridSchema) as sub_schema:
    sub_schema.add_field('event', label='Narrative Event')
    sub_schema.add_field('narrative', label='Linked Narrative')
    sub_schema.add_field('progression_value', label='Progression Value')
    sub_schema.add_field('above_link', label='Above Link')
    sub_schema.add_field('above_threshold', label='Above Threshold')
    sub_schema.add_field('below_link', label='Below Link')
    sub_schema.add_field('below_threshold', label='Below Threshold')with narratives_schema.add_view_cheat('narrative.start_narrative', label='Start Narrative') as start_narrative_command:
    start_narrative_command.add_token_param('narrative')with narratives_schema.add_view_cheat('narrative.end_narrative', label='End Narrative') as end_narrative_command:
    end_narrative_command.add_token_param('narrative')with narratives_schema.add_view_cheat('narrative.reset_completion', label='Reset Completion') as reset_completion_command:
    reset_completion_command.add_token_param('narrative')
@GsiHandler('narratives_view', narratives_schema)
def generate_narrative_view():
    narratives = []
    narrative_service = services.narrative_service()
    narrative_tuning_manager = services.get_instance_manager(Types.NARRATIVE)
    for narrative in narrative_tuning_manager.types.values():
        narratives.append({'narrative': str(narrative.__name__), 'groups': ', '.join(group.name for group in narrative.narrative_groups), 'active': narrative in narrative_service.active_narratives, 'previously_completed': narrative in narrative_service.completed_narratives, 'Linked Narratives': list({'event': str(event.name), 'narrative': str(link.__name__)} for (event, link) in narrative.narrative_links.items())})
    return sorted(narratives, key=operator.itemgetter('narrative'))
narratives_links_schema = GsiGridSchema(label='Narratives/Narrative Links', auto_refresh=False)narratives_links_schema.add_field('event', label='Narrative Event', width=1)narratives_links_schema.add_field('narrative', label='Source Narrative', width=1)narratives_links_schema.add_field('narrative_link', label='Linked Narrative', width=1)narratives_links_schema.add_field('progression_value', label='Progression Value')narratives_links_schema.add_field('above_link', label='Above Link')narratives_links_schema.add_field('above_threshold', label='Above Threshold')narratives_links_schema.add_field('below_link', label='Below Link')narratives_links_schema.add_field('below_threshold', label='Below Threshold')with narratives_links_schema.add_view_cheat('narrative.trigger_event', label='Trigger Narrative Event') as trigger_narrative_command:
    trigger_narrative_command.add_token_param('event')
@GsiHandler('narratives_links_view', narratives_links_schema)
def generate_narrative_links_view():
    narrative_links = []
    narrative_service = services.narrative_service()
    for (narrative_cls, narrative_instance) in narrative_service.get_active_narrative_instances():
        for (event, linked_narrative) in narrative_cls.narrative_links.items():
            narrative_links.append({'event': str(event.name), 'narrative': str(narrative_cls.__name__), 'narrative_link': str(linked_narrative.__name__)})
        for (event, progression_value) in narrative_instance._narrative_progression.items():
            narrative_threshold_link = narrative_instance.narrative_threshold_links[event]
            narrative_links.append({'event': str(event.name), 'progression_value': str(progression_value), 'above_link': None if narrative_threshold_link.above_link is None else str(narrative_threshold_link.above_link.__name__), 'above_threshold': None if narrative_threshold_link.above_link is None else str(narrative_threshold_link.interval.upper_bound), 'below_link': None if narrative_threshold_link.below_link is None else str(narrative_threshold_link.below_link.__name__), 'below_threshold': None if narrative_threshold_link.below_link is None else str(narrative_threshold_link.interval.lower_bound)})
    return sorted(narrative_links, key=operator.itemgetter('event'))
