from database import is_post_present, post_list, board_post, board_edit, board_delete, obj
from datetime import datetime
from flask import Blueprint, render_template, redirect, request, flash
from flask_login import login_required, current_user
# from re import sub

board_bp = Blueprint("board", __name__, url_prefix="/board")

# def censore(t):
#     return sub(r"[^ㄱ-ㅣ가-힣0-9a-zA-Zぁ-ゔァ-ヴ一-龥!@#$%^&*()`~'\";:/?.>,<\\|=\-+_\s]", "", t)

# --------- LIST --------- #
@board_bp.route("/")
def board_list_page():
    posts = post_list({})
    if not posts: return redirect('/board')

    sort = request.args.get('sort')
    query = request.args.get('q')
    if sort == 'oldest': posts.sort(key=lambda x : x['time'])
    else: posts.sort(key=lambda x : -x['time'])

    results = None
    if not query:
        results = posts
    elif query.strip() == '':
        results = posts
    else:
        results = []
        for post in posts:
            if query in post['title'] or query in post['content']: results.append(post)

    return render_template('board/list.html', posts=results)




# --------- POST --------- #
@board_bp.route("/post", methods=['GET','POST'])
@login_required
def board_post_page():
    if request.method == "GET": return render_template('board/post.html')

    category = request.form.get('category')
    title = request.form.get('title')
    content = request.form.get('content')
    author_id = current_user.get_id()
    
    success = board_post({"title" : title, "category" : category, "content" : content, "author_id" : author_id, "time" : int(datetime.now().timestamp()), "view" : 0, "comment": []})
    return redirect('/board')




# --------- EDIT --------- #
@board_bp.route('/edit/<id>', methods=['GET', 'POST'])
@login_required
def board_edit_page(id):
    if not current_user.is_admin():
        flash('권한이 없습니다.', 'error')
        return redirect('/board')
    
    is_present, posts = is_post_present({'_id': obj(id)})
    post = posts[0]
    if not is_present:
        return redirect('/board')
    elif current_user.get_id() != str(post['_id']) and not current_user.is_admin():
        flash('자신의 글만 수정할 수 있습니다.', 'error')
        return redirect('/board/{id}')
    
    if request.method == "GET": return render_template('/board/post.html', post=post)

    category = request.form.get('category')
    title = request.form.get('title')
    content = request.form.get('content')

    success = board_edit({"title" : title, "category" : category, "content" : content}, id)
    
    if success:
        flash('글이 성공적으로 수정되었습니다.', 'success')
        return redirect(f'/board/{id}')
    else: return redirect(f'/board/edit/{id}')




# --------- VIEW --------- #
@board_bp.route('/view/<id>')
def board_view_page(id):
    is_present, posts = is_post_present({'_id': obj(id)})
    if not is_present: return redirect('/board')
    post = posts[0]
    success = board_edit({'view': post['view']+1}, id)
    post['view'] += 1
    if not success: return redirect(f'/board/view/{id}')
    return render_template('/board/view.html', post=posts[0])




# --------- DELETE --------- #
@board_bp.route('/delete/<id>', methods=['POST'])
def board_delete_page(id):
    is_present, posts = is_post_present({'_id': obj(id)})
    if not is_present: return redirect('/board')
    post = posts[0]
    success = board_delete({'_id': obj(id)})
    if not success: return redirect(f'/board/view/{id}')
    return redirect('/board')