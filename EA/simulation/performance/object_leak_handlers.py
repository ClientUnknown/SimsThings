from performance.object_leak_tracker import NodeStatusfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemaimport servicesschema = GsiGridSchema(label='Object Leaks')schema.add_field('status', label='Status')schema.add_field('pid', label='Python Id', unique_field=True)schema.add_field('pid_hex', label='Python Id (hex)')schema.add_field('type', label='Type')schema.add_field('old_manager', label='Old Manager')schema.add_field('old_obj_id', label='Old Object Id')with schema.add_has_many('history', GsiGridSchema) as sub_schema:
    sub_schema.add_field('status', label='Status')
    sub_schema.add_field('gc_pass', label='GC Pass')
    sub_schema.add_field('time', label='Time')schema.add_view_cheat('mem.gc.collect', label='|mem.gc.collect')with schema.add_view_cheat('object_leak_tracker.dump_pid', label='|object_leak_tracker.dump_pid <python id>') as cheat:
    cheat.add_token_param('pid')
@GsiHandler('leaked_objects', schema)
def generate_data(*args, **kwargs):
    data = []
    tracker = services.get_object_leak_tracker()
    if tracker is None:
        return data
    for status in NodeStatus:
        for node in tracker.buckets[status]:
            node_data = {}
            node_data['status'] = status.name
            node_data['pid'] = node.pid
            node_data['pid_hex'] = hex(node.pid)
            node_data['type'] = node.obj_type.__name__
            node_data['old_manager'] = node.manager_type.__name__
            node_data['old_obj_id'] = hex(node.old_obj_id)
            time_data = []
            for (time_status, time_stamp) in node.time_stamps.items():
                time_data.append({'status': time_status.name, 'gc_pass': time_stamp.gc_pass, 'time': str(time_stamp.time)})
            node_data['history'] = time_data
            data.append(node_data)
    return data
