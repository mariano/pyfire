# Pyfire: Campfire API implementation in Python #

The goal of this package is to provide an easy to use implementation
of the [Campfire API] [api] in Python.

## INSTALLATION ##

### Requirements ###

Pyfire requires [Chris AtLee's poster package] [poster] to be installed.

1. Download the [latest poster package] [poster-download]
2. Unzip the downloaded file, and run the following command from within the created directory:

		$ python setup.py install

### Installing ###

1. Uncompress the pyfire package file.
2. Unzip the downloaded file, and run the following command from within the created directory:

		$ python setup.py install

## Usage Examples ##

### Sending a message to a room ###

This example shows us how to join a room, ask the user for a message,
post that message in the room, and then leave the room.

	import pyfire

	campfire = pyfire.Campfire("SUBDOMAIN", "USERNAME", "PASSWORD", ssl=True)
	room = campfire.get_room_by_name("My Room")
	room.join()
	message = raw_input("Enter your message --> ")
	if message:
		room.speak(message)
	room.leave()

### Uploading a file to a room ###

This example shows us how to upload a file to a room. The upload takes place
in a separate thread, so you should always use join() to wait for the thread
to complete before finishing your application.

NOTE: As you can see, we did not join the room to post an upload, since it
is not a requirement.

	import pyfire

	campfire = pyfire.Campfire("SUBDOMAIN", "USERNAME", "PASSWORD", ssl=True)
	room = campfire.get_room_by_name("My Room")
	upload = room.upload("/tmp/myfile.tar.gz")
	upload.start()
	print "Uploading %s" % path
	upload.join()

### Streaming a room ###

This example shows us how to print out messages sent, or being sent, to a room.
Notice that this process will be listening for messages until you finish the 
process (by pressing ENTER).

The stream creates a thread to process the incoming messages. By default, it
will also create a second process to fetch data from Campfire. Make sure
you wait for the thread to finish (using join()) before finishing your main
process.

NOTE: It is not necessary to join a room to listen for messages.

	import pyfire

	class MessageListener:
		@staticmethod
		def message(message):
			user = ""
			if message.user:
				user = message.user.name

			if message.is_joining():
				print "--> %s ENTERS THE ROOM" % user
			elif message.is_leaving():
				print "<-- %s LEFT THE ROOM" % user
			elif message.is_tweet():
				print "[%s] %s TWEETED '%s' - %s" % (user, message.tweet["user"], message.tweet["tweet"], message.tweet["url"])
			elif message.is_text():
				print "[%s] %s" % (user, message.body)
			elif message.is_upload():
				print "-- %s UPLOADED FILE %s: %s" % (user, message.upload["name"], message.upload["full_url"])
			elif message.is_topic_change():
				print "-- %s CHANGED TOPIC TO '%s'" % (user, message.body)

	campfire = pyfire.Campfire("SUBDOMAIN", "USERNAME", "PASSWORD", ssl=True)
	stream = campfire.get_room_by_name("My Room").get_stream()
	stream.attach(MessageListener.message).start()
	raw_input("|| Press ENTER to finish ||")
	stream.stop().join()

[api]: http://developer.37signals.com/campfire
[poster]:
[poster-download]:
