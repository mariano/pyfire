import cookielib
import copy
import httplib
import json
import string
import types
import urllib
import urllib2

from twisted.internet import reactor
from twisted.protocols import basic
from twisted.web import client
from twisted.web import http_headers

import poster

class ConnectionError(Exception):
	pass

class AuthenticationError(Exception):
	pass

class RESTRequest(urllib2.Request, object):
	""" A request for :class:`Connection`.
	
	Allows specification of method for request, besides built-in POST and GET """

	def __init__(self, url, method=None, data=None, headers={}, origin_req_host=None, unverifiable=False):
		self.set_method(method)
		super(RESTRequest, self).__init__(url, 
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

class Connection(object):
	""" A connection to the Campfire API """
	
	def __init__(self, url=None, base_url=None, user=None, password=None, authorizations={}, debug=False):
		""" Initialize.

		Kwargs:
			url (str): Destination URL
			base_url (str): If url is not provided, base_url is the base URL (e.g: mysite.campfirenow.com)
			user (str): The user for basic auth
			password (str): The password for basic auth
			authorizations (dict): Authorization header to send, indexed by URL
			debug (bool): wether to set debug ON or OFF
		"""
		self._settings = {
			"url": url,
			"base_url": base_url,
			"user": user,
			"password": password,
			"authorizations": authorizations or {},
			"debug": debug
		}

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
			authorizations = settings["authorizations"],
			debug = settings["debug"]
		)

	def get_settings(self):
		""" Get settings.

		Returns:
			dict. Settings
		"""
		return self._settings

	def get_setting(self, name):
		""" Get a setting value.

		Args:
			name (str): Setting name

		Returns:
			Value
		"""
		return self._settings[name]

	def set_setting(self, name, value):
		""" Set a setting value.

		Args:
			name (str): Setting name
			value: Setting value
		"""
		self._settings["name"] = value

	def set_debug(self, debug):
		""" Enable/disable debug

		Args:
			bool. Debug
		"""
		self._settings["debug"] = debug

	def delete(self, url=None, post_data={}, parse_data=False, key=None, parameters=None):
		""" Issue a PUT request.

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
		return self._fetch("DELETE", url, post_data=post_data, parse_data=parse_data, key=key, parameters=parameters, full_return=True)

	def put(self, url=None, post_data={}, parse_data=False, key=None, parameters=None):
		""" Issue a PUT request.

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
		return self._fetch("PUT", url, post_data=post_data, parse_data=parse_data, key=key, parameters=parameters, full_return=True)

	def post(self, url=None, post_data={}, parse_data=False, key=None, parameters=None, listener=None):
		""" Issue a POST request.

		Kwargs:
			url (str): Destination URL
			post_data (dict): Dictionary of parameter and values
			parse_data (bool): If true, parse response data
			key (string): If parse_data==True, look for this key when parsing data
			parameters (dict): Additional GET parameters to append to the URL
			listener (func): callback called when uploading a file

		Returns:
			dict. Response (a dict with keys: success, data, info, body)
		
		Raises:
			AuthenticationError, ConnectionError, urllib2.HTTPError, ValueError, Exception
		"""
		return self._fetch("POST", url, post_data=post_data, parse_data=parse_data, key=key, parameters=parameters, listener=listener, full_return=True)

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
		return self._fetch("GET", url, post_data=None, parse_data=parse_data, key=key, parameters=parameters)

	def get_headers(self):
		""" Get headers.

		Returns:
			tuple: Headers
		"""
		headers = {
			"User-Agent": "kFlame 1.0"
		}

		password_url = self._get_password_url()
		if password_url and password_url in self._settings["authorizations"]:
			headers["Authorization"] = self._settings["authorizations"][password_url]

		return headers

	def _get_password_url(self):
		""" Get URL used for authentication

		Returns:
			string: URL
		"""
		password_url = None
		if self._settings["user"] or self._settings["authorization"]:
			if self._settings["url"]:
				password_url = self._settings["url"]
			elif self._settings["base_url"]:
				password_url = self._settings["base_url"]
		return password_url

	def parse(self, text, key=None):
		""" Parses a response.

		Args:
			text (str): Text to parse

		Kwargs:
			key (str): Key to look for, if any

		Returns:
			Parsed value

		Raises:
			ValueError
		"""
		try:
			data = json.loads(text)
		except ValueError as e:
			raise ValueError("%s in %s: Value: [%s]" % (e, uri, text))

		if data and key:
			if key not in data:
				raise ValueError("Invalid response (key %s not found): %s" % (key, data))
			data = data[key]
		return data

	def build_twisted_request(self, method, url, body_producer=None, full_url=False):
		""" Build a request for twisted

		Args:
			method (str): Request method (GET/POST/PUT/DELETE/etc.) If not specified, it will be POST if post_data is not None
			url (str): Destination URL (full, or relative)

		Kwargs:
			body_producer (:class:`twisted.web.iweb.IBodyProducer`): Object producing request body
			full_url (bool): If False, URL is relative

		Returns:
			tuple. Tuple with two elements: reactor, and request
		"""
		uri = url if full_url else self._url(url)

		agent = client.Agent(reactor)
		rawHeaders = self.get_headers()
		headers = http_headers.Headers()
		for header in rawHeaders:
			headers.addRawHeader(header, rawHeaders[header])
		request = agent.request(method, uri, headers, body_producer)

		return (reactor, request)
			
	def _fetch(self, method, url=None, post_data=None, parse_data=True, key=None, parameters=None, listener=None, full_return=False):
		""" Issue a request.

		Args:
			method (str): Request method (GET/POST/PUT/DELETE/etc.) If not specified, it will be POST if post_data is not None

		Kwargs:
			url (str): Destination URL
			post_data (str): A string of what to POST
			parse_data (bool): If true, parse response data
			key (string): If parse_data==True, look for this key when parsing data
			parameters (dict): Additional GET parameters to append to the URL
			listener (func): callback called when uploading a file
			full_return (bool): If set to True, get a full response (with success, data, info, body)

		Returns:
			dict. Response. If full_return==True, a dict with keys: success, data, info, body, otherwise the parsed data

		Raises:
			AuthenticationError, ConnectionError, urllib2.HTTPError, ValueError
		"""
		has_file = False
		if post_data is not None and isinstance(post_data, dict):
			for key in post_data:
				if hasattr(post_data[key], "read"):
					has_file = True
					break

		headers = self.get_headers()
		if not has_file:
			headers["Content-Type"] = "application/json"

		handlers = []
		debuglevel = int(self._settings["debug"])
	
		if has_file:
			handlers.append(poster.streaminghttp.StreamingHTTPHandler(debuglevel=debuglevel))
			handlers.append(poster.streaminghttp.StreamingHTTPRedirectHandler())
			if hasattr(httplib, "HTTPS"):
				handlers.append(poster.streaminghttp.StreamingHTTPSHandler(debuglevel=debuglevel))
		else:
			handlers.append(urllib2.HTTPHandler(debuglevel=debuglevel))
			if hasattr(httplib, "HTTPS"):
				handlers.append(urllib2.HTTPSHandler(debuglevel=debuglevel))

		handlers.append(urllib2.HTTPCookieProcessor(cookielib.CookieJar()))

		password_url = self._get_password_url()
		if password_url and "Authorization" not in headers:
			pwd_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
			pwd_manager.add_password(None, password_url, self._settings["user"], self._settings["password"])
			if has_file:
				handlers.append(poster.streaminghttp.StreamingHTTPBasicAuthHandler(pwd_manager))
			else:
				handlers.append(urllib2.HTTPBasicAuthHandler(pwd_manager))

		opener = urllib2.build_opener(*handlers)

		if post_data is not None:
			if has_file:
				post_data, file_headers = poster.encode.multipart_encode(post_data, cb=listener)
				headers.update(file_headers)
			elif isinstance(post_data, dict):
				post_data = json.dumps(post_data)

		uri = self._url(url, parameters)
		request = RESTRequest(uri, method=method, headers=headers)
		if post_data is not None:
			request.add_data(post_data)

		response = None

		try:
			response = opener.open(request)
			body = response.read()
			if password_url and password_url not in self._settings["authorizations"] and request.has_header("Authorization"):
				self._settings["authorizations"][password_url] = request.get_header("Authorization")
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

			opener.close()

		data = None
		if parse_data:
			if not key:
				key = string.split(url, "/")[0]

			data = self.parse(body, key)

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

	def _url(self, url=None, parameters=None):
		""" Build destination URL.

		Kwargs:
			url (str): Destination URL
			parameters (dict): Additional GET parameters to append to the URL

		Returns:
			str. URL 
		"""

		uri = url or self._settings["url"]
		if url and self._settings["base_url"]:
			uri = "%s/%s" % (self._settings["base_url"], url)
		uri += ".json"
		if parameters:
			uri += "?%s" % urllib.urlencode(parameters)
		return uri
