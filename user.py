from .entity import CampfireEntity

class User(CampfireEntity):
	""" Campfire user """
	
	def __init__(self, campfire, id, current=False):
		""" Initialize.

		Args:
			campfire (:class:`Campfire`): Campfire instance
			id (str): User ID

		Kwargs:
			current (bool): Wether user is current user, or not
   		"""

		CampfireEntity.__init__(self, campfire)
		self.set_data(self._connection.get("users/%s" % id, key="user"))
		self.current = current
