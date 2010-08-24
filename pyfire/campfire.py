import operator

from .connection import Connection
from .user import User
from .room import Room

class RoomNotFoundException(Exception):
	pass

class Campfire(object):
	""" Campfire API """
	
	def __init__(self, subdomain, user, password, ssl=False):
		""" Initialize.

		Args:
			subdomain (str): Campfire subdomain
			user (str): User
			password (str): pasword

		Kwargs:
			ssl (bool): enabled status of SSL
		"""
		self.base_url = "http%s://%s.campfirenow.com" % ("s" if ssl else "", subdomain)
		self._settings = {
			"user": user,
			"password": password
		}
		self._user = None
		self._users = {}
		self._rooms = {}

		_connection = Connection(url="%s/users/me" % self.base_url, user=user, password=password)
		user = _connection.get(key="user")
		
		self._connection = Connection(base_url=self.base_url, user=user["api_auth_token"], password="x")
		self._user = User(self, user["id"], current=True)
		self._user.token = user["api_auth_token"]

	def get_connection(self):
		""" Get connection

		Returns:
			:class:`Connection`. Connection
		"""
		return self._connection
	
	def get_rooms(self, sort=True):
		""" Get rooms list

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
		""" Get room

		Returns:
			:class:`Room`. Room
		"""
		if id not in self._rooms:
			self._rooms[id] = Room(self, id)
		return self._rooms[id]

	def get_user(self, id = None):
		""" Get user

		Returns:
			:class:`User`. User
		"""
		if not id:
			id = self._user.id

		if id not in self._users:
			self._users[id] = self._user if id == self._user.id else User(self, id)

		return self._users[id]
