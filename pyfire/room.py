from threading import Thread

from .connection import Connection
from .entity import CampfireEntity
from .message import Message
from .stream import Stream

class Room(CampfireEntity):
	""" Campfire room """
	
	def __init__(self, campfire, id):
		""" Initialize.

		Args:
			campfire (:class:`Campfire`): Campfire instance
			password (str): Room ID
		"""
		super(Room, self).__init__(campfire)
		self._load(id)

	def _load(self, id=None):
		self.set_data(self._connection.get("room/%s" % (id or self.id)))

	def get_stream(self, live=True):
		""" Get room stream to listen for messages.

		Kwargs:
			live (bool): If True, issue a live stream, otherwise an offline stream

		Returns:
			:class:`Stream`. Stream
		"""
		if live:
			self.join()
		return Stream(self, live=live)

	def get_uploads(self):
		""" Get list of recent uploads.

		Returns:
			array. List of uploads
		"""
		return self._connection.get("room/%s/uploads" % self.id, key="uploads")

	def get_users(self):
		""" Get list of users in the room.

		Returns:
			array. List of users
		"""
		self._load()
		return self.users

	def join(self):
		""" Join room.

		Returns:
			bool. Success
		"""
		return self._connection.post("room/%s/join" % self.id)["success"]

	def leave(self):
		""" Leave room.

		Returns:
			bool. Success
		"""
		return self._connection.post("room/%s/leave" % self.id)["success"]

	def lock(self):
		""" Lock room.

		Returns:
			bool. Success
		"""
		return self._connection.post("room/%s/lock" % self.id)["success"]

	def set_name(self, name):
		""" Set the room name.

		Args:
			name (str): Name

		Returns:
			bool. Success
		"""
		if not self._campfire.get_user().admin:
			return False

		result = self._connection.put("room/%s" % self.id, {"room": {"name": name}})
		if result["success"]:
			self._load()
		return result["success"]

	def set_topic(self, topic):
		""" Set the room topic.

		Args:
			topic (str): Topic

		Returns:
			bool. Success
		"""
		result = self._connection.put("room/%s" % self.id, {"room": {"topic": topic}})
		if result["success"]:
			self._load()

		return result["success"]

	def speak(self, message):
		""" Post a message.

		Args:
			message (:class:`Message` or string): Message

		Returns:
			bool. Success
		"""
		campfire = self.get_campfire()
		if not isinstance(message, Message):
			message = Message(campfire, message)

		result = self._connection.post(
			"room/%s/speak" % self.id,
			{"message": message.get_data()},
			parse_data=True,
			key="message"
		)

		if result["success"]:
			return Message(campfire, result["data"])
		return result["success"]

	def unlock(self):
		""" Unlock room.

		Returns:
			bool. Success
		"""
		return self._connection.post("room/%s/unlock" % self.id)["success"]

	def upload(self, path, listener=None):
		""" Create a new thread to upload a file (thread should be
		then started with start() to perform upload.)

		Args:
			path (str): Path to file

		Kwargs:
			listener (func): Callback to call as file is uploaded (parameters: parameter, current, total)

		Returns:
			:class:`Upload`. Upload thread
		"""
		return Upload(self, path, listener=listener)

class Upload(Thread):
	""" A live stream to a room in a separate thread """
	
	def __init__(self, room, path, listener=None):
		""" Initialize.

		Args:
			room (:class:`Room`): Room where we are uploading
			path (str): Path to file

		Kwargs:
			listener (func): Callback
		"""
		Thread.__init__(self)

		settings = room.get_campfire().get_connection().get_settings()
		self._path = path
		self._connection = Connection.create_from_settings(settings)
		self._room = room
		self._listener = listener

	def run(self):
		""" Called by the thread, it runs the process.

		NEVER call this method directly. Instead call start() to start the thread.

		Before finishing the thread using this thread, call join()
		"""
		file_handle = open(self._path, "r")

		try:
			result = self._connection.post(
				"room/%s/uploads" % self._room.id, 
				{"upload": file_handle},
				listener=self._listener
			)
		except:
			raise
		finally:
			file_handle.close()

