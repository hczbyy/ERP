"""Flask 扩展集中初始化，避免循环导入"""

from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

db = SQLAlchemy()
cors = CORS()