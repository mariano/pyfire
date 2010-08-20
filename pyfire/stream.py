import time

from threading import Thread
from multiprocessing import Process, Queue
from Queue import Empty

from twisted.internet import defer
from twisted.protocols import basic

from .connection import Connection
from .message import Message

class Stream(Thread):
	""" A live stream to a room in a separate thread """
	
	def __init__(self, room, live=True, error_callback=None, pause=1, use_process=True):
		""" Initialize.

		Args:
			room (:class:`Room`): Room that is being streamed

		Kwargs:
			live (bool): If True, issue a live stream, otherwise an offline stream
			error_callback (func): A callback to call when an error occurs
			pause (int): Pause in seconds between requests
			use_process (bool): If True, use a separate process to fetch the messages

		Raises:
			AssertionError
		"""
		assert pause > 0, 'A pause of at least 1 second is needed'

		Thread.__init__(self)

		if pause < 1:
			raise ValueError("A minimum pause of 1 second needs to be specified")

		self._room = room
		self._live = live
		self._observers = []
		self._error_callback = error_callback
		self._pause = pause
		self._use_process = use_process
		self._streaming = False

	def attach(self, observer):
		""" Attach an observer.

		Args:
			observer (func): A function to be called when new messages arrive

		Returns:
			:class:`Stream`. Current instance to allow chaining
		"""
		if not observer in self._observers:
			self._observers.append(observer)
		return self

	def detach(self, observer):
		""" Detach an observer.

		Args:
			observer (func): The observer function already attached

		Returns:
			:class:`Stream`. Current instance to allow chaining
		"""
		try:
			self._observers.remove(observer)
		except ValueError:
			pass
		return self

	def incoming(self, messages):
		""" Called when incoming messages arrive.

		Args:
			messages (tuple): Messages (each message is a dict)
		"""
		if self._observers:
			campfire = self._room.get_campfire()
			for message in messages:
				for observer in self._observers:
					observer(Message(campfire, message))

	def is_streaming(self):
		""" Tell if streaming is in progress.

		Returns:
			bool. Success
		"""
		return self._streaming

	def stop(self):
		""" Stop streaming.

		It is recommended that you call join() after stopping this thread.

		Returns:
			:class:`Stream`. Current instance to allow chaining
		"""
		self._abort = True
		return self
	
	def run(self):
		""" Called by the thread, it runs the process.

		NEVER call this method directly. Instead call start() to start the thread.

		To stop, call stop(), and then join()
		"""

		if self._live:
			self._use_process = True

		self._abort = False
		campfire = self._room.get_campfire()
		process = StreamProcess(campfire.get_connection().get_settings(), self._room.id, live=self._live, pause=self._pause)

		if not self._use_process:
			process.set_callback(self.incoming)

		if self._use_process:
			queue = Queue()
			process.set_queue(queue)
			process.start()
			if not process.is_alive():
				return

		self._streaming = True

		while not self._abort:
			if self._use_process:
				if not process.is_alive():
					self._abort = True
					break

				try:
					self.incoming(queue.get_nowait())
				except Empty:
					time.sleep(0.5)
					pass
			else:
				process.fetch()
				time.sleep(self._pause)

		self._streaming = False
		if self._use_process and self._abort and not process.is_alive() and self._error_callback:
			self._error_callback(Exception("Streaming process was killed"))

		if self._use_process:
			queue.close()
			if process.is_alive():
				process.stop()
				process.terminate()
			process.join()

class StreamProcess(Process, basic.LineOnlyReceiver):
	""" Separate process implementation to get messages """
	
	delimiter = '\r'
	
	def __init__(self, settings, room_id, live=True, pause=1):
		""" Initialize.

		Args:
			settings (dict): Settings used to create a :class:`Connection` instance
			room_id (int): Room ID

		Kwargs:
			live (bool): If True, issue a live stream, otherwise an offline stream
			callback (func): Called when new messages arrive
			pause (int): Pause in seconds between requests
		"""
		Process.__init__(self)
		self._live = live
		self._pause = pause
		self._room_id = room_id
		self._callback = None
		self._queue = None
		self._reactor = None
		self._connection = Connection.create_from_settings(settings)
		self._last_message_id = None
	
	def set_callback(self, callback):
		""" Set callback.

		Args:
			callback (func): Called when new messages arrive
		"""
		self._callback = callback

	def set_queue(self, queue):
		""" Set the queue to communicate between processes.

		Args:
			queue (:class:`multiprocessing.Queue`): Queue to share data between processes
		"""
		self._queue = queue

	def run(self):
		""" Called by the process, it runs it.

		NEVER call this method directly. Instead call start() to start the separate process.
		If you don't want to use a second process, then call fetch() directly on this istance.

		To stop, call terminate()
		"""
		if not self._queue:
			raise Exception("No queue available to send messages")

		if self._live:
			self.fetch()
		else:
			while True:
				self.fetch()
				time.sleep(self._pause)

	def fetch(self):
		""" Fetch new messages. """
		if self._live:
			url = 'https://streaming.campfirenow.com/room/%s/live.json' % self._room_id

			self._reactor, request = self._connection.build_twisted_request("GET", url, full_url=True)

			request.addCallback(self._twisted_response)
			request.addErrback(self._twisted_shutdown)

			self._reactor.run()
		else:
			try:
				if not self._last_message_id:
					messages = self._connection.get("room/%s/transcript" % self._room_id, key="messages")
				else:
					messages = self._connection.get("room/%s/recent" % self._room_id, key="messages", parameters={
						"since_message_id": self._last_message_id
					})
			except:
				messages = []

			if messages:
				self._last_message_id = messages[-1]["id"]

			self.received(messages)

	def stop(self):
		""" Stop streaming (only applicable when self._live is True) """
		if self._live and self._reactor and self._reactor.running:
			self._reactor.stop()

	def received(self, messages):
		""" Called when new messages arrive.

		Args:
			messages (tuple): Messages
		"""
		if messages:
			if self._queue:
				self._queue.put_nowait(messages)

			if self._callback:
				self._callback(messages)

	def _twisted_response(self, response):
		""" Called issued by twisted when response arrives.

		Args:
			response (:class:`twisted.web.client.Response`): Response

		Returns:
			:class:(`twisted.internet.defer`). Deferred
		"""
		response.deliverBody(self)
		return defer.Deferred()
	
	def _twisted_shutdown(self, reason):
		""" Called issued by twisted when shutting down.

		Args:
			reason: Reason
		"""
		if self._reactor and self._reactor.running:
			self._reactor.stop()

	def lineReceived(self, line):
		""" Callback issued by twisted when new line arrives.

		Args:
			line (str): Incoming line
		"""
		message = self._connection.parse(line)
		if message:
			self.received([message])

	def connectionLost(self, reason):
		""" Callback isued by twisted when connection is lost.

		Args:
			reason (Exception): reason
		"""
		pass
