import operatorimport protocolbuffers.Consts_pb2from protocolbuffers import DistributorOps_pb2from gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersfrom google.protobuf.text_format import MessageToStringimport servicesimport sims4.reload
def _configure_distributor_schema(schema):
    schema.add_field('index', label='Index', type=GsiFieldVisualizers.INT, width=0.67, unique_field=True)
    schema.add_field('target_name', label='Target Name', width=2)
    schema.add_field('type', label='Type', width=2)
    schema.add_field('size', label='Size', width=0.5)
    schema.add_field('manager', label='Manager', width=1)
    schema.add_field('mask', label='Mask Override', width=1)
    schema.add_field('blockers', label='Blockers(Mgr:Obj:Mask)', width=2.5)
    schema.add_field('tags', label='Barriers(Tag:Mask)', width=1.75)
    schema.add_field('details', label='Message Details', width=5)
    schema.add_view_cheat('distributor.gsi.toggle_op_details', label='Toggle Details')
    with schema.add_view_cheat('distributor.gsi.hide_op', label='Hide Selected Type') as cheat:
        cheat.add_token_param('type')
    schema.add_view_cheat('distributor.gsi.show_all_ops', label='Show All Types')
distributor_archive_schema = GsiGridSchema(label='Distributor Log')_configure_distributor_schema(distributor_archive_schema)archiver = GameplayArchiver('Distributor', distributor_archive_schema, max_records=250)sim_distributor_archive_schema = GsiGridSchema(label='Distributor Log Sim', sim_specific=True)_configure_distributor_schema(sim_distributor_archive_schema)sim_archiver = GameplayArchiver('SimDistributor', sim_distributor_archive_schema, max_records=150)with sims4.reload.protected(globals()):
    LOG_OP_DETAILS = False
    EXCLUDE_OP_TYPES = {DistributorOps_pb2.Operation.HEARTBEAT, DistributorOps_pb2.Operation.SET_GAME_TIME}
def archive_operation(target_id, target_name, manager_id, message, payload_type, index, client):
    if message.type in EXCLUDE_OP_TYPES:
        return
    message_type = '? UNKNOWN ?'
    manager_type = manager_id
    for (enum_name, enum_value) in protocolbuffers.Consts_pb2._MANAGERIDS.values_by_name.items():
        if enum_value.number == manager_id:
            manager_type = enum_name
            break
    for (enum_name, enum_value) in message.DESCRIPTOR.enum_values_by_name.items():
        if enum_value.number == message.type:
            message_type = enum_name
            break
    blocker_entries = []
    tag_entries = []
    for channel in sorted(message.additional_channels, key=operator.attrgetter('id.manager_id', 'id.object_id')):
        mask = hex(channel.mask) if channel.mask is not None else None
        if channel.id.manager_id == protocolbuffers.Consts_pb2.MGR_UNMANAGED:
            tag_entries.append('{}:{}'.format(str(channel.id.object_id), str(mask)))
        else:
            blocker_entries.append('{}:{}:{}'.format(str(channel.id.manager_id), '0x{:016x}'.format(channel.id.object_id), str(mask)))
    mask_override = ''
    if message.HasField('primary_channel_mask_override'):
        mask_override = '0x{:08x}'.format(message.primary_channel_mask_override)
    entry = {'target_name': target_name, 'index': index, 'size': len(message.data), 'type': message_type, 'manager': manager_type, 'mask': mask_override, 'blockers': ',\n'.join(blocker_entries), 'tags': ',\n'.join(tag_entries), 'details': ''}
    if LOG_OP_DETAILS:
        if not message.data:
            payload_details = ''
        elif payload_type is not None:
            payload_msg = payload_type()
            try:
                payload_msg.ParseFromString(message.data)
                try:
                    payload_details = MessageToString(payload_msg, as_one_line=True)
                except:
                    payload_details = '<exception formatting>'
            except:
                payload_details = '<exception parsing>'
        else:
            payload_details = '<unknown type>'
        entry['details'] = payload_details
    if manager_id == protocolbuffers.Consts_pb2.MGR_OBJECT:
        obj = services.object_manager().get(target_id)
        if obj is not None and obj.is_sim:
            if sim_archiver.enabled:
                sim_archiver.archive(data=entry, object_id=target_id, zone_override=client.zone_id)
            return
    elif manager_id == protocolbuffers.Consts_pb2.MGR_SIM_INFO:
        if sim_archiver.enabled:
            sim_info = services.sim_info_manager().get(target_id)
            if sim_info is not None:
                sim_archiver.archive(data=entry, object_id=sim_info.sim_id, zone_override=client.zone_id)
        return
    if archiver.enabled:
        archiver.archive(data=entry, object_id=target_id, zone_override=client.zone_id)
