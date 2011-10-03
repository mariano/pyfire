import datetime
import re

class Entity(object):
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
        super(CampfireEntity, self).__init__(data)
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

    def set_connection(self, connection):
        """ Set campfire connection.

        Args:
            connection (:class:`Connection`): Connection
        """
        self._connection = connection
    
    def set_data(self, data={}, datetime_fields=[]):
        """ Set entity data

        Args:
            data (dict): Entity data
            datetime_fields (array): Fields that should be parsed as datetimes
        """
        if datetime_fields:
            for field in datetime_fields:
                if field in data:
                    data[field] = self._parse_datetime(data[field])

        super(CampfireEntity, self).set_data(data)

    def _parse_datetime(self, value):
        """ Parses a datetime string from "YYYY/MM/DD HH:MM:SS +HHMM" format

        Args:
            value (str): String

        Returns:
            datetime. Datetime
        """
        offset = 0
        pattern = r"\s+([+-]{1}\d+)\Z"
        matches = re.search(pattern, value)
        if matches:
            value = re.sub(pattern, '', value)
            offset = datetime.timedelta(hours=int(matches.group(1))/100)
        return datetime.datetime.strptime(value, "%Y/%m/%d %H:%M:%S") - offset

