"""财务管理模块测试：应收 / 应付 / 收款 / 付款。

收款/付款创建依赖系统中未结清的应收/应付单（balance > 0）：
从列表选取，环境无数据时自动跳过（pytest.skip）。
"""
import allure
import pytest

from common.assertions import assert_business_error, assert_success, list_items

pytestmark = allure.feature("财务管理")


def _first_open(api_method, **params):
    """从列表响应中取第一条未结清（balance > 0）单据，无则返回 None。"""
    items = list_items(assert_success(api_method(**params)))
    for item in items:
        if float(item.get("balance") or 0) > 0:
            return item
    return None


def _half_balance(balance: float) -> float:
    """取余额一半作为收/付款金额，保留两位小数，避免精度问题。"""
    amount = round(balance / 2, 2)
    return amount if amount > 0 else balance


@allure.story("应收")
@allure.title("分页查询应收列表成功")
def test_receivables_list(finance_api):
    assert_success(finance_api.list_receivables(page=1, page_size=10))


@allure.story("应付")
@allure.title("分页查询应付列表成功")
def test_payables_list(finance_api):
    assert_success(finance_api.list_payables(page=1, page_size=10))


@allure.story("收款")
@allure.title("分页查询收款单列表成功")
def test_receipts_list(finance_api):
    assert_success(finance_api.list_receipts(page=1, page_size=10))


@allure.story("收款")
@allure.title("对未结清应收单创建收款成功")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_receipt(finance_api):
    receivable = _first_open(finance_api.list_receivables, page=1, page_size=20)
    if not receivable:
        pytest.skip("环境无未结清应收单，跳过收款创建用例")

    assert_success(
        finance_api.create_receipt(
            {
                "receivable_id": receivable["id"],
                "amount": _half_balance(receivable["balance"]),
                "pay_method": "cash",
                "remark": "自动化收款",
            }
        )
    )


@allure.story("收款")
@allure.title("收款金额超过应收余额返回业务错误")
def test_create_receipt_over_amount(finance_api):
    receivable = _first_open(finance_api.list_receivables, page=1, page_size=20)
    if not receivable:
        pytest.skip("环境无未结清应收单，跳过超收用例")

    assert_business_error(
        finance_api.create_receipt(
            {
                "receivable_id": receivable["id"],
                "amount": receivable["balance"] + 100,
                "pay_method": "cash",
            }
        ),
        http_status=400,
    )


@allure.story("付款")
@allure.title("分页查询付款单列表成功")
def test_payments_list(finance_api):
    assert_success(finance_api.list_payments(page=1, page_size=10))


@allure.story("付款")
@allure.title("对未结清应付单创建付款成功")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_payment(finance_api):
    payable = _first_open(finance_api.list_payables, page=1, page_size=20)
    if not payable:
        pytest.skip("环境无未结清应付单，跳过付款创建用例")

    assert_success(
        finance_api.create_payment(
            {
                "payable_id": payable["id"],
                "amount": _half_balance(payable["balance"]),
                "pay_method": "cash",
                "remark": "自动化付款",
            }
        )
    )