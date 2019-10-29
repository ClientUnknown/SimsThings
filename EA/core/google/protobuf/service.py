__author__ = 'petar@google.com (Petar Petrov)'
class RpcException(Exception):
    pass

class Service(object):

    def GetDescriptor():
        raise NotImplementedError

    def CallMethod(self, method_descriptor, rpc_controller, request, done):
        raise NotImplementedError

    def GetRequestClass(self, method_descriptor):
        raise NotImplementedError

    def GetResponseClass(self, method_descriptor):
        raise NotImplementedError

class RpcController(object):

    def Reset(self):
        raise NotImplementedError

    def Failed(self):
        raise NotImplementedError

    def ErrorText(self):
        raise NotImplementedError

    def StartCancel(self):
        raise NotImplementedError

    def SetFailed(self, reason):
        raise NotImplementedError

    def IsCanceled(self):
        raise NotImplementedError

    def NotifyOnCancel(self, callback):
        raise NotImplementedError

class RpcChannel(object):

    def CallMethod(self, method_descriptor, rpc_controller, request, response_class, done):
        raise NotImplementedError
