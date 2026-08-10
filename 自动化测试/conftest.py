"""pytest 全局夹具：登录 token 管理、各模块 API 实例、依赖数据自动创建与清理。

依赖数据（分类/商品/客户/供应商/仓库/部门）由 fixture 动态创建，
用例结束后自动删除，保证用例可独立重复执行、不污染环境。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import config, data  # noqa: E402
from common.assertions import assert_success  # noqa: E402
from common.client import RequestClient  # noqa: E402
from api.auth_api import AuthApi  # noqa: E402
from api.dashboard_api import DashboardApi  # noqa: E402
from api.finance_api import FinanceApi  # noqa: E402
from api.inventory_api import InventoryApi  # noqa: E402
from api.master_api import MasterApi  # noqa: E402
from api.purchase_api import PurchaseApi  # noqa: E402
from api.sales_api import SalesApi  # noqa: E402
from api.system_api import SystemApi  # noqa: E402

# ---------- 客户端与 API 实例 ----------


@pytest.fixture(scope="session")
def client():
    """全局唯一登录客户端，token 由 RequestClient 自动管理。"""
    c = RequestClient()
    c.login()
    return c


@pytest.fixture(scope="session")
def fresh_client():
    """未登录客户端，用于 401/鉴权类用例。"""
    return RequestClient()


@pytest.fixture(scope="session")
def auth_api(client):
    return AuthApi(client)


@pytest.fixture(scope="session")
def dashboard_api(client):
    return DashboardApi(client)


@pytest.fixture(scope="session")
def master_api(client):
    return MasterApi(client)


@pytest.fixture(scope="session")
def inventory_api(client):
    return InventoryApi(client)


@pytest.fixture(scope="session")
def system_api(client):
    return SystemApi(client)


@pytest.fixture(scope="session")
def finance_api(client):
    return FinanceApi(client)


@pytest.fixture(scope="session")
def purchase_api(client):
    return PurchaseApi(client)


@pytest.fixture(scope="session")
def sales_api(client):
    return SalesApi(client)


# ---------- 依赖数据：创建 + 自动清理 ----------

def _create_and_cleanup(create_fn, create_body: dict, delete_fn, entity: str):
    """通用创建夹具：创建成功返回 id，用例结束后尝试删除。"""
    obj = assert_success(create_fn(create_body))
    obj_id = obj.get("id")
    assert obj_id, f"{entity} 创建响应缺少 id: {obj}"
    yield obj_id
    try:
        assert_success(delete_fn(obj_id))
    except AssertionError as e:
        # 删除失败不阻断后续用例（可能被业务引用），记录即可
        import logging
        logging.getLogger("erp").warning("清理 %s(id=%s) 失败: %s", entity, obj_id, e)


@pytest.fixture()
def category(master_api):
    """创建一条分类并自动删除。"""
    gen = _create_and_cleanup(
        master_api.create_category,
        {"name": data.rand_name("分类")},
        master_api.delete_category,
        "分类",
    )
    yield from gen


@pytest.fixture()
def product(master_api, category):
    """创建一条商品（依赖分类）并自动删除。"""
    gen = _create_and_cleanup(
        master_api.create_product,
        {
            "code": data.uniq("P"),
            "name": data.rand_name("商品"),
            "category_id": category,
            "purchase_price": data.rand_price(5, 50),
            "sale_price": data.rand_price(50, 500),
            "safety_stock": 5,
            "status": "active",
        },
        master_api.delete_product,
        "商品",
    )
    yield from gen


@pytest.fixture()
def customer(master_api):
    """创建一条客户并自动删除。"""
    gen = _create_and_cleanup(
        master_api.create_customer,
        {
            "code": data.uniq("C"),
            "name": data.rand_name("客户"),
            "phone": data.rand_phone(),
            "status": "active",
        },
        master_api.delete_customer,
        "客户",
    )
    yield from gen


@pytest.fixture()
def supplier(master_api):
    """创建一个供应商并自动删除。"""
    gen = _create_and_cleanup(
        master_api.create_supplier,
        {
            "code": data.uniq("S"),
            "name": data.rand_name("供应商"),
            "phone": data.rand_phone(),
            "status": "active",
        },
        master_api.delete_supplier,
        "供应商",
    )
    yield from gen


@pytest.fixture()
def warehouse(master_api):
    """创建一个仓库并自动删除。"""
    gen = _create_and_cleanup(
        master_api.create_warehouse,
        {
            "code": data.uniq("W"),
            "name": data.rand_name("仓库"),
            "status": "active",
        },
        master_api.delete_warehouse,
        "仓库",
    )
    yield from gen


@pytest.fixture()
def department(system_api):
    """创建一个部门并自动删除。"""
    gen = _create_and_cleanup(
        system_api.create_department,
        {
            "code": data.uniq("DEPT"),
            "name": data.rand_name("部门"),
        },
        system_api.delete_department,
        "部门",
    )
    yield from gen


# ---------- 订单明细数据 ----------

def order_items(product_id: int, quantity: int = 2, price: float | None = None):
    """构造订单/调拨明细。实测后端 items 元素结构为：
    {"product_id": 商品ID, "qty": 数量, "price": 单价}
    """
    return [{"product_id": product_id, "qty": quantity, "price": price or data.rand_price(10, 100)}]


@pytest.fixture()
def auth_config():
    """返回当前登录账号密码，供改密用例恢复使用。"""
    return {"username": config.ADMIN_USERNAME, "password": config.ADMIN_PASSWORD}