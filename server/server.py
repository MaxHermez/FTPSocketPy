import socket, logging, sys, os, constants
from typing import Union
from tqdm import tqdm
from itertools import zip_longest
"""
Name: Maxim Hermez
ID: 201706267
user: mnh34
server script file
"""

class Server:
    ChunkSize = 1024
    BUFFER = []
    def __init__(self, port, loglevel=0):
        """ftp server class

        Args:
            port (str): port number for the server
            loglevel (str, optional): logging level. Defaults to 0.
        """         
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = "localhost"
        self.port = int(port)
        self.logger = self._getLogger(loglevel)
    
    def _getLogger(self, loglevel=0):
        """handles initializing the right level of logging

        Args:
            loglevel (int, optional): 0 for none, 1 for terminal debug, 2 terminal and file logging. Defaults to 0.

        Returns:
            logging.Logger: logger object
        """
        logger = logging.getLogger()
        if loglevel == 0:
            return logger
        logger.setLevel(logging.DEBUG)
        if loglevel == 1:
            return logger
        fh = logging.FileHandler(f'./server.log')
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)
        return logger

    def operate(self):
        """Entry function for the user
        """        
        while True:
            self.server.bind((self.host, self.port))
            self.server.listen(2)
            c, addr = self.server.accept()
            self.logger.info(f'Connected to {addr}')
            self._initiateSocket(c)

    def _initiateSocket(self, c):
        """Main server loop after connection to a client

        Args:
            c (socket): TCP socket connection with the client
        """        
        while True:
            self.BUFFER = []
            fb = c.recv(1, socket.MSG_PEEK)
            fb = self._byteToBit(fb)
            self.logger.debug(f"new response receiver{fb}")
            process, FL = self._getOp(fb)
            if process == "000":
                self._recvFile(c)
                code = self._processRequest()
                self._sendResponse(code, c)
                continue
            elif process == "001":
                self.BUFFER = [c.recv(FL+1)]
                self.logger.info("Finished receiving request.")
                code = self._processRequest()
                self._sendResponse(code, c)
                continue
            elif process == "010":
                part = c.recv(FL+2, socket.MSG_PEEK)
                FLN = int(part[len(part)-1])
                self.BUFFER = [c.recv(FL+FLN+2)]
                self.logger.info("Finished receiving request.")
                code = self._processRequest(FLN)
                self._sendResponse(code, c)
                continue
            elif process == "011":
                self.BUFFER = [c.recv(1)]
                self.logger.info("Finished receiving request.")
                code = self._processRequest()
                self._sendResponse(code, c)
                continue

    def _processRequest(self, FLN=None):
        """begins processing of any request saved in the buffer variable

        Args:
            FLN (str, optional): new filename's length. Defaults to None.

        Returns:
            str: response code
        """
                
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

    def _getOp(self, firstByte = None):
        """gets a tuple of two strings representing in binary the operation code
        and the filename length. The byte is retrieved from the buffer if no arguments
        are supplied

        Args:
            firstByte (bytes, optional): alternative byte to read. Defaults to None.

        Returns:
            tuple(str,str): extracted bits tuple
        """
        if firstByte == None: firstByte = self._byteToBit(self.BUFFER[0][0])
        return (firstByte[0:3],int(firstByte[3:8], 2))

    def _recvFile(self, c):
        """recieve a file from the server, handles chunking and adding to the buffer

        Args:
            c (socket): client socket
        """
        finalChunk = False
        while not finalChunk:
            data = c.recv(self.ChunkSize)
            if data == bytes(self.ChunkSize):
                self.logger.info("Finished receiving request.")
                finalChunk = True
                continue
            self.BUFFER.append(data)

    def _handlePut(self, fl):
        """handle the backend processing for put request

        Args:
            fl (str): filename length
        """
        fn = self._getFileName(fl)
        fs = self._getFileSize(fl)
        self._getFile(fl+5, fn)

    def _handleGet(self, fl):
        """handle the backend processing for get request

        Args:
            fl (str): filename length
        """
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
        """handle the backend processing for change request

        Args:
            fl (str): filename length
            fln (str): new filename length

        Returns:
            str/bool: True if successful, str(response_code) if failed
        """
        fileName = self._getFileName(fl)
        newFileName = self._getNewFileName(fl, fln)
        if not os.path.isfile(fileName):
            return "010"
        os.rename(fileName, newFileName)
        return True

    def _handleHelp(self):
        """handle the backend processing for help request

        Returns:
            bool: success
        """
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

    def _getFileName(self, fl):
        """handles getting the string filename from the request in the buffer

        Args:
            fl (int): filename length

        Returns:
            str: filename
        """
        return self.BUFFER[0][1:fl+1].decode('utf-8')

    def _getNewFileName(self, fl, fln):
        """handles getting the string new filename from the request in the buffer (only used for change request)

        Args:
            fl (int): filename length
            fln (int): new filename length

        Returns:
            str: new file name
        """
        return self.BUFFER[0][fl+2:fln+fl+2].decode('utf-8')

    def _getFileSize(self, fl):
        """retrieve the file size from a request in the buffer

        Args:
            fl (int): filename length

        Returns:
            int: file size in bytes
        """
        return int.from_bytes(self.BUFFER[0][fl+1:fl+5], "big")
    
    def _getFile(self, offset, fn):
        """handles writing the file's data to the computer's memory

        Args:
            offset (int): offset of bytes where the file starts
            fn (str): filename
        """
        self.BUFFER[0] = self.BUFFER[0][offset:]
        file = open(fn, 'wb')
        for each in self.BUFFER:
            file.write(each)
        file.close()

    def _getBitNameLen(self, fn):
        """get the length of the string in binary

        Args:
            fn (str): filename

        Returns:
            str/bool: binary string if successful or False if error occured
        """
        out = "{0:b}".format(len(fn))
        if len(out) < 5:
            for _ in range(5-len(out)):
                out = "0" + out
            return out
        elif len(out) > 5:
            return False
        else: 
            return out
    
    def _getByteFileSize(self, fn):
        """get a file's size in a bytes object

        Args:
            fn (str): filename/path

        Returns:
            bytes/bool: size of the file if successful or False if error occured
        """
        fs = os.path.getsize(fn)
        if fs > 2**32:
            return False
        else: 
            return fs.to_bytes(4, 'big')

    def _getByteFile(self, fn):
        """read a file as binary

        Args:
            fn (str): filename/path

        Returns:
            bytes: file content
        """
        with open(fn, 'rb') as file:
            data = file.read()
            return data
    
    def _bitstring_to_bytes(self, s):
        """converts a string of 1's and 0's to its bytes object

        Args:
            s (str): binary data

        Returns:
            bytes: output
        """
        return int(s.replace(" ", ""), 2).to_bytes((len(s) + 7) // 8, byteorder='big')
        
    def _byteToBit(self, b):
        """convert a bytes string to a string of 1's and 0's

        Args:
            b (bytes): bytes to convert

        Returns:
            str: binary string
        """
        if isinstance(b, int):
            b = b.to_bytes(1, 'big')
        elif isinstance(b, str):
            b = bytes(b, 'utf-8')
        return format(int.from_bytes(b, byteorder=sys.byteorder), '#010b')[2:10]
    
    def _sendResponse(self, code, c):
        """Send response to the client

        Args:
            code (str): response code
            c (socket): client socket
        """
        if code == "000":
            c.send((0).to_bytes(1, 'big'))
        if code in ["001", "110"]:
            self._sendFile(c)
        if code in ["010", "011", "101"]:
            self._sendError("010", c)
    
    def _sendError(self, code, c):
        """send error response to the client

        Args:
            code (str): response code
            c (socket): client socket
        """
        c.send(self._bitstring_to_bytes(code+"00000"))

    def _sendFile(self, c):
        """handles sending whatever data/file that's in the buffer to the client in chunks
        equal to the predefined variable

        Args:
            c (socket): client socket
        """
        req = self.BUFFER[0]
        chunks = self._chunker(req, self.ChunkSize)
        n = len(chunks)
        self.logger.info(f'File is chunked into {n}')
        for i in tqdm(range(n), desc="sending file"):
            c.send(chunks[i])
        c.send(bytes(self.ChunkSize))
    
    def _chunker(self, iterable, n, fillvalue=b'\x00'):
        """handles chunking any bytes string into n equal chunks, if the last chunk
        is not of size n it will be padded with the fillvalue

        Args:
            iterable (bytes): bytes string to chunk
            n (int): chunk size
            fillvalue (bytes, optional): padding fill value. Defaults to b'\x00'.

        Returns:
            list(bytes): list of the bytes chunks
        """
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


if len(sys.argv) < 2:
    raise ValueError('Please provide server hostname and port.')
if sys.argv[2]:
    s = Server(sys.argv[1], sys.argv[2])
else:
    s = Server(sys.argv[1])
s.operate()