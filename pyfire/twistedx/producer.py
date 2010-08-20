import mimetypes
import os
import urllib

from twisted.internet import defer
from twisted.protocols import basic
from twisted.web import iweb
from zope.interface import implements

class MultiPartProducer:
	""" A producer that sends files and parameters as a multi part request. 
	
	INSPIRATIONS:

	The chunk creation is largely inspired by the work of Chris AtLee for his Poster package,
    a solution for multi part encoding in urllib2. You can find his work at Poster's website
	in http://atlee.ca/software/poster
	"""
	
	implements(iweb.IBodyProducer)

	CHUNK_SIZE = 2 ** 14

	def __init__(self, files={}, data={}, callback=None, deferred=None):
		""" Initialize.

		Kwargs:
			files (dict): A dictionary, where key is the field name, and value is the file path
			data (dict): Additional data to post
			callback (func): Callback to inform progress (receives sent, and total)
			deferred: Deferred to call when done, or when error occurs
		"""

		self._files = files
		self._file_lengths = {}
		self._data = data
		self._callback = callback
		self._deferred = deferred
		self.boundary = self._boundary()
		self.length = self._length()

	def startProducing(self, consumer):
		""" Start producing.

		Args:
			consumer: Consumer
		"""
		self._consumer = consumer
		self._current_deferred = defer.Deferred()
		self._sent = 0
		self._paused = False

		if not hasattr(self, "_chunk_headers"):
			self._build_chunk_headers()

		if self._data:
			block = ""
			for field in self._data:
				block += self._chunk_headers[field]
				block += self._data[field]
				block += "\r\n"

			self._send_to_consumer(block)

		if self._files:
			self._files_iterator = self._files.iterkeys()
			self._files_sent = 0
			self._files_length = len(self._files)
			self._current_file_path = None
			self._current_file_handle = None
			self._current_file_length = None
			self._current_file_sent = 0

			result = self._produce()
			if result:
				return result
		else:
			return defer.succeed(None)

		return self._current_deferred

	def resumeProducing(self):
		""" Resume producing """
		self._paused = False
		result = self._produce()
		if result:
			return result

	def pauseProducing(self):
		""" Pause producing """
		self._paused = True
	
	def stopProducing(self):
		""" Stop producing """
		self._finish(True)
		if self._deferred and self._sent < self.length:
			self._deferred.errback(Exception("Consumer asked to stop production of request body (%d sent out of %d)" % (self._sent, self.length)))

	def _produce(self):
		if self._paused:
			return

		done = False
		while not done and not self._paused:
			if not self._current_file_handle:
				field = self._files_iterator.next()
				self._current_file_path = self._files[field]
				self._current_file_sent = 0
				self._current_file_length = self._file_lengths[field]

				self._current_file_handle = open(self._current_file_path, "r")
				self._send_to_consumer(self._chunk_headers[field])

			chunk = self._current_file_handle.read(self.CHUNK_SIZE)
			if chunk:
				self._send_to_consumer(chunk)
				self._current_file_sent += len(chunk)

			if not chunk or self._current_file_sent == self._current_file_length:
				self._send_to_consumer("\r\n")
				self._current_file_handle.close()
				self._current_file_handle = None
				self._current_file_sent = 0
				self._current_file_path = None
				self._files_sent += 1

			if self._files_sent == self._files_length:
				done = True
				
		if done:
			self._send_to_consumer("--%s--\r\n" % self.boundary)
			self._finish()
			return defer.succeed(None)

	def _finish(self, forced=False):
		""" Cleanup code after asked to stop producing.

		Kwargs:
			forced (bool): If True, we were forced to stop
		"""
		if hasattr(self, "_current_file_handle") and self._current_file_handle:
			self._current_file_handle.close()
		
		if self._current_deferred:
			self._current_deferred.callback(self._sent)
			self._current_deferred = None

		if not forced and self._deferred:
			self._deferred.callback(self._sent)

	def _send_to_consumer(self, block):
		""" Send a block of bytes to the consumer.

		Args:
			block (str): Block of bytes
		"""
		self._consumer.write(block)
		self._sent += len(block)
		if self._callback:
			self._callback(self._sent, self.length)

	def _length(self):
		""" Returns total length for this request.

		Returns:
			int. Length
		"""
		self._build_chunk_headers()

		length = 0

		if self._data:
			for field in self._data:
				length += len(self._chunk_headers[field])
				length += len(self._data[field])
				length += 2

		if self._files:
			for field in self._files:
				length += len(self._chunk_headers[field])
				length += self._file_size(field)
				length += 2

		length += len(self.boundary)
		length += 6

		return length

	def _build_chunk_headers(self):
		""" Build headers for each field. """
		if hasattr(self, "_chunk_headers") and self._chunk_headers:
			return

		self._chunk_headers = {}
		for field in self._files:
			self._chunk_headers[field] = self._headers(field, True)
		for field in self._data:
			self._chunk_headers[field] = self._headers(field)

	def _headers(self, name, is_file=False):
		""" Returns the header of the encoding of this parameter.
		
		Args:
			name (str): Field name
		
		Kwargs:
			is_file (bool): If true, this is a file field
		
		Returns:
			array. Headers
		"""
		value = self._files[name] if is_file else self._data[name]
		_boundary = self.boundary.encode("utf-8") if isinstance(self.boundary, unicode) else urllib.quote_plus(self.boundary)
   
		headers = ["--%s" % _boundary]

		if is_file:
			disposition = 'form-data; name="%s"; filename="%s"' % (name, os.path.basename(value))
		else:
			disposition = 'form-data; name="%s"' % name

		headers.append("Content-Disposition: %s" % disposition)

		if is_file:
			file_type = self._file_type(name)
		else:
			file_type = "text/plain; charset=utf-8"

		headers.append("Content-Type: %s" % file_type)

		if is_file:
			headers.append("Content-Length: %i" % self._file_size(name))
		else:
			headers.append("Content-Length: %i" % len(value))

		headers.append("")
		headers.append("")

		return "\r\n".join(headers)

	def _boundary(self):
		""" Returns a random string to use as the boundary for a message.
		
		Returns:
			string. Boundary
		"""
		boundary = None
		try:
			import uuid
			boundary = uuid.uuid4().hex
		except ImportError:
			import random, sha
			bits = random.getrandbits(160)
			boundary = sha.new(str(bits)).hexdigest()
		return boundary

	def _file_type(self, field):
		""" Returns file type for given file field.
		
		Args:
			field (str): File field

		Returns:
			string. File type
		"""
		type = mimetypes.guess_type(self._files[field])[0]
		return type.encode("utf-8") if isinstance(type, unicode) else str(type)

	def _file_size(self, field):
		""" Returns the file size for given file field.

		Args:
			field (str): File field

		Returns:
			int. File size
		"""
		size = 0
		try:
			handle = open(self._files[field], "r")
			size = os.fstat(handle.fileno()).st_size
			handle.close()
		except:
			size = 0
		self._file_lengths[field] = size
		return self._file_lengths[field]
