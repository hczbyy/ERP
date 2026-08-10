"""收藏路由（无 N+1 风险）"""

from flask import Blueprint, request, jsonify
from app.models import Novel, Favorite, User
from app.extensions import db
from app.utils import verify_token

favorite_bp = Blueprint("favorites", __name__, url_prefix="/api")


def _get_current_user():
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else auth
    uid = verify_token(token)
    return db.session.get(User, uid) if uid else None


@favorite_bp.route("/favorites", methods=["GET"])
def list_favorites():
    """我的收藏"""
    user = _get_current_user()
    if not user:
        return jsonify(code=401, message="请先登录"), 401

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    query = Favorite.query.filter_by(user_id=user.id).order_by(Favorite.created_at.desc())
    total = query.count()
    pages = (total + per_page - 1) // per_page
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify(code=200, data={
        "items": [f.to_dict() for f in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }), 200


@favorite_bp.route("/favorites", methods=["POST"])
def add_favorite():
    """添加收藏"""
    user = _get_current_user()
    if not user:
        return jsonify(code=401, message="请先登录"), 401

    data = request.get_json(force=True)
    novel_id = data.get("novel_id") if data else None
    if not novel_id:
        return jsonify(code=400, message="novel_id 不能为空"), 400

    novel = db.session.get(Novel, novel_id)
    if not novel:
        return jsonify(code=404, message="小说不存在"), 404

    exists = Favorite.query.filter_by(user_id=user.id, novel_id=novel_id).first()
    if exists:
        return jsonify(code=409, message="已收藏过该小说"), 409

    fav = Favorite(user_id=user.id, novel_id=novel_id)
    db.session.add(fav)
    db.session.commit()

    return jsonify(code=200, message="收藏成功", data=fav.to_dict()), 200


@favorite_bp.route("/favorites/<int:novel_id>", methods=["DELETE"])
def remove_favorite(novel_id):
    """取消收藏"""
    user = _get_current_user()
    if not user:
        return jsonify(code=401, message="请先登录"), 401

    fav = Favorite.query.filter_by(user_id=user.id, novel_id=novel_id).first()
    if not fav:
        return jsonify(code=404, message="未收藏该小说"), 404

    db.session.delete(fav)
    db.session.commit()
    return jsonify(code=200, message="取消收藏成功"), 200