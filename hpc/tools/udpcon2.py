#!/usr/bin/python
import cmd
import errno
import socket
import os
import re
import sys
import threading
"""
sends its own return on start. exits gracefully, still has the wonky cursor thing though.
0cd change to control.
1cd change to iot.
lightly monitors state, 1ls ,0ls will alert state, but you can just give commands without 
altering state, instead of prefixing every command with a state. state, being contorl or iot
"""

class UDPConn(cmd.Cmd):

    prompt = ''

    def __init__(self, s, destination):
        cmd.Cmd.__init__(self)

        self.s = s
        self.destination = destination
        self.target = 'iot'
        self._prompt_tail = b''

    def observe_output(self, data):
        """Follow remote prompts, including prompts split across datagrams."""
        output = self._prompt_tail + data
        end = 0
        for match in re.finditer(rb'nyle_(iot|control)>', output):
            self.target = match.group(1).decode('ascii')
            end = match.end()
        self._prompt_tail = output[end:][-12:]

    def do_EOF(self, line):
        return True
    # only change if I tell you to change. 
    def precmd(self, line):
        line = line.strip()
        if line == 'EOF':
            return line
        if line.startswith('0'):
            self.target = 'control'
        elif line.startswith('1'):
            self.target = 'iot'
            line = line[1:]
        elif self.target == 'control':
            line = '0' + line
        line += '\r'
        self.s.sendto(line.encode(), self.destination)
        return ""

# close gracefully
def read_thread(sock, connection):
    while True:
        try:
            data = sock.recv(65536)
            connection.observe_output(data)
            os.write(sys.stdout.fileno(), data)
        except OSError:
            break


if __name__ == '__main__':

    host = 'localhost'
    port = 2323
    if len(sys.argv) >= 2:
        host = sys.argv[1]
    if len(sys.argv) >= 3:
        port = int(sys.argv[2])

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # gracefully reject duplicate connections
    try:
        s.bind(('',50001)) # must bind on windows
    except OSError as exc:
        s.close()
        if exc.errno == errno.EADDRINUSE or getattr(exc, 'winerror', None) == 10048:
            sys.exit('IP in use. - Connection denied')
        raise
    connection = UDPConn(s, (host, port))
    th = threading.Thread(target=read_thread, args=(s, connection), daemon=True)
    th.start()
    # Request the ESP32 prompt immediately on startup
    s.sendto(b'\r', (host, port))
    try:
        connection.cmdloop()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting...")
    finally:
        s.close()
        print("UDP socket closed.")

