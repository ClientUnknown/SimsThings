try:
    from _pathing import connectivity_handle as Handle, connectivity_handle_list as HandleList
except ImportError:

    class Handle:

        def __init__(self, location):
            self.location = location

    class HandleList:

        def __init__(self):
            pass
