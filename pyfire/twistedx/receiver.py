from twisted.internet import protocol
from twisted.web import client

class StringReceiver(protocol.Protocol):
    buffer = ""

    def __init__(self, deferred=None):
        self._deferred = deferred

    def dataReceived(self, data):
        self.buffer += data

    def connectionLost(self, reason):
        if self._deferred and reason.check(client.ResponseDone):
            self._deferred.callback(self.buffer)
        else:
            self._deferred.errback(self.buffer)
