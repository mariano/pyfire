import time
from threading import Thread
from multiprocessing import Process, Queue
from Queue import Empty
from .connection import Connection
from .message import Message

class Stream(Thread):
	""" A live stream to a room in a separate thread """
	
	def __init__(self, room, pause=1, use_process=True):
		""" Initialize.

		Args:
			room (:class:`Room`): Room that is being streamed

		Kwargs:
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
		self._observers = []
		self._pause = pause
		self._use_process = use_process

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

	def notify(self, message):
		""" Notify all observers of a new message.

		Args:
			message (:class:`Message`): Incoming message
		"""

		for observer in self._observers:
			observer(message)

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

		self._abort = False
		campfire = self._room.get_campfire()
		process = StreamProcess(campfire.get_connection().get_settings(), self._room.id, pause=self._pause)

		if self._use_process:
			queue = Queue()
			process.set_queue(queue)
			process.start()

		while not self._abort:
			messages = None
			if self._use_process:
				try:
					messages = queue.get_nowait()
				except Empty:
					time.sleep(0.5)
					pass
			else:
				messages = process.fetch()

			if messages:
				for message in messages:
					self.notify(Message(campfire, message))

		if self._use_process:
			queue.close()
			process.terminate()

class StreamProcess(Process):
	""" Separate process implementation to get messages """
	
	def __init__(self, settings, room_id, queue=None, pause=1):
		""" Initialize.

		Args:
			settings (dict): Settings used to create a :class:`Connection` instance
			room_id (int): Room ID
			queue (:class:`multiprocessing.Queue`): A queue to share data between processes
			pause (int): Pause in seconds between requests
		"""

		Process.__init__(self)
		self._pause = pause
		self._room_id = room_id
		self._connection = Connection.create_from_settings(settings)
		self._last_message_id = None
		self.set_queue(queue)

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

		while True:
			messages = self.fetch()
			if messages:
				self._queue.put_nowait(messages)
			time.sleep(self._pause)

	def fetch(self):
		""" Fetch new messages.

		Returns:
			tuple. List of messages
		"""

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

		return messages
