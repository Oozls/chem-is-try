from bson import ObjectId
from database import is_account_present
from flask import flash, redirect
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from pages import app

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_message = None

@login_manager.unauthorized_handler
def unauthorized():
    flash('로그인이 필요합니다.','error')
    return redirect("/account/login")

class User(UserMixin):
    def __init__(self, id, username, password, admin):
        self.id = id
        self.username = username
        self.password = password
        self.admin = admin

    def __repr__(self):
        r = {
            'user_id': self.id,
            'username': self.username,
            'password': self.password,
            'admin': self.admin,
        }
        return str(r)
    
    def is_active(self) -> bool: #idk
        return True
    
    def is_admin(self) -> bool:
        return self.admin

    def get_id(self) -> str:
        return self.id

    def get_name(self) -> str:
        return self.username
    
@login_manager.user_loader
def user_loader(user_id):
    try:
        is_present, users = is_account_present({"_id":ObjectId(user_id)})
        if not is_present: ValueError('사용자 정보를 불러오는 과정에서 오류가 발생했습니다.')
        user = users[0]
        user['id'] = str(user.pop('_id'))
        return User(**user)
    except Exception as e:
        print(f'오류 발생: {e}')
        return