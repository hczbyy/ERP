"""路由注册 —— 复原版

改动说明：
  - 移除 _preloaded_app 全局缓存（原为 Gunicorn 方案B 服务）
  - 移除 get_preloaded_app() 辅助函数
  - 恢复干净工厂函数 create_app()
  - 连接池清理设计已改为标准方案：
    · 方案A（preload_app=False）：根源杜绝 fork 复制，推荐
    · 方案B（preload_app=True）：post_fork 中通过 db.apps 遍历所有已注册引擎
      并 dispose()，无需自定义缓存变量
"""

from flask import Flask
from app.extensions import db, cors
from app.config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化扩展
    db.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # 注册蓝图
    from app.routes.auth import auth_bp
    from app.routes.novels import novel_bp
    from app.routes.chapters import chapter_bp
    from app.routes.comments import comment_bp
    from app.routes.favorites import favorite_bp
    from app.routes.stats import stats_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(novel_bp)
    app.register_blueprint(chapter_bp)
    app.register_blueprint(comment_bp)
    app.register_blueprint(favorite_bp)
    app.register_blueprint(stats_bp)

    # 全局健康检查
    @app.route("/api/health")
    def health():
        return {"code": 200, "message": "OK", "data": {"status": "running"}}

    # 全局异常处理
    @app.errorhandler(404)
    def not_found(e):
        return {"code": 404, "message": "接口不存在"}, 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return {"code": 405, "message": "请求方法不允许"}, 405

    @app.errorhandler(500)
    def server_error(e):
        return {"code": 500, "message": "服务器内部错误"}, 500

    return app