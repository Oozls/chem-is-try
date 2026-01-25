from flask import flash
from flask_pymongo import PyMongo
from pymongo import MongoClient
from os import getenv

mongo = PyMongo()
client = MongoClient(getenv("DB_CONNECT"), 27017)
db = client['chemistry']
account_collection = db['account']

def is_account_present(keyword: dict) -> bool | list:
    try:
        accounts = account_collection.find(keyword)
        accounts = list(accounts)
    except Exception as e:
        print(str(e))
        flash(f'계정을 확인하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return False, None
    else:
        if len(accounts) == 0: return False, []
        return True, accounts

def accound_register(data: dict) -> bool:
    try:
        account_collection.insert_one(data)
    except Exception as e:
        print(str(e))
        flash(f'계정을 등록하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return False
    else:
        flash('계정이 등록되었습니다.', 'success')
        return True