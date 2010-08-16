import cookielib
import copy
import json
import string
import types
import urllib
import urllib2

class ConnectionError(Exception):
	pass

class AuthenticationError(Exception):
	pass

class RESTRequest(urllib2.Request):
	""" A request for :class:`Connection`.
	
	Allows specification of method for request, besides built-in POST and GET """

	def __init__(self, url, method=None, data=None, headers={}, origin_req_host=None, unverifiable=False):
		self.set_method(method)
		urllib2.Request.__init__(self, url, 
			data=data,
			headers=headers, 
			origin_req_host=origin_req_host,
			unverifiable=unverifiable
		)

	def set_method(self, method):
		""" Set HTTP method.

		Args:
			method (str): Method (GET/POST/PUT/DELETE/etc.)
		"""
		self._method = method
		
	def get_method(self):
		""" Get HTTP method.

		Returns:
			str. The method (GET/POST/PUT/DELETE/etc.)
		"""
		return self._method or urllib2.Request.get_method(self)

class Connection:
	""" A connection to the Campfire API """
	
	def __init__(self, url=None, base_url=None, user=None, password=None, debug=False):
		""" Initialize.

		Kwargs:
			url (str): Destination URL
			base_url (str): If url is not provided, base_url is the base URL (e.g: mysite.campfirenow.com)
			user (str): The user for basic auth
			password (str): The password for basic auth
			debug (bool): wether to set debug ON or OFF
		"""
		self._settings = {
			"url": url,
			"base_url": base_url,
			"user": user,
			"password": password,
			"debug": debug
		}

		handlers = [
			urllib2.HTTPSHandler(debuglevel=int(self._settings["debug"])),
			urllib2.HTTPCookieProcessor(cookielib.CookieJar())
		]

		if self._settings["user"]:
			pwd_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
			password_url = None
			if url:
				password_url = url
			elif base_url:
				password_url = base_url
			if password_url:
				pwd_manager.add_password(None, password_url, self._settings["user"], self._settings["password"])

			handlers.append(urllib2.HTTPBasicAuthHandler(pwd_manager))

		self._opener = urllib2.build_opener(*handlers)

	@staticmethod
	def create_from_settings(settings):
		""" Create a connection with given settings.

		Args:
			settings (dict): A dictionary of settings

		Returns:
			:class:`Connection`. The connection
		"""
		return Connection(
			settings["url"], 
			settings["base_url"],
			settings["user"],
			settings["password"],
			settings["debug"]
		)

	def get_settings(self):
		""" Get settings

		Returns:
			dict. Settings
		"""
		return self._settings

	def post(self, url=None, post_data={}, parse_data=False, key=None, parameters=None):
		""" Issue a POST request.

		Kwargs:
			url (str): Destination URL
			post_data (dict): Dictionary of parameter and values
			parse_data (bool): If true, parse response data
			key (string): If parse_data==True, look for this key when parsing data
			parameters (dict): Additional GET parameters to append to the URL

		Returns:
			dict. Response (a dict with keys: success, data, info, body)
		
		Raises:
			AuthenticationError, ConnectionError, urllib2.HTTPError, ValueError, Exception
		"""

		post_data = json.dumps(post_data) if type(post_data) != types.StringType else post_data
		return self._fetch('POST', url=url, post_data=post_data, parse_data=parse_data, key=key, parameters=parameters, full_return=True)

	def get(self, url=None, parse_data=True, key=None, parameters=None):
		""" Issue a GET request.

		Kwargs:
			url (str): Destination URL
			parse_data (bool): If true, parse response data
			key (string): If parse_data==True, look for this key when parsing data
			parameters (dict): Additional GET parameters to append to the URL

		Returns:
			dict. Response (a dict with keys: success, data, info, body)

		Raises:
			AuthenticationError, ConnectionError, urllib2.HTTPError, ValueError, Exception
		"""

		return self._fetch('GET', url=url, post_data=None, parse_data=parse_data, key=key, parameters=parameters)
			
	def _fetch(self, method=None, url=None, post_data=None, parse_data=True, key=None, parameters=None, full_return=False):
		""" Issue a request.

		Kwargs:
			method (str): Request method (GET/POST/PUT/DELETE/etc.) If not specified, it will be POST if post_data is not None
			url (str): Destination URL
			post_data (str): A string of what to POST
			parse_data (bool): If true, parse response data
			key (string): If parse_data==True, look for this key when parsing data
			parameters (dict): Additional GET parameters to append to the URL
			full_return (bool): If set to True, get a full response (with success, data, info, body)

		Returns:
			dict. Response. If full_return==True, a dict with keys: success, data, info, body, otherwise the parsed data

		Raises:
			AuthenticationError, ConnectionError, urllib2.HTTPError, ValueError, Exception
		"""

		uri = url or self._settings["url"]
		if url and self._settings["base_url"]:
			uri = "%s/%s" % (self._settings["base_url"], url)
		uri += ".json"
		if parameters:
			uri += "?%s" % urllib.urlencode(parameters)

		headers = {
			"User-Agent": "kFlame 1.0",
			"Content-Type": "application/json"
		}

		request = RESTRequest(uri, method=method, headers=headers)
		if post_data is not None:
			request.add_data(post_data)
		response=None

		try:
			response = self._opener.open(request)
			body = response.read()
		except urllib2.HTTPError as e:
			if e.code == 401:
				raise AuthenticationError("Access denied while trying to access %s" % uri)
			elif e.code == 404:
				raise ConnectionError("URL not found: %s" % uri)
			else:
				raise
		except urllib2.URLError as e:
			raise ConnectionError("Error while fetching from %s: %s" % (uri, e))
		finally:
			if response:
				response.close()
			self._opener.close()

		data = None
		if parse_data:
			try:
				data = json.loads(body)
			except ValueError as e:
				raise ValueError("%s: Value: [%s]" % (e, body))

			if not key:
				key = string.split(url, "/")[0]
			if data and key:
				if key not in data:
					raise Exception("Invalid response (key %s not found): %s" % (key, data))
				data = data[key]

		if full_return:
			info = response.info() if response else None
			status = int(string.split(info["status"])[0]) if (info and "status" in info) else None

			return {
				"success": (status >= 200 and status < 300), 
				"data": data, 
				"info": info, 
				"body": body
			}

		return data
