import socket
from process import *
from loguru import logger


logger.add("server.log", format="{time} {level} {message}", level="INFO", rotation="10 MB", compression="zip", retention="10 days")

"""Some constant variables of the socket server"""
localhost = "cointrack.ru"
HOST = ""
PORT = int(43210)
HOST_KGB = "vragi-vezde.to.digital"
PORT_KGB = int(51624)
PERMISSION = "АМОЖНА? РКСОК/1.0\r\n"
ENCODING = "UTF-8"
STOP_STRING = "\r\n\r\n"
BUFFER_SIZE = int(1024)
DB = DATA_BASE = "db.json"


"""A dictionary used by function 'process_client_request(DB, full_data, command)' that replaces the command received from the client's request with the corresponding function."""
command = {
    "ОТДОВАЙ": receive_client_data,
    "ЗОПИШИ": write_client_data,
    "УДОЛИ": delete_client_data,
}


"""The main programm of the server"""

"""These three lines of code create a socket on the server"""
try:
    serv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serv_sock = socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serv_sock.bind((HOST, PORT))
    serv_sock.listen(10)
    logger.info(f"Server {localhost} {PORT} is running...")
    while True:
        run_data_base(DB)
        """Starts an endless loop to wait for a socket connetion"""
        client_sock, client_addr = serv_sock.accept()
        host, port = client_addr
        logger.info(f"Client {host} {port} connected.")
        full_data = ''
        while not full_data.endswith(STOP_STRING):
            """Reads data from a socket to a specific line (STOP_STRING)"""
            data = client_sock.recv(BUFFER_SIZE)
            full_data += data.decode(ENCODING)
            if not data:
                """Stops reading from a socket if the client socket is closed."""
                logger.info(f"Client {host} {port} closed the connection")
                break
        logger.info(f"Client {host} {port}: {full_data}")
        if parse_client_request(full_data):
            """Parses client request and create new request to validation server (vragi-vezde)"""
            ask_kgb = PERMISSION + full_data
            """Creates a client socket to connect to the validation server."""
            kgb = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            kgb.connect((HOST_KGB, PORT_KGB))
            logger.info(f"Connected to validation server {HOST_KGB} {PORT_KGB}.")
            """Sends request to validation server and receives response."""
            kgb.sendall(ask_kgb.encode(ENCODING))
            """If the answer is 'НИЛЬЗЯ', then it is completely forwarded to the client."""
            response = kgb.recv(BUFFER_SIZE).decode(ENCODING)
            """Closes the socket with the validation server"""
            logger.info(f"Validation server {HOST_KGB} {PORT_KGB}: {response}")
            kgb.shutdown(socket.SHUT_RDWR)
            kgb.close()
            if response.startswith("МОЖНА"):
                """If the response from the validation server is positive, then the request is processed."""
                response = process_client_request(DB, full_data, command)
        else:
            """Returns this response if the request is invalid (does not match the regular expression)."""
            response = "НИПОНЯЛ РКСОК/1.0\r\n\r\n"
        """Sends the final response to the client and closes the socket."""
        client_sock.sendall(response.encode(ENCODING))
        logger.info(f"Server {localhost} {PORT} response: {response}")
        client_sock.shutdown(socket.SHUT_RDWR)
        client_sock.close()
except KeyboardInterrupt:
    logger.info(f"Server {localhost} {PORT} closed.")
    serv_sock.shutdown(socket.SHUT_RDWR)
    serv_sock.close()
except OSError:
    logger.exception("Something went wrong... Connection failed, server closed.")
    serv_sock.close()

