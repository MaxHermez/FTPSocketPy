import socket, logging, sys, os, constants
from typing import Union
from tqdm import tqdm
from itertools import zip_longest

class server():
    ChunkSize = 1024
    BUFFER = []
    def __init__(self, port) -> None:
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = "localhost"
        self.port = int(port)
    
    def operate(self) -> None:
        while True:
            self.server.bind((self.host, self.port))
            self.server.listen(2)
            c, addr = self.server.accept()
            logging.info(f'Connected to {addr}')
            self._initiateSocket(c)

    def _initiateSocket(self, c) -> None:
        while True:
            self.BUFFER = []
            fb = c.recv(1, socket.MSG_PEEK)
            fb = self._byteToBit(fb)
            process, FL = self._getOp(fb)
            if process == "000":
                self._recvFile(c)
                code = self._processRequest()
                self._sendResponse(code, c)
                continue
            elif process == "001":
                self.BUFFER = [c.recv(FL+1)]
                logging.info("Finished receiving request.")
                code = self._processRequest()
                self._sendResponse(code, c)
                continue
            elif process == "010":
                part = c.recv(FL+2, socket.MSG_PEEK)
                FLN = int(part[len(part)-1])
                self.BUFFER = [c.recv(FL+FLN+2)]
                logging.info("Finished receiving request.")
                code = self._processRequest(FLN)
                self._sendResponse(code, c)
                continue
            elif process == "011":
                self.BUFFER = [c.recv(1)]
                logging.info("Finished receiving request.")
                code = self._processRequest()
                self._sendResponse(code, c)
                continue

    def _processRequest(self, FLN=None) -> str:
        operation, FL = self._getOp()
        if operation == "000":
            self._handlePut(FL)
        elif operation == "001":
            self._handleGet(FL)
        elif operation == "010":
            res = self._handleChange(FL, FLN)
            if res == True:
                return "000"
            else:
                return res
        elif operation == "011":
            self._handleHelp()
            return "110"
        return operation

    def _getOp(self, firstByte = None) -> tuple:
        if firstByte == None: firstByte = self._byteToBit(self.BUFFER[0][0])
        return (firstByte[0:3],int(firstByte[3:8], 2))

    def _recvFile(self, c) -> None:
        finalChunk = False
        while not finalChunk:
            data = c.recv(self.ChunkSize)
            if data == bytes(self.ChunkSize):
                logging.info("Finished receiving request.")
                finalChunk = True
                continue
            self.BUFFER.append(data)

    def _handlePut(self, fl) -> None:
        fn = self._getFileName(fl)
        fs = self._getFileSize(fl)
        self._getFile(fl+5, fn)

    def _handleGet(self, fl) -> None:
        fileName = self._getFileName(fl)
        opcode = "001"
        FL = self._getBitNameLen(fileName)
        byteName = bytes(fileName, 'utf-8')
        fileSize = self._getByteFileSize(fileName)
        fileData = self._getByteFile(fileName)
        r = self._bitstring_to_bytes(opcode+FL)
        r += byteName+fileSize+fileData
        self.BUFFER = [r]

    def _handleChange(self, fl, fln):
        fileName = self._getFileName(fl)
        newFileName = self._getNewFileName(fl, fln)
        if not os.path.isfile(fileName):
            return "010"
        os.rename(fileName, newFileName)
        return True

    def _handleHelp(self):
        helpBytes = constants.HELP.encode('utf-8')
        ln = "{0:b}".format(len(helpBytes))
        print(ln)
        if len(ln) < 5:
            for _ in range(5-len(ln)):
                out = "0" + out
        opcode = "110"
        r = self._bitstring_to_bytes(opcode+ln)
        r += helpBytes
        self.BUFFER = [r]
        print(r)
        return True

    def _getFileName(self, fl) -> str:
        return self.BUFFER[0][1:fl+1].decode('utf-8')

    def _getNewFileName(self, fl, fln) -> str:
        return self.BUFFER[0][fl+2:fln+fl+2].decode('utf-8')

    def _getFileSize(self, fl) -> int:
        return int.from_bytes(self.BUFFER[0][fl+1:fl+5], "big")
    
    def _getFile(self, offset, fn) -> bytes:
        self.BUFFER[0] = self.BUFFER[0][offset:]
        file = open(fn, 'wb')
        for each in self.BUFFER:
            file.write(each)
        file.close()

    def _getBitNameLen(self, fn) -> Union[bool, str]:
        out = "{0:b}".format(len(fn))
        if len(out) < 5:
            for _ in range(5-len(out)):
                out = "0" + out
            return out
        elif len(out) > 5:
            return False
        else: 
            return out
    
    def _getByteFileSize(self, fn) -> Union[bool, bytes]:
        fs = os.path.getsize(fn)
        if fs > 2**32:
            return False
        else: 
            return fs.to_bytes(4, 'big')

    def _getByteFile(self, fn) -> str:
        with open(fn, 'rb') as file:
            data = file.read()
            return data
    
    def _bitstring_to_bytes(self, s) -> bytes:
        return int(s.replace(" ", ""), 2).to_bytes((len(s) + 7) // 8, byteorder='big')
        
    def _byteToBit(self, b) -> str:
        if isinstance(b, int):
            b = b.to_bytes(1, 'big')
        elif isinstance(b, str):
            b = bytes(b, 'utf-8')
        return format(int.from_bytes(b, byteorder=sys.byteorder), '#010b')[2:10]
    
    def _sendResponse(self, code, c) -> None:
        if code == "000":
            c.send((0).to_bytes(1, 'big'))
        if code in ["001", "110"]:
            self._sendFile(c)
        if code in ["010", "011", "101"]:
            self._sendError("010", c)
    
    def _sendError(self, code, c):
        c.send(self._bitstring_to_bytes(code+"00000"))

    def _sendFile(self, c):
        req = self.BUFFER[0]
        chunks = self._chunker(req, 1024)
        n = len(chunks)
        logging.info(f'File is chunked into {n}')
        for i in tqdm(range(n), desc="sending file"):
            c.send(chunks[i])
        c.send(bytes(self.ChunkSize))
    
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


        
logging.basicConfig(level=logging.DEBUG)
ser = server(32323)
ser.operate()