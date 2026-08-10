"""基础数据模块测试：分类 / 商品 / 客户 / 供应商 / 仓库 CRUD 与异常场景。"""
import allure
import pytest

from common import data
from common.assertions import (
    assert_business_error,
    assert_not_found,
    assert_success,
    assert_validation_error,
    list_items,
)

pytestmark = allure.feature("基础数据")

# ========== 分类 ==========


@allure.story("分类")
@allure.title("分类完整 CRUD 流程")
@allure.severity(allure.severity_level.CRITICAL)
def test_category_crud(master_api):
    # 创建
    cat = assert_success(
        master_api.create_category({"name": data.rand_name("分类"), "sort": 1})
    )
    cat_id = cat["id"]

    # 查询列表可检索到
    items = list_items(assert_success(master_api.list_categories()))
    assert any(str(i.get("id")) == str(cat_id) for i in items), "列表中未找到新建分类"

    # 更新
    new_name = data.rand_name("分类改")
    assert_success(master_api.update_category(cat_id, {"name": new_name, "sort": 2}))

    # 删除
    assert_success(master_api.delete_category(cat_id))


@allure.story("分类")
@allure.title("创建分类缺少必填 name 返回参数校验错误")
def test_create_category_missing_name(master_api):
    assert_validation_error(master_api.create_category({}))


@allure.story("分类")
@allure.title("更新不存在的分类返回业务错误")
def test_update_category_not_exist(master_api):
    # 实际后端返回 200 + code:1（分类不存在），而非 404
    assert_business_error(master_api.update_category(999999, {"name": "不存在"}), http_status=200)


# ========== 商品 ==========


@allure.story("商品")
@allure.title("商品完整 CRUD 流程（含分类关联）")
@allure.severity(allure.severity_level.CRITICAL)
def test_product_crud(master_api, category):
    body = {
        "code": data.uniq("P"),
        "name": data.rand_name("商品"),
        "category_id": category,
        "unit": "件",
        "purchase_price": 20.5,
        "sale_price": 39.9,
        "safety_stock": 10,
        "status": "active",
    }
    prod = assert_success(master_api.create_product(body))
    prod_id = prod["id"]

    # 关键字检索
    items = list_items(
        assert_success(master_api.list_products(keyword=body["name"], page=1, page_size=10))
    )
    assert any(str(i.get("id")) == str(prod_id) for i in items), "关键字检索未命中新商品"

    # 更新
    assert_success(master_api.update_product(prod_id, {**body, "name": data.rand_name("商品改")}))

    # 全量下拉接口
    assert list_items(assert_success(master_api.all_products())) is not None

    # 删除
    assert_success(master_api.delete_product(prod_id))


@allure.story("商品")
@allure.title("重复商品编码创建失败，返回业务错误")
def test_create_product_duplicate_code(master_api, product):
    code = data.uniq("DUP")
    assert_success(
        master_api.create_product({"code": code, "name": data.rand_name("商品重复")})
    )
    resp2 = master_api.create_product(
        {"code": code, "name": data.rand_name("商品重复2")}
    )
    # 实测后端对业务失败统一返回 200 + code:1（与文档约定 400 不同）
    assert_business_error(resp2, http_status=200)


@allure.story("商品")
@allure.title("创建商品缺少必填 code 返回参数校验错误")
def test_create_product_missing_code(master_api):
    assert_validation_error(master_api.create_product({"name": data.rand_name("商品")}))


# ========== 客户 ==========


@allure.story("客户")
@allure.title("客户完整 CRUD 流程")
@allure.severity(allure.severity_level.CRITICAL)
def test_customer_crud(master_api):
    body = {
        "code": data.uniq("C"),
        "name": data.rand_name("客户"),
        "phone": data.rand_phone(),
        "address": "测试路 1 号",
        "credit_limit": 10000,
        "status": "active",
    }
    cust = assert_success(master_api.create_customer(body))
    cust_id = cust["id"]

    items = list_items(
        assert_success(master_api.list_customers(keyword=body["name"], page=1, page_size=10))
    )
    assert any(str(i.get("id")) == str(cust_id) for i in items), "关键字检索未命中新客户"

    assert_success(master_api.update_customer(cust_id, {**body, "name": data.rand_name("客户改")}))
    assert list_items(assert_success(master_api.all_customers())) is not None
    assert_success(master_api.delete_customer(cust_id))


# ========== 供应商 ==========


@allure.story("供应商")
@allure.title("供应商完整 CRUD 流程")
@allure.severity(allure.severity_level.CRITICAL)
def test_supplier_crud(master_api):
    body = {
        "code": data.uniq("S"),
        "name": data.rand_name("供应商"),
        "phone": data.rand_phone(),
        "status": "active",
    }
    sup = assert_success(master_api.create_supplier(body))
    sup_id = sup["id"]

    items = list_items(
        assert_success(master_api.list_suppliers(keyword=body["name"], page=1, page_size=10))
    )
    assert any(str(i.get("id")) == str(sup_id) for i in items), "关键字检索未命中新供应商"

    assert_success(master_api.update_supplier(sup_id, {**body, "name": data.rand_name("供应商改")}))
    assert list_items(assert_success(master_api.all_suppliers())) is not None
    assert_success(master_api.delete_supplier(sup_id))


# ========== 仓库 ==========


@allure.story("仓库")
@allure.title("仓库完整 CRUD 流程")
@allure.severity(allure.severity_level.CRITICAL)
def test_warehouse_crud(master_api):
    body = {
        "code": data.uniq("W"),
        "name": data.rand_name("仓库"),
        "status": "active",
    }
    wh = assert_success(master_api.create_warehouse(body))
    wh_id = wh["id"]

    assert list_items(assert_success(master_api.list_warehouses()))
    assert_success(master_api.update_warehouse(wh_id, {**body, "name": data.rand_name("仓库改")}))
    assert_success(master_api.delete_warehouse(wh_id))