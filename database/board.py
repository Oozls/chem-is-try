from bson import ObjectId
from flask import flash
from flask_pymongo import PyMongo
from pymongo import MongoClient
from os import getenv

mongo = PyMongo()
client = MongoClient(getenv("DB_CONNECT"), 27017)
db = client['chemistry']
board_collection = db['board']

def is_post_present(keyword: dict) -> bool | list:
    try:
        posts = board_collection.find(keyword)
        posts = list(posts)
        if len(posts) == 0: raise ValueError('존재하지 않는 글입니다.')
    except Exception as e:
        print(str(e))
        flash(f'글을 확인하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return False, []
    else:
        return True, posts

def post_list(keyword: dict) -> list:
    try:
        posts = board_collection.find(keyword)
        posts = list(posts)
    except Exception as e:
        print(str(e))
        flash(f'시약 목록을 불러오는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return None
    else:
        return posts

def board_post(data: dict) -> bool:
    try:
        board_collection.insert_one(data)
    except Exception as e:
        print(str(e))
        flash(f'글을 게시하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return False
    else:
        flash('글이 성공적으로 게시되었습니다.', 'success')
        return True

def board_edit(data: dict, id: str) -> bool:
    try:
        is_present, posts = is_post_present({'_id': ObjectId(id)})
        if not is_present:
            raise ValueError('존재하지 않는 글입니다.')
        board_collection.update_one({'_id': ObjectId(id)}, {'$set': data})
    except Exception as e:
        print(str(e))
        flash(f'글을 수정하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return False
    else:
        return True

def board_delete(keyword: dict) -> bool:
    try:
        is_present, posts = is_post_present(keyword)
        if not is_present: raise ValueError('존재하지 않는 글입니다.')
        board_collection.delete_many(keyword)
    except Exception as e:
        print(str(e))
        flash(f'글을 삭제하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return False
    else:
        flash('글을 삭제하였습니다.', 'success')
        return True