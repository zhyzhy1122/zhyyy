import json
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR/"配置文件"/("config.json")

class ServiceItem(BaseModel):
    name:str
    qty:int = 1

def load_price_map():
    "读取并返回服务的价目表（dict）"
    #docstring:读取配置里面的价目表“：输入无，返回dict
    with open(CONFIG_PATH,"r",encoding="utf-8")as f:
        cfg= json.load(f)
    price_map = cfg.get("price_map",{})
    return price_map
@tool
def calculate_price(service_items:list[ServiceItem])->str:
    """根据客户购买的服务项目清单计算总价并且返回报价文本。
    服务名请使用店内规范名称，例如：猫咪普通洗护，猫咪深度洗护，药浴，剪指甲，体内驱虫"""
    price_map = load_price_map()

    total = 0.0
    parts = []
    for item in service_items:
        name = item.name
        name = name.strip()
        qty = item.qty
        unit = price_map.get(name)

        if unit is None:
            parts.append(f"未找到服务{(name)}")
            continue

        subtotal = float(unit)*int(qty)

        total+= subtotal
        parts.append(f"{name} {unit}*{qty} = {subtotal:g}元")


    if parts:
        summary = ";".join(parts)
        summary += f":总计{total:g}元"
        return summary

    return "未收到有效服务项"

if __name__ == "__main__":
    # 自测：用 .invoke() 调用工具，参数传字典（工具会自动转成 ServiceItem）
    print(calculate_price.invoke({
        "service_items": [
            {"name": "猫咪普通洗护", "qty": 2},
            {"name": "剪指甲", "qty": 0},
            {"name": "不存在的服务", "qty": 1},
        ]
    }))
