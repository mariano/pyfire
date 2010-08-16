class Entity:
	""" Dictionary based entity """
	
	def __init__(self, data={}):
		""" Initialize.

		Kwargs:
			data (dict): Data
		"""

		self.set_data(data)

	def __getattr__(self, name):
		""" If given attribute is not a class attribute, it will look
		for it in the entity data.

		Args:
			name (str): Property name to look for

		Returns:
			Value

		Raises:
			AttributeError
		"""
		
		if name in self._data:
			return self._data[name]
		raise AttributeError("No property named %s" % name)

	def get_data(self):
		""" Get entity data

		Returns:
			dict. Data
		"""

		return self._data

	def set_data(self, data={}):
		""" Set entity data

		Args:
			data (dict): Entity data
		"""

		self._data = data

class CampfireEntity(Entity):
	""" A Campfire entity """
	
	def __init__(self, campfire, data=None):
		""" Initialize.
		
		Args:
			campfire (:class:`Campfire`): Campfire Instance

		Kwargs:
			data (dict): Entity data
		"""

		Entity.__init__(self, data)
		self._campfire = campfire
		self._connection = None
		if self._campfire:
			self._connection = self._campfire.get_connection()

	def get_campfire(self):
		""" Get campfire instance.

		Returns:
			:class:`Campfire`. Campfire instance
		"""

		return self._campfire

	def get_connection(self):
		""" Get campfire connection.

		Returns:
			:class:`Connection`. Connection
		"""

		return self._connection
