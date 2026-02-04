from database import is_account_present, obj
from dotenv import load_dotenv
from flask import Flask, render_template
from flask_cors import CORS
from flask_session import Session
from os import getenv

load_dotenv()

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = getenv('SECRET_KEY')
app.template_folder = "../templates"
app.static_folder = "../static"
app.config['SESSION_TYPE'] = 'filesystem' 
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True

Session(app)
CORS(app)




from .reagent import reagent
from .account import account
from .board import board

app.register_blueprint(reagent.reagent_bp)
app.register_blueprint(account.account_bp)
app.register_blueprint(board.board_bp)

@app.route('/')
def main_page():
    return render_template('main.html')




from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
def unix_to_date(t):
    date = datetime.fromtimestamp(t)
    today = datetime.today()
    diff = today - date

    if diff.days == 0:
        return datetime.fromtimestamp(t, tz=KST).strftime('%H:%M')
    else:
        return datetime.fromtimestamp(t, tz=KST).strftime('%Y.%m.%d')

app.jinja_env.filters["unix_to_date"] = unix_to_date




def id_to_username(id):
    is_present, users = is_account_present({'_id': obj(id)})
    if not is_present: return '알 수 없음'
    user = users[0]
    return user['username']

app.jinja_env.filters["id_to_username"] = id_to_username