"""仪表盘与健康检查冒烟测试。"""
import allure
import pytest

from common.assertions import assert_success

pytestmark = allure.feature("仪表盘")


@allure.story("健康检查")
@allure.title("健康检查接口返回成功")
@allure.severity(allure.severity_level.CRITICAL)
def test_health(dashboard_api):
    # health 不走统一响应格式，返回 {"status": "ok", "app": ..., "version": ...}
    resp = dashboard_api.health()
    assert resp.status_code == 200, f"health 期望 200，实际 {resp.status_code}"
    body = resp.json()
    assert body.get("status") == "ok", f"health 状态异常: {body}"


@allure.story("汇总")
@allure.title("获取仪表盘汇总数据成功")
def test_summary(dashboard_api):
    data_ = assert_success(dashboard_api.summary())
    assert data_ is not None, "summary 返回空数据"


@allure.story("销售趋势")
@allure.title("默认参数获取销售趋势成功")
def test_sales_trend_default(dashboard_api):
    assert_success(dashboard_api.sales_trend())


@allure.story("销售趋势")
@allure.title("指定 days=7 获取销售趋势成功")
def test_sales_trend_with_days(dashboard_api):
    assert_success(dashboard_api.sales_trend(days=7))


@allure.story("TOP 商品")
@allure.title("指定 limit=5 获取销量 TOP 商品成功")
def test_top_products(dashboard_api):
    assert_success(dashboard_api.top_products(limit=5))


@allure.story("库存预警")
@allure.title("获取库存预警列表成功")
def test_low_stocks(dashboard_api):
    assert_success(dashboard_api.low_stocks(limit=5))


@allure.story("最近订单")
@allure.title("获取最近销售订单成功")
def test_recent_orders(dashboard_api):
    assert_success(dashboard_api.recent_orders(limit=5))