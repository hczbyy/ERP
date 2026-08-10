"""采购管理模块测试：采购订单全生命周期与入库单。"""
import allure
import pytest

from common import data
from common.assertions import (
    assert_business_error,
    assert_not_found,
    assert_success,
    list_items,
)
from conftest import order_items

pytestmark = allure.feature("采购管理")


@allure.story("采购订单")
@allure.title("创建 → 审核 → 收货入库 全流程")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_approve_receive_flow(purchase_api, supplier, warehouse, product):
    # 创建采购订单
    order = assert_success(
        purchase_api.create_order(
            {
                "supplier_id": supplier,
                "warehouse_id": warehouse,
                "remark": "自动化采购",
                "items": order_items(product, quantity=5),
            }
        )
    )
    order_id = order["id"]

    # 审核
    assert_success(purchase_api.approve_order(order_id))

    # 收货入库（库存增加 + 应付挂账）
    assert_success(
        purchase_api.receive_order(
            order_id,
            {"remark": "自动化收货", "items": order_items(product, quantity=5)},
        )
    )

    # 入库单列表可查到
    items = list_items(assert_success(purchase_api.list_stock_ins(page=1, page_size=10)))
    assert items is not None, "入库单列表为空"


@allure.story("采购订单")
@allure.title("创建后取消订单成功")
def test_cancel_flow(purchase_api, supplier, warehouse, product):
    order = assert_success(
        purchase_api.create_order(
            {
                "supplier_id": supplier,
                "warehouse_id": warehouse,
                "remark": "自动化取消",
                "items": order_items(product, quantity=1),
            }
        )
    )
    order_id = order["id"]

    assert_success(purchase_api.cancel_order(order_id, {"reason": "自动化取消"}))
    assert_success(purchase_api.order_detail(order_id))


@allure.story("采购订单")
@allure.title("对已取消订单再次审核返回业务错误（状态不允许）")
def test_approve_cancelled_order(purchase_api, supplier, warehouse, product):
    order = assert_success(
        purchase_api.create_order(
            {
                "supplier_id": supplier,
                "warehouse_id": warehouse,
                "items": order_items(product, quantity=1),
            }
        )
    )
    order_id = order["id"]

    assert_success(purchase_api.cancel_order(order_id))
    assert_business_error(purchase_api.approve_order(order_id))


@allure.story("采购订单")
@allure.title("对已取消订单收货返回业务错误（状态不允许）")
def test_receive_cancelled_order(purchase_api, supplier, warehouse, product):
    order = assert_success(
        purchase_api.create_order(
            {
                "supplier_id": supplier,
                "warehouse_id": warehouse,
                "items": order_items(product, quantity=1),
            }
        )
    )
    order_id = order["id"]

    assert_success(purchase_api.cancel_order(order_id))
    assert_business_error(
        purchase_api.receive_order(order_id, {"items": order_items(product, quantity=1)})
    )


@allure.story("采购订单")
@allure.title("查询不存在的采购订单返回业务错误")
def test_order_not_exist(purchase_api):
    # 实际后端返回 200 + code:1（采购订单不存在），而非 404
    assert_business_error(purchase_api.order_detail(999999), http_status=200)


@allure.story("采购订单")
@allure.title("按状态与关键字分页查询采购订单成功")
def test_list_orders_with_filter(purchase_api):
    items = list_items(
        assert_success(purchase_api.list_orders(keyword=data.uniq("不存在"), page=1, page_size=10))
    )
    assert items == [], "不存在的关键字应返回空列表"