#!/usr/bin/env python

# Copyright 2014 Dave Hughes <dave@waveform.org.uk>.
#
# This file is part of compoundpi.
#
# compoundpi is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# compoundpi is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# compoundpi.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )
str = type('')

import sys
import re
import datetime
import fractions
import time
import select
import socket
import SocketServer
import ipaddr

from compoundpi.cmdline import Cmd, CmdSyntaxError, CmdError


class CompoundPiCmd(Cmd):

    prompt = 'cpi> '

    def __init__(self):
        Cmd.__init__(self)
        self.pprint('CompoundPi Client')
        self.pprint(
            'Type "help" for more information, '
            'or "find" to locate Pi servers')
        self.servers = set()
        self.network = ipaddr.IPv4Network('192.168.0.0/16')
        self.client_port = 8000
        self.server_port = 8000
        self.timeout = 5
        self.path = '/tmp'
        # Set up a broadcast capable UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def parse_address(self, s):
        try:
            a = ipaddr.IPv4Address(s.strip())
        except ValueError:
            raise CmdSyntaxError('Invalid address "%s"' % s)
        if not a in self.network:
            raise CmdSyntaxError(
                'Address "%s" does not belong to the configured network '
                '"%s"' % (a, self.network))

    def parse_address_range(self, s):
        if not '-' in s:
            raise CmdSyntaxError('Expected two dash-separated addresses')
        start, finish = (
            self.parse_address(i)
            for i in s.split('-', 1)
            )
        return start, finish

    def parse_address_list(self, s):
        result = set()
        for i in s.split(','):
            if '-' in i:
                start, finish = self.parse_address_range(i)
                result |= {
                        ipaddr.IPv4Address(a)
                        for a in range(start, finish + 1)
                        }
            else:
                result.add(self.parse_address(i))
        return result

    def no_servers(self):
        raise CmdError(
                "You must define servers first (see help for 'find' and 'add')")

    def send(self, data, addresses):
        if isinstance(addresses, str):
            addresses = [address]
        for address in addresses:
            self.socket.sendto(data, (str(address), self.server_port))

    def broadcast(self, data):
        self.send(data, [self.network.broadcast])

    def responses(self, servers=None):
        if servers is None:
            servers = self.servers
        if not servers:
            servers = self.network
        result = {}
        start = time.time()
        while time.time() - start < self.timeout:
            if select.select([self.socket], [], [], 1)[0]:
                data, address = self.socket.recvfrom(512)
                address, port = address
                address = ipaddr.IPv4Address(address)
                if port != self.server_port:
                    self.pprint('Ignoring response from wrong port %s:%d' % (address, port))
                elif address in result:
                    self.pprint('Ignoring double response from %s' % address)
                elif address not in servers:
                    self.pprint('Ignoring response from %s' % address)
                else:
                    result[address] = data
                    if not isinstance(servers, ipaddr.IPv4Network):
                        if len(result) == len(servers):
                            break
        if not isinstance(servers, ipaddr.IPv4Network):
            if len(result) < len(servers):
                self.pprint('Missing response from %d servers' % (
                    len(servers) - len(result)))
        return result

    def transact(self, data, addresses):
        if addresses:
            addresses = self.parse_address_list(addresses)
            self.send(data, addresses)
        else:
            addresses = self.servers
            if not addresses:
                self.no_servers()
            self.broadcast(data)
        return self.responses(addresses)

    def do_config(self, arg=''):
        """
        Prints the client configuration.

        Syntax: config

        The config command is used to display the current client configuration.
        Use the related "set" command to alter the configuration.

        cpi> config
        """
        self.pprint_table(
            [('Setting', 'Value')] +
            [(name, getattr(self, name)) for name in (
                'network',
                'timeout',
                'client_port',
                'server_port',
                'path',
                )]
            )

    def do_servers(self, arg=''):
        """
        Display the list of servers.

        Syntax: servers

        The 'servers' command is used to list the set of servers that the
        client expects to communicate with. The content of the list can be
        manipulated with the 'find', 'add', and 'remove' commands.

        See also: find, add, remove.

        cpi> servers
        """
        if arg:
            raise CmdSyntaxError('Unexpected argument "%s"' % arg)
        if not self.servers:
            self.pprint('No servers are defined')
        else:
            self.pprint_table(
                [('Address',)] +
                [(key,) for key in self.servers]
                )

    def do_find(self, arg=''):
        """
        Find all servers on the current subnet.

        Syntax: find [count]

        The 'find' command is typically the first command used in a client
        session to locate all Pi's on the current subnet. If a count is
        specified, the command will display an error if the expected number of
        Pi's is not located.

        See also: add, remove, servers.

        cpi> find
        cpi> find 20
        """
        if arg:
            raise CmdSyntaxError('Unexpected argument "%s"' % arg)
        # XXX Implement count
        self.broadcast('PING\n')
        responses = self.responses()
        for address, response in responses.items():
            if response.strip() != 'PONG':
                self.pprint('Ignoring bogus response from %s' % address)
                del responses[address]
        if responses:
            self.servers = set(responses.keys())
            self.pprint('Found %d servers' % len(self.servers))
        else:
            raise CmdError('Failed to find any servers')

    def do_add(self, arg):
        """
        Add addresses to the list of servers.

        Syntax: add addresses

        The 'add' command is used to manually define the set of Pi's to
        communicate with. Addresses can be specified individually, as a
        dash-separated range, or a comma-separated list of ranges and
        addresses.

        See also: find, remove, servers.

        cpi> add 192.168.0.1
        cpi> add 192.168.0.1-192.168.0.10
        cpi> add 192.168.0.1,192.168.0.5-192.168.0.10
        """
        if not arg:
            raise CmdSyntaxError('You must specify address(es) to add')
        self.servers |= self.parse_address_list(arg)

    def do_remove(self, arg):
        """
        Remove addresses from the list of servers.

        Syntax: remove addresses

        The 'remove' command is used to remove addresses from the set of Pi's
        to communicate with. Addresses can be specified individually, as a
        dash-separated range, or a comma-separated list of ranges and
        addresses.

        See also: add, find, servers.

        cpi> remove 192.168.0.1
        cpi> remove 192.168.0.1-192.168.0.10
        cpi> remove 192.168.0.1,192.168.0.5-192.168.0.10
        """
        if not arg:
            raise CmdSyntaxError('You must specify address(es) to remove')
        self.servers -= self.parse_address_list(arg)

    status_re = re.compile(
            r'RESOLUTION (?P<width>\d+) (?P<height>\d+)\n'
            r'FRAMERATE (?P<rate>\d+(.\d+)?)\n'
            r'TIMESTAMP (?P<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6})\n')
    def do_status(self, arg=''):
        """
        Retrieves status from the defined servers.

        Syntax: status [addresses]

        The 'status' command is used to retrieve configuration information from
        servers. If no addresses are specified, then all defined servers will
        be queried.

        See also: resolution, framerate.

        cpi> status
        """
        responses = [
            (address, self.status_re.match(data))
            for (address, data) in self.transact('STATUS\n', arg).items()
            ]
        self.pprint_table(
            [('Address', 'Resolution', 'Framerate', 'Timestamp')] +
            [
                (
                    address,
                    '%sx%s' % (match.group('width'), match.group('height')),
                    '%sfps' % match.group('rate'),
                    match.group('time')
                    )
                for (address, match) in responses
                ])

    def do_resolution(self, arg):
        """
        Sets the resolution on the defined servers.

        Syntax: resolution res [addresses]

        The 'resolution' command is used to set the capture resolution of the
        camera on all or some of the defined servers.

        If no address is specified then all currently defined servers will be
        targetted. Multiple addresses can be specified with dash-separated
        ranges, comma-separated lists, or any combination of the two.

        See also: status, framerate.

        cpi> resolution 640x480
        cpi> resolution 1280x720 192.168.0.54
        cpi> resolution 1280x720 192.168.0.1,192.168.0.3
        """
        if not arg:
            raise CmdSyntaxError('You must specify a resolution')
        arg = arg.split(' ', 1)
        try:
            width, height = arg[0].lower().split('x')
            width, height = int(width), int(height)
        except TypeError, ValueError:
            raise CmdSyntaxError('Invalid resolution "%s"' % arg[0])
        responses = self.transact(
                'RESOLUTION %d %d\n' % (width, height),
                arg[1] if len(arg) > 1 else '')
        for address, response in responses.items():
            if response.strip() == 'OK':
                self.pprint('Changed resolution to %dx%d on %s' % (
                    width, height, address))
            else:
                self.pprint('Failed to change resolution on %s:' % address)
                self.pprint(response.strip())

    def do_framerate(self, arg):
        """
        Sets the framerate on the defined servers.

        Syntax: framerate rate [addresses]

        The 'framerate' command is used to set the capture framerate of the
        camera on all or some of the defined servers. The rate can be specified
        as an integer or floating-point number, or as a fractional value.

        If no address is specified then all currently defined servers will be
        targetted. Multiple addresses can be specified with dash-separated
        ranges, comma-separated lists, or any combination of the two.

        See also: status, resolution.

        cpi> framerate 30
        cpi> framerate 90 192.168.0.1
        cpi> framerate 15 192.168.0.1-192.168.0.10
        """
        if not arg:
            raise CmdSyntaxError('You must specify a framerate')
        arg = arg.split(' ', 1)
        try:
            rate = fractions.Fraction(rate)
        except TypeError, ValueError:
            raise CmdSyntaxError('Invalid framerate "%s"' % arg[0])
        responses = self.transact(
                'FRAMERATE %s\n' % rate,
                arg[1] if len(arg) > 1 else '')
        for address, response in responses.items():
            if response.strip() == 'OK':
                self.pprint('Changed framerate to %s on %s' % (rate, address))
            else:
                self.pprint('Failed to change framerate on %s:' % address)
                self.pprint(response.strip())

    def do_capture(self, arg=''):
        """
        Captures images from the defined servers.

        Syntax: capture [addresses]

        The 'capture' command causes the servers to capture an image and send
        it to the client. If no addresses are specified, a broadcast message to
        all defined servers will be used in which case the timestamp of the
        captured images are likely to be extremely close together. If addresses
        are specified, unicast messages will be sent to each server in turn.
        While this is still reasonably quick there will be a measurable
        difference between the timestamps of the last and first captures.

        cpi> capture
        cpi> capture 192.168.0.1
        cpi> capture 192.168.0.50-192.168.0.53
        """
        responses = self.transact('SHOOT\n', arg)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    proc = CompoundPiCmd()
    proc.cmdloop()


if __name__ == '__main__':
    main()
