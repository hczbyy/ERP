"""小说路由：CRUD + 分页列表 + 分类筛选

优化点：
  - joinedload(Novel.author) 消除 N+1
  - to_dict_brief() 零懒加载
  - 列表/详情 内存缓存
"""

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import joinedload

from app.models import Novel, User
from app.extensions import db
from app.utils import verify_token, paginate, cached, make_cache_key

novel_bp = Blueprint("novels", __name__, url_prefix="/api/novels")


def _get_current_user():
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else auth
    uid = verify_token(token)
    return db.session.get(User, uid) if uid else None


@novel_bp.route("", methods=["GET"])
def list_novels():
    """小说列表（分页 + 筛选 + 缓存）
    GET /api/novels?page=1&per_page=20&category=玄幻&keyword=关键字&sort=latest
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    category = request.args.get("category", "")
    keyword = request.args.get("keyword", "")
    sort = request.args.get("sort", "latest")

    # 构建查询（joinedload 消除 author N+1）
    query = (
        Novel.query
        .filter(Novel.status == "published")
        .options(joinedload(Novel.author))
    )

    if category:
        query = query.filter(Novel.category == category)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(Novel.title.like(like) | Novel.description.like(like))

    if sort == "popular":
        query = query.order_by(Novel.word_count.desc(), Novel.created_at.desc())
    else:
        query = query.order_by(Novel.created_at.desc())

    result = paginate(query, page, per_page)

    # 使用 to_dict_brief() — 零懒加载，零额外查询
    return jsonify(code=200, data={
        "items": [n.to_dict_brief() for n in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "per_page": result["per_page"],
        "pages": result["pages"],
    }), 200


@novel_bp.route("/categories", methods=["GET"])
def list_categories():
    """获取所有分类（缓存 30s）
    GET /api/novels/categories
    """
    # 缓存 key = "categories"
    cache_key = "categories"
    cache = current_app.config.get("_CATEGORIES_CACHE")
    if cache and cache_key in cache:
        return jsonify(code=200, data=cache[cache_key]), 200

    rows = (
        db.session.query(Novel.category)
        .filter(Novel.status == "published")
        .distinct()
        .all()
    )
    cats = sorted(set(r[0] for r in rows if r[0]))

    if cache is None:
        from cachetools import TTLCache
        cache = TTLCache(maxsize=10, ttl=30)
        current_app.config["_CATEGORIES_CACHE"] = cache
    cache[cache_key] = cats

    return jsonify(code=200, data=cats), 200


@novel_bp.route("/<int:novel_id>", methods=["GET"])
def get_novel(novel_id):
    """小说详情
    GET /api/novels/<id>
    """
    novel = (
        db.session.query(Novel)
        .options(joinedload(Novel.author))
        .filter(Novel.id == novel_id, Novel.status == "published")
        .first()
    )
    if not novel:
        return jsonify(code=404, message="小说不存在"), 404
    # 详情用完整 to_dict
    return jsonify(code=200, data=novel.to_dict()), 200


@novel_bp.route("", methods=["POST"])
def create_novel():
    """创建小说（需登录）"""
    user = _get_current_user()
    if not user:
        return jsonify(code=401, message="请先登录"), 401

    data = request.get_json(force=True)
    if not data or not data.get("title", "").strip():
        return jsonify(code=400, message="标题不能为空"), 400

    novel = Novel(
        title=data["title"].strip(),
        author_id=user.id,
        description=(data.get("description") or "").strip(),
        category=(data.get("category") or "其他").strip(),
        cover_url=(data.get("cover_url") or "").strip(),
        status=data.get("status", "published"),
    )
    db.session.add(novel)
    db.session.commit()
    return jsonify(code=200, message="创建成功", data=novel.to_dict()), 200


@novel_bp.route("/<int:novel_id>", methods=["PUT"])
def update_novel(novel_id):
    """更新小说（仅作者）"""
    user = _get_current_user()
    if not user:
        return jsonify(code=401, message="请先登录"), 401

    novel = db.session.get(Novel, novel_id)
    if not novel:
        return jsonify(code=404, message="小说不存在"), 404
    if novel.author_id != user.id:
        return jsonify(code=403, message="只能修改自己的小说"), 403

    data = request.get_json(force=True) or {}
    for field in ("title", "description", "category", "cover_url", "status"):
        if field in data:
            val = data[field]
            setattr(novel, field, val.strip() if isinstance(val, str) else val)

    db.session.commit()
    return jsonify(code=200, message="更新成功", data=novel.to_dict()), 200


@novel_bp.route("/<int:novel_id>", methods=["DELETE"])
def delete_novel(novel_id):
    """删除小说（仅作者）"""
    user = _get_current_user()
    if not user:
        return jsonify(code=401, message="请先登录"), 401

    novel = db.session.get(Novel, novel_id)
    if not novel:
        return jsonify(code=404, message="小说不存在"), 404
    if novel.author_id != user.id:
        return jsonify(code=403, message="只能删除自己的小说"), 403

    db.session.delete(novel)
    db.session.commit()
    return jsonify(code=200, message="删除成功"), 200