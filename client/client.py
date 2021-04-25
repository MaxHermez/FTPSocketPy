import socket, os, sys
from bitstring import BitStream, BitArray
import constants;

class client():

    def __init__(self, host, port):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
    
    def operate(self):
        while True:
            userIn = input(prompt="waiting for command")

    def _createRequest(self, operation, fileName):
        if operation == "put":
            FL = "{0:b}".format(len(fileName))
            opcode = "000"
            binName = self._stringToBin(fileName)
            req = BitArray('0b'+opcode+FL)

    def _stringToBin(self, s):
        ' '.join(format(ord(x), 'b') for x in s)
    
    def _getBitLen(self, fn):
        out = "{0:b}".format(len(fn))
        