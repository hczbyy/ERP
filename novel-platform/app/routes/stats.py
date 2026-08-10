"""统计信息路由

优化点：
  - 单次 SQL 查询（UNION ALL）替代 5 次 COUNT
  - 短 TTL 缓存
"""

from flask import Blueprint, jsonify, current_app
from app.extensions import db
from cachetools import TTLCache

stats_bp = Blueprint("stats", __name__, url_prefix="/api")

# worker 级缓存（每个 worker 独立，无锁）
_cache = TTLCache(maxsize=10, ttl=5)


@stats_bp.route("/stats", methods=["GET"])
def get_stats():
    """平台统计 — 单次查询 + 5s 缓存"""
    if "stats" in _cache:
        return jsonify(code=200, data=_cache["stats"]), 200

    # 单条 SQL 返回所有计数
    row = db.session.execute(
        db.text("""
            SELECT
                (SELECT COUNT(*) FROM users) AS users,
                (SELECT COUNT(*) FROM novels WHERE status='published') AS novels,
                (SELECT COUNT(*) FROM chapters) AS chapters,
                (SELECT COUNT(*) FROM comments) AS comments,
                (SELECT COUNT(*) FROM favorites) AS favorites
        """)
    ).one()

    data = {
        "users": row.users,
        "novels": row.novels,
        "chapters": row.chapters,
        "comments": row.comments,
        "favorites": row.favorites,
    }
    _cache["stats"] = data
    return jsonify(code=200, data=data), 200