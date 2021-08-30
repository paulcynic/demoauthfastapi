import requests
import hmac
import hashlib
import base64
import json
from typing import Optional

from fastapi import FastAPI, Form, Cookie, Body
from fastapi.responses import Response


app = FastAPI()

SECRET_KEY = "672b65de9006fa8d1687b39d85eba84c9decdbc8663381884c9722be151c1a2b"
PASSWORD_SALT = "9cdc7437bc56ba94397067033b60b260593a72ef8cc2b2d47909c42425aaa310"


def phone_mask(raw_phone: str) -> str:
    num = "".join(filter(str.isdigit, raw_phone))
    if len(num) < 10 or len(num) > 11 or num[-10] != '9':
        return num
    phone = "8 (9{}{}) {}{}{}-{}{}-{}{}".format(*num[-9:])
    return phone


def sign_data(data: str) -> str:
    return hmac.new(
            SECRET_KEY.encode(),
            msg=data.encode(),
            digestmod=hashlib.sha256
            ).hexdigest().upper()


def get_username_from_signed_string(username_signed: str) -> Optional[str]:
    username_base64, sign = username_signed.split(".")
    username = base64.b64decode(username_base64.encode()).decode()
    valid_sign = sign_data(username)
    # сравнивает переданную через куки подпись и реальную подпись
    if hmac.compare_digest(valid_sign, sign):
        return username

def verify_password(username: str, password: str) -> bool:
    password_hash = hashlib.sha256((password + PASSWORD_SALT).encode()).hexdigest().lower()
    stored_password_hash = users[username]["password"].lower()
    return password_hash == stored_password_hash

users = {
        "paul@user.com": {
            "name": "Павел",
            "password": "91b4ee8fbef6540ab68edd4d455a9f388fd2f2b5a007bdbe0c1521f1d22d1899",
            "balance": 1000
            },
        "petr@user.com": {
            "name": "Пётр",
            "password": "8640b4ad8b0e8f85ca68873427bd120b57a34c446b15da196b0d0668120d7736",
            "balance": 50
            }
        }
# читает куку "username" как параметр функции
@app.get("/")
def index_page(username: Optional[str] = Cookie(default=None)):
    with open('templates/login.html', 'r') as f:
        login_page = f.read()
    if not username:
        return Response(login_page)
    try:
        valid_username = get_username_from_signed_string(username)
    except ValueError:
        response =  Response(login_page)
        response.delete_cookie(key="username")
        return response
    try:
        user = users[valid_username]
    except KeyError:
        response =  Response(login_page)
        # удаляет куку
        response.delete_cookie(key="username")
        return response
    return Response(f"Hello, {users[valid_username]['name']}!<br />Balance: {users[valid_username]['balance']}.",
            media_type="text/html")

# читает переданные данные формы "username", "password" как параметры функции
@app.post("/login")
def process_login_page(data: dict = Body(...)):
    #data_decoded = json.loads(data.decode())
    username = data["username"]
    password = data["password"]
    user = users.get(username)
    #Если не найдёт ключ, вернёт пустое значение
    #user = users[username] выдаст KeyError при пустом значении.
    if not user or not verify_password(username, password):
        return Response(json.dumps({
            "success": False,
            "message": f"Я вас не знаю!"
            }), media_type='application/json')
    response =  Response(json.dumps({
        "success": True,
        "message": f"Привет, {user['name']}!<br />Ваш баланс: {user['balance']}."
        }), media_type='application/json')
    # кодирует пользователя в base64 и подписывает данные(hmac)
    username_signed = base64.b64encode(username.encode()).decode() + "." + sign_data(username)
    # записывает куку с пользователем
    response.set_cookie(key="username", value=username_signed)
    return response


@app.post("/unify_phone_from_json")
def phone_from_json(phone_from_body: dict = Body(...)):
    raw_phone = phone_from_body["phone"]
    phone = phone_mask(raw_phone)
    return Response(phone)


@app.post("/unify_phone_from_form")
def phone_from_form(phone: str = Form(...)):
    raw_phone = phone
    resp_phone = phone_mask(raw_phone)
    return Response(resp_phone)


@app.get("/unify_phone_from_query")
def phone_from_query(phone: Optional[str] = None):
    raw_phone = phone
    resp_phone = phone_mask(raw_phone)
    return Response(resp_phone)


@app.get("/unify_phone_from_cookies")
def phone_from_cookies(phone: Optional[str] = Cookie(default=None)):
    resp_phone = phone_mask(phone)
    return Response(resp_phone)

@app.get("/coin")
def request_coin():
    with open('templates/form.html', 'r') as f:
        form_page = f.read()
    return Response(form_page)

@app.post("/request/coin")
def request_coin(coin: str = Form(...), currency: str = Form(...)):
    print(coin, currency)
    payload = {'ids': coin, 'vs_currencies': currency}
    r = requests.get('https://api.coingecko.com/api/v3/simple/price', params=payload)
    print(r.json())
    return r.json()
