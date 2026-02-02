from database import is_reagent_present, reagent_list, reagent_register, reagent_edit, reagent_delete, reagent_bulk_register, obj
from difflib import SequenceMatcher
from flask import Blueprint, render_template, redirect, request, flash, send_file, session
from flask_login import login_required, current_user
from io import BytesIO
from json import load
from pandas import DataFrame, ExcelWriter, read_excel
from requests import get
from requests.exceptions import Timeout

reagent_bp = Blueprint("reagent", __name__, url_prefix="/reagent")

# --------- REGISTER --------- #
@reagent_bp.route('/register', methods=["GET", "POST"])
@login_required
def reagent_register_page():
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

        success = reagent_register(name, category, amount, left_amount, location, misc, cid)
        return redirect('/reagent/register')
    return render_template('/reagent/register.html')




# --------- LIST --------- #
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

    if '/' in inner_content:
        parts = inner_content.rsplit('/', 1)
        english_part = parts[0].strip()
        formula = parts[1].strip()
    else:
        english_part = inner_content.strip()

    if '&' in english_part:
        english_names = [name.strip() for name in english_part.split('&')]
    else:
        english_names = [english_part]

    return korean_name, english_names, formula

@reagent_bp.route('/')
def reagent_list_page():
    name = request.args.get('name')
    if name: name = name.lower()
    category = request.args.get('category')
    amount = request.args.get('amount')
    left_amount = request.args.get('left_amount')
    location = request.args.get('location')
    misc = request.args.get('misc')

    keyword = {}
    if category or amount or left_amount or location or misc: # 이름 제외 args는 일치해야 함
        if category != "all": keyword['category'] = category
        if amount != "": keyword['amount'] = amount
        if left_amount != "": keyword['left_amount'] = left_amount
        if location != "all": keyword['location'] = location
        if misc != "all": keyword['misc'] = misc

    reagents = reagent_list(keyword)
    if not reagents: return redirect('/reagent')
    reagents.sort(key=lambda x : (int(x['location']), x['name']))

    results = []

    if name and name != "": 
        for item in reagents:
            korean_name, english_names, formula = extract_chemical_info(item['name'])

            def compare(text1, text2):
                threshold = 0.6
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

    return render_template('/reagent/list.html', reagents=results)




# --------- DETAIL --------- #
def get_info(cid):
    ghs_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=Safety+and+Hazards"
    cas_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=CAS"
    
    ghs_info = {}
    cas_info = {}

    # ---- GHS ---- #
    try:
        response = get(ghs_url, timeout=15)
        response.raise_for_status()
        data = response.json()

        def find_ghs_section(sections): # 재귀함수
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

        ghs_info["status"] = "success"
        if not ghs_section:
            ghs_info["message"] = "GHS info not found."
        else:
            ghs_info["message"] = "GHS info found."
            pictograms = []
            hazard_statements = []

            for info in ghs_section.get("Information", []):
                name = info.get("Name")
                if name == "Pictogram(s)":
                    for markup in info["Value"]["StringWithMarkup"][0].get("Markup", []):
                        pictograms.append(markup["URL"])
                elif name == "GHS Hazard Statements":
                    for item in info["Value"]["StringWithMarkup"]:
                        hazard_statements.append(item.get("String"))
            ghs_info['pictograms'] = pictograms
            ghs_info['hazard_statements'] = hazard_statements
    except Timeout:
        ghs_info['status'] = 'error'
        ghs_info['message'] = 'Timeout'
    except Exception as e:
        ghs_info['status'] = 'error'
        ghs_info['message'] = str(e)
    
    # ---- CAS ---- #
    try:
        response = get(cas_url, timeout=15)
        response.raise_for_status()
        data = response.json()

        def find_cas_section(sections): # 재귀함수
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

        cas_info['status'] = 'success'
        if not cas_section:
            cas_info['message'] = 'Cas info not found.'
        else:
            infos = cas_section.get("Information", [])
            infos.sort(key=lambda x: x["ReferenceNumber"])
            cas = infos[0]["Value"]["StringWithMarkup"][0]["String"]
            cas_info['cas'] = cas
    except Timeout:
        cas_info['status'] = 'error'
        cas_info['message'] = 'Timeout'
    except Exception as e:
        cas_info['status'] = 'error'
        cas_info['message'] = str(e)

    return ghs_info, cas_info

@reagent_bp.route('/detail/<id>')
def reagent_detail_page(id):
    is_present, reagents = is_reagent_present({'_id': obj(id)})

    if not is_present: return redirect('/reagent')

    reagent = reagents[0]
    ghs_info, cas_info = None, None
    if reagent['cid'] != "" and reagent['cid'] != None:
        ghs_info, cas_info = get_info(reagent['cid'])

        with open('static/json/ghs.json', 'r') as f:
            ghs_translation = load(f)

        if 'pictograms' in ghs_info.keys(): ghs_info['pictograms'] = list(set(ghs_info['pictograms']))
        if 'hazard_statements' in ghs_info.keys():
            ghs_info['hazard_statements'] = list(set(ghs_info['hazard_statements']))
            msgs = []
            for msg in ghs_info['hazard_statements']:
                if msg[0] == 'H':
                    space_index = msg.find(' ')
                    code = msg[:space_index].strip().replace(':', '')
                    
                    if code in ghs_translation.keys(): msgs.append(f"{code} : {ghs_translation[code]}")
                    else: msgs.append(msg)
                else: msgs.append(msg)
            ghs_info['hazard_statements'] = msgs
            ghs_info['hazard_statements'].sort(key=lambda x: x[:4])

    return render_template('/reagent/detail.html', reagent=reagent, ghs_info=ghs_info, cas_info=cas_info)




# --------- EDIT --------- #
@reagent_bp.route('/edit/<id>', methods=["GET", "POST"])
@login_required
def reagent_edit_page(id):
    if not current_user.is_admin():
        flash('권한이 없습니다.', 'error')
        return redirect('/reagent')
    
    is_present, reagents = is_reagent_present({'_id': obj(id)})

    if not is_present: return redirect('/')
    reagent = reagents[0]

    if request.method == 'GET': return render_template('/reagent/edit.html', reagent=reagent)
    
    name = request.form.get('name')
    category = request.form.get('category')
    amount = request.form.get('amount')
    left_amount = request.form.get('left_amount')
    location = request.form.get('location')
    misc = request.form.get('misc')
    cid = request.form.get('cid')
    if cid.strip() == "": cid = None

    success = reagent_edit({'name':name, 'category':category, 'amount':amount, 'left_amount':left_amount, 'location':location, 'misc':misc, 'cid':cid}, id)

    if success: return redirect(f'/reagent/detail/{id}')
    else: return redirect(f'/reagent/edit/{id}')




# --------- DELETE --------- #
@reagent_bp.route('/delete/<id>')
@login_required
def reagent_delete_page(id):
    if not current_user.is_admin():
        flash('권한이 없습니다.', 'error')
        return redirect('/reagent')
    
    is_present, reagents = is_reagent_present({'_id': obj(id)})
    if not is_present: return redirect(f'/reagent/edit/{id}')
    
    success = reagent_delete({'_id': obj(id)})

    if success: return redirect('/reagent')
    else: return redirect(f'/reagent/edit/{id}')




# --------- DOWNLOAD --------- #
@reagent_bp.route('/download')
def reagent_download_page():
    data = reagent_list({})

    if not data: return redirect('/')

    data.sort(key=lambda x : (int(x['location']), x['name']))

    try:
        df = DataFrame(data)

        column_order = ['name', 'category', 'amount', 'left_amount', 'location', 'misc', 'cid']
        df = df[column_order]
        df.rename(columns={
            'name': '시약',
            'category': '구분',
            'amount': '수량',
            'left_amount': '잔량',
            'location': '밀폐 시약장 번호',
            'misc': '비고',
            'cid': "CID"
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
    except Exception as e:
        print(str(e))
        flash(f'파일 처리 중 오류가 발생했습니다.\n{str(e)}', 'error')
        return redirect(request.url)




# --------- UPLOAD --------- #
@reagent_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if not current_user.is_admin():
        flash('권한이 없습니다.', 'error')
        return redirect('/')
    
    if request.method == 'GET':
        session.pop('preview_data', None)
        return render_template('/reagent/upload.html', preview=None)
    
    file = request.files.get('file')
    if not file or file.filename == '':
        flash('파일을 선택해주세요.', 'error')
        return redirect('/reagent/upload')

    if not file or not file.filename.endswith(('.xlsx', '.xls')):
        flash('엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.', 'error')
        return redirect('/reagent/upload')

    try:
        df = read_excel(file)
        
        df = df.fillna('')

        col_map = {
            '시약': 'name',
            '구분': 'category',
            '수량': 'amount',
            '잔량': 'left_amount',
            '밀폐 시약장 번호': 'location',
            '비고': 'misc',
            'CID': 'cid'
        }
        
        df.rename(columns=col_map, inplace=True)

        if 'name' in df.columns:
            df = df[df['name'] != '']
        
        valid_columns = ['name', 'category', 'amount', 'left_amount', 'location', 'misc', 'cid']
        existing_cols = [c for c in valid_columns if c in df.columns]
        
        reagents_list = df[existing_cols].to_dict('records')
        for reagent in reagents_list:
            print(reagent)
            reagent['amount'] = int(float(reagent['amount'])) if reagent['amount'] != '' else None
            reagent['left_amount'] = int(float(reagent['left_amount'])) if reagent['left_amount'] != '' else None
            reagent['cid'] = int(float(reagent['cid'])) if reagent['cid'] != '' else None

        if not reagents_list: raise ValueError('등록할 데이터가 없거나 형식이 올바르지 않습니다.')

        session['preview_data'] = reagents_list
        flash(f'총 {len(reagents_list)}개의 시약이 인식되었습니다. 아래 목록을 확인 후 등록 버튼을 눌러주세요.', 'info')
        return render_template('/reagent/upload.html', preview=reagents_list)

    except Exception as e:
        print(str(e))
        flash(f'파일 처리 중 오류가 발생했습니다.\n{str(e)}', 'error')
        return redirect('/reagent/upload')

@reagent_bp.route('/upload/confirm', methods=['POST'])
def save_upload():
    reagents = session.get('preview_data')
    mode = request.form.get('mode')

    if not reagents:
        flash('저장할 데이터가 만료되었습니다. 다시 업로드해주세요.', 'error')
        return redirect('/reagent/upload')

    if mode == 'replace':
        delete_success = reagent_delete({})
        if not delete_success: return redirect('/reagent/upload')

    success = reagent_bulk_register(reagents)
    if success:
        session.pop('preview_data', None)
        return redirect('/reagent')
    else:
        return redirect('/reagent/upload')