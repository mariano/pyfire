import types
from .entity import CampfireEntity

class Message(CampfireEntity):
	""" Campfire message """
	
	_TYPE_ENTER = "EnterMessage"
	_TYPE_LEAVE = "KickMessage"
	_TYPE_PASTE = "PasteMessage"
	_TYPE_SOUND = "SoundMessage"
	_TYPE_TEXT = "TextMessage"
	_TYPE_TWEET = "TweetMessage"

	def __init__(self, campfire, data):
		""" Initialize.

		Args:
			campfire (:class:`Campfire`): Campfire instance
			data (dict or str): If string, message type will be set to either paste or text
		"""

		if type(data) == types.StringType:
			data = {
				"type": self._TYPE_PASTE if data.find("\n") >= 0 else self._TYPE_TEXT,
				"body": data
			}

		CampfireEntity.__init__(self, campfire, data)
		self.user = None
		self.room = None

		if "user_id" in data and data["user_id"]:
			self.user = self._campfire.get_user(data["user_id"])
		if "room_id" in data and data["room_id"]:
			self.room = self._campfire.get_room(data["room_id"])

	def is_joining(self):
		""" Tells if this message is a room join message.

		Returns:
			bool. Success
		"""

		return self.type == self._TYPE_ENTER

	def is_leaving(self):
		""" Tells if this message is a room leave message.

		Returns:
			bool. Success
		"""

		return self.type == self._TYPE_LEAVE

	def is_paste(self):
		""" Tells if this message is a paste.

		Returns:
			bool. Success
		"""

		return self.type == self._TYPE_PASTE

	def is_text(self):
		""" Tells if this message is a text message.

		Returns:
			bool. Success
		"""

		return self.type in [
			self._TYPE_PASTE,
			self._TYPE_TEXT,
			self._TYPE_TWEET
		]

	def highlight(self):
		""" Highlights a message.

		Returns:
			bool. Success
		"""
		return self._connection.post("messages/%s/star" % self.id)["success"]

	def remove_highlight(self):
		""" Removes the highlight of a message.

		Returns:
			bool. Success
		"""

		return self._connection.delete("messages/%s/star" % self.id)["success"]
