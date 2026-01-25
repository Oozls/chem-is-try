from bson import ObjectId
from flask import flash
from flask_pymongo import PyMongo
from pymongo import MongoClient, InsertOne
from os import getenv

mongo = PyMongo()
client = MongoClient(getenv("DB_CONNECT"), 27017)
db = client['chemistry']
reagent_collection = db['reagent']

def is_reagent_present(keyword: dict) -> bool | list:
    try:
        reagents = reagent_collection.find(keyword)
        reagents = list(reagents)
        if len(reagents) == 0: raise ValueError('존재하지 않는 시약입니다.')
    except Exception as e:
        print(str(e))
        flash(f'시약을 확인하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return False, []
    else:
        return True, reagents

def reagent_list(keyword: dict) -> list:
    try:
        reagents = reagent_collection.find(keyword)
        reagents = list(reagents)
    except Exception as e:
        print(str(e))
        flash(f'시약 목록을 불러오는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return None
    else:
        return reagents
    
def reagent_register(name, category, amount, left_amount, location, misc, cid) -> bool:
    try:
        reagent_collection.insert_one({'name':name, 'category':category, 'amount':amount, 'left_amount':left_amount, 'location':location, 'misc':misc, 'cid':cid})
    except Exception as e:
        print(str(e))
        flash(f'시약을 등록하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return False
    else:
        flash('시약이 등록되었습니다.', 'success')
        return True

def reagent_bulk_register(reagents: list) -> bool:
    try:
        operations = [InsertOne(item) for item in reagents]
        
        if operations:
            result = reagent_collection.bulk_write(operations)
            flash(f'성공적으로 {result.inserted_count}개의 시약이 등록되었습니다.', 'success')
        else:
            flash('등록할 데이터가 없습니다.', 'info')
    except Exception as e:
        print(str(e))
        flash(f'시약을 등록하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return False
    else:
        flash('시약이 등록되었습니다.', 'success')
        return True

def reagent_edit(data: dict, id: str) -> bool:
    try:
        is_present, reagents = is_reagent_present({'_id': ObjectId(id)})
        if not is_present:
            raise ValueError('존재하지 않는 시약입니다.')
        reagent_collection.update_one({'_id': ObjectId(id)}, {'$set': data})
    except Exception as e:
        print(str(e))
        flash(f'시약 정보를 수정하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return False
    else:
        flash('시약 정보가 성공적으로 수정되었습니다.', 'success')
        return True

def reagent_delete(keyword: dict) -> bool:
    try:
        is_present, reagents = is_reagent_present(keyword)
        if not is_present: raise ValueError('존재하지 않는 시약입니다.')
        reagent_collection.delete_many(keyword)
    except Exception as e:
        print(str(e))
        flash(f'시약을 제거하는 과정에서 오류가 발생했습니다.\n{str(e)}'.split('\n'), 'error')
        return False
    else:
        flash('시약을 제거하였습니다.', 'success')
        return True