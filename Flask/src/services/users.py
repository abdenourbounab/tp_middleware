import json
import requests
from sqlalchemy import exc
from marshmallow import EXCLUDE
from flask_login import current_user

from schemas.user import UserSchema
from models.user import User as UserModel
from models.http_exceptions import *
import repositories.users as users_repository


users_url = "http://localhost:8081/users"  
def get_users():
    response = requests.request(method="GET", url=users_url)
    return response.json(), response.status_code

def get_user(id):
    response = requests.request(method="GET", url=users_url+"/"+id)
    return response.json(), response.status_code


def create_user(user_register):
    user_model = UserModel.from_dict_with_clear_password(user_register)
    user_schema = UserSchema().loads(json.dumps(user_register), unknown=EXCLUDE)
    print(user_schema)
    response = requests.request(method="POST", url=users_url, json=user_schema)
     
    print(response.status_code)

    if response.status_code != 201:
        return response.json(), response.status_code

   
    try:
        user_model.id = response.json()["id"]
        users_repository.add_user(user_model)
    except Exception:
        raise SomethingWentWrong

    return response.json(), response.status_code


def modify_user(id, user_update):
    if id != current_user.id:
        raise Forbidden

    user_schema = UserSchema().loads(json.dumps(user_update), unknown=EXCLUDE)
    print(user_schema)
    response = None
    if not UserSchema.is_empty(user_schema):
        # on lance la requête de modification
        response = requests.request(method="PUT", url=users_url+"/"+id, json=user_schema)
        print(response.status_code)
        if response.status_code != 200:
            return response.json(), response.status_code

    user_model = UserModel.from_dict_with_clear_password(user_update)
    if not user_model.is_empty():
        user_model.id = id
        found_user = users_repository.get_user_from_id(id)
        if not user_model.username:
            user_model.username = found_user.username
        if not user_model.encrypted_password:
            user_model.encrypted_password = found_user.encrypted_password
        try:
            users_repository.update_user(user_model)
        except exc.IntegrityError as e:
            if "NOT NULL" in e.orig.args[0]:
                raise UnprocessableEntity
            raise Conflict

    return (response.json(), response.status_code) if response else get_user(id)


def get_user_from_db(username):
    return users_repository.get_user(username)


def user_exists(username):
    return get_user_from_db(username) is not None

def delete_user(id):
    if id != current_user.id:
        raise Forbidden

    #  suppression
    response = requests.request(method="DELETE", url=users_url+"/"+id)

    if response.status_code == 204:
        users_repository.delete_user(id)
        
        return "Deleted", 204

    return response.json(), response.status_code

