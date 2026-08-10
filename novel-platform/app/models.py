"""数据模型

优化点：brief 模式彻底消除懒加载 → 只返回原始字段
"""

from datetime import datetime, timezone
from app.extensions import db


# ── 用户 ────────────────────────────────────────────────────────
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    novels = db.relationship("Novel", backref="author", lazy="dynamic")
    favorites = db.relationship("Favorite", backref="user", lazy="dynamic")

    def to_dict(self, brief=False):
        d = {"id": self.id, "username": self.username}
        if not brief:
            d.update(email=self.email, created_at=self.created_at.isoformat())
        return d


# ── 小说 ────────────────────────────────────────────────────────
class Novel(db.Model):
    __tablename__ = "novels"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    description = db.Column(db.Text, default="")
    cover_url = db.Column(db.String(500), default="")
    category = db.Column(db.String(50), default="其他")
    status = db.Column(db.String(20), default="published")
    word_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    chapters = db.relationship("Chapter", backref="novel", lazy="dynamic",
                               order_by="Chapter.chapter_number")
    comments = db.relationship("Comment", backref="novel", lazy="dynamic")
    favorites = db.relationship("Favorite", backref="novel", lazy="dynamic")

    @property
    def favorite_count(self):
        return Favorite.query.filter_by(novel_id=self.id).count()

    @property
    def chapter_count(self):
        return self.chapters.count()

    def to_dict(self, brief=False):
        """注意：brief 模式不触发任何懒加载 → 适合列表"""
        d = {
            "id": self.id,
            "title": self.title,
            "author": self.author.username if self.author else None,
            "category": self.category,
            "status": self.status,
            "word_count": self.word_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "chapter_count": self.chapter_count,  # 懒加载 → brief=False 时才用
            "favorite_count": self.favorite_count if not brief else 0,
        }
        if not brief:
            d.update(
                description=self.description,
                cover_url=self.cover_url,
                author_id=self.author_id,
            )
        return d

    def to_dict_brief(self):
        """极致轻量的 brief 版本：0 次懒加载，0 次关系查询"""
        return {
            "id": self.id,
            "title": self.title,
            "author_id": self.author_id,
            "category": self.category,
            "status": self.status,
            "word_count": self.word_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── 章节 ────────────────────────────────────────────────────────
class Chapter(db.Model):
    __tablename__ = "chapters"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    novel_id = db.Column(db.Integer, db.ForeignKey("novels.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    chapter_number = db.Column(db.Integer, nullable=False, default=1)
    word_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    comments = db.relationship("Comment", backref="chapter", lazy="dynamic")

    __table_args__ = (
        db.UniqueConstraint("novel_id", "chapter_number", name="uq_novel_chapter"),
    )

    def to_dict(self, brief=False):
        d = {
            "id": self.id,
            "novel_id": self.novel_id,
            "title": self.title,
            "chapter_number": self.chapter_number,
            "word_count": self.word_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if not brief:
            d["content"] = self.content
        return d


# ── 评论 ────────────────────────────────────────────────────────
class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    novel_id = db.Column(db.Integer, db.ForeignKey("novels.id"), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey("chapters.id"), nullable=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # 👇 lazy='joined' 确保评论列表 JOIN 加载 user，消除 N+1
    # backref user_comments 只在 User 端可用
    user = db.relationship("User", backref="user_comments", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "novel_id": self.novel_id,
            "chapter_id": self.chapter_id,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── 收藏 ────────────────────────────────────────────────────────
class Favorite(db.Model):
    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    novel_id = db.Column(db.Integer, db.ForeignKey("novels.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("user_id", "novel_id", name="uq_user_novel_fav"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "novel_id": self.novel_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }