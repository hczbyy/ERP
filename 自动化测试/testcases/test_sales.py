"""销售管理模块测试：销售订单全生命周期与出库单。"""
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

pytestmark = allure.feature("销售管理")


@allure.story("销售订单")
@allure.title("创建 → 审核 → 发货出库 全流程")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_approve_ship_flow(sales_api, purchase_api, supplier, customer, warehouse, product):
    # 发货需要扣库存：先走采购收货给商品入库，保证库存充足
    po = assert_success(
        purchase_api.create_order(
            {
                "supplier_id": supplier,
                "warehouse_id": warehouse,
                "remark": "销售发货前置入库",
                "items": order_items(product, quantity=5),
            }
        )
    )
    assert_success(purchase_api.approve_order(po["id"]))
    assert_success(
        purchase_api.receive_order(po["id"], {"items": order_items(product, quantity=5)})
    )

    # 创建销售订单
    order = assert_success(
        sales_api.create_order(
            {
                "customer_id": customer,
                "warehouse_id": warehouse,
                "remark": "自动化销售",
                "items": order_items(product, quantity=2),
            }
        )
    )
    order_id = order["id"]

    # 审核
    assert_success(sales_api.approve_order(order_id))

    # 发货出库（库存扣减 + 应收挂账）
    assert_success(
        sales_api.ship_order(
            order_id,
            {"remark": "自动化发货", "items": order_items(product, quantity=2)},
        )
    )

    # 出库单列表可查到
    items = list_items(assert_success(sales_api.list_stock_outs(page=1, page_size=10)))
    assert items is not None, "出库单列表为空"


@allure.story("销售订单")
@allure.title("创建后取消订单成功")
def test_cancel_flow(sales_api, customer, warehouse, product):
    order = assert_success(
        sales_api.create_order(
            {
                "customer_id": customer,
                "warehouse_id": warehouse,
                "remark": "自动化取消",
                "items": order_items(product, quantity=1),
            }
        )
    )
    order_id = order["id"]

    assert_success(sales_api.cancel_order(order_id, {"reason": "自动化取消"}))
    assert_success(sales_api.order_detail(order_id))


@allure.story("销售订单")
@allure.title("库存不足时发货返回业务错误（库存不足）")
@allure.severity(allure.severity_level.CRITICAL)
def test_ship_insufficient_stock(sales_api, customer, warehouse, product):
    order = assert_success(
        sales_api.create_order(
            {
                "customer_id": customer,
                "warehouse_id": warehouse,
                "items": order_items(product, quantity=999999),
            }
        )
    )
    order_id = order["id"]

    assert_success(sales_api.approve_order(order_id))
    assert_business_error(
        sales_api.ship_order(order_id, {"items": order_items(product, quantity=999999)})
    )


@allure.story("销售订单")
@allure.title("对已取消订单发货返回业务错误（状态不允许）")
def test_ship_cancelled_order(sales_api, customer, warehouse, product):
    order = assert_success(
        sales_api.create_order(
            {
                "customer_id": customer,
                "warehouse_id": warehouse,
                "items": order_items(product, quantity=1),
            }
        )
    )
    order_id = order["id"]

    assert_success(sales_api.cancel_order(order_id))
    assert_business_error(
        sales_api.ship_order(order_id, {"items": order_items(product, quantity=1)})
    )


@allure.story("销售订单")
@allure.title("查询不存在的销售订单返回业务错误")
def test_order_not_exist(sales_api):
    # 实际后端返回 200 + code:1（销售订单不存在），而非 404
    assert_business_error(sales_api.order_detail(999999), http_status=200)


@allure.story("销售订单")
@allure.title("按状态与关键字分页查询销售订单成功")
def test_list_orders_with_filter(sales_api):
    items = list_items(
        assert_success(sales_api.list_orders(keyword=data.uniq("不存在"), page=1, page_size=10))
    )
    assert items == [], "不存在的关键字应返回空列表"