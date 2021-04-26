# FTPSocketPy
A client-server script
## Project description

This project is made as a submission for a networking course. It is a simple/bare-bones implementation of ftp through sockets in python

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install tqdm.

```bash
pip install tqdm
```

## Usage
First you have to initialize your server, open a command-line interface to the server's directory and run the python script passing the port number as an argument

```bash
python server.py 32323
```
Then you need to launch the client in a separate window after navigating a command-line to the client directory, pass localhost as the first argument and the server's port number as a second argument
```bash
python client.py localhost 32323
```
For both the server and client, you have the option to add an extra command-line argument representing the level of logging to be used:

* 0 (default, no logging)
* 1 (display debug logging on the terminal
* 2 (display debug logging as well as save it to .log file)

## Client
To get the list of commands you can write, type "help", and to get an extended version of help type "details"

## License
[MIT](https://choosealicense.com/licenses/mit/)