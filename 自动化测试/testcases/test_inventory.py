"""库存管理模块测试：库存查询 / 流水 / 盘点流程 / 调拨流程。"""
import allure
import pytest

from common import data
from common.assertions import (
    assert_business_error,
    assert_success,
    list_items,
)
from conftest import order_items

pytestmark = allure.feature("库存管理")


@allure.story("库存查询")
@allure.title("分页查询库存列表成功")
def test_stocks_list(inventory_api, warehouse):
    data_ = assert_success(inventory_api.list_stocks(page=1, page_size=10))
    assert data_ is not None


@allure.story("库存查询")
@allure.title("仅查询低库存商品成功")
def test_stocks_low_stock_only(inventory_api):
    assert_success(inventory_api.list_stocks(low_stock_only=True))


@allure.story("库存流水")
@allure.title("查询库存流水成功")
def test_logs_list(inventory_api):
    assert_success(inventory_api.list_logs(page=1, page_size=10))


@allure.story("盘点")
@allure.title("盘点全流程：创建 → 明细 → 录入盘点结果 → 提交")
@allure.severity(allure.severity_level.CRITICAL)
def test_check_flow(inventory_api, warehouse, product):
    # 创建盘点单（盘指定仓库下的商品）
    check = assert_success(
        inventory_api.create_check(
            {"warehouse_id": warehouse, "remark": "自动化盘点", "product_ids": [product]}
        )
    )
    check_id = check["id"]

    # 盘点单详情
    detail = assert_success(inventory_api.check_detail(check_id))
    assert detail, "盘点单详情为空"

    # 录入盘点结果：items 结构假设为
    # {"product_id": 商品ID, "book_qty": 账面数量, "actual_qty": 实盘数量}，如与实际不符请调整
    assert_success(
        inventory_api.update_check(
            check_id,
            {"items": [{"product_id": product, "book_qty": 10, "actual_qty": 12}]},
        )
    )

    # 提交盘点（盘盈入/盘亏出）
    assert_success(inventory_api.done_check(check_id))


@allure.story("盘点")
@allure.title("查询不存在的盘点单返回业务错误")
def test_check_detail_not_exist(inventory_api):
    # 实际后端返回 200 + code:1（盘点单不存在），而非 404
    assert_business_error(inventory_api.check_detail(999999), http_status=200)


@allure.story("调拨")
@allure.title("创建库存调拨并查询列表成功")
@allure.severity(allure.severity_level.CRITICAL)
def test_transfer_flow(inventory_api, master_api, purchase_api, supplier, warehouse, product):
    # 调拨要求商品在源仓库有库存：先走采购收货给商品入库，再调拨
    order = assert_success(
        purchase_api.create_order(
            {
                "supplier_id": supplier,
                "warehouse_id": warehouse,
                "remark": "调拨前置入库",
                "items": order_items(product, quantity=5),
            }
        )
    )
    assert_success(purchase_api.approve_order(order["id"]))
    assert_success(
        purchase_api.receive_order(order["id"], {"items": order_items(product, quantity=5)})
    )

    # 调拨需要两个仓库，动态创建第二个仓库
    wh2 = assert_success(
        master_api.create_warehouse({"code": data.uniq("W2"), "name": data.rand_name("仓库2")})
    )
    try:
        transfer = assert_success(
            inventory_api.create_transfer(
                {
                    "from_warehouse_id": warehouse,
                    "to_warehouse_id": wh2["id"],
                    "remark": "自动化调拨",
                    "items": order_items(product, quantity=1),
                }
            )
        )
        assert transfer.get("id"), f"调拨单创建响应缺少 id: {transfer}"

        # 调拨单列表
        assert_success(inventory_api.list_transfers(page=1, page_size=10))
    finally:
        master_api.delete_warehouse(wh2["id"])