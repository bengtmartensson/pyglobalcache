#! /usr/bin/env python3

# Copyright (C) 2024, 2026 Bengt Martensson.

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
Control a GlobalCache device through its TCP API, all models (probably). Supports IR, serial and relay devices.
Contains a factory funtion: do not use the constructor for GlobalCache.
"""

import argparse
import logging
import socket
import sys
import time
import typing
import threading

VERSION = "0.2.0"

DEFAULT_GLOBALCACHE_IP = '192.168.1.70'
DEFAULT_GLOBALCACHE_CONTROLPORT = 4998 # No way to change in GlobalCache products
DEFAULT_TIMEOUT = 5
DEFAULT_SERIAL_SETTINGS = '9600,FLOW_NONE,PARITY_NO'

COMPLETEIR = 'completeir'
GETVERSION = 'getversion'
GETSERIAL  = 'get_SERIAL'
SENDIR     = 'sendir'
SETSERIAL  = 'set_SERIAL'
SETSTATE   = 'setstate'
GETSTATE   = 'getstate'

logger = logging.getLogger(__name__)

class GlobalCache(object):

    locks = {}
    def _get_lock(ip):
        lock = GlobalCache.locks.get(ip)
        if lock is not None:
            return lock

        GlobalCache.locks[ip] = threading.Lock()
        return GlobalCache.locks[ip]

    _globalcaches = {}

    class SmartSocket(object):
        def __init__(self, ip: str, portnr: int, timeout: int, immediate_close: bool = True) -> None:
            self._ip = ip
            self._timeout = timeout
            self._portnr = portnr
            self._immediate_close = immediate_close
            self._sock = None

        def close(self) -> None:
            self._sock.close()
            self._sock = None

        def _open(self):
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self._timeout)
            self._sock.connect((self._ip, self._portnr))

        def send_read(self, command: str, no_lines: str=1) -> typing.List[str]:
            logger.info('Sending "' + command + '" to ' + self._ip + ':' + str(self._portnr))
            if self._sock is None:
                self._open()
            try:
                self._sock.send(bytearray(command + '\r', 'US-ASCII'))
            except BrokenPipeError, AttributeError:
                logger.info('BrokenPipeError')
                self._open()
                self._sock.send(bytearray(command + '\r', 'US-ASCII'))
            answer = []
            for i in range(no_lines):
                a = self._sock.recv(4096)
                answer.append(a.decode('US-ASCII').rstrip())
            if self._immediate_close:
                self.close()
            logger.info('Response: "' + answer[0] + '"')
            return answer

    def globalcache(ip_address: str = DEFAULT_GLOBALCACHE_IP, portnr: int = DEFAULT_GLOBALCACHE_CONTROLPORT, timeout: int = DEFAULT_TIMEOUT, immediate_close: bool = False) -> GlobalCache:
        canon_ip = socket.gethostbyname(ip_address)
        gc = GlobalCache._globalcaches.get(canon_ip)
        if gc is None:
            gc = GlobalCache(canon_ip, portnr, timeout, immediate_close)
            GlobalCache._globalcaches[canon_ip] = gc
        return gc

    # "private", do not use, use the factory instead
    def __init__(self, ip_address: str = DEFAULT_GLOBALCACHE_IP, portnr: int = DEFAULT_GLOBALCACHE_CONTROLPORT, timeout: int = DEFAULT_TIMEOUT, immediate_close: bool = True) -> None:
        self._ip = ip_address # socket.gethostbyname(ip_address)
        self._portnr = portnr
        self._sequence_no = 1
        self._timeout = timeout
        self._lock = threading.Lock() # GlobalCache._get_lock(self._ip)
        self._immediate_close = immediate_close
        self._smartsock = GlobalCache.SmartSocket(self._ip, portnr, self._timeout, self._immediate_close)
        self._version = self._sendstring(GETVERSION, 1)[0]

    def IRDevice(self, module: int, port: int = 1, commands: typing.Dict[str, str] = {}) -> GCIRDevice:
        return GCIRDevice(self, module, port, commands)
    
    def RelayDevice(self, module: int=3, port: int=1) -> GCRelayDevice:
        return GCRelayDevice(self, module, port)

    def SerialDevice(self, module: int=1, timeout: int = DEFAULT_TIMEOUT) -> GCSerialDevice:
        return GCSerialDevice(self, module, timeout)
        
    def ready(self, timeout: int) -> bool:
        return self._version != None

    def close(self) -> None:
        self._smartsock.close()
    
    def getversion(self) -> str:
        return self._version

    def sendir(self, module: int, port: int, command, count: int) -> bool:
        cmdstring = self._ir_string(module, port, command, count)
        return self._sendir(cmdstring)

    def _sendir(self, commandstring: str) -> bool:
        self._sequence_no = self._sequence_no + 1
        answ = self._sendstring(commandstring)[0]
        list = commandstring.split(',')
        expected = COMPLETEIR + ',' + list[1] + ',' + list[2]
        return expected == answ

    def _sendstring(self, command: str, no_lines: int=1) -> typing.List[str]:
        with self._lock:
            answ = self._smartsock.send_read(command, no_lines)
        return answ
    
    def _connector(self, module: int, port: int = 1) -> str:
        return str(module) + ':' + str(port)

    def _moduleversion(self, module: int) -> str:
        return GETVERSION + "," + str(module)
        
    def _ir_string(self, module: int, port: int, command: str, count: int) -> str:
        return SENDIR + ',' + self._connector(module, port) + ',' + str(self._sequence_no) + ',' + str(command._frequency) + ',' + str(count) + command._datastring

    def setrelay(self, module: int, port: int, onoff: bool) -> bool:
        cmdstring = self._relay_set_string(module, port, onoff)
        answer = self._sendstring(cmdstring)
        return answer[0] == cmdstring[3:]

    def getrelay(self, module: int, port: int) -> bool:
        cmdstring = self._relay_get_string(module, port)
        answer = self._sendstring(cmdstring)[0]
        value = answer[10:11]
        return value == '1'

    def _relay_set_string(self, module: int, port: int, onoff: bool) -> str:
        return SETSTATE + ',' + self._connector(module, port) + ',' + ('1' if onoff else '0')

    def _relay_get_string(self, module: int, port: int) -> str:
        return GETSTATE + ',' + self._connector(module, port)
    
    def getserial(self, module: int=1) -> str:
        cmdstring = GETSERIAL + ',' + self._connector(module)
        return self._sendstring(cmdstring)[0]

    # settings is a string of the form
    # <baudrate>,<flowcontrol/duplex>,<parity>[,stopbits][,cable_id]
    def setserial(self, module: int=1, settings: str=DEFAULT_SERIAL_SETTINGS) -> str:
        cmdstring = SETSERIAL + ',' + self._connector(module) + ',' + settings
        return self._sendstring(cmdstring)[0]

    def version(self) -> str:
        return self._version

    def getmoduleversion(self, module: int) -> str:
        cmd = self._moduleversion(module)
        return self._sendstring(cmd)

class GCSerialDevice(object):
    def __init__(self, globalCache, module:int = 1, port:int = 1, timeout=DEFAULT_TIMEOUT):
        self._globalCache = globalCache
        self._module = module
        self._port = port
        self._timeout = timeout
        self._socketno = globalCache._portnr + module
        self._smartsocket = GlobalCache.SmartSocket(self._globalCache._ip, self._socketno, timeout, self._globalCache._immediate_close)

    def send(self, command: str, no_lines: str=1) -> typing.List[str]:
        with self._globalCache._lock:
            answ = self._smartsocket.send_read(command, no_lines)
        return answ

    def set(self, parameters=DEFAULT_SERIAL_SETTINGS) -> str:
        return self._globalCache.setserial(self._module, self._port, parameters)

    def close(self):
        self._smartsocket.close()

    def getversion(self) -> str:
        return self._globalCache.getmoduleversion(self._module)

class GCIRDevice(object):         
    def __init__(self, globalCache, module, port, commands):
        self._commands = commands if isinstance(commands, dict) else self.parse_commands_file(commands)
        self._globalCache = globalCache
        self._module = module
        self._port = port
    
    def send(self, command_name: str, count: int = 1) -> bool:
        command = self._commands[command_name]
        return self._globalCache.sendir(self._module, self._port, command, count)

    def getversion(self) -> str:
        return self._globalCache.getmoduleversion(self._module)

    def parse_commands_file(self, filename: str) -> typing.Dict[str, str]:
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
        def __init__(self, prontohex: str) -> None:
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

        def _pronto_int(self, list: typing.List[str]) -> int:
            x = list.pop(0)
            return int(x, 16)

    class InvalidProntoException(Exception):
        """This exception is thrown in response to Pronto Hex code."""
        pass

    class CommandNotFoundException(Exception):
        """"This exception is thrown when a command is not found."""
        pass

class GCRelayDevice(object):
    def __init__(self, globalCache: GlobalCache, module: int=3, port: int=1, pulselength: int=1) -> None:
        self._globalCache = globalCache
        self._module = module
        self._port = port
        self._pulselength = pulselength
    
    def setstate(self, onoff: bool) -> bool:
        return self._globalCache.setrelay(self._module, self._port, onoff)

    def turn_on(self) -> bool:
        return self.setstate(True)

    def turn_off(self) -> bool:
        return self.setstate(False)

    def toggle(self) -> bool:
        return self.setstate(not self.getstate())
    
    def getstate(self) -> bool:
        return self._globalCache.getrelay(self._module, self._port)

    def pulse(self) -> bool:
        status = self.turn_on()
        if not status:
            return False
        time.sleep(self._pulselength)
        return self.turn_off()

    def getversion(self) -> str:
        return self._globalCache.getmoduleversion(self._module)

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
        dest='timeout', type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument(
        '-V', '--version',
        help='Display version information for this program',
        dest='version', action='store_true')
    parser.add_argument(
        '-v', '--verbose',
        help='Have the communication with the GlobalCache echoed',
        dest='verbose', action='store_true')
 
    subparsers = \
        parser.add_subparsers(dest='subcommand', metavar='command')

    parser_sendir = subparsers.add_parser(
        'sendir',
        help='Send an IR signal.'
        )
    parser_sendir.add_argument(
        '-c', '--command',
        help='Named command to send from file in filename',
        dest='commandname', type=str, default=None
    )
    parser_sendir.add_argument(
        "-f", "--file",
        help='File containing command definitions',
        dest='filename', type=str, default=None
    )
    parser_sendir.add_argument(
        '--count',
        help='Number of times to send command',
        dest='count', type=int, default=1
    )
    parser_sendir.add_argument(
        'pronto_hex_numbers',
        help='Numbers making up a pronto hex ir signal',
        nargs='*'
    )
    parser_serial = subparsers.add_parser(
        'serial',
        help='Send a string to a serial port, get the response.'
        )
    parser_serial.add_argument(
        'message',
        help='String to send to the serial port',
        nargs='*', type=str
        )
    parser_relay = subparsers.add_parser(
        'relay',
        help='Set or clear a relay.'
        )
    parser_relay.add_argument('onoff',
            help='Value to set the relay to',
            nargs=1, type=str, default='pulse')
    parser_version = subparsers.add_parser(
        'version',
        help='Inquire version of the GlobalCache. '
        + ' (Use "--version" for the version of this program.)'
        )
    parser_getserial = subparsers.add_parser(
        'getserial',
        help='Inquire current serial parameters. '
        )

    return parser.parse_args()

def main():
    logging.basicConfig(level=logging.INFO)
    args = parse_commandline()

    if (args.version):
        print(VERSION)
        sys.exit(0)

    status = False
    try:
        globalcache = GlobalCache(args.ip, args.tcpport, args.timeout)
    except IOError:
        print('Could not open GlobalCache')
        sys.exit(2)

    if (args.subcommand == 'version'):
        print(globalcache.getversion())
        status = True
    elif args.subcommand == 'sendir':
        status = False
        if (args.filename != None and args.commandname != None):
            device = GCIRDevice(globalcache, args.module, args.port, args.filename)
            try:
                status = device.send(args.commandname, args.count)
            except KeyError:
                print('Command "' + args.commandname + '" unknown.')
        else:
            pronto_hex = " ".join(args.pronto_hex_numbers)
            cmd = GCIRDevice.Command(pronto_hex)
            status = globalcache.sendir(args.module, args.port, cmd, args.count)
    elif args.subcommand == 'relay':
        device = GCRelayDevice(globalcache, args.module, args.port)
        if args.onoff in ['on', '1', 'set']:
            status = device.turn_on()
        elif args.onoff in ['off', '0', 'clear']:
            status = device.turn_off()
        else:
            status = device.pulse()
    elif args.subcommand == 'getserial':
        answer = globalcache.getserial(args.module, args.port)
        print(answer)
        success = answer != None
    elif args.subcommand == 'serial':
        print('Not implemented yet')
    else:
        print('Unknown or missing subcommand, use --help for syntax.')

    if (not status):
        print('Failure')

    #print("Success" if status else "Failure")
    sys.exit(0 if status else 1)

if __name__ == "__main__":
    main()
