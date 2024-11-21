#! /usr/bin/env python3

# Copyright (C) 2024 Bengt Martensson.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see http://www.gnu.org/licenses/.

"""
Control a GlobalCache device. Supports IR and relay devices.
"""

import argparse
import logging
import socket
import sys
import time

VERSION = "0.0.1"

DEFAULT_GLOBALCACHE_IP = '192.168.1.70'
DEFAULT_GLOBALCACHE_CONTROLPORT = 4998 # No way to change in GlobalCache products
DEFAULT_TIMEOUT = 5

COMPLETEIR = 'completeir'
GETVERSION='getversion'
SENDIR = 'sendir'
SETSTATE = 'setstate'

logger = logging.getLogger(__name__)

class GlobalCache(object):
    def __init__(self, ip_address=DEFAULT_GLOBALCACHE_IP, portnr=DEFAULT_GLOBALCACHE_CONTROLPORT, timeout=DEFAULT_TIMEOUT):
        self._ip = ip_address
        self._portnr = portnr
        self._sequence_no = 1
        self._socket = None
        self._timeout = timeout
        self._version = self._sendstring(GETVERSION)

    def IRDevice(self, module, port, commands):
        return GCIRDevice(self, module, port, commands)
    
    def RelayDevice(self, module=3, port=1):
        return GCRelayDevice(self, module, port)
        
    def ready(self, timeout):
        return self._version != None
    
    def getversion(self):
        return self._version

    def sendir(self, module, port, command, count):
        cmdstring = self._ir_string(module, port, command, count)
        return self._sendir(cmdstring)

    def _sendir(self, commandstring):
        self._sequence_no = self._sequence_no + 1
        answ = self._sendstring(commandstring)
        list = commandstring.split(',')
        expected = COMPLETEIR + ',' + list[1] + ',' + list[2]
        return expected == answ

    def _sendstring(self, command):
        logger.info('Sending "' + command + '" to ' + str(self._ip) + '...')
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(self._timeout)
        self._socket.connect((self._ip, self._portnr))
        self._socket.send(bytearray(command + '\r', 'US-ASCII'))
        answ = self._socket.recv(4096)
        self._socket.close()
        answer = answ.decode('US-ASCII').rstrip()
        logger.info('Response: "' + answer + '"')
        return answer
        
    def _ir_string(self, module, port, command, count):
        return SENDIR + ',' + str(module) + ':' + str(port) + ',' + str(self._sequence_no) + ',' + str(command._frequency) + ',' + str(count) + command._datastring

    def setrelay(self, module, port, onoff):
        cmdstring = self._relay_string(module, port, onoff)
        answer = self._sendstring(cmdstring)
        return answer == cmdstring[3:]

    def _relay_string(self, module, port, onoff):
        return SETSTATE + ',' + str(module) + ':' + str(port) + ',' + ('1' if onoff else '0')

    def version(self):
        # todo
        return None

class GCIRDevice(object):         
    def __init__(self, globalCache, module, port, commands):
        self._commands = commands if isinstance(commands, dict) else self.parse_commands_file(commands)
        self._globalCache = globalCache
        self._module = module
        self._port = port

    #def _gc_string(self, command, count):
    #    return self._globalCache._ir_string(self._module, self._port, command, count)
    
    def send(self, command_name, count):
        command = self._commands[command_name]
        return self._globalCache.sendir(self._module, self._port, command, count)

    def parse_commands_file(self, filename):
        commands = {}
        with open(filename,'r') as cmds:  
            name = None
            for line in cmds:
                l = line.rstrip()
                if l == '':
                    continue

                if name == None:
                    name = l
                else:
                    commands[name] = self.Command(l)
                    name = None
        return commands
    
    class Command(object):
        def __init__(self, prontohex):
            list = prontohex.split()
            type = self._pronto_int(list)
            if type != 0:
                raise self.InvalidProntoException('Pronto does not start with 0000')
            fcode = self._pronto_int(list)
            self._frequency = int(1000000.0 / (0.241246 * fcode))
            no_intro_pair = self._pronto_int(list)
            no_reps_pair = self._pronto_int(list)
            self._datastring = "," + str(2*no_intro_pair + 1)
            for duration in list:
                self._datastring += ("," + str(int(duration, 16)))

        def _pronto_int(self, list):
            x = list.pop(0)
            return int(x, 16)

    class InvalidProntoException(Exception):
        """This exception is thrown in response to Pronto Hex code."""
        pass

    class CommandNotFoundException(Exception):
        """"This exception is when a command is not found."""
        pass

class GCRelayDevice(object):
    def __init__(self, globalCache, module=3, port=1, pulselength=1):
        self._globalCache = globalCache
        self._module = module
        self._port = port
        self._pulselength = pulselength
    
    def turn_on(self):
        return self._globalCache.setrelay(self._module, self._port, True)
    
    def turn_off(self):
        return self._globalCache.setrelay(self._module, self._port, False)
    
    def pulse(self):
        status = self.turn_on()
        if not status:
            return False
        time.sleep(self._pulselength)
        return self.turn_off()

def parse_commandline():
    parser = argparse.ArgumentParser(
        prog='globalcache',
        description="Program to send IR codes and relay commands to a GlobalCache."
    )
    parser.add_argument(
        '-i', '--ip', '-a', '--address',
        help='IP address or name of GlobalCache',
        dest='ip', type=str, default=DEFAULT_GLOBALCACHE_IP
    )
    parser.add_argument(
        '-c', '--command',
        help='Named command to send from file in filename',
        dest='commandname', type=str, default=None
    )
    parser.add_argument(
        "-f", "--file",
        help='File containing command definitions',
        dest='filename', type=str, default=None
    )
    parser.add_argument(
        '--count',
        help='Number of times to send command',
        dest='count', type=int, default=1
    )
    parser.add_argument(
        '--tcpport',
        help='TCP port of GlobalCache, default ' + str(DEFAULT_GLOBALCACHE_CONTROLPORT),
        dest='tcpport', default=DEFAULT_GLOBALCACHE_CONTROLPORT, type=int)
    parser.add_argument(
        '-p', '--port',
        help='Port to use within selected module on GlobalCache, default 1',
        metavar='port',
        dest='port', default=1, type=int)
    parser.add_argument(
        '-m', '--module',
        help='Module on GlobalCache, default 1',
        dest='module', default=1, type=int)
    parser.add_argument(
        '-t', '--timeout',
        help='Timeout in seconds',
        # metavar='s',
        dest='timeout', type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument(
        '-V', '--version',
        help='Display version information for this program',
        dest='version', action='store_true')
    parser.add_argument(
        '-v', '--verbose',
        help='Have the communication with the GlobalCache echoed',
        dest='verbose', action='store_true')
    parser.add_argument(
        'pronto_hex_numbers',
        help='Numbers making up a pronto hex ir signal',
        nargs='*'
    )
   
    return parser.parse_args()

def main():
    args = parse_commandline()

    if (args.version):
        print(VERSION)
        sys.exit(0)

    status = False
    globalcache = GlobalCache(args.ip, args.tcpport, args.timeout)
    if (args.filename != None and args.commandname != None):
        device = globalcache.IRDevice(args.module, args.port, args.filename)
        try:
            status = device.send(args.commandname, args.count)
        except KeyError:
            print('Command "' + args.commandname + '" unknown.')
    else:
        pronto_hex = " ".join(args.pronto_hex_numbers)
        cmd = GCIRDevice.Command(pronto_hex)
        status = globalcache.sendir(args.module, args.port, cmd, args.count)

    #else:
    #    print('Unknown or missing subcommand, use --help for syntax.')

    print("Success" if status else "Failure")
    sys.exit(0 if status else 1)

if __name__ == "__main__":
    main()