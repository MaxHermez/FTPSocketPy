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
    def __init__(self, host, port, loglevel=0):
        """ftp client class

        Args:
            host (str): host's address
            port (str): host's port
            loglevel (int, optional): logging level. Defaults to 0.
        """
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
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
        fh = logging.FileHandler(f'./client.log')
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)
        return logger

    def _checkErrors(self):
        """checks if there were any errors buffered, pops and prints them

        Returns:
            bool: False if no errors are found
        """
        if self.Errors:
            for each in self.Errors:
                self.logger.warning(each)
            self.Errors = []
            return True
        else:
            return False

    def operate(self):
        """Entry function for the user
        """
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

    def _validateArgs(self, args):
        """validate that the arguments are correct in respect to the request called

        Args:
            args (list[str]): user's input

        Returns:
            bool: validation passed
        """
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
        
    def _sendRequest(self, req, opcode):
        """handles sending requests to the server after they're compiled

        Args:
            req (bytes): request to be sent
            opcode (str): operation code
        """
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

    def _createRequest(self, operation, fileName=None, fileNameNew=None):
        """compiles the properly formatted bytes packet to send as a request based
        on the operation requirements

        Args:
            operation (str): operation code
            fileName (str, optional): filename. Defaults to None.
            fileNameNew (str, optional): new filename. Defaults to None.

        Returns:
            Tuple(bytes, str): (request data, operation code)
        """
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
            
    def _chunker(self, iterable, n, fillvalue =b'\x00'):
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
            self.Error.append(constants.ERROR_FILENAME)
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
            self.Error.append(constants.ERROR_FILESIZE)
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

    def _awaitResponse(self):
        """handles waiting and sorting out all the different server responses
        """
        response = self.client.recv(1, socket.MSG_PEEK)
        if response == (0).to_bytes(1, 'big'): # success response
            response = self.client.recv(1)
            self.logger.debug(f"new response receiver{self._byteToBit(response)}")
            return
        operation = self._byteToBit(response)[0:3]
        self.logger.debug(f"new response receiver{self._byteToBit(response)}")
        if operation == "001":
            self._recvFile()
            operation, fl = self._getOp()
            fn = self._getFileName(fl)
            fs = self._getFileSize(fl)
            self._getFile(fl+5, fn)
            return
        if operation == "110":
            operation, fl = self._getOp(response)
            self._recvFile()
            print(self.BUFFER[0][1:].decode('utf-8'))
            return

    def _getFileName(self, fl):
        """handles getting the string filename from the request in the buffer

        Args:
            fl (int): filename length

        Returns:
            str: filename
        """
        return self.BUFFER[0][1:fl+1].decode('utf-8')
    
    def _getFileSize(self, fl):
        """retrieve the file size from a request in the buffer

        Args:
            fl (int): filename length

        Returns:
            int: file size in bytes
        """
        return int.from_bytes(self.BUFFER[0][fl+1:fl+5], "big")
    
    def _recvFile(self):
        """recieve a file from the server, handles chunking and adding to the buffer
        """
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

    def _getOp(self, firstByte=None):
        """gets a tuple of two strings representing in binary the operation code
        and the filename length. The byte is retrieved from the buffer if no arguments
        are supplied

        Args:
            firstByte (bytes, optional): alternative byte to read. Defaults to None.

        Returns:
            tuple(str,str): extracted bits tuple
        """
        if firstByte == None:
            firstByte = self._byteToBit(self.BUFFER[0][0])
        else:
            firstByte = self._byteToBit(firstByte)
        return (firstByte[0:3],int(firstByte[3:8], 2))
    
    def _byteToBit(self, b):
        """convert a bytes string to a string of 1's and 0's

        Args:
            b (bytes): bytes to convert

        Returns:
            str: binary string
        """
        if isinstance(b, int):
            b = b.to_bytes(1, 'big')
        return format(int.from_bytes(b, byteorder=sys.byteorder), '#010b')[2:10]

    def _createDetails(self):
        """create the local details info

        Returns:
            str: details string
        """
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