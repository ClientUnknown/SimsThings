import itertoolsfrom animation.animation_utils import clip_event_type_namefrom gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersfrom sims4.utils import setdefault_callablefrom uid import UniqueIdGeneratorimport servicesimport sims4.loglogger = sims4.log.Logger('GSI')with sims4.reload.protected(globals()):
    gsi_log_id = UniqueIdGenerator()
    animation_archive = {}
class AnimationArchiveGSILog:

    def __init__(self):
        self.clear_log()

    def clear_log(self):
        self.id = gsi_log_id()
        services_time_service = services.time_service()
        if services_time_service is not None and services_time_service.sim_timeline is not None:
            self.now = str(services_time_service.sim_timeline.now)
        else:
            self.now = 'Unavailable'
        self.events = []
        self.asm_requests = {}
animation_archive_schema = GsiGridSchema(label='Animation Archive', sim_specific=True)animation_archive_schema.add_field('game_time', label='GameTime', hidden=True)animation_archive_schema.add_field('arb_id', label='ARB ID', visualizer=GsiFieldVisualizers.INT)animation_archive_schema.add_field('asm', label='ASM', width=20)animation_archive_schema.add_field('request', label='Request', width=20)animation_archive_schema.add_field('arb', label='ARB String', width=75)with animation_archive_schema.add_has_many('Actors', GsiGridSchema) as sub_schema:
    sub_schema.add_field('name', label='Actor Name', width=20)
    sub_schema.add_field('actor', label='Actor', width=35)
    sub_schema.add_field('actor_id', label='Actor ID', width=35)
    sub_schema.add_field('suffix', label='Suffix', width=10)with animation_archive_schema.add_has_many('Params', GsiGridSchema) as sub_schema:
    sub_schema.add_field('name', label='Param Name', width=25)
    sub_schema.add_field('value', label='Value', width=25)
    sub_schema.add_field('type', label='Type', width=25)
    sub_schema.add_field('data', label='Data', width=25)with animation_archive_schema.add_has_many('Events', GsiGridSchema) as sub_schema:
    sub_schema.add_field('clip_name', label='Clip Name', width=20)
    sub_schema.add_field('type', label='Type', width=15)
    sub_schema.add_field('event_id', label='ID', width=5, visualizer=GsiFieldVisualizers.INT)
    sub_schema.add_field('callbacks', label='Callbacks', width=30)
    sub_schema.add_field('event_data', label='Event Data', width=30)
    sub_schema.add_field('tag', label='Tag', width=5)
    sub_schema.add_field('errors', label='Errors', width=10)archiver = GameplayArchiver('animation_archive', animation_archive_schema, add_to_archive_enable_functions=True)
def get_animation_log(arb, clear=False):
    animation_log = setdefault_callable(animation_archive, id(arb), AnimationArchiveGSILog)
    if clear:
        del animation_archive[id(arb)]
    return animation_log

def process_actors(animation_log, asm):
    actors = []
    if asm not in animation_log.asm_requests:
        for (name, obj, suffix) in asm.actors_info_gen():
            actors.append({'name': name, 'actor': str(obj), 'actor_id': str(obj.id), 'suffix': suffix})
    return actors

def process_parameters(animation_log, asm):
    params = []
    if asm not in animation_log.asm_requests:
        all_param_dicts = asm.get_all_parameters()
        for param_dict in all_param_dicts:
            for (k, v) in param_dict.items():
                if isinstance(k, str):
                    params.append({'name': k, 'value': str(v), 'type': 'Global'})
                else:
                    params.append({'name': '{}:{}'.format(k[1], k[0]), 'value': str(v), 'type': 'Object', 'data': str(k[2])})
    return params

def process_animation_request(arb, animation_log):
    pass

def process_handled_events(arb, animation_log):
    pass

def archive_animation_request(arb):
    animation_log = get_animation_log(arb, clear=True)
    if animation_log is None:
        return
    process_handled_events(arb, animation_log)
    process_animation_request(arb, animation_log)
    object_manager = services.object_manager()
    for asm_request in animation_log.asm_requests.values():
        asm_request['arb_id'] = int(animation_log.id)
        asm_request['game_time'] = animation_log.now
        asm_request['arb'] = animation_log.arb_contents
        for actor_id in arb.actor_ids:
            actor = object_manager.get(actor_id)
            if actor is not None and actor.is_sim:
                archiver.archive(data=asm_request, object_id=actor.id)
