import os, sys
from flask import Flask, render_template
from twisted.web.server import Site

from orbit.resource import WebSocketResource, WSGISiteResource
from orbit.transaction import Transaction, WSProtocol, TransactionManager
from twisted.web.static import File
from twisted.internet import reactor
from twisted.web.wsgi import WSGIResource
from twisted.python import log
from twisted.web.resource import Resource

app = Flask(__name__)
app.root_path = os.path.join(os.path.dirname(__file__), '..')
app.static_folder = os.path.join(app.root_path, 'static')
app.template_folder = os.path.join(app.root_path, 'templates')

class EchoProtocol(WSProtocol):
	def dataReceived(self, ws, data, isBinary):
		ws.sendMessage(data, isBinary)


test_manager = TransactionManager()
test_resource = WebSocketResource(test_manager, 'echo_id')

@app.route('/')
def index():
	echo_id = test_manager.addTransaction(Transaction(EchoProtocol))
	return render_template('echo/index.html', echo_id=echo_id)

resource = WSGIResource(reactor, reactor.getThreadPool(), app)
static_resource = File(app.static_folder)

log.startLogging(sys.stdout)
ws = Resource()
ws.putChild('echo', test_resource)
root_resource = WSGISiteResource(resource, {'static': static_resource, 'ws': ws})
site = Site(root_resource)

if __name__ == '__main__':
	app.debug = True
	log.startLogging(sys.stdout)
	reactor.listenTCP(8000, site)
	reactor.run()