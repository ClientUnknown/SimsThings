try:
    import _profanity_filter
except:

    class _profanity_filter:

        @staticmethod
        def scan(*_, **__):
            pass

        @staticmethod
        def check(*_, **__):
            pass
scan = _profanity_filter.scancheck = _profanity_filter.check
def is_name_profane(sim_info):
    profanity_count = scan(sim_info.first_name)
    if profanity_count > 0:
        return True
    profanity_count = scan(sim_info.last_name)
    if profanity_count > 0:
        return True
    else:
        profanity_count = scan(sim_info.breed_name)
        if profanity_count > 0:
            return True
    return False
