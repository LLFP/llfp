#!/usr/bin/python3
# -*- coding: utf-8 -*-

'''
llfp by JJTech0130 - a Lutron LEAP library for Python
https://github.com/LLFP/llfp

'''

import json
import socket, ssl
import colorsys
import warnings

DEBUG = False

class leap:
    '''
    low-level LEAP commmands
    '''
    def __init__(self, host, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        self._sock = ssl.wrap_socket(sock)
        self._sock.connect((host,port))

    def send(self, packet):
        packet = json.dumps(packet) # Turn it into JSON
        packet += '\r\n' # Add a newline
        packet = packet.encode('utf-8') # Encode it in UTF-8
        self._sock.send(packet) # Send the packet
        return json.loads(self._sock.recv().decode('utf-8')) # Decode the result

    def read(self, url):
        packet = {
            "CommuniqueType": "ReadRequest",
            "Header": {
                "Url": str(url)
            }
        }

        return self.send(packet)

    def run(self, url, command):
        packet = {
            "CommuniqueType": "CreateRequest",
            "Header": {
                "Url": str(url)
            },
            "Body": {
                "Command": command
            }
        }

        return self.send(packet)

    # TODO: Run periodically to keep the connection allive
    def ping(self):
        return self.read("/server/status/ping")

    # Compat.
    @property
    def sock(self):
        return self.__sock

class bridge:
    '''
    Control the bridge/processor
    '''
    def __init__(self, host, port=8081):
        self.__leap = leap(host,port)


    def login(self, id, password):
        packet = {
            "CommuniqueType": "UpdateRequest",
            "Header": {
                "Url": "/login"
            },
            "Body": {
                "Login": {
                    "ContextType": "Application",
                    "LoginID": id,
                    "Password": password
                }
            }
        }

        return self.__leap.send(packet)

    @property
    def leap(self):
        return self.__leap

    @property
    def root(self):
        return area(self, "/area/rootarea")

class area():
    '''
    Area object
    '''
    def __init__(self, parent, href):
        self.__href = href
        self.__parent = parent
        self.__leap = self.__parent.leap
        summary = self.__getsummary()['Body']['Area']
        self.__href = summary['href'] # Prefer absolute href as returned by getsummary over any realative one we were given (for eg. /area/3 over /area/rootarea)
        self.__name = summary['Name'] # Human readable name
        self.__children = self.__getchildren() # Save children as private variable so we don't end up with repeat objects

    # Private functions
    def __getsummary(self):
        packet = {
            "CommuniqueType": "ReadRequest",
            "Header": {
                "Url": str(self.__href)
            }
        }

        return self.__leap.send(packet)

    def __getchildareas(self):
        packet = {
            "CommuniqueType": "ReadRequest",
            "Header": {
                "Url": str(self.__href) + "/childarea/summary"
            }
        }

        return self.__leap.send(packet)


    def __getchildren(self):
        children = []
        # Try to get child areas
        try:
            childlist = self.__getchildareas()['Body']['AreaSummaries']
            for child in childlist:
                childobj = area(self, child['href'])
                children.append(childobj)
        except KeyError:
            # We are a leaf, so see if we have any zones
            self.__leaf = True # Probably a better way, but this is how we tell for now.
            try:
                associatedzones = self.__getsummary()['Body']['Area']['AssociatedZones']
                for associatedzone in associatedzones:
                    zoneobj = zone(self, associatedzone['href'])
                    children.append(zoneobj)
            except KeyError:
                # We don't seem to have any children...
                pass

        return children

    # Properties
    @property
    def children(self):
        return self.__children.copy() # Lists are not automatically passed as copies

    @property
    def name(self):
        return self.__name

    @property
    def href(self):
        return self.__href

    @property
    def leaf(self):
        return self.__leaf

    @property
    def parent(self):
        return self.__parent

    @property
    def leap(self):
        return self.__leap

class leafArea(area):
    pass



class zone():
    '''
    Zone Base Class
    '''
    def __init__(self, parent, href):
        self._href = href
        self._parent = parent
        self._leap = self._parent.leap
        summary = self._getsummary()['Body']['Zone']
        self._href = summary['href'] # Prefer absolute href as returned by getsummary over any realative one we were given (for eg. /area/3 over /area/rootarea)
        self._name = summary['Name'] # Human readable name
        self._type = summary['ControlType'] # Type of zone

    # Private functions
    def _getsummary(self):
        packet = {
            "CommuniqueType": "ReadRequest",
            "Header": {
                "Url": str(self._href)
            }
        }

        return self._leap.send(packet)

    def _getstatus(self):
        packet = {
            "CommuniqueType": "ReadRequest",
            "Header": {
                "Url": str(self._href) + "/status"
            }
        }

        return self._leap.send(packet)

    # Properties
    @property
    def name(self):
        return self._name

    @property
    def href(self):
        return self._href

    @property
    def parent(self):
        return self._parent

    @property
    def leap(self):
        return self._leap

    @property
    def type(self):
        return self._type

# Zone Subclasses

class switchedZone(zone):
    def __init__(self, parent, href):
        super().__init__(parent, href)
        if self._type != 'Switched':
            warnings.warn("Zone Type Mismatch")

    # Private Functions
    def _getstate(self):
        # Return True or False
        state = self._getstatus()['Body']['ZoneStatus']['SwitchedLevel']
        if state == "On":
            return True
        else:
            return False

    def _setstate(self, state):
        # Accept True or False
        if state == True:
            s = "On"
        else:
            s = "Off"

        packet = {
            "CommuniqueType": "CreateRequest",
            "Header": {
                "Url": self._href + "/commandprocessor",
            },
            "Body": {
                "Command": {
                    "CommandType": "GoToSwitchedLevel",
                    "SwitchedLevelParameters": {
                        "SwitchedLevel": s,
                        "DelayTime":"00:00:01"
                    }
                }
            }
        }
        
        return self._leap.send(packet)

    # Properties
    @property
    def state(self):
        return self._getstate()

    @state.setter
    def state(self, state):
        self._setstate(state)




    

class dimmedZone(zone):
    pass

class spectrumTuningZone(zone):
    pass