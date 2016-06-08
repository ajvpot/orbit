from twisted.internet.defer import Deferred
from twisted.internet.interfaces import ITransport
from twisted.internet.protocol import Protocol, Factory, connectionDone
from twisted.internet.task import LoopingCall
from zope.interface import implements

from orbit import framing

class WebSocketServerFactory(Factory):
	def __init__(self, *args, **kwargs):
		reactor = kwargs.pop('reactor', None)
		if reactor is None:
			from twisted.internet import reactor
		self.reactor = reactor

	def buildProtocol(self, addr):
		return WebSocketProtocol()


class WebSocketProtocol(Protocol):
	def __init__(self):
		self.finished = Deferred()
		self.pingLoop = LoopingCall(self.ping)
		self.connected = False
		self.closedCleanly = False

	def write(self, payload):
		'''
			Send a BINARY message to the remote endpoint
		:param payload: The data to send
		'''
		self.sendMessage(payload)

	def sendMessage(self, data, isBinary=True):
		'''
			Send a message (either with the BINARY or TEXT opcode) to the remote user
		:param data: The data to send.
		:param isBinary: Whether the data is binary or text
		'''
		self.sendFrame(framing.BINARY if isBinary else framing.TEXT, data)

	def sendFrame(self, opcode, data):
		'''
			Send a raw WebSocket frame to the remote endpoint.
		:param opcode: The opcode to use
		:param data: The data to send with
		'''
		self.transport.write(framing.buildFrame(opcode, data))

	def ping(self):
		if self.connected:
			self.sendFrame(framing.PING, 'orbit-ping')

	def connectionMade(self):
		self.connected = True
		self.inner.connectionMade(self)
		self.pingLoop.start(10)

	def close(self, wasClean, code, reason):
		self.pingLoop.stop()
		self.finished.callback((wasClean, code, reason))

	def dataReceived(self, data):
		for opcode, data, (code, message), fin in framing.parseFrames(data):
			if opcode == framing.CLOSE:
				self.closedCleanly = True
				self.close(True, code, message)
			elif opcode == framing.PING:
				self.sendFrame(framing.PONG, data)
			elif opcode == framing.PONG:
				# we don't care about this
				pass
			elif opcode in (framing.BINARY, framing.TEXT):
				self.inner.dataReceived(self, data, opcode == framing.BINARY)


	def connectionLost(self, reason=connectionDone):
		self.connected = False
		if not self.closedCleanly:
			self.close(False, -1, str(reason))



