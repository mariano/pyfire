# Pyfire: Campfire API implementation in Python #

The goal of this package is to provide an easy to use implementation
of the [Campfire API] [api] in Python.

## LICENSE ##

Pyfire is released under the [MIT License] [license].

## INSTALLATION ##

### Requirements ###

#### Twisted ####

Pyfire requires [Twisted] [twisted] (version 10.1.0 or greater.) The 
[Twisted download page] [twisted-download] shows how to install Twisted on 
several platforms. 

For *Ubuntu based* systems, Twisted is in the official repositories, and can be
installed the following way:

*Ubuntu Lucid (10.04)*: the version included in the official repositories (10.0)
is older than what Pyfire requires. You can use twisted PPA's repository
instead, and install Twisted:

		$ sudo add-apt-repository ppa:twisted-dev/ppa
		$ sudo apt-get update
		$ sudo apt-get install python-twisted

*Ubuntu Maverick (10.10)*: the version included is what Pyfire requires, so
Twisted can be easily installed with:

		$ sudo apt-get install python-twisted

For *Fedora*, Twisted is in the official repositories and can be installed with:

		$ yum install python-twisted

For *Arch Linux*, Twisted is in the extra repository and can be installed with:

		$ pacman -S twisted

#### PyOpenSSL ####

For *Ubuntu/Debian based* systems, PyOpenSSL is in the official repositories, and can be
installed the following way:

		$ sudo apt-get install python-openssl

For *Fedora*, PyOpenSSL is in the official repositories and can be installed the following way:

		$ yum install pyOpenSSL

For *Arch Linux*, PyOpenSSL is in the extra repository, and can be installed with:

		$ pacman -S python2-pyopenssl

Other OS should read [PyOpenSSL download page] [pyopenssl-download].

### Installing ###

1. Uncompress the pyfire package file.
2. Unzip the downloaded file, and run the following command from within the 
created directory:

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

This example shows us how to upload a file to a room. The upload takes place in
a separate thread that spawns a separate process, so you should always use join()
to wait for the thread to complete before finishing your application.

Also in this example, you can see the use of callback functions to keep a
progress report of the upload, inform when the upload finished, or errored out.

NOTE: We did not join the room to post an upload, since it is not a requirement.

	import pyfire

	def progress(current, total):
		print("\b" * 80)
		print("Uploading %d out of %d (%-.1f%%)" % (
			current,
			total,
			100 * (float(current) / float(total))
		))

	def finished():
		print("\nUpload Finished!")
		print("Press ENTER to continue")

	def error(e):
		print("\nUpload STOPPED due to ERROR: %s" % e)
		print("Press ENTER to continue")

	campfire = pyfire.Campfire("SUBDOMAIN", "USERNAME", "PASSWORD", ssl=True)
	room = campfire.get_room_by_name("My Room")
	upload = room.upload(
		"/tmp/myfile.tar.gz",
		progress_callback = progress,
		finished_callback = finished,
		error_callback = error
	)
	upload.start()
	print ("Started upload of %s (press ENTER to stop upload)" % path)
	raw_input()
	if upload.is_uploading():
		upload.stop()
	upload.join()

### Streaming a room ###

This example shows us how to print out messages sent, or being sent, to a room.
Notice that this process will be listening for messages until you finish the 
process (by pressing ENTER).

#### LIVE streaming ####

Inspired by the work of Lawrence Oluyede on [Pinder] [pinder], live streaming of
a room is performed using the [Twisted] [twisted] module. This allows for real
live streaming (rather than the transcript based streaming shown in the next
example.) In order to stream a room, you first have to join it (Pyfire will 
automatically join the room for you)

The live stream will create a thread to process the incoming messages, and a
child process to fetch the messages from the server. Make sure you wait for the
thread to finish (using join()) before ending your main process.

	import pyfire

	def incoming(message):
		user = ""
		if message.user:
			user = message.user.name

		if message.is_joining():
			print "--> %s ENTERS THE ROOM" % user
		elif message.is_leaving():
			print "<-- %s LEFT THE ROOM" % user
		elif message.is_tweet():
			print "[%s] %s TWEETED '%s' - %s" % (user, message.tweet["user"], 
				message.tweet["tweet"], message.tweet["url"])
		elif message.is_text():
			print "[%s] %s" % (user, message.body)
		elif message.is_upload():
			print "-- %s UPLOADED FILE %s: %s" % (user, message.upload["name"],
				message.upload["url"])
		elif message.is_topic_change():
			print "-- %s CHANGED TOPIC TO '%s'" % (user, message.body)

	def error(e):
		print("Stream STOPPED due to ERROR: %s" % e)
		print("Press ENTER to continue")

	campfire = pyfire.Campfire("SUBDOMAIN", "USERNAME", "PASSWORD", ssl=True)
	room = campfire.get_room_by_name("My Room")
	room.join()
	stream = room.get_stream(error_callback=error)
	stream.attach(incoming).start()
	raw_input("Waiting for messages (Press ENTER to finish)\n")
	stream.stop().join()
	room.leave()

#### Transcript based streaming ####

This example shows how to stream a room without using actual live streaming, but
by using the room transcripts. This allows you to listen for messages without
having to explicitly join the room. If you want live streaming, it is always
recommended that you use LIVE steaming (as shown in the previous example), but
transcript based streaming may serve useful in other scenarios.

The trancript based stream creates a thread to process the incoming messages. 
By default, it will also create a second process to fetch data from Campfire.
Make sure you wait for the thread to finish (using join()) before ending your
main process.

NOTE: It is not necessary to join a room to listen for messages by using
transcripts.

	import pyfire

	def incoming(message):
		user = ""
		if message.user:
			user = message.user.name

		if message.is_joining():
			print "--> %s ENTERS THE ROOM" % user
		elif message.is_leaving():
			print "<-- %s LEFT THE ROOM" % user
		elif message.is_tweet():
			print "[%s] %s TWEETED '%s' - %s" % (user, message.tweet["user"], 
				message.tweet["tweet"], message.tweet["url"])
		elif message.is_text():
			print "[%s] %s" % (user, message.body)
		elif message.is_upload():
			print "-- %s UPLOADED FILE %s: %s" % (user, message.upload["name"], 
				message.upload["url"])
		elif message.is_topic_change():
			print "-- %s CHANGED TOPIC TO '%s'" % (user, message.body)

	campfire = pyfire.Campfire("SUBDOMAIN", "USERNAME", "PASSWORD", ssl=True)
	stream = campfire.get_room_by_name("My Room").get_stream(live=False)
	stream.attach(incoming).start()
	raw_input("|| Press ENTER to finish ||")
	stream.stop().join()

[license]: http://www.opensource.org/licenses/mit-license.php
[api]: http://developer.37signals.com/campfire
[poster]: http://atlee.ca/software/poster
[poster-download]: http://atlee.ca/software/poster#download
[twisted]: http://twistedmatrix.com
[twisted-download]: http://twistedmatrix.com/trac/wiki/Downloads
[pyopenssl-download]: http://pypi.python.org/pypi/pyOpenSSL
[pinder]: http://github.com/rhymes/pinder
