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
    BUFFER = []
    def __init__(self, host, port, loglevel=0) -> None:
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = int(port)
        self.logger = self._getLogger(loglevel)
    
    def _getLogger(self, loglevel=0) -> logging.Logger:
        logger = logging.getLogger()
        if loglevel == 0:
            return logger
        logger.setLevel(logging.DEBUG)
        if loglevel == 1:
            return logger
        fh = logging.FileHandler(f'./client.log')
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)
        return logger

    def _checkErrors(self) -> bool:
        if self.Errors:
            for each in self.Errors:
                self.logger.warning(each)
            self.Errors = []
            return True
        else:
            return False

    def operate(self) -> None:
        self.client.connect((self.host, self.port))
        self.logger.info("Successfully conencted to the server")
        while (True):
            self.BUFFER = []
            if self._checkErrors(): continue
            userIn = input("waiting for command\n")
            args = userIn.split(" ")
            if args[0] in ["get", "put"]:
                if not self._validateArgs(args): continue
                r, opcode = self._createRequest(args[0], args[1])
                self._sendRequest(r, opcode)
                self._awaitResponse()
                continue
            elif args[0] == "change":
                if not self._validateArgs(args): continue
                r, opcode = self._createRequest(args[0], args[1], args[2])
                self._sendRequest(r, opcode)
                self._awaitResponse()
                continue
            elif args[0] == "help":
                if not self._validateArgs(args): continue
                r, opcode = self._createRequest(args[0])
                self._sendRequest(r, opcode)
                self._awaitResponse()
                continue
            elif args[0] == "details":
                print(self._createDetails())
                continue
            elif args[0] == "bye":
                self.client.close()
                break

    def _validateArgs(self, args) -> bool:
        if args[0] == "put":
            if len(args) < 2:
                self.Errors.append(constants.ERROR_ARG_PUT)
                return False
            elif not os.path.isfile(args[1]):
                self.Errors.append(constants.ERROR_ARG_FILE)
                return False
            else:
                return True
        elif args[0] == "get":
            if len(args) != 2:
                self.Errors.append(constants.ERROR_ARG)
                return False
            else:
                return True
        elif args[0] == "change":
            if len(args) != 3:
                self.Errors.append(constants.ERROR_ARG)
                return False
            else:
                return True
        elif args[0] == "help":
            if len(args) != 1:
                self.Errors.append(constants.ERROR_ARG)
                return False
            else:
                return True
        
    def _sendRequest(self, req, opcode) -> bool:
        if opcode == "000":
            chunks = self._chunker(req, self.ChunkSize)
            n = len(chunks)
            self.logger.info(f'File is chunked into {n}')
            for i in tqdm(range(n), desc="sending file"):
                self.client.send(chunks[i])
            self.client.send(bytes(self.ChunkSize))
        elif opcode in ["001", "010", "011"]:
            self.client.send(req)
            self.logger.info('Request sent to server')

    def _createRequest(self, operation, fileName=None, fileNameNew=None) -> tuple:
        if operation == "put":
            opcode = "000"
            FL = self._getBitNameLen(fileName)
            byteName = bytes(fileName, 'utf-8')
            fileSize = self._getByteFileSize(fileName)
            fileData = self._getByteFile(fileName)
            r = self._bitstring_to_bytes(opcode+FL)
            r += byteName+fileSize+fileData
            return r, opcode
        if operation == "get":
            opcode = "001"
            FL = self._getBitNameLen(fileName)
            byteName = bytes(fileName, 'utf-8')
            r = self._bitstring_to_bytes(opcode+FL)
            r += byteName
            return r, opcode
        if operation == "change":
            opcode = "010"
            FL = self._getBitNameLen(fileName)
            byteName = bytes(fileName, 'utf-8')
            FLN = self._getBitNameLen(fileNameNew)
            byteNewName = bytes(fileNameNew, 'utf-8')
            r = self._bitstring_to_bytes(opcode+FL)
            r += byteName
            r += self._bitstring_to_bytes(FLN)
            r += byteNewName
            return r, opcode
        if operation == "help":
            opcode = "011"
            r = self._bitstring_to_bytes(opcode+"00000")
            return r, opcode
            
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
    
    def _bitstring_to_bytes(self, s) -> bytes:
        return int(s.replace(" ", ""), 2).to_bytes((len(s) + 7) // 8, byteorder='big')

    def _awaitResponse(self) -> True:
        response = self.client.recv(1, socket.MSG_PEEK)
        if response == (0).to_bytes(1, 'big'): # success response
            response = self.client.recv(1)
            self.logger.debug(f"new response receiver{self._byteToBit(response)}")
            return True
        operation = self._byteToBit(response)[0:3]
        self.logger.debug(f"new response receiver{self._byteToBit(response)}")
        if operation == "001":
            self._recvFile()
            operation, fl = self._getOp()
            fn = self._getFileName(fl)
            fs = self._getFileSize(fl)
            self._getFile(fl+5, fn)
            return True
        if operation == "110":
            operation, fl = self._getOp(response)
            self._recvFile()
            print(self.BUFFER[0][1:].decode('utf-8'))
            return True

    def _getFileName(self, fl) -> str:
        return self.BUFFER[0][1:fl+1].decode('utf-8')
    
    def _getFileSize(self, fl) -> int:
        return int.from_bytes(self.BUFFER[0][fl+1:fl+5], "big")
    
    def _recvFile(self):
        self.logger.info("Began receiving response.")
        finalChunk = False
        self.BUFFER = []
        while not finalChunk:
            data = self.client.recv(self.ChunkSize)
            if data == bytes(self.ChunkSize):
                self.logger.info("Finished receiving response.")
                finalChunk = True
                continue
            self.BUFFER.append(data)

    def _getFile(self, offset, fn):
        self.BUFFER[0] = self.BUFFER[0][offset:]
        file = open(fn, 'wb')
        for each in self.BUFFER:
            file.write(each)
        file.close()

    def _getOp(self, firstByte=None) -> tuple:
        if firstByte == None:
            firstByte = self._byteToBit(self.BUFFER[0][0])
        else:
            firstByte = self._byteToBit(firstByte)
        return (firstByte[0:3],int(firstByte[3:8], 2))
    
    def _byteToBit(self, b) -> str:
        if isinstance(b, int):
            b = b.to_bytes(1, 'big')
        return format(int.from_bytes(b, byteorder=sys.byteorder), '#010b')[2:10]

    def _createDetails(self) -> str:
        h = ""
        for each in constants.HELP:
            h += each + "\n"
        h += "When launching the script, you can add a 1 at the end to enable debug log printing, or you can add a 2 to save the logs to a file in the local dir"
        return h

if len(sys.argv) < 3:
    print(sys.argv)
    raise ValueError('Please provide server hostname and port.')
if sys.argv[3]:
    c = client(sys.argv[1], sys.argv[2], sys.argv[3])
else:
    c = client(sys.argv[1], sys.argv[2])
c.operate()