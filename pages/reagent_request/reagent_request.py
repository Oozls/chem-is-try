from database import is_request_present, request_list, request_create, request_edit, is_reagent_present, reagent_edit, obj
from datetime import datetime
from flask import Blueprint, render_template, redirect, request, flash
from flask_login import login_required, current_user

reagent_request_bp = Blueprint("reagent_request", __name__, url_prefix="/request")

@reagent_request_bp.route('/new/<reagent_id>', methods=['GET', 'POST'])
@login_required
def reagent_request_new_page(reagent_id):
    is_present, reagents = is_reagent_present({'_id': obj(reagent_id)})
    if not is_present: return redirect('/reagent')
    reagent = reagents[0]

    if request.method == 'GET':
        return render_template('reagent_request/new.html', reagent=reagent)

    data = {
        'reagent_id': obj(reagent_id),
        'requester_id': current_user.get_id(),
        'new_left_amount': request.form.get('new_left_amount'),
        'detail': request.form.get('detail'),
        'status': 'pending',
        'time': int(datetime.now().timestamp()),
    }
    request_create(data)
    return redirect('/reagent')


@reagent_request_bp.route('/')
@login_required
def reagent_request_list_page():
    if not current_user.is_admin():
        flash('권한이 없습니다.', 'error')
        return redirect('/reagent')

    requests = request_list({})
    if requests is None: return redirect('/reagent')

    for r in requests:
        is_ok, reagents = is_reagent_present({'_id': r['reagent_id']})
        r['reagent_name'] = reagents[0]['name'] if is_ok else '삭제된 시약'
    requests.sort(key=lambda x: -x['time'])

    return render_template('reagent_request/list.html', requests=requests)


@reagent_request_bp.route('/<id>')
@login_required
def reagent_request_detail_page(id):
    if not current_user.is_admin():
        flash('권한이 없습니다.', 'error')
        return redirect('/reagent')

    is_present, requests = is_request_present({'_id': obj(id)})
    if not is_present: return redirect('/request')
    req = requests[0]

    reagent = None
    is_reagent_ok, reagents = is_reagent_present({'_id': req['reagent_id']})
    if is_reagent_ok: reagent = reagents[0]

    return render_template('reagent_request/detail.html', req=req, reagent=reagent)


@reagent_request_bp.route('/<id>/approve', methods=['POST'])
@login_required
def reagent_request_approve_page(id):
    if not current_user.is_admin():
        flash('권한이 없습니다.', 'error')
        return redirect('/reagent')

    is_present, requests = is_request_present({'_id': obj(id)})
    if not is_present: return redirect('/request')
    req = requests[0]

    success = reagent_edit({'left_amount': req['new_left_amount']}, str(req['reagent_id']))
    if success:
        request_edit({'status': 'approved'}, id)

    return redirect(f'/request/{id}')


@reagent_request_bp.route('/<id>/reject', methods=['POST'])
@login_required
def reagent_request_reject_page(id):
    if not current_user.is_admin():
        flash('권한이 없습니다.', 'error')
        return redirect('/reagent')

    is_present, requests = is_request_present({'_id': obj(id)})
    if not is_present: return redirect('/request')

    request_edit({'status': 'rejected'}, id)
    return redirect(f'/request/{id}')
