from flask import Flask, render_template, request, redirect, flash, url_for, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_pymongo import PyMongo
from pymongo import MongoClient
from dotenv import load_dotenv
from os import getenv
from bson.objectid import ObjectId
from re import match, search
from difflib import SequenceMatcher
from waitress import serve
from pandas import DataFrame, ExcelWriter
from io import BytesIO
import requests

load_dotenv()




app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SECRET_KEY'] = getenv('SECRET_KEY')
app.config['SESSION_TYPE'] = 'mongodb'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_message = None

@login_manager.unauthorized_handler
def unauthorized():
    flash('로그인이 필요합니다.','error')
    return redirect(url_for('login'))

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
    
    def is_active(self):
        return True
    
    def is_admin(self):
        return self.admin

    def get_id(self):
        return self.id

    def get_name(self):
        return self.username
    



mongo = PyMongo()
client = MongoClient(getenv("DB_CONNECT"), 27017)
db = client['chemistry']
user_collection = db['user']
reagent_collection = db['reagent']




@login_manager.user_loader
def user_loader(user_id):
    target_user = user_collection.find_one({"_id":ObjectId(str(user_id))})
    target_user['id'] = str(target_user.pop('_id'))
    return User(**target_user)




@app.route('/')
def main_page():
    return render_template('main.html')




@app.route('/login', methods=["GET", "POST"])
def login_page():
    if current_user.is_authenticated: return redirect('/')
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')

        target_user = user_collection.find_one({'username':username, 'password':password})
        if target_user:
            target_user['id'] = str(target_user.pop('_id'))
            login_user(User(**target_user))
            flash("로그인 되었습니다.", "success")
            return redirect('/')
        flash("해당 사용자가 존재하지 않습니다. 정보를 바르게 기입해주세요.", 'error')
        return redirect('/login')
    return render_template('login.html')




@app.route('/signup', methods=["GET", "POST"])
def signup_page():
    if current_user.is_authenticated: return redirect('/')
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        if not bool(match(r'^[가-힣]{2,4}$', username)):
            flash('올바른 형식의 이름이 아닙니다.', 'error')
            return redirect('/signup')
        elif user_collection.find_one({'username':username}):
            flash('이미 존재하는 사용자 이름입니다.', 'error')
            return redirect('/signup')
        elif password_confirm != password:
            flash('비밀번호가 일치하지 않습니다.', 'error')
            return redirect('/signup')

        user_data = {
            'username':username,
            'password':password,
            'admin': False
        }
        user_collection.insert_one(user_data)
        target_user = user_collection.find_one(user_data)
        
        target_user['id'] = str(target_user.pop('_id'))
        login_user(User(**target_user))
        flash("회원 가입이 정상적으로 완료되었습니다.", 'success')
        return redirect('/')
    return render_template('signup.html')




@app.route('/logout')
@login_required
def logout_page():
    logout_user()
    flash("로그아웃 되었습니다.", "success")
    return redirect('/')




def extract_chemical_info(text):
    first_paren_idx = text.find('(')
    last_paren_idx = text.rfind(')')
    
    if first_paren_idx == -1 or last_paren_idx == -1:
        return {
            "korean": text.strip(),
            "english": [],
            "formula": None
        }

    korean_name = text[:first_paren_idx].strip()

    inner_content = text[first_paren_idx+1 : last_paren_idx]
    
    english_part = ""
    formula = None

    if ',' in inner_content:
        parts = inner_content.rsplit(',', 1)
        english_part = parts[0].strip()
        formula = parts[1].strip()
    else:
        english_part = inner_content.strip()

    if '&' in english_part:
        english_names = [name.strip() for name in english_part.split('&')]
    else:
        english_names = [english_part]

    return korean_name, english_names, formula

@app.route('/search')
def search_page():
    name = request.args.get('name')
    if name: name = name.lower()
    category = request.args.get('category')
    amount = request.args.get('amount')
    left_amount = request.args.get('left_amount')
    location = request.args.get('location')
    misc = request.args.get('misc')

    keyword = {}
    if category or amount or left_amount or location or misc:
        if category != "all": keyword['category'] = category
        if amount != "": keyword['amount'] = amount
        if left_amount != "": keyword['left_amount'] = left_amount
        if location != "all": keyword['location'] = location
        if misc != "all": keyword['misc'] = misc

    reagents = list(reagent_collection.find(keyword))
    reagents.sort(key=lambda x : (int(x['location']), x['name']))

    results = []

    if name and name != "":
        for item in reagents:
            # it's so old school
            # match = search(r"^(.*?)\(([^,)]+)(?:,\s*([^)]+))?\)$", item['name'])
            # korean_name = match.group(1).strip()
            # english_name = match.group(2).strip().lower()
            # formula = match.group(3).strip() if match.group(3) else None

            # matcher1 = SequenceMatcher(None, name, korean_name)
            # matcher2 = SequenceMatcher(None, name, english_name)
            # matcher3 = SequenceMatcher(None, name, formula)
            # matcher4 = SequenceMatcher(None, name, item['name'.lower()])

            korean_name, english_names, formula = extract_chemical_info(item['name'])

            def compare(text1, text2):
                threshold = 0.7
                similarity = SequenceMatcher(None, text1, text2).ratio()
                if similarity >= threshold: return True
                return False

            ready = False
            if name.lower() in item['name'].lower(): ready = True
            elif compare(name.lower(), korean_name.lower()): ready = True
            else:
                if formula:
                    if compare(name, formula): ready = True
                if not ready:
                    for english_name in english_names:
                        if compare(name.lower(), english_name.lower()): ready = True
            
            if ready: results.append(item)
    else: results = reagents

    return render_template('search.html', reagents=results)




@app.route('/register', methods=["GET", "POST"])
@login_required
def register_page():
    if not current_user.is_admin():
        flash('권한이 없습니다.', 'error')
        return redirect('/')
    if request.method == "POST":
        name = request.form.get('name')
        category = request.form.get('category')
        amount = request.form.get('amount')
        left_amount = request.form.get('left_amount')
        location = request.form.get('location')
        misc = request.form.get('misc')
        cid = request.form.get('cid')

        # reagents = reagent_collection.find()
        # for item in reagents:
        #     match = search(r"(.*?)\((.*?)\)", item['name'])
        #     korean_name = match.group(1).strip()
        #     english_name = match.group(2).strip().lower()     
        #     if korean_name in name or english_name in name:
        #         flash(f'유사한 시약({item['name']})이 이미 등록되어 있습니다.', 'info')

        reagent_data = {'name':name, 'category':category, 'amount':amount, 'left_amount':left_amount, 'location':location, 'misc':misc, 'cid':cid}
        reagent_collection.insert_one(reagent_data)

        flash('시약이 등록되었습니다.', 'success')
        return redirect('/register')
    return render_template('register.html')




def pubview_ghs(cid):
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=Safety+and+Hazards"
        
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        def find_ghs_section(sections):
            for section in sections:
                if section.get("TOCHeading") == "GHS Classification":
                    return section
                if "Section" in section:
                    result = find_ghs_section(section["Section"])
                    if result:
                        return result
            return None

        root_sections = data.get("Record", {}).get("Section", [])
        ghs_section = find_ghs_section(root_sections)

        if not ghs_section:
            return {"status": "success", "message": "GHS INFO NOT FOUND"}

        result = {
            "status": "success",
            "pictograms": [],
            "signal_word": "",
            "hazard_statements": []
        }

        for info in ghs_section.get("Information", []):
            name = info.get("Name")
            
            # 그림문자 (Pictograms)
            if name == "Pictogram(s)":
                for markup in info["Value"]["StringWithMarkup"][0].get("Markup", []):
                    result["pictograms"].append(markup["URL"])
            
            # 신호어 (Signal Word)
            elif name == "Signal":
                result["signal_word"] = info["Value"]["StringWithMarkup"][0].get("String")
            
            # 유해위험 문구 (Hazard Statements)
            elif name == "GHS Hazard Statements":
                for item in info["Value"]["StringWithMarkup"]:
                    result["hazard_statements"].append(item.get("String"))

        return result

    except requests.exceptions.Timeout:
        return {"status": "error", "message": "TIMEOUT"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def pubview_cas(cid):
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=CAS"
        
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        def find_cas_section(sections):
            for section in sections:
                if section.get("TOCHeading") == "CAS":
                    return section
                if "Section" in section:
                    result = find_cas_section(section["Section"])
                    if result:
                        return result
            return None

        root_sections = data.get("Record", {}).get("Section", [])
        cas_section = find_cas_section(root_sections)

        if not cas_section:
            return {"status": "success", "message": "CAS INFO NOT FOUND"}

        result = {
            "status": "success",
            "cas": "",
        }

        infos = cas_section.get("Information", [])
        infos.sort(key=lambda x: x["ReferenceNumber"])
        cas = infos[0]["Value"]["StringWithMarkup"][0]["String"]
        result['cas'] = cas

        return result

    except requests.exceptions.Timeout:
        return {"status": "error", "message": "TIMEOUT"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.route('/reagent/<id>')
def detail_page(id):
    reagent = reagent_collection.find_one({'_id':ObjectId(id)})

    if not reagent:
        flash('등록되지 않은 시약입니다.', 'error')
        return redirect('/search')

    if 'cid' not in reagent.keys():
        reagent_collection.update_one({'_id':ObjectId(id)},{'$set':{'cid':None}})
        reagent['cid'] = ""
    elif reagent['cid'] != "" and reagent['cid'] != None:
        ghs = pubview_ghs(reagent['cid'])
        cas = pubview_cas(reagent['cid'])
        # if ghs['status'] == 'success' and cas['status'] == 'success':
        ghs['pictograms'] = list(set(ghs['pictograms']))
        ghs['hazard_statements'] = list(set(ghs['hazard_statements']))
        reagent['ghs'] = ghs
        reagent['cas'] = cas

    return render_template('detail.html', reagent=reagent)





@app.route('/edit/<id>', methods=["GET", "POST"])
@login_required
def edit_page(id):
    if not current_user.is_admin():
        flash('권한이 없습니다.', 'error')
        return redirect('/')
    
    reagent = reagent_collection.find_one({'_id':ObjectId(id)})

    if not reagent:
        flash('등록되지 않은 시약입니다.', 'error')
        return redirect('/search')

    if request.method == 'GET':
        if "cid" not in reagent.keys(): reagent['cid'] = ""
        elif reagent['cid'] == "" or reagent['cid'] == None: reagent['cid'] = ""
        return render_template('edit.html', reagent=reagent)
    
    name = request.form.get('name')
    category = request.form.get('category')
    amount = request.form.get('amount')
    left_amount = request.form.get('left_amount')
    location = request.form.get('location')
    misc = request.form.get('misc')
    cid = request.form.get('cid')
    if cid.strip() == "": cid = None

    reagent_data = {'name':name, 'category':category, 'amount':amount, 'left_amount':left_amount, 'location':location, 'misc':misc, 'cid':cid}
    reagent_collection.update_one({'_id':ObjectId(id)}, {'$set':reagent_data})

    flash('시약 정보를 수정하였습니다.', 'success')
    return redirect(f'/reagent/{id}')




@app.route('/delete/<id>')
@login_required
def delete_page(id):
    if not current_user.is_admin():
        flash('권한이 없습니다.', 'error')
        return redirect('/')
    
    reagent = reagent_collection.find_one({'_id':ObjectId(id)})
    if not reagent:
        flash('등록되지 않은 시약입니다.', 'error')
        return redirect('/search')
    
    reagent_collection.delete_one({'_id':ObjectId(id)})
    flash('시약을 삭제했습니다.', 'success')
    return redirect('/search')




@app.route('/download')
def download_page():
    data = list(reagent_collection.find({}, {'_id': 0}))
    data.sort(key=lambda x : (int(x['location']), x['name']))

    df = DataFrame(data)

    column_order = ['name', 'category', 'amount', 'left_amount', 'location', 'misc']
    df = df[column_order]
    df.rename(columns={
        'name': '시약',
        'category': '구분',
        'amount': '수량',
        'left_amount': '잔량',
        'location': '밀폐 시약장 번호',
        'misc': '비고'
    }, inplace=True)

    output = BytesIO()
    with ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='시약')
    
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='청원고등학교 시약.xlsx'
    )




if __name__ == "__main__":
    # app.run(host='0.0.0.0', port=8000, debug=True)
    serve(app, host='0.0.0.0', port=8000)