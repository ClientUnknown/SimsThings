from gsi_handlers.gameplay_archiver import GameplayArchiver
    sub_schema.add_field('object_name', label='Object Name')
    sub_schema.add_field('object_id', label='Object ID')
    sub_schema.add_field('tests', label='Test')
    sub_schema.add_field('object_name', label='Object Name')
    sub_schema.add_field('object_id', label='Object ID')
    sub_schema.add_field('tests', label='Test')
    sub_schema.add_field('object_name', label='Object Name')
    sub_schema.add_field('object_id', label='Object ID')
    sub_schema.add_field('tests', label='Test')
def archive_picker_message(interaction, actor, target, picked_object, gen_objects):
    entry = {'interaction': str(interaction.affordance.__name__), 'actor': str(actor), 'target': str(target), 'picked_object': str(picked_object.definition.name)}
    gen_objects_info = []
    entry['gen_objects'] = gen_objects_info
    valid_objects_info = []
    entry['valid_objects'] = valid_objects_info
    invalid_objects_info = []
    entry['invalid_objects'] = invalid_objects_info
    for (obj, results) in gen_objects:
        test_results = ''
        valid = False
        lockout = False
        objid = str(obj.id)
        name = str(obj.definition.name)
        if results == AutonomousObjectPickerInteraction.LOCKOUT_STR:
            lockout = True
        if not lockout:
            for (result, continuation) in results:
                if result:
                    valid = True
                test_results += '\nResult: {} \nTest: {} \nAffordance Name {}\n'.format(result.result, result.reason, continuation)
        if valid:
            valid_object_info = {'object_name': name, 'object_id': objid, 'tests': test_results}
            valid_objects_info.append(valid_object_info)
        elif not lockout:
            invalid_object_info = {'object_name': name, 'object_id': objid, 'tests': test_results}
            invalid_objects_info.append(invalid_object_info)
        else:
            invalid_object_info = {'object_name': name, 'object_id': objid, 'tests': 'lockout'}
            invalid_objects_info.append(invalid_object_info)
        if not lockout:
            gen_object_info = {'object_name': name, 'object_id': objid, 'tests': test_results}
            gen_objects_info.append(gen_object_info)
        else:
            gen_object_info = {'object_name': name, 'object_id': objid, 'tests': 'lockout'}
            gen_objects_info.append(gen_object_info)
    picker_log_archiver.archive(data=entry)
