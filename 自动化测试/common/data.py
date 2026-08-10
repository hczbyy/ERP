"""测试数据工厂：生成唯一编码/名称/随机数值，避免用例间数据冲突。"""
import random
import time


def uniq(prefix: str) -> str:
    """生成唯一标识，如 CAT_173412345678_42。

    总长度控制在 20 字符内（后端 code 字段限长 20），
    时间戳取毫秒值保证同秒并发也不重复。
    """
    ts = int(time.time() * 1000) % 100_000_000  # 8 位毫秒时间戳
    return f"{prefix}_{ts:08d}_{random.randint(10, 99)}"


def rand_name(prefix: str = "测试") -> str:
    return f"{prefix}{uniq('')}"


def rand_phone() -> str:
    return f"13{random.randint(0, 9)}{random.randint(10000000, 99999999)}"


def rand_price(min_: float = 1.0, max_: float = 1000.0) -> float:
    return round(random.uniform(min_, max_), 2)


def rand_int(min_: int = 1, max_: int = 100) -> int:
    return random.randint(min_, max_)