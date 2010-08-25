import re
import types
from .entity import CampfireEntity

class Message(CampfireEntity):
	""" Campfire message """
	
	_TYPE_ENTER = "EnterMessage"
	_TYPE_LEAVE = "LeaveMessage"
	_TYPE_PASTE = "PasteMessage"
	_TYPE_SOUND = "SoundMessage"
	_TYPE_TEXT = "TextMessage"
	_TYPE_TIMESTAMP = "TimestampMessage"
	_TYPE_TOPIC_CHANGE = "TopicChangeMessage"
	_TYPE_TWEET = "TweetMessage"
	_TYPE_UPLOAD = "UploadMessage"

	def __init__(self, campfire, data):
		""" Initialize.

		Args:
			campfire (:class:`Campfire`): Campfire instance
			data (dict or str): If string, message type will be set to either paste or text
		"""
		if type(data) == types.StringType:
			messageType = self._TYPE_PASTE if data.find("\n") >= 0 else self._TYPE_TEXT
			if messageType == self._TYPE_TEXT:
				matches = re.match("^https?://(www\.)?twitter\.com/([^/]+)/status/(\d+)", data)
				if matches:
					messageType = self._TYPE_TWEET
			data = {
				"type": messageType,
				"body": data
			}

		super(Message, self).__init__(campfire)

		self.set_data(data, ["created_at"])
		
		self.user = None
		self.room = None

		if "user_id" in data and data["user_id"]:
			self.user = self._campfire.get_user(data["user_id"])
		if "room_id" in data and data["room_id"]:
			self.room = self._campfire.get_room(data["room_id"])
			if self.is_upload():
				self.upload = self._connection.get("room/%s/messages/%s/upload" % (self.room.id, self.id), key="upload")
				if "full_url" in self.upload:
					self.upload["url"] = self.upload["full_url"]
					del self.upload["full_url"]

		if self.is_tweet():
			# Tweet formats may be different if the streaming is line, or transcript based (I know, I know...)
			matches = re.match("(.+)\s+--\s+@([^,]+),\s*(.+)$", self.body)
			if matches:
				self.tweet = {
					"tweet": matches.group(1),
					"user": matches.group(2),
					"url": matches.group(3)
				}
			else:
				tweet_data = {}
				if re.match("^---", self.body):
					for line in self.body.split("\n")[1:]:
						matches = re.match('^:([^:]+):\s*"?(.+)"?$', line)
						if matches:
							tweet_data[matches.group(1)] = matches.group(2)
	
				if tweet_data and "author_username" in tweet_data and "message" in tweet_data and "id" in tweet_data:
					self.tweet = {
						"tweet": tweet_data["message"],
						"user": tweet_data["author_username"],
						"url": "http://twitter.com/%s/status/%s" % (tweet_data["author_username"], tweet_data["id"])
					}
				else:
					self.type = self._TYPE_TEXT

	def is_by_current_user(self):
		""" Tells if this message was written by the current user.

		Returns:
			bool. Success
		"""
		return self.user.id == self._campfire.get_user().id

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

	def is_timestamp(self):
		""" Tells if this message is a timestamp.

		Returns:
			bool. Success
		"""
		return self.type == self._TYPE_TIMESTAMP

	def is_topic_change(self):
		""" Tells if this message is a topic change.

		Returns:
			bool. Success
		"""
		return self.type == self._TYPE_TOPIC_CHANGE

	def is_tweet(self):
		""" Tells if this message is a tweet.

		Returns:
			bool. Success
		"""
		return self.type == self._TYPE_TWEET

	def is_upload(self):
		""" Tells if this message is an upload message.

		Returns:
			bool. Success
		"""
		return self.type == self._TYPE_UPLOAD

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
