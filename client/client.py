import socket, os, sys, logging
from bitstring import BitStream, BitArray
from typing import Union
from itertools import zip_longest
from tqdm import tqdm
import constants;
logging.level = logging.DEBUG
class client():
    ChunkSize = 1024
    Errors = []
    def __init__(self, host, port) -> None:
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = int(port)
    
    def _checkErrors(self) -> bool:
        if self.Errors:
            for each in self.Errors:
                print(each)
            return True
        else:
            return False

    def operate(self) -> None:
        self.client.connect((self.host, self.port))
        logging.info("Successfully conencted to the server")
        while (True):
            if self._checkErrors(): continue
            userIn = input("waiting for command\n")
            args = userIn.split(" ")
            if args[0] in ["get", "put"]:
                if not self._validateArgs(args): continue
                r = self._createRequest(args[0], args[1])
                self._sendRequest(r)
                self._awaitResponse()
                continue
            

    def _validateArgs(self, args) -> bool:
        if args[0] == "000":
            if len(args) < 2:
                self.Errors.append(constants.ERROR_ARG_PUT)
                return False
            elif not os.path.isfile(args[1]):
                self.Errors.append(constants.ERROR_ARG_FILE)
                return False
            else:
                return True
        elif args[1] == "001":
            if len(args) < 2:
                self.Errors.append(constants.ERROR_ARG_PUT)
                return False
            else:
                return True
        
    def _sendRequest(self, req) -> bool:
        chunks = self._chunker(req, 1024)
        n = len(chunks)
        logging.info(f'File is chunked into {n}')
        for i in tqdm(range(n), desc="sending file"):
            self.client.send(chunks[i])
        self.client.send(bytes(self.ChunkSize))

    def _createRequest(self, operation, fileName) -> BitArray:
        if operation == "put":
            opcode = "000"
            FL = self._getBitNameLen(fileName)
            byteName = bytes(fileName, 'utf-8')
            fileSize = self._getByteFileSize(fileName)
            fileData = self._getByteFile(fileName)
            r = self._bitstring_to_bytes(opcode+FL)
            r += byteName+fileSize+fileData
            return r
        if operation == "get":
            opcode = "001"
            FL = self._getBitNameLen(fileName)
            byteName = bytes(fileName, 'utf-8')
            r = self._bitstring_to_bytes(opcode+FL)
            r += byteName
            return r

    def _chunker(self, iterable, n, fillvalue =b'\x00') -> bytes:
        args = [iter(iterable)] * n
        ans = list(zip_longest(fillvalue=fillvalue, *args))
        fin = []
        for sub in ans:
            chunk = b''
            for each in sub:
                if isinstance(each, bytes): chunk += each
                else: chunk += int(each).to_bytes(1, 'big')
            fin.append(chunk)
        return fin
        
    def _stringToBin(self, s) -> str:
        return ''.join(format(ord(x), 'b') for x in s)
    
    def _getBitNameLen(self, fn) -> Union[bool, str]:
        out = "{0:b}".format(len(fn))
        if len(out) < 5:
            for _ in range(5-len(out)):
                out = "0" + out
            return out
        elif len(out) > 5:
            self.Error.append(constants.ERROR_FILENAME)
            return False
        else: 
            return out

    def _getByteFileSize(self, fn) -> Union[bool, bytes]:
        fs = os.path.getsize(fn)
        if fs > 2**32:
            self.Error.append(constants.ERROR_FILESIZE)
            return False
        else: 
            return fs.to_bytes(4, 'big')

    def _getByteFile(self, fn) -> str:
        with open(fn, 'rb') as file:
            data = file.read()
            return data
    
    def _bitstring_to_bytes(self, s):
        return int(s.replace(" ", ""), 2).to_bytes((len(s) + 7) // 8, byteorder='big')

    def _awaitResponse(self) -> True:
        response = self.client.recv(1)
        if response == (0).to_bytes(1, 'big'):
            return True
        operation, fl = self._byteToBit(response)[0:3]
        if operation == "001":
            response += self.client.recv(1024) # get the rest of the first chunk
            fn = self._getFileName(fl)
            fs = self._getFileSize(fl)
            self._recvFile()

    def _getFileName(self, fl) -> str:
        return self.BUFFER[0][1:fl+1].decode('utf-8')
    
    def _getFileSize(self, fl) -> int:
        return int.from_bytes(self.BUFFER[0][fl+1:fl+5], "big")
    
    def _getFile(self, offset, fn):
        self.BUFFER[0] = self.BUFFER[0][offset:]
        file = open(fn, 'wb')
        for each in self.BUFFER:
            file.write(each)
        file.close()

    def _getOp(self) -> tuple:
        firstBit = self._byteToBit(self.BUFFER[0][0])
        return (firstBit[0:3],int(firstBit[3:8], 2))


if len(sys.argv) != 3:
    print(sys.argv)
    raise ValueError('Please provide server hostname and port.')
c = client(sys.argv[1], sys.argv[2])
c.operate()