import json
import re
from loguru import logger
from typing import Optional


@logger.catch
def process_client_request(DB: str, full_data: str, command: dict[str, any]) -> str:
    """A function that receives three variables as input: a database, a request from a client, a dictionary with commands.Returns an appropriate response."""
    name = " ".join(full_data.split("\r\n")[0].strip().split()[1:-1])
    phone = "\r\n".join(full_data.split("\r\n")[1:]).strip()
    response = command[full_data.strip().split()[0]](DB, name, phone)
    return response


@logger.catch
def receive_client_data(DB: str, name: str, phone: Optional[str] = None) -> str:
    """The function processes the request 'ОТДОВАЙ' from the client, returns the phone number by the person`s name or None."""
    with open(DB, "r") as db:
        data_base = json.load(db)
        phone = data_base.get(name, None)
    if phone:
        response = f"НОРМАЛДЫКС РКСОК/1.0\r\n{phone}\r\n\r\n"
        return response
    else:
        response = "НИНАШОЛ РКСОК/1.0\r\n\r\n"
        return response


@logger.catch
def write_client_data(DB: str, name: str, phone: str) -> str:
    """The function processes the request 'ЗОПИШИ' from the client, writes the person`s name and his phone to the database and returns a positive answer if the operation is successful."""
    with open(DB, "r") as db:
        data_base = json.load(db)
    data_base[name] = phone
    with open(DB, "w") as db:
        json.dump(data_base, db)
    response = "НОРМАЛДЫКС РКСОК/1.0\r\n\r\n"
    return response


@logger.catch
def delete_client_data(DB: str, name: str, phone: Optional[str] = None) -> str:
    """The function processes the request 'УДОЛИ' from the client, removes client data from the database, returns a positive answer if the operation is successful or returns 'НИНАШОЛ' if cannot find the data."""
    with open(DB, "r") as db:
        data_base = json.load(db)
    if data_base.pop(name, None):
        with open(DB, "w") as db:
            json.dump(data_base, db)
        response = "НОРМАЛДЫКС РКСОК/1.0\r\n\r\n"
        return response
    response = "НИНАШОЛ РКСОК/1.0\r\n\r\n"
    return response


@logger.catch
def parse_client_request(data: str) -> Optional[str]:
    """The function parses the client request according to the regular expression and returns the valid client request or None if the request is not valid."""
    raw_string = re.match(r'^((ОТДОВАЙ|ЗОПИШИ|УДОЛИ) .{1,30} РКСОК/1\.0)(\r\n.+)?(\r\n\r\n$)', data, re.DOTALL)
    if raw_string:
        return raw_string
    else:
        return None


@logger.catch
def run_data_base(DB: str) -> None:
    """The function creates a database file (if it did not exist before) and writes an empty dictionary to it. It is necessary for normal writing/reading json."""
    with open(DB, "a") as db:
        with open(DB, "r") as file:
            data_base = file.read()
            if not data_base:
                db.write("{}")

