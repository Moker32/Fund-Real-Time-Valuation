"""QDII fund to overseas index mapping.

Pure data mapping from known QDII fund codes to their tracking overseas indices.
This module is standalone and contains no I/O or async code.
"""

from __future__ import annotations

IndexInfo = dict[str, float | str]

_MAPPING: dict[str, list[IndexInfo]] = {
    "270042": [
        {"index_type": "nasdaq", "weight": 100.0, "name": "纳斯达克100指数"},
    ],
    "164906": [
        {"index_type": "hang_seng", "weight": 60.0, "name": "恒生指数"},
        {"index_type": "hang_seng_tech", "weight": 40.0, "name": "恒生科技指数"},
    ],
    "162411": [
        {"index_type": "sp500", "weight": 100.0, "name": "标准普尔500指数"},
    ],
    "470888": [
        {"index_type": "sp500", "weight": 100.0, "name": "标准普尔500指数"},
    ],
    "000041": [
        {"index_type": "sp500", "weight": 40.0, "name": "标准普尔500指数"},
        {"index_type": "nasdaq", "weight": 30.0, "name": "纳斯达克综合指数"},
        {"index_type": "hang_seng", "weight": 30.0, "name": "恒生指数"},
    ],
    "519696": [
        {"index_type": "sp500", "weight": 50.0, "name": "标准普尔500指数"},
        {"index_type": "nasdaq", "weight": 30.0, "name": "纳斯达克综合指数"},
        {"index_type": "dax", "weight": 20.0, "name": "德国DAX指数"},
    ],
    "160723": [
        {"index_type": "hang_seng", "weight": 100.0, "name": "恒生指数"},
    ],
    "161128": [
        {"index_type": "sp500", "weight": 100.0, "name": "标准普尔500指数"},
    ],
    "161815": [
        {"index_type": "nasdaq", "weight": 100.0, "name": "纳斯达克综合指数"},
    ],
    "501018": [],  # commodity QDII, no tracking index
    "165513": [],  # commodity QDII, no tracking index
    "006373": [
        {"index_type": "nasdaq", "weight": 70.0, "name": "纳斯达克综合指数"},
        {"index_type": "sp500", "weight": 30.0, "name": "标准普尔500指数"},
    ],
    "513030": [
        {"index_type": "dax", "weight": 100.0, "name": "德国DAX指数"},
    ],
    "513180": [
        {"index_type": "hang_seng_tech", "weight": 100.0, "name": "恒生科技指数"},
    ],
    "513520": [
        {"index_type": "nikkei225", "weight": 100.0, "name": "日经225指数"},
    ],
    "513360": [
        {"index_type": "sp500", "weight": 100.0, "name": "标准普尔500指数"},
    ],
    "513500": [
        {"index_type": "sp500", "weight": 100.0, "name": "标准普尔500指数"},
    ],
    "164701": [
        {"index_type": "hang_seng", "weight": 100.0, "name": "恒生指数"},
    ],
    "000043": [
        {"index_type": "sp500", "weight": 100.0, "name": "标准普尔500指数"},
    ],
}


def get_qdii_tracking_indices(fund_code: str) -> list[IndexInfo]:
    """Return the tracking indices for a given QDII fund code.

    The function looks up a small, hard-coded mapping. If the fund_code is not
    present, an empty list is returned, allowing callers to fall back to
    name-based detection.

    Args:
        fund_code: The fund code as a string, e.g., "270042".

    Returns:
        A list of dictionaries with keys:
          - index_type: str, one of the supported index types
          - weight: float, percentage weight (0-100)
          - name: str, Chinese name of the index
    """
    key = (fund_code or "").strip()
    return _MAPPING.get(key, [])


def is_qdii_fund(code: str) -> bool:
    """Check whether a code is a known QDII fund.

    This is a fast, in-memory check with no I/O.

    Args:
        code: Fund code to test.

    Returns:
        True if the code is known in the mapping, else False.
    """
    if not code:
        return False
    return code.strip() in _MAPPING
