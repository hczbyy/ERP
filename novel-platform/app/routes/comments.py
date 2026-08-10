"""评论路由

优化点：Comment.user 已设为 lazy='joined'，默认 JOIN 加载
"""

from flask import Blueprint, request, jsonify
from app.models import Novel, Comment, User
from app.extensions import db
from app.utils import verify_token

comment_bp = Blueprint("comments", __name__, url_prefix="/api")


def _get_current_user():
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else auth
    uid = verify_token(token)
    return db.session.get(User, uid) if uid else None


@comment_bp.route("/novels/<int:novel_id>/comments", methods=["GET"])
def list_comments(novel_id):
    """小说评论列表
    Comment.user 已 lazy='joined' → 自动 JOIN，0 额外查询
    """
    novel = db.session.get(Novel, novel_id)
    if not novel:
        return jsonify(code=404, message="小说不存在"), 404

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    query = Comment.query.filter_by(novel_id=novel_id).order_by(Comment.created_at.desc())
    total = query.count()
    pages = (total + per_page - 1) // per_page
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify(code=200, data={
        "items": [c.to_dict() for c in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }), 200


@comment_bp.route("/comments", methods=["POST"])
def create_comment():
    """发表评论（需登录）"""
    user = _get_current_user()
    if not user:
        return jsonify(code=401, message="请先登录"), 401

    data = request.get_json(force=True)
    if not data or not data.get("content", "").strip():
        return jsonify(code=400, message="评论内容不能为空"), 400

    novel_id = data.get("novel_id")
    if not novel_id:
        return jsonify(code=400, message="novel_id 不能为空"), 400

    novel = db.session.get(Novel, novel_id)
    if not novel:
        return jsonify(code=404, message="小说不存在"), 404

    comment = Comment(
        user_id=user.id,
        novel_id=novel_id,
        chapter_id=data.get("chapter_id"),
        content=data["content"].strip(),
    )
    db.session.add(comment)
    db.session.commit()

    return jsonify(code=200, message="评论成功", data=comment.to_dict()), 200