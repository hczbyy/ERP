"""认证路由：注册 / 登录 / 获取用户信息

优化点：JWT 无状态 Token → 跨 Gunicorn 多 Worker 兼容
"""

from flask import Blueprint, request, jsonify
from app.models import User
from app.extensions import db
from app.utils import hash_password, verify_password, generate_token, verify_token

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True)
    if not data:
        return jsonify(code=400, message="请求体不能为空"), 400

    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    email = (data.get("email") or "").strip()

    if not username or len(username) < 2:
        return jsonify(code=400, message="用户名至少2个字符"), 400
    if not password or len(password) < 4:
        return jsonify(code=400, message="密码至少4个字符"), 400

    if User.query.filter_by(username=username).first():
        return jsonify(code=409, message="用户名已存在"), 409
    if email and User.query.filter_by(email=email).first():
        return jsonify(code=409, message="邮箱已注册"), 409

    user = User(
        username=username,
        password_hash=hash_password(password),
        email=email or None,
    )
    db.session.add(user)
    db.session.commit()

    token = generate_token(user.id)
    return jsonify(code=200, message="注册成功", data={
        "user": user.to_dict(),
        "token": token,
    }), 200


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    if not data:
        return jsonify(code=400, message="请求体不能为空"), 400

    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    user = User.query.filter_by(username=username).first()
    if not user or not verify_password(password, user.password_hash):
        return jsonify(code=401, message="用户名或密码错误"), 401

    token = generate_token(user.id)
    return jsonify(code=200, message="登录成功", data={
        "user": user.to_dict(),
        "token": token,
    }), 200


@auth_bp.route("/me", methods=["GET"])
def get_me():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else auth_header
    user_id = verify_token(token)
    if not user_id:
        return jsonify(code=401, message="未登录或 Token 已过期"), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify(code=404, message="用户不存在"), 404

    return jsonify(code=200, data=user.to_dict()), 200