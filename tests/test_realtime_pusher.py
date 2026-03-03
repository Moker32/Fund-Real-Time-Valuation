"""
实时数据推送器工具函数测试

测试 _to_camel_case 和 _convert_dict_to_camel_case 函数。
"""

from src.utils.websocket_manager import _to_camel_case, _convert_dict_to_camel_case


class TestToCamelCase:
    """snake_case 转 camelCase 测试"""

    def test_simple_snake_case(self):
        """测试简单 snake_case 转换"""
        assert _to_camel_case("fund_code") == "fundCode"
        assert _to_camel_case("net_value") == "netValue"
        assert _to_camel_case("change_percent") == "changePercent"

    def test_multiple_underscores(self):
        """测试多个下划线的情况"""
        assert _to_camel_case("net_value_date") == "netValueDate"
        assert _to_camel_case("a_b_c_d") == "aBCD"
        assert _to_camel_case("one_two_three_four") == "oneTwoThreeFour"

    def test_already_camel_case(self):
        """测试已经是 camelCase 的情况"""
        assert _to_camel_case("fundCode") == "fundCode"
        assert _to_camel_case("netValue") == "netValue"
        assert _to_camel_case("a") == "a"

    def test_empty_string(self):
        """测试空字符串"""
        assert _to_camel_case("") == ""

    def test_no_underscores(self):
        """测试没有下划线的字符串"""
        assert _to_camel_case("code") == "code"
        assert _to_camel_case("name") == "name"
        assert _to_camel_case("value") == "value"

    def test_single_underscore(self):
        """测试单个下划线"""
        assert _to_camel_case("a_b") == "aB"

    def test_trailing_underscore(self):
        """测试尾部下划线"""
        # 尾部下划线会产生空字符串组件，但 join 会忽略
        assert _to_camel_case("code_") == "code"

    def test_leading_underscore(self):
        """测试头部下划线"""
        # 头部下划线：第一个组件是空字符串
        assert _to_camel_case("_code") == "Code"

    def test_consecutive_underscores(self):
        """测试连续下划线"""
        # 连续下划线会产生空字符串组件
        assert _to_camel_case("a__b") == "aB"


class TestConvertDictToCamelCase:
    """字典键转换为 camelCase 测试"""

    def test_simple_dict(self):
        """测试简单字典转换"""
        data = {"fund_code": "000001", "net_value": 1.234}
        result = _convert_dict_to_camel_case(data)
        assert result == {"fundCode": "000001", "netValue": 1.234}

    def test_nested_dict(self):
        """测试嵌套字典转换"""
        data = {
            "fund_code": "000001",
            "detail_info": {"manager_name": "张三", "company_name": "测试公司"}
        }
        result = _convert_dict_to_camel_case(data)
        assert result == {
            "fundCode": "000001",
            "detailInfo": {"managerName": "张三", "companyName": "测试公司"}
        }

    def test_dict_with_list(self):
        """测试包含列表的字典转换"""
        data = {
            "fund_list": [
                {"fund_code": "000001", "fund_name": "基金A"},
                {"fund_code": "000002", "fund_name": "基金B"}
            ]
        }
        result = _convert_dict_to_camel_case(data)
        assert result == {
            "fundList": [
                {"fundCode": "000001", "fundName": "基金A"},
                {"fundCode": "000002", "fundName": "基金B"}
            ]
        }

    def test_dict_with_primitive_list(self):
        """测试包含基本类型列表的字典"""
        data = {"tag_list": ["tag1", "tag2", "tag3"]}
        result = _convert_dict_to_camel_case(data)
        assert result == {"tagList": ["tag1", "tag2", "tag3"]}

    def test_mixed_data_types(self):
        """测试混合数据类型"""
        data = {
            "string_value": "test",
            "int_value": 123,
            "float_value": 45.67,
            "bool_value": True,
            "none_value": None,
            "list_value": [1, 2, 3],
            "dict_value": {"inner_key": "inner_value"}
        }
        result = _convert_dict_to_camel_case(data)
        assert result == {
            "stringValue": "test",
            "intValue": 123,
            "floatValue": 45.67,
            "boolValue": True,
            "noneValue": None,
            "listValue": [1, 2, 3],
            "dictValue": {"innerKey": "inner_value"}
        }

    def test_empty_dict(self):
        """测试空字典"""
        result = _convert_dict_to_camel_case({})
        assert result == {}

    def test_deeply_nested_dict(self):
        """测试深度嵌套字典"""
        data = {
            "level_one": {
                "level_two": {
                    "level_three": {
                        "deep_value": "found"
                    }
                }
            }
        }
        result = _convert_dict_to_camel_case(data)
        assert result == {
            "levelOne": {
                "levelTwo": {
                    "levelThree": {
                        "deepValue": "found"
                    }
                }
            }
        }

    def test_list_of_lists(self):
        """测试嵌套列表"""
        data = {
            "matrix": [[1, 2], [3, 4]]
        }
        result = _convert_dict_to_camel_case(data)
        assert result == {"matrix": [[1, 2], [3, 4]]}

    def test_complex_nested_structure(self):
        """测试复杂嵌套结构"""
        data = {
            "fund_code": "000001",
            "holdings": [
                {
                    "stock_code": "600000",
                    "stock_name": "浦发银行",
                    "position_ratio": 5.23
                },
                {
                    "stock_code": "000001",
                    "stock_name": "平安银行",
                    "position_ratio": 3.45
                }
            ],
            "performance": {
                "one_month": 2.3,
                "three_month": 5.6,
                "one_year": 12.5
            }
        }
        result = _convert_dict_to_camel_case(data)
        assert result == {
            "fundCode": "000001",
            "holdings": [
                {
                    "stockCode": "600000",
                    "stockName": "浦发银行",
                    "positionRatio": 5.23
                },
                {
                    "stockCode": "000001",
                    "stockName": "平安银行",
                    "positionRatio": 3.45
                }
            ],
            "performance": {
                "oneMonth": 2.3,
                "threeMonth": 5.6,
                "oneYear": 12.5
            }
        }