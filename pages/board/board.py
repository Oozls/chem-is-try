from collections import defaultdict
from database import is_post_present, post_list, board_post, board_edit, board_delete, is_comment_present, comment_list, comment_post, comment_delete, obj
from datetime import datetime
from flask import Blueprint, render_template, redirect, request, flash, session
from flask_login import login_required, current_user
# from re import sub

board_bp = Blueprint("board", __name__, url_prefix="/board")

# def censore(t):
#     return sub(r"[^ㄱ-ㅣ가-힣0-9a-zA-Zぁ-ゔァ-ヴ一-龥!@#$%^&*()`~'\";:/?.>,<\\|=\-+_\s]", "", t)

# --------- LIST --------- #
@board_bp.route("/")
def board_list_page():
    posts = post_list({})
    if posts == None: return redirect('/')

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
    
    success = board_post({"title" : title, "category" : category, "content" : content, "author_id" : author_id, "time" : int(datetime.now().timestamp()), "view" : 0})
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
        return redirect(f'/board/view/{id}')
    
    if request.method == "GET": return render_template('/board/post.html', post=post)

    category = request.form.get('category')
    title = request.form.get('title')
    content = request.form.get('content')

    success = board_edit({"title" : title, "category" : category, "content" : content}, obj(id))
    
    if success:
        flash('글이 성공적으로 수정되었습니다.', 'success')
        return redirect(f'/board/view/{id}')
    else: return redirect(f'/board/view/{id}')




# --------- VIEW --------- #
def get_sorted_comments(post_id): # 댓글 순서 정리 - 사실 어떻게 작동하는지 잘 모르겠음
    raw_comments = comment_list({'post_id': post_id}) # 댓글의 "post_id"가 post_id인 놈들 반환
    comments_by_parent = defaultdict(list) # 디폴드 딕셔너리 - value가 자동으로 빈 리스트 (아마?)
    
    for comment in raw_comments:
        p_id = str(comment.get('parent_id', 'root'))
        if p_id == 'None' or p_id == '': 
            p_id = 'root'
            
        comments_by_parent[p_id].append(comment)

    sorted_list = []

    def add_children(parent_id, current_depth):
        children = comments_by_parent.get(parent_id, [])
        
        for child in children:
            child['depth'] = current_depth
            sorted_list.append(child)
            
            add_children(str(child['_id']), current_depth + 1)

    add_children('root', 0)

    return sorted_list

@board_bp.route('/view/<id>')
def board_view_page(id):
    # 존재하는 글임?
    is_present, posts = is_post_present({'_id': obj(id)})
    if not is_present: return redirect('/board') # 아님

    # 존재함
    post = posts[0] # 글 정보

    # 조회수 업데이트
    viewed_posts = session.get('viewed_posts', []) # 사용자 세션에서 봤던 글 id 목록 가져오기
    if viewed_posts == None: session['viewed_posts'] = [] # 세션이 비어있음(None) -> 빈 리스트로 바꿈
    if id not in viewed_posts: # 사용자가 아직 글을 안 봄 -> 조회수 추가
        viewed_posts.append(id)
        session['viewed_posts'] = viewed_posts
        success = board_edit({'view': post['view']+1}, obj(id)) #
        if not success: return redirect(f'/board/view/{id}')
        post['view'] += 1
    
    comments = get_sorted_comments(id)
    return render_template('/board/view.html', post=post, comments=comments)




# --------- DELETE --------- #
@board_bp.route('/delete/<id>', methods=['POST'])
def board_delete_page(id):
    is_present, posts = is_post_present({'_id': obj(id)})
    if not is_present: return redirect('/board')
    post = posts[0]
    success = board_delete({'_id': obj(id)})
    if not success: return redirect(f'/board/view/{id}')
    return redirect('/board')




# --------- COMMENT POST --------- #
@board_bp.route('/comment/post/<id>', methods=['POST'])
@login_required
def board_comment_post_page(id):
    parent_id = request.form.get('parent_id')
    depth = request.form.get('depth')
    depth = int(depth)
    content = request.form.get('content')

    is_present, posts = is_post_present({'_id': obj(id)})
    if not is_present: return redirect('/board')
    post = posts[0]

    data = {'post_id': id, 'author_id': current_user.get_id(), 'parent_id': parent_id, 'depth': depth, 'content': content, "time" : int(datetime.now().timestamp())}
    success = comment_post(data)
    if not success: return redirect(f'/board/view/{id}')

    is_present, comments = is_comment_present(data)
    if not is_present: return redirect(f'/board/view/{id}')
    comment = comments[0]

    # post_comment_list = post['comment']
    # post_comment_list.append(str(comment['_id']))

    # success = board_edit({'comment': post_comment_list}, obj(id))
    # if not success: return redirect(f'/board/view/{id}')

    return redirect(f'/board/view/{id}')




# --------- COMMENT DELETE --------- #
@board_bp.route('/comment/delete/<id>', methods=['POST'])
@login_required
def board_comment_delete_page(id):
    is_present, comments = is_comment_present({'_id': obj(id)})
    if not is_present: return redirect('/board')
    comment = comments[0]

    if current_user.get_id() != comment['author_id'] and not current_user.is_admin():
        flash('권한이 없습니다.', 'error')
        return redirect(f'/board/view/{comment['post_id']}')

    success = comment_delete({'_id': obj(id)}, obj(comment['post_id']))
    return redirect(f'/board/view/{comment['post_id']}')