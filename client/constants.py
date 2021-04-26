"""
Name: Maxim Hermez
ID: 201706267
user: mnh34
client constants file
"""
HPUT = "<put filename>This command instructs the client to send a put request to the server in order to transfer a file from the client machine to the server machine. \n Example: put file.txt"
HGET = "<get filename>This command instructs the client to send a get request to the server in order to retrieve a file from the server machine to the client machine. \n Example: get file.txt"
HCHANGE = "<change OldFileName NewFileName>This command instructs the client to send a change request to the server to rename a file at the server machine."
HHELP = "<help>This command instructs the client to send a help request to the server to get a list of the commands that the server support. \n Example: help"
HBYE = "<bye>This command instructs the client to break the connection with the server and exit."
ERROR_FILENAME = "Your file name is too long, it has to be 31 characters or less."
ERROR_FILESIZE = "Your file size is too big."
ERROR_ARG_FILE = "Could not find the specified file. Check for typos and make sure you open the terminal from the scripts directory."
ERROR_ARG = "Incorrect number of arguments, if you're lost type (help) to see the list of instructions"

HELP = [HPUT, HGET, HCHANGE, HHELP, HBYE]