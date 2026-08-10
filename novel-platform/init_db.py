"""数据库初始化脚本
运行方式：python init_db.py
功能：在 app 数据库中创建所有表
"""

from app import create_app
from app.extensions import db
from app.models import User, Novel, Chapter, Comment, Favorite

app = create_app()

with app.app_context():
    print("[INFO] 正在创建数据库表...")
    db.create_all()
    print("[INFO] 所有表创建完成！")
    print("[INFO] 已创建的表：")
    for table in db.metadata.sorted_tables:
        print(f"  - {table.name}")