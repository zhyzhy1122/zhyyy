"""价格计算工具的测试（纯本地逻辑，不联网）。"""
import json

import pytest

from services import price_tool


@pytest.fixture
def price_config(monkeypatch, tmp_path):
    """把 CONFIG_PATH 指向临时配置文件，避免依赖开发者本地的 config.json。"""

    def _write(mapping):
        path = tmp_path / "config.json"
        path.write_text(
            json.dumps({"price_map": mapping}, ensure_ascii=False), encoding="utf-8"
        )
        monkeypatch.setattr(price_tool, "CONFIG_PATH", path)
        return path

    return _write


def test_load_price_map_reads_configured_mapping(price_config):
    price_config({"药浴": 45, "剪指甲": 15})
    assert price_tool.load_price_map() == {"药浴": 45, "剪指甲": 15}


def test_missing_price_map_returns_empty_dict(price_config):
    price_config({})
    assert price_tool.load_price_map() == {}


def test_calculate_price_totals_multiple_items(price_config):
    price_config({"药浴": 45, "剪指甲": 15})

    result = price_tool.calculate_price.invoke(
        {"service_items": [{"name": "药浴", "qty": 2}, {"name": "剪指甲", "qty": 1}]}
    )

    assert "总计105元" in result
    assert "药浴 45*2 = 90元" in result


def test_calculate_price_reports_unknown_service(price_config):
    price_config({"药浴": 45})

    result = price_tool.calculate_price.invoke(
        {"service_items": [{"name": "不存在的服务", "qty": 1}]}
    )

    assert "未找到服务不存在的服务" in result


def test_calculate_price_ignores_surrounding_whitespace(price_config):
    price_config({"药浴": 45})

    result = price_tool.calculate_price.invoke(
        {"service_items": [{"name": "  药浴  ", "qty": 1}]}
    )

    assert "总计45元" in result


def test_calculate_price_with_empty_items(price_config):
    price_config({"药浴": 45})
    assert price_tool.calculate_price.invoke({"service_items": []}) == "未收到有效服务项"
