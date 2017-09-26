"""
    Troop Server
    ------------

    Real-time collaborative Live Coding with FoxDot and SuperCollder.

    Sits on a machine (can be a performer machine) and listens for incoming
    connections and messages and distributes these to other connected peers.

"""

import socket
import SocketServer
import Queue
import sys
import time
import os.path
import json

from datetime import datetime
from time import sleep
from getpass import getpass
from hashlib import md5
from threading import Thread

from threadserv import ThreadedServer
from message import *
from interpreter import *
from config import *

from interface import DummyInterface
from interface.peer import Peer

class TroopServer:
    """
        This the master Server instance. Other peers on the
        network connect to it and send their keypress information
        to the server, which then sends it on to the others
    """
    def __init__(self, port=57890, log=False, debug=False):
          
        # Address information
        self.hostname = str(socket.gethostname())

        # Listen on any IP
        self.ip_addr  = "0.0.0.0"
        self.port     = int(port)

        # Public ip for server is the first IPv4 address we find, else just show the hostname
        self.ip_pub = self.hostname
        
        try:
            for info in socket.getaddrinfo(socket.gethostname(), None):
                if info[0] == 2:
                    self.ip_pub = info[4][0]
                    break
        except socket.gaierror:
            pass            

        # ID numbers
        self.clientIDs = {}
        self.last_id = -1

        # Look for an empty port
        port_found = False
        
        while not port_found:

            try:

                self.server = ThreadedServer((self.ip_addr, self.port), TroopRequestHandler)
                port_found  = True

            except socket.error:

                self.port += 1

        # Reference to the thread that is listening for new connections
        self.server_thread = Thread(target=self.server.serve_forever)
        
        # Clients (hostname, ip)
        self.clients = []

        # Give request handler information about this server
        TroopRequestHandler.master = self

        # Set a password for the server
        try:

            self.password = md5(getpass("Password (leave blank for no password): "))

        except KeyboardInterrupt:

            sys.exit("Exited")

        # Set up a char queue
        self.char_queue = Queue.Queue()
        self.char_queue_thread = Thread(target=self.update_send)

        # Set up log for logging a performance

        if log:
            
            # Check if there is a logs folder, if not create it

            log_folder = os.path.join(ROOT_DIR, "logs")

            if not os.path.exists(log_folder):

                os.mkdir(log_folder)

            # Create filename based on date and times
            
            self.fn = time.strftime("server-log-%d%m%y_%H%M%S.txt", time.localtime())
            path    = os.path.join(log_folder, self.fn)
            
            self.log_file   = open(path, "w")
            self.is_logging = True
            
        else:

            self.is_logging = False
            self.log_file = None

        ## Store text in a 2D array to compare to the gui

        ## self.text = [[]] # raw text

        self.contents = {"ranges":{}, "contents":"", "marks": []}

        # Debugging flag

        self.debugging = debug

    def get_client(self, client_address):
        """ Returns the server-side representation of a client
            using the client address tuple """
        for client in self.clients:
            if client == client_address:
                return client

    def leader(self):
        return self.clients[0]

    def get_contents(self):
        return self.contents

##    def get_contents(self):
##        """ Returns the text data stored on the server as a string """
##        lines = []
##        for line in self.text:
##            lines.append("".join([char[0] for char in line]))
##        return "\n".join(lines)
##
##    def get_ranges(self):
##        if self.text == [[]]:
##            return {}
##        # Define tags
##        ranges = {"text_{}".format(n):[] for n in [client.id for client in self.clients]}
##        # Get first tag
##        tag = None
##        for row in self.text:
##            for char, client in row:
##                stdout(char, client)
##                tag = "text_{}".format(client.id)
##                break
##            if tag != None:
##                break
##        else:
##            return {}
##        # Begin collecting ranges
##        endpoint = (len(self.text)-1, len(self.text[-1])-1)
##        start = "1.0"
##        for row, line in enumerate(self.text):
##            col = 0
##            for char, client in line:
##                next_tag = "text_{}".format(client.id)
##                if next_tag != tag or (row, col) == endpoint:
##                    end = "{}.{}".format(row + 1, col)
##                    ranges[tag].append([start, end])
##                    start = "{}.{}".format(row + 1, col + 1)                
##                col += 1
##        return ranges
##
##    def get_set_all_data(self):
##        return {"ranges": self.get_ranges(), "contents": self.get_contents()}

####    def handle_message(self, msg, client_address):
####        """ Update self.clients row/col and text information """
##
####        client = self.get_client(client_address)
##
####        if type(msg) == MSG_INSERT:
####
####            # Add a character(s) to self.text
####
####            row = msg['row'] - 1 
####            col = msg['col']
####
####            if msg["char"] == "\n":
####
####                # Create newline
####
####                self.text.insert(row + 1, self.text[row][col:])
####
####            else:
####
####                for i, char in enumerate(msg["char"]):
####
####                    col += i
####
####                    # Store the char and the appropriate client id
####
####                    self.text[row].insert(col, (char, client))
####
####            # Update client position
####
####            client.row = row
####            client.col = col
####
####        elif type(msg) == MSG_DELETE:
####
####            # Remove a character from self.text
####
####            row = msg['row'] - 1 
####            col = msg['col']
####
####            if col == len(self.text[row]):
####
####                # pull up the next line (if possible)
####
####                if row < (len(self.text)-1):
####
####                    new_row = self.text.pop(row + 1)
####
####                    self.text[row].extend(new_row)
####
####            else:
####
####                self.text[row].pop(col)
####
####        elif type(msg) == MSG_BACKSPACE:
####
####            # Remove a character from self.text
####
####            row = msg['row'] - 1 
####            col = msg['col']
####
####            if col == 0:
####
####                if row > 0:
####
####                    new_row = self.text.pop(row)
####
####                    self.text[row-1].extend(new_row)
####
####            else:
####
####                self.text[row].pop(col - 1) # delete the character before
####
####            # Update client position
####
####            client.row = row
####            client.col = col - 1       
####
####        elif type(msg) == MSG_SELECT:
####
####            pass
####
####        elif type(msg) == MSG_GET_ALL:
####
####            # TODO -- Send back to the client that requested
####
####            # MSG_SET_ALL(self.client_id(), self.get_set_all_data(), msg['client_id'])
####
####            pass
####
####        elif type(msg) == MSG_SET_MARK:
####
####            for client in self.clients:
####
####                if client == client_address:
####
####                    client.row = msg['row']
####                    client.col = msg['col']
####
####                    break
##
##        # Send any information to clients
##
####        self.respond(msg)
##        
##        return

    def respond(self, msg):
        """ Update all clients with a message. Only sends back messages to
            a client if the `reply` flag is nonzero. """

        for client in self.clients:

            try:

                if 'reply' in msg.data:

                    if msg['reply'] == 1 or client.id != msg['src_id']:

                        client.send(msg)

                else:

                    client.send(msg)

            except DeadClientError as err:

                # Remove client if no longer contactable

                self.remove_client(client.address)

                stdout(err)
        return

    def start(self):

        self.running = True
        self.server_thread.start()
        self.char_queue_thread.start()

        stdout("Server running @ {} on port {}\n".format(self.ip_pub, self.port))

        # if debugging, we can run a version on the server

        if self.debugging:

            self.gui = DummyInterface()
        
            self.gui.run()

            stdout("\nStopping...\n")

            self.kill()

        else:

            while True:

                try:

                    sleep(1)

                except KeyboardInterrupt:
    
                    stdout("\nStopping...\n")

                    self.kill()

                    break
        return

    def get_next_id(self):
        self.last_id += 1
        return self.last_id

    @staticmethod
    def read_configuration_file(filename):
        conf = {}
        with open(filename) as f:
            for line in f.readlines():
                line = line.strip().split("=")
                conf[line[0]] = line[1]
        return conf['host'], int(conf['port'])

    def update_send(self):
        """ This continually sends any characters to clients
        """
        # Attach the message with the ID of sender

        while self.running:

            try:

                client_address, msg = self.char_queue.get_nowait()

                # if debugging, add character to the gui

                if self.debugging:

                    self.gui.text.queue.put(msg)

                # If there is no src_id, remove the client from the address book

                try:

                    msg['src_id'] = self.clientIDs[client_address]

                except KeyError as err:

                    self.remove_client(client_address)

                    stdout(err)

                # If logging is set to true, store the message info

                if self.is_logging:

                    self.log_file.write("%.4f" % time.clock() + " " + repr(str(msg)) + "\n")

                # Store the response of the messages

                self.respond(msg)

            except Queue.Empty:

                sleep(0.01)

        return

    def remove_client(self, client_address):

        # Get the ID of the dead clienet

        for client in self.clients:

            if client == client_address:

                dead_client = client

                break

        else:

            dead_client = None

        # Remove from list(s)

        if client_address in self.clients:

            self.clients.remove(client_address)

        if client_address in self.clientIDs:
    
            del self.clientIDs[client_address]

        # Notify other clients

        if dead_client is not None:

            for client in self.clients:
                
                client.send(MSG_REMOVE(dead_client.id))

        return
        
    def kill(self):
        """ Properly terminates the server """
        if self.log_file is not None: self.log_file.close()

        outgoing = MSG_RESPONSE(-1, "Warning: Server manually killed by keyboard interrupt. Please close the application")

        for client in self.clients:

            client.send(outgoing)

        sleep(0.5)
        
        self.running = False
        self.server.shutdown()
        self.server.server_close()
        
        return

    def write(self, string):
        """ Replaces sys.stdout """
        if string != "\n":

            outgoing = MSG_RESPONSE(-1, string)

            for client in self.clients:
                
                client.send(outgoing)
                    
        return

# Request Handler for TroopServer 

class TroopRequestHandler(SocketServer.BaseRequestHandler):
    master = None
    bytes  = 2048
        
    def client_id(self):
        return self.master.clientIDs[self.client_address]

    def authenticate(self, password):
        
        if password == self.master.password.hexdigest():

            # Reply with the client id

            self.master.clientIDs[self.client_address] = self.master.get_next_id()

            stdout("New Connection from {}".format(self.client_address[0]))

            user_id = self.client_id()

        else:

            # Negative ID indicates failed login

            stdout("Failed login from {}".format(self.client_address[0]))

            user_id = -1

        self.request.send(str(user_id))

        return user_id

    def not_authenticated(self):
        return self.authenticate(self.get_message()[0]['password']) < 0

    def get_message(self):
        return self.reader.feed(self.request.recv(self.bytes))

    def handle_client_lost(self):
        stdout("Client @ {} has disconnected".format(self.client_address))
        self.master.remove_client(self.client_address)
        return

    def handle_connect(self, msg):
        """ Stores information about the new client """
        assert isinstance(msg, MSG_CONNECT)
        if self.client_address not in self.master.clients:
            new_client = Client(self.client_address, self.client_id(), self.request, name=msg['name'])
            self.connect_clients(new_client) # Contacts other clients
        return new_client

    def handle_set_all(self, msg):
        """ Forwards the SET_ALL message to requesting client """
        assert isinstance(msg, MSG_SET_ALL)
        new_client_id = msg['client_id']
        for client in self.master.clients:
            if client.id == new_client_id:
                data = msg["data"]
                client.send( MSG_SET_ALL(self.client_id(), data, new_client_id) )
                break
        return

    def leader(self):
        """ Returns the peer client that is "leading" """
        return self.master.leader()
    
    def handle(self):
        """ self.request = socket
            self.server  = ThreadedServer
            self.client_address = (address, port)
        """

        # This takes strings read from the socket and returns json objects

        self.reader = NetworkMessageReader()

        # Password test

        if self.not_authenticated():

            return

        # Enter loop
        
        while self.master.running:

            try:

                network_msg = self.get_message()

                # If we get none, just read in again

                if network_msg is None:

                    continue

            except Exception as e:

                # Handle the loss of a client

                self.handle_client_lost()

                break

            for msg in network_msg:

                # Some messages need to be handled here

                if isinstance(msg, MSG_CONNECT):

                    new_client = self.handle_connect(msg)

                    # Request the contents of Client 1 and update the new client

                    if len(self.master.clients) > 1:

                        ## TODO - Retrieve latest version from leader and update

                        self.leader().send(MSG_GET_ALL(self.client_id(), new_client.id))

                    else:

                        self.leader().send(MSG_SET_ALL(self.leader().id, self.master.get_contents(), 0))

                elif isinstance(msg, MSG_SET_ALL):

                    # Send the client *all* of the current code

                    self.handle_set_all(msg)

                else:

                    # Add any other messages to the send queue

                    self.master.char_queue.put((self.client_address, msg))
                        
        return

    def connect_clients(self, new_client):
        """ Update all other connected clients with info on new client & vice versa """

        # Store the client

        self.master.clients.append(new_client)

        # Add to the gui tracker -- test

        if self.master.debugging:       

            self.master.gui.text.peers[self.client_id()] = Peer(self.client_id(), self.master.gui.text, 0, 0)
            self.master.gui.text.peers[self.client_id()].name.set(new_client.name)

        # Connect each client

        msg1 = MSG_CONNECT(new_client.id, new_client.name, new_client.hostname, new_client.port)

        for client in self.master.clients:

            # Tell other clients about the new connection

            client.send(msg1)

            # Tell the new client about other clients

            if client != self.client_address:

                msg2 = MSG_CONNECT(client.id, client.name, client.hostname, client.port, client.row_tk(), client.col)

                new_client.send(msg2)

        return
    
# Keeps information about each connected client

class Client:

    def __init__(self, address, id_num, request_handle, name=""):

        self.hostname = address[0]
        self.port     = address[1]
        self.address  = address
        
        self.source = request_handle

        self.contents = None

        # For identification purposes

        self.id   = id_num
        self.name = name
        
        self.row = 0
        self.col = 0

    def row_tk(self):
        return self.row + 1

    def __repr__(self):
        return repr(self.address)

    def send(self, message):
        try:
            self.source.sendall(str(message)) 
        except:
            raise DeadClientError(self.hostname)
        return

    def __eq__(self, other):
        return self.address == other
    def __ne__(self, other):
        return self.address != other

