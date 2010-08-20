from threading import Thread

from .connection import Connection
from .entity import CampfireEntity
from .message import Message
from .stream import Stream
from .upload import Upload

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

	def get_stream(self):
		""" Get room stream to listen for messages.

		Returns:
			:class:`Stream`. Stream
		"""
		return Stream(self)

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

	def upload(self, path, progress_callback=None, finished_callback=None, error_callback=None):
		""" Create a new thread to upload a file (thread should be
		then started with start() to perform upload.)

		Args:
			path (str): Path to file

		Kwargs:
			progress_callback (func): Callback to call as file is uploaded (parameters: current, total)
			finished_callback (func): Callback to call when upload is finished
			error_callback (func): Callback to call when an error occurred (parameters: exception)

		Returns:
			:class:`Upload`. Upload thread
		"""
		return Upload(
			self,
			{"upload": path},
			progress_callback = progress_callback,
			finished_callback = finished_callback,
			error_callback = error_callback
		)
