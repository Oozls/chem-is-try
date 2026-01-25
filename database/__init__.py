from .board import board_collection, is_post_present, post_list, board_post, board_edit, board_delete
from .reagent import reagent_collection, is_reagent_present, reagent_list, reagent_register, reagent_bulk_register, reagent_edit, reagent_delete
from .account import account_collection, is_account_present, accound_register
from bson import ObjectId

def obj(id) -> ObjectId:
    try:
        converted = ObjectId(id)
    except Exception as e:
        return None
    else:
        return converted