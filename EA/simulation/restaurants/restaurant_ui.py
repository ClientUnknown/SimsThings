from distributor.ops import Op, protocol_constants
class ShowMenu(Op):

    def __init__(self, show_menu_message):
        super().__init__()
        self.op = show_menu_message

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.RESTAURANT_SHOW_MENU)
