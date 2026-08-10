"""章节路由（已优化：无 N+1 风险）"""

from flask import Blueprint, request, jsonify
from sqlalchemy.orm import joinedload

from app.models import Novel, Chapter, User
from app.extensions import db
from app.utils import verify_token

chapter_bp = Blueprint("chapters", __name__, url_prefix="/api")


def _get_current_user():
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else auth
    uid = verify_token(token)
    return db.session.get(User, uid) if uid else None


@chapter_bp.route("/novels/<int:novel_id>/chapters", methods=["GET"])
def list_chapters(novel_id):
    """章节列表（不含正文）"""
    novel = db.session.get(Novel, novel_id)
    if not novel:
        return jsonify(code=404, message="小说不存在"), 404

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    query = Chapter.query.filter_by(novel_id=novel_id).order_by(Chapter.chapter_number)
    total = query.count()
    pages = (total + per_page - 1) // per_page
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify(code=200, data={
        "items": [c.to_dict(brief=True) for c in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }), 200


@chapter_bp.route("/chapters/<int:chapter_id>", methods=["GET"])
def get_chapter(chapter_id):
    """章节详情（含正文）"""
    chapter = db.session.get(Chapter, chapter_id)
    if not chapter:
        return jsonify(code=404, message="章节不存在"), 404
    return jsonify(code=200, data=chapter.to_dict()), 200


@chapter_bp.route("/novels/<int:novel_id>/chapters", methods=["POST"])
def create_chapter(novel_id):
    """创建章节"""
    user = _get_current_user()
    if not user:
        return jsonify(code=401, message="请先登录"), 401

    novel = db.session.get(Novel, novel_id)
    if not novel:
        return jsonify(code=404, message="小说不存在"), 404
    if novel.author_id != user.id:
        return jsonify(code=403, message="只能给自己的小说添加章节"), 403

    data = request.get_json(force=True)
    if not data or not data.get("title", "").strip() or not data.get("content", "").strip():
        return jsonify(code=400, message="标题和内容不能为空"), 400

    chapter_number = data.get("chapter_number", 1)
    if chapter_number is None or chapter_number <= 0:
        last = Chapter.query.filter_by(novel_id=novel_id).order_by(Chapter.chapter_number.desc()).first()
        chapter_number = (last.chapter_number + 1) if last else 1

    exists = Chapter.query.filter_by(novel_id=novel_id, chapter_number=chapter_number).first()
    if exists:
        return jsonify(code=409, message=f"第{chapter_number}章已存在"), 409

    content = data["content"]
    word_count = len(content.replace(" ", "").replace("\n", ""))

    chapter = Chapter(
        novel_id=novel_id,
        title=data["title"].strip(),
        content=content,
        chapter_number=chapter_number,
        word_count=word_count,
    )
    db.session.add(chapter)
    novel.word_count = (novel.word_count or 0) + word_count
    db.session.commit()

    return jsonify(code=200, message="创建成功", data=chapter.to_dict()), 200