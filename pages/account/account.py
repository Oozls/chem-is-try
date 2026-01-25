from database import is_account_present, accound_register
from flask import Blueprint, render_template, redirect, request, flash
from flask_login import login_required, current_user, login_user, logout_user
from re import match
from user import User

account_bp = Blueprint("account", __name__, url_prefix="/account")

# --------- LOGIN --------- #
@account_bp.route('/login', methods=["GET", "POST"])
def account_login_page():
    if current_user.is_authenticated: return redirect('/')
    if request.method == "GET": return render_template('/account/login.html')

    username = request.form.get('username')
    password = request.form.get('password')

    is_present, users = is_account_present({'username':username, 'password':password})

    if not is_present:
        flash('존재하지 않는 계정입니다.', 'error')
        return redirect('/account/login')
    user = users[0]
    user['id'] = str(user.pop('_id'))
    login_user(User(**user))

    flash("로그인 되었습니다.", "success")
    return redirect('/')




# --------- SIGNUP --------- #
@account_bp.route('/signup', methods=["GET", "POST"])
def account_signup_page():
    if current_user.is_authenticated: return redirect('/')
    if request.method == "GET": return render_template('/account/signup.html')

    username = request.form.get('username')
    password = request.form.get('password')
    password_confirm = request.form.get('password_confirm')
    
    is_present1, users = is_account_present({'username': username})
    if not bool(match(r'^[가-힣]{2,4}$', username)):
        flash('올바른 형식의 이름이 아닙니다.', 'error')
        return redirect('/account/signup')
    elif is_present1:
        flash('이미 존재하는 사용자 이름입니다.', 'error')
        return redirect('/account/signup')
    elif password_confirm != password:
        flash('비밀번호가 일치하지 않습니다.', 'error')
        return redirect('/account/signup')

    success = accound_register({'username':username, 'password':password, 'admin': False})
    if not success: redirect('/account/signup')

    is_present2, users = is_account_present({'username':username, 'password':password, 'admin': False})
    if not is_present2:
        flash('계정 등록 후 로그인하는 과정에서 오류가 발생했습니다.\n다시 로그인해주세요.', 'error')
        return redirect('/account/login')
    user = users[0]
    user['id'] = str(user.pop('_id'))
    login_user(User(**user))
    return redirect('/')




# --------- LOGOUT --------- #
@account_bp.route('/logout')
@login_required
def account_logout_page():
    logout_user()
    flash("로그아웃 되었습니다.", "success")
    return redirect('/')