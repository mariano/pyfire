import re
import time

from threading import Thread
from multiprocessing import Process, Queue
from Queue import Empty

from twisted.internet import defer
from twisted.internet import protocol
from twisted.internet import ssl
from twisted.protocols import basic

from .connection import Connection
from .message import Message

class Stream(Thread):
    """ A live stream to a room in a separate thread """
    
    def __init__(self, room, live=True, error_callback=None, pause=None, use_process=True):
        """ Initialize.

        Args:
            room (:class:`Room`): Room that is being streamed

        Kwargs:
            live (bool): If True, issue a live stream, otherwise an offline stream
            error_callback (func): A callback to call when an error occurs
            pause (int): Pause in seconds between requests (if live==False), or pause
                         between queue checks
            use_process (bool): If True, use a separate process to fetch the messages

        Raises:
            AssertionError
        """
        if not live:
            if live is None:
                pause = 1
            assert pause > 0, 'A pause of at least 1 second is needed'
        elif pause is None:
            pause = 0.25

        Thread.__init__(self)

        self._room = room
        self._live = live
        self._observers = []
        self._error_callback = error_callback
        self._pause = pause
        self._use_process = use_process
        self._streaming = False

    def attach(self, observer):
        """ Attach an observer.

        Args:
            observer (func): A function to be called when new messages arrive

        Returns:
            :class:`Stream`. Current instance to allow chaining
        """
        if not observer in self._observers:
            self._observers.append(observer)
        return self

    def detach(self, observer):
        """ Detach an observer.

        Args:
            observer (func): The observer function already attached

        Returns:
            :class:`Stream`. Current instance to allow chaining
        """
        try:
            self._observers.remove(observer)
        except ValueError:
            pass
        return self

    def incoming(self, messages):
        """ Called when incoming messages arrive.

        Args:
            messages (tuple): Messages (each message is a dict)
        """
        if self._observers:
            campfire = self._room.get_campfire()
            for message in messages:
                for observer in self._observers:
                    observer(Message(campfire, message))

    def is_streaming(self):
        """ Tell if streaming is in progress.

        Returns:
            bool. Success
        """
        return self._streaming

    def stop(self):
        """ Stop streaming.

        It is recommended that you call join() after stopping this thread.

        Returns:
            :class:`Stream`. Current instance to allow chaining
        """
        self._abort = True
        return self
    
    def run(self):
        """ Called by the thread, it runs the process.

        NEVER call this method directly. Instead call start() to start the thread.

        To stop, call stop(), and then join()
        """

        if self._live:
            self._use_process = True

        self._abort = False
        campfire = self._room.get_campfire()

        if self._live:
            process = LiveStreamProcess(campfire.get_connection().get_settings(), self._room.id)
        else:
            process = StreamProcess(campfire.get_connection().get_settings(), self._room.id, pause=self._pause)

        if not self._use_process:
            process.set_callback(self.incoming)

        if self._use_process:
            queue = Queue()
            process.set_queue(queue)
            process.start()
            if not process.is_alive():
                return

        self._streaming = True

        while not self._abort:
            if self._use_process:
                if not process.is_alive():
                    self._abort = True
                    break

                try:
                    incoming = queue.get_nowait()
                    if isinstance(incoming, list):
                        self.incoming(incoming)
                    elif isinstance(incoming, Exception):
                        if self._error_callback:
                            self._error_callback(incoming)
                        self._abort = True

                except Empty:
                    time.sleep(self._pause)
                    pass
            else:
                process.fetch()
                time.sleep(self._pause)

        self._streaming = False
        if self._use_process and self._abort and not process.is_alive() and self._error_callback:
            self._error_callback(Exception("Streaming process was killed"))

        if self._use_process:
            queue.close()
            if process.is_alive():
                process.stop()
                process.terminate()
            process.join()

class StreamProcess(Process):
    """ Separate process implementation to get messages """
    
    def __init__(self, settings, room_id, pause=1):
        """ Initialize.

        Args:
            settings (dict): Settings used to create a :class:`Connection` instance
            room_id (int): Room ID

        Kwargs:
            pause (int): Pause in seconds between requests
        """
        Process.__init__(self)
        self._pause = pause
        self._room_id = room_id
        self._callback = None
        self._queue = None
        self._connection = Connection.create_from_settings(settings)
        self._last_message_id = None

    def get_room_id(self):
        """ Get room ID.

        Returns:
            int. Room ID
        """
        return self._room_id
    
    def set_callback(self, callback):
        """ Set callback.

        Args:
            callback (func): Called when new messages arrive
        """
        self._callback = callback

    def set_queue(self, queue):
        """ Set the queue to communicate between processes.

        Args:
            queue (:class:`multiprocessing.Queue`): Queue to share data between processes
        """
        self._queue = queue

    def run(self):
        """ Called by the process, it runs it.

        NEVER call this method directly. Instead call start() to start the separate process.
        If you don't want to use a second process, then call fetch() directly on this istance.

        To stop, call terminate()
        """
        if not self._queue:
            raise Exception("No queue available to send messages")

        while True:
            self.fetch()
            time.sleep(self._pause)

    def fetch(self):
        """ Fetch new messages. """
        try:
            if not self._last_message_id:
                messages = self._connection.get("room/%s/transcript" % self._room_id, key="messages")
            else:
                messages = self._connection.get("room/%s/recent" % self._room_id, key="messages", parameters={
                    "since_message_id": self._last_message_id
                })
        except:
            messages = []

        if messages:
            self._last_message_id = messages[-1]["id"]

        self.received(messages)

    def stop(self):
        pass

    def received(self, messages):
        """ Called when new messages arrive.

        Args:
            messages (tuple): Messages
        """
        if messages:
            if self._queue:
                self._queue.put_nowait(messages)

            if self._callback:
                self._callback(messages)

class LiveStreamProcess(StreamProcess):
    """ Separate process implementation to get messages """
    
    def __init__(self, settings, room_id):
        """ Initialize.

        Args:
            settings (dict): Settings used to create a :class:`Connection` instance
            room_id (int): Room ID
        """
        StreamProcess.__init__(self, settings, room_id)
        self._reactor = self._connection.get_twisted_reactor()
        self._protocol = None

    def get_connection(self):
        """ Get connection

        Returns:
            :class:`Connection`. Connection
        """
        return self._connection

    def set_protocol(self, protocol):
        """ Set protocol.

        Args:
            :class:`LiveStreamProtocol`: Protocol
        """
        self._protocol = protocol

    def run(self):
        """ Called by the process, it runs it.

        NEVER call this method directly. Instead call start() to start the separate process.
        If you don't want to use a second process, then call fetch() directly on this istance.

        To stop, call terminate()
        """
        if not self._queue:
            raise Exception("No queue available to send messages")

        factory = LiveStreamFactory(self)
        self._reactor.connectSSL("streaming.campfirenow.com", 443, factory, ssl.ClientContextFactory())
        self._reactor.run()

    def stop(self):
        """ Stop streaming """
        
        if self._protocol:
            self._protocol.factory.continueTrying = 0
            self._protocol.transport.loseConnection()

        if self._reactor and self._reactor.running:
            self._reactor.stop()

    def connected(self):
        """ Callback when a connection is made. """
        pass

    def disconnected(self, reason):
        """ Callback when an attempt to connect failed, or when connection is dropped.

        Args:
            reason (Exception): Exception
        """
        self._queue.put(reason)

class LiveStreamProtocol(basic.LineReceiver):
    """ Protocol for live stream """
    
    delimiter = "\r\n"

    def __init__(self):
        """ Constructor. """
        self._in_header = True
        self._headers = []
        self._len_expected = None
        self._buffer = ""
    
    def connectionMade(self):
        """ Called when a connection is made, and used to send out headers """

        headers = [
            "GET %s HTTP/1.1" % ("/room/%s/live.json" % self.factory.get_stream().get_room_id())
        ]

        connection_headers = self.factory.get_stream().get_connection().get_headers()
        for header in connection_headers:
            headers.append("%s: %s" % (header, connection_headers[header]))

        headers.append("Host: streaming.campfirenow.com")

        self.transport.write("\r\n".join(headers) + "\r\n\r\n")
        self.factory.get_stream().set_protocol(self)

    def lineReceived(self, line):
        """ Callback issued by twisted when new line arrives.

        Args:
            line (str): Incoming line
        """
        while self._in_header:
            if line:
                self._headers.append(line)
            else:
                http, status, message = self._headers[0].split(" ", 2)
                status = int(status)
                if status == 200:
                    self.factory.get_stream().connected()
                else:
                    self.factory.continueTrying = 0
                    self.transport.loseConnection()
                    self.factory.get_stream().disconnected(RuntimeError(status, message))
                    return

                self._in_header = False
            break
        else:
            try:
                self._len_expected = int(line, 16)
                self.setRawMode()
            except:
                pass

    def rawDataReceived(self, data):
        """ Process data.

        Args:
            data (str): Incoming data
        """
        if self._len_expected is not None:
            data, extra = data[:self._len_expected], data[self._len_expected:]
            self._len_expected -= len(data)
        else:
            extra = ""

        self._buffer += data
        if self._len_expected == 0:
            data = self._buffer.strip()
            if data:
                lines = data.split("\r")
                for line in lines:
                    try:
                        message = self.factory.get_stream().get_connection().parse(line)
                        if message:
                            self.factory.get_stream().received([message])
                    except ValueError:
                        pass

            self._buffer = ""
            self._len_expected = None
            self.setLineMode(extra)

class LiveStreamFactory(protocol.ReconnectingClientFactory):
    maxDelay = 120
    protocol = LiveStreamProtocol

    def __init__(self, stream):
        """ Initialize.

        Args:
            stream (:class:`LiveStreamProcess`): process receiving messages
        """
        self._stream = stream

    def get_stream(self):
        """ Get stream.

        Returns:
            stream (:class:`LiveStreamProcess`): process receiving messages
        """
        return self._stream
