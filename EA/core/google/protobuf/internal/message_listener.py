__author__ = 'robinson@google.com (Will Robinson)'
class MessageListener(object):

    def Modified(self):
        raise NotImplementedError

class NullMessageListener(object):

    def Modified(self):
        pass
