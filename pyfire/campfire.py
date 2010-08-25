import operator
import urllib

from .connection import Connection
from .message import Message
from .user import User
from .room import Room

class RoomNotFoundException(Exception):
	pass

class Campfire(object):
	""" Campfire API """
	
	def __init__(self, subdomain, username, password, ssl=False, currentUser=None):
		""" Initialize.

		Args:
			subdomain (str): Campfire subdomain
			username (str): User
			password (str): pasword

		Kwargs:
			ssl (bool): enabled status of SSL
			currentUser (:class:`User`): If specified, don't auto load current user, use this one instead
		"""
		self.base_url = "http%s://%s.campfirenow.com" % ("s" if ssl else "", subdomain)
		self._settings = {
			"subdomain": subdomain,
			"username": username,
			"password": password,
			"ssl": ssl
		}
		self._user = currentUser
		self._users = {}
		self._rooms = {}

		if not self._user:
			_connection = Connection(url="%s/users/me" % self.base_url, user=username, password=password)
			user = _connection.get(key="user")
			
		self._connection = Connection(
			base_url=self.base_url, 
			user=self._user.token if self._user else user["api_auth_token"], 
			password="x"
		)

		if self._user:
			self._user.set_connection(self._connection)
		else:
			self._user = User(self, user["id"], current=True)
			self._user.token = user["api_auth_token"]

	def __copy__(self):
		""" Clone.

		Returns:
			:class:`Campfire`. Cloned instance
		"""
		return Campfire(
			self._settings["subdomain"],
			self._settings["username"],
			self._settings["password"],
			self._settings["ssl"],
			self._user
		)

	def get_connection(self):
		""" Get connection

		Returns:
			:class:`Connection`. Connection
		"""
		return self._connection
	
	def get_rooms(self, sort=True):
		""" Get rooms list.

		Kwargs:
			sort (bool): If True, sort rooms by name

		Returns:
			array. List of rooms (each room is a dict)
		"""
		rooms = self._connection.get("rooms")
		if sort:
			rooms.sort(key=operator.itemgetter("name"))
		return rooms

	def get_room_by_name(self, name):
		""" Get a room by name.

		Returns:
			:class:`Room`. Room

		Raises:
			RoomNotFoundException
		"""
		rooms = self.get_rooms()
		for room in rooms or []:
			if room["name"].lower() == name.lower():
				return self.get_room(room["id"])
		raise RoomNotFoundException("Room %s not found" % name)

	def get_room(self, id):
		""" Get room.

		Returns:
			:class:`Room`. Room
		"""
		if id not in self._rooms:
			self._rooms[id] = Room(self, id)
		return self._rooms[id]

	def get_user(self, id = None):
		""" Get user.

		Returns:
			:class:`User`. User
		"""
		if not id:
			id = self._user.id

		if id not in self._users:
			self._users[id] = self._user if id == self._user.id else User(self, id)

		return self._users[id]

	def search(self, terms):
		""" Search transcripts.

		Args:
			terms (str): Terms for search

		Returns:
			array. Messages
		"""
		messages = self._connection.get("search/%s" % urllib.quote_plus(terms), key="messages")
		if messages:
			messages = [Message(self, message) for message in messages]
		return messages

