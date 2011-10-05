import time

from multiprocessing import Process, Queue
from Queue import Empty
from threading import Thread

from twisted.internet import defer

from .twistedx import producer
from .twistedx import receiver
from .connection import Connection

class Upload(Thread):
    """ A live stream to a room in a separate thread """
    
    def __init__(self, room, files, data={}, progress_callback=None, finished_callback=None, error_callback=None):
        """ Initialize.

        Args:
            room (:class:`Room`): Room where we are uploading
            files (dict): A dictionary, where key is the field name, and value is the file path

        Kwargs:
            data (dict): Additional data to post
            progress_callback (func): Callback to call as file is uploaded (parameters: current, total)
            finished_callback (func): Callback to call when upload is finished
            error_callback (func): Callback to call when an error occurred (parameters: exception)
        """
        Thread.__init__(self)

        self._connection_settings = room.get_campfire().get_connection().get_settings()
        self._room = room
        self._files = files
        self._data = data
        self._progress_callback = progress_callback
        self._finished_callback = finished_callback
        self._error_callback = error_callback
        self._abort = False
        self._uploading = False

    def is_uploading(self):
        """ Tell if upload is in progress.
        
        Returns:
            bool. Success
        """
        return self._uploading

    def stop(self):
        """ Stop uploading.

        It is recommended that you call join() after stopping this thread.

        Returns:
            :class:`Stream`. Current instance to allow chaining
        """
        self._abort = True
        return self

    def run(self):
        """ Called by the thread, it runs the process.

        NEVER call this method directly. Instead call start() to start the thread.

        Before finishing the thread using this thread, call join()
        """
        queue = Queue()
        process = UploadProcess(self._connection_settings, self._room, queue, self._files)
        if self._data:
            process.add_data(self._data)
        process.start()

        if not process.is_alive():
            return

        self._uploading = True

        done = False
        while not self._abort and not done:
            if not process.is_alive():
                self._abort = True
                break

            messages = None
            try:
                data = queue.get()
                if not data:
                    done = True
                    if self._finished_callback:
                        self._finished_callback()
                elif isinstance(data, tuple):
                    sent, total = data
                    if self._progress_callback:
                        self._progress_callback(sent, total)
                else:
                    self._abort = True
                    if self._error_callback:
                        self._error_callback(data, self._room)
            except Empty:
                time.sleep(0.5)

        self._uploading = False
        if self._abort and not process.is_alive() and self._error_callback:
            self._error_callback(Exception("Upload process was killed"), self._room)

        queue.close()
        if process.is_alive():
            queue.close()
            process.terminate()
        process.join()

class UploadProcess(Process):
    """ Separate process implementation to upload files """
    
    def __init__(self, settings, room, queue, files):
        """ Initialize.

        Args:
            settings (dict): Settings used to create a :class:`Connection` instance
            room (int): Room
            queue (:class:`multiprocessing.Queue`): Queue to share data between processes
            files (dict): Dictionary, where key is the field name, and value is the path
        """
        Process.__init__(self)
        self._room = room
        self._queue = queue
        self._files = files
        self._data = {}
        self._connection = Connection.create_from_settings(settings)
        self._reactor = None
        self._producer = None
        self._receiver = None

    def add_data(self, data):
        """ Add POST data.

        Args:
            data (dict): key => value dictionary
        """
        if not self._data:
            self._data = {}
        self._data.update(data)

    def run(self):
        """ Called by the process, it runs it.

        NEVER call this method directly. Instead call start() to start the separate process.
        If you don't want to use a second process, then call fetch() directly on this istance.

        To stop, call terminate()
        """

        producer_deferred = defer.Deferred()
        producer_deferred.addCallback(self._request_finished)
        producer_deferred.addErrback(self._request_error)

        receiver_deferred = defer.Deferred()
        receiver_deferred.addCallback(self._response_finished)
        receiver_deferred.addErrback(self._response_error)

        self._producer = producer.MultiPartProducer(
            self._files,
            self._data,
            callback = self._request_progress,
            deferred = producer_deferred
        )
        self._receiver = receiver.StringReceiver(receiver_deferred)

        headers = {
            'Content-Type': "multipart/form-data; boundary=%s" % self._producer.boundary
        }

        self._reactor, request = self._connection.build_twisted_request(
            "POST",
            "room/%s/uploads" % self._room.id,
            extra_headers = headers,
            body_producer = self._producer
        )

        request.addCallback(self._response)
        request.addErrback(self._shutdown)

        self._reactor.run()

    def _request_finished(self, bytes):
        pass

    def _request_progress(self, current, total):
        self._queue.put_nowait((current, total))

    def _request_error(self, error):
        self._queue.put_nowait(error)

    def _response_finished(self, data):
        self._reactor.stop()
        self._queue.put(None)

    def _response_error(self, data):
        self._reactor.stop()
        self._queue.put_nowait(error)

    def _response(self, response):
        response.deliverBody(self._receiver)

    def _shutdown(self, reason):
        pass
