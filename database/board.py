from bson import ObjectId
from flask import flash
from flask_pymongo import PyMongo
from pymongo import MongoClient
from os import getenv

mongo = PyMongo()
client = MongoClient(getenv("DB_CONNECT"), 27017)
db = client['chemistry']
board_collection = db['board']
comment_collection = db['comment']




# -------- BOARD/POST --------- #
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
        flash(f'글 목록을 불러오는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
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

def board_edit(data: dict, id: ObjectId) -> bool:
    try:
        is_present, posts = is_post_present({'_id': id})
        if not is_present:
            raise ValueError('존재하지 않는 글입니다.')
        board_collection.update_one({'_id': id}, {'$set': data})
    except Exception as e:
        print(str(e))
        flash(f'글 정보를 수정하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
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




# --------- COMMENT --------- #
def is_comment_present(keyword: dict) -> bool | list:
    try:
        comments = comment_collection.find(keyword)
        comments = list(comments)
        if len(comments) == 0: raise ValueError('존재하지 않는 댓글입니다.')
    except Exception as e:
        print(str(e))
        flash(f'댓글을 확인하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return False, []
    else:
        return True, comments

def comment_list(keyword: dict) -> list:
    try:
        comments = comment_collection.find(keyword)
        comments = list(comments)
    except Exception as e:
        print(str(e))
        flash(f'댓글 목록을 불러오는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return None
    else:
        return comments

def comment_post(data: dict) -> bool:
    try:
        comment_collection.insert_one(data)
    except Exception as e:
        print(str(e))
        flash(f'댓글을 게시하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return False
    else:
        flash('댓글이 성공적으로 게시되었습니다.', 'success')
        return True

def comment_delete(keyword: dict, post_id: ObjectId) -> bool:
    try:
        is_present, comments = is_comment_present(keyword)
        if not is_present: raise ValueError('존재하지 않는 댓글입니다.')
        comment_collection.delete_many(keyword)

        is_present, posts = is_post_present({'_id': post_id})
        if not is_present: raise ValueError('존재하지 않는 글입니다.')
        post = posts[0]
    except Exception as e:
        print(str(e))
        flash(f'댓글을 삭제하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return False
    else:
        flash('댓글을 삭제하였습니다.', 'success')
        return True