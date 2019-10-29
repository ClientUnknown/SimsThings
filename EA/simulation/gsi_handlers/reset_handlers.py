import sys
    sub_schema.add_field('callstack', label='Callstack')
def archive_reset_log_record(action, record, include_callstack=False):
    entry = {'action': action, 'target_object': str(record.obj), 'reset_reason': str(record.reset_reason), 'source_object': str(record.source), 'cause': str(record.cause)}
    if include_callstack:
        frame = sys._getframe(1)
        tb = traceback.format_stack(frame)
        lines = []
        for line in tb:
            index = line.find('Scripts')
            if index < 0:
                index = 0
            lines.append({'callstack': line[index:-1]})
        entry['Callstack'] = lines
    else:
        entry['Callstack'] = [{'callstack': ''}]
    reset_log_archiver.archive(data=entry)

def archive_reset_log_message(message):
    entry = {'action': message, 'target_object': '*****', 'reset_reason': '*****', 'source_object': '*****', 'cause': '*****'}
    entry['Callstack'] = [{'callstack': ''}]
    reset_log_archiver.archive(data=entry)

def archive_reset_log_entry(action, target, reason, source=None, cause=None, include_callstack=False):
    entry = {'action': action, 'target_object': str(target), 'reset_reason': str(reason), 'source_object': str(source), 'cause': cause}
    if include_callstack:
        frame = sys._getframe(1)
        tb = traceback.format_stack(frame)
        lines = []
        for line in tb:
            index = line.find('Scripts')
            if index < 0:
                index = 0
            lines.append({'callstack': line[index:-1]})
        entry['Callstack'] = lines
    else:
        entry['Callstack'] = [{'callstack': ''}]
    reset_log_archiver.archive(data=entry)
