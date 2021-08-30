import asyncio
import json
import aiofiles
import re
from typing import Optional
from loguru import logger


logger.add("server.log", format="{time} {level} {message}", level="INFO", rotation="10 MB", compression="zip", retention="10 days")


"""Verbs specified in RKSOK"""
GET = "ОТДОВАЙ"
DELETE = "УДОЛИ"
WRITE = "ЗОПИШИ"
PERMISSION = "АМОЖНА? РКСОК/1.0\r\n"
APPROVED = "МОЖНА"
BAD_REQUEST = "НИПОНЯЛ РКСОК/1.0\r\n\r\n"
OK = "НОРМАЛДЫКС РКСОК/1.0\r\n\r\n"
NOT_FOUND = "НИНАШОЛ РКСОК/1.0\r\n\r\n"


HOST = '0.0.0.0'
PORT = int(8888)
CHECKING_SERVER = ('vragi-vezde.to.digital', 51624)
STOP_STRING = '\r\n\r\n'
DB = DATA_BASE = "db.json"



@logger.catch
def validate_request(data: str) -> Optional[str]:
    """The function parses the client request according to the regular expression and returns the valid client request or None if the request is not valid."""
    raw_string = re.match(r'^((ОТДОВАЙ|ЗОПИШИ|УДОЛИ) .{1,30} РКСОК/1\.0)(\r\n.+)?(\r\n\r\n$)', data, re.DOTALL)
    if raw_string:
        return raw_string
    else:
        return None


@logger.catch
def parse_client_request(message: str) -> str:
    """A function that parses an input message and returns a tupple with three elements: command, name, phone."""
    name = " ".join(message.split("\r\n")[0].strip().split()[1:-1])
    phone = "\r\n".join(message.split("\r\n")[1:]).strip()
    command = message.strip().split()[0]
    return (command, name, phone)


@logger.catch
def run_data_base(DB: str) -> None:
    """The function creates a database file (if it did not exist before) and writes an empty dictionary to it. It is necessary for normal writing/reading json."""
    with open(DB, "a") as db:
        with open(DB, "r") as file:
            data_base = file.read()
            if not data_base:
                db.write("{}")


@logger.catch
async def write_data(name: str, phone: str) -> str:
    """The asynchronous function processes the request 'ЗОПИШИ' from the client, writes the person`s name and his phone to the database and returns a positive answer if the operation is successful."""
    async with aiofiles.open(DB, mode="r") as db:
        content = await db.read()
    data_base = json.loads(content)
    data_base[name] = phone
    async with aiofiles.open(DB, mode="w") as db:
        await db.write(json.dumps(data_base))
    response = OK
    return response


@logger.catch
async def delete_data(name: str) -> str:
    """The asynchronous function processes the request 'УДОЛИ' from the client, removes client data from the database, returns a positive answer if the operation is successful or returns 'НИНАШОЛ' if cannot find the data."""
    async with aiofiles.open(DB, mode="r") as db:
        content = await db.read()
    data_base = json.loads(content)
    if data_base.pop(name, None):
        async with aiofiles.open(DB, mode="w") as db:
            await db.write(json.dumps(data_base))
        response = OK
        return response
    response = NOT_FOUND
    return response


@logger.catch
async def receive_data(name: str) -> str:
    """The asynchronous function processes the request 'ОТДОВАЙ' from the client, returns the phone number by the person`s name or None."""
    async with aiofiles.open(DB, mode="r") as db:
        content = await db.read()
    data_base = json.loads(content)
    phone = data_base.get(name, None)
    if phone:
        response = f"НОРМАЛДЫКС РКСОК/1.0\r\n{phone}\r\n\r\n"
        return response
    else:
        response = NOT_FOUND
        return response


@logger.catch
async def send_to_check(data):
    """An asynchronous function that sends a client request to the checking server and awaits a response. When the response is ready to write breaks an awaiting coroutine and return response as usual function"""
    reader, writer = await asyncio.open_connection(*CHECKING_SERVER)
    message = PERMISSION + data.decode()
    logger.info(f'Send my server: {message!r}')
    writer.write(message.encode())
    await writer.drain()

    response = await reader.readuntil(separator=STOP_STRING.encode())
    logger.info(f'Received from checking server: {response.decode()!r}')

    logger.info('Close the connection with the checking server.')
    writer.close()
    await writer.wait_closed()

    return response


@logger.catch
async def server_processes(reader, writer):
    """The function creates two streams for reading and for writing."""
    message = ''
    while not message.endswith(STOP_STRING):
        """This loop allows you to read the entire request up to the special line(STOP_STRING), even if the buffer is full. In addition, it allows you to read an empty byte string."""
        data = await reader.read(512)
        if not data:
            break
        message += data.decode()
    valid_data = validate_request(message)
    addr = writer.get_extra_info('peername')
    logger.info(f"Received {message!r} from {addr!r}")
    if valid_data is None:
        """Returns this response if the request is invalid (does not match the regular expression)."""
        raw_response = BAD_REQUEST
        response = raw_response.encode()
    else:
        """If the request is valid this line sends it to checking server."""
        response = await asyncio.create_task(send_to_check(data))
        response_decoded = response.decode()
        if response_decoded.startswith(APPROVED):
            """If the response from the checking server is positive, then the response is processed."""
            command, name, phone = parse_client_request(message)
            if command == WRITE:
                raw_response = await asyncio.create_task(write_data(name, phone))
                response = raw_response.encode()
            elif command == DELETE:
                raw_response = await asyncio.create_task(delete_data(name))
                response = raw_response.encode()
            elif command == GET:
                raw_response = await asyncio.create_task(receive_data(name))
                response = raw_response.encode()
        else:
            raw_response = response_decoded
    logger.info(f"Send to client: {raw_response!r}")
    writer.write(response)
    await writer.drain()
    logger.info("Close the connection")
    writer.close()


@logger.catch
async def run_server():
    """Starts the server by accepting a handling function, host and port as input."""
    server = await asyncio.start_server(server_processes, HOST, PORT)

    addr = server.sockets[0].getsockname()
    logger.info(f'Serving on {addr}')

    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    run_data_base(DB)
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.warning('Server stopped by server owner')
        exit()
    except Exception:
        logger.warning('Something went wrong... ')
        exit()

