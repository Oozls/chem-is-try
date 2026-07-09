from bson import ObjectId
from flask import flash
from pymongo import MongoClient
from os import getenv

client = MongoClient(getenv("DB_CONNECT"), 27017)
db = client['chemistry']
request_collection = db['request']

def is_request_present(keyword: dict) -> bool | list:
    try:
        requests = request_collection.find(keyword)
        requests = list(requests)
        if len(requests) == 0: raise ValueError('존재하지 않는 요청입니다.')
    except Exception as e:
        print(str(e))
        flash(f'요청을 확인하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return False, []
    else:
        return True, requests

def request_list(keyword: dict) -> list:
    try:
        requests = request_collection.find(keyword)
        requests = list(requests)
    except Exception as e:
        print(str(e))
        flash(f'요청 목록을 불러오는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return None
    else:
        return requests

def request_create(data: dict) -> bool:
    try:
        request_collection.insert_one(data)
    except Exception as e:
        print(str(e))
        flash(f'요청을 등록하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return False
    else:
        flash('수정 요청이 등록되었습니다.', 'success')
        return True

def request_edit(data: dict, id: str) -> bool:
    try:
        is_present, requests = is_request_present({'_id': ObjectId(id)})
        if not is_present:
            raise ValueError('존재하지 않는 요청입니다.')
        request_collection.update_one({'_id': ObjectId(id)}, {'$set': data})
    except Exception as e:
        print(str(e))
        flash(f'요청을 처리하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return False
    else:
        flash('요청이 처리되었습니다.', 'success')
        return True
