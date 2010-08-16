# Pyfire: Campfire API implementation in Python #

The goal of this package is to provide an easy to use implementation
of the [Campfire API] [api] in Python.

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

### Streaming a room ###

This example shows us how to print out messages sent, or being sent, to a room.
Notice that this process will be listening for messages until you finish the 
process (by pressing ENTER). Also notice how it is not necessary to join the 
room in order to listen to messages.

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
			elif message.is_text():
				print "[%s] %s" % (user, message.body)

	campfire = pyfire.Campfire("SUBDOMAIN", "USERNAME", "PASSWORD", ssl=True)
	stream = campfire.get_room_by_name("My Room").get_stream()
	stream.attach(MessageListener.message).start()
	raw_input("|| Press ENTER to finish ||")
	stream.stop().join()

[api]: http://developer.37signals.com/campfire
