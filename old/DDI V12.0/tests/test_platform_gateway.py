# -*- coding: utf-8 -*-
"""
平台执行网关测试。

本模块验证历史适配器返回值可在公共网关中转换为统一查询与文件产物契约。
"""

# 导入单元测试模块。
import unittest

# 导入平台执行网关。
from ddi_framework.platform_gateway import PlatformExecutionGateway

# 导入日期范围对象。
from ddi_framework.task_core import DateRangeSpec


# 定义用于验证迁移网关的历史适配器。
class LegacyPlatformAdapter:

    """
    提供历史平台方法返回值的最小测试替身。

    :return: None。
    :rtype: None
    """

    # 声明测试商业名称。
    company_name = "测试商业"

    # 声明测试平台配置。
    account = {"平台": "测试平台"}

    # 初始化测试适配器。
    def __init__(self):

        """
        初始化历史适配器调用记录。

        :return: None。
        :rtype: None
        """

        # 初始化查询参数记录。
        self.query_calls = []

    # 执行历史查询入口。
    def query(self, data_type, date_range):

        """
        返回跨记录出现字段差异的原始行。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param date_range: 查询日期范围。
        :type date_range: DateRangeSpec
        :return: 原始记录集合。
        :rtype: list[dict]
        """

        # 保存网关传入的统一查询参数。
        self.query_calls.append((data_type, date_range.start_date, date_range.end_date))

        # 返回第二条记录新增字段的历史数据。
        return [{"客户": "甲", "数量": 1}, {"客户": "乙", "二级商业": "丙"}]

    # 执行历史查询落地入口。
    def query_to_excel(self, data_type, date_range, output_dir):

        """
        返回多个查询文件路径。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param date_range: 查询日期范围。
        :type date_range: DateRangeSpec
        :param output_dir: 输出目录。
        :type output_dir: str
        :return: Excel 文件路径集合。
        :rtype: list[str]
        """

        # 返回多个模拟查询文件。
        return [f"{output_dir}/查询一.xlsx", f"{output_dir}/查询二.xlsx"]

    # 执行历史原生导出入口。
    def export(self, data_type, date_range, output_dir):

        """
        返回单个原生导出文件路径。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param date_range: 查询日期范围。
        :type date_range: DateRangeSpec
        :param output_dir: 输出目录。
        :type output_dir: str
        :return: Excel 文件路径。
        :rtype: str
        """

        # 返回单个模拟原生导出文件。
        return f"{output_dir}/原生导出.xlsx"


# 定义平台执行网关测试类。
class PlatformExecutionGatewayTests(unittest.TestCase):

    """
    验证公共网关隔离历史适配器调用细节。

    :return: None。
    :rtype: None
    """

    # 定义原始查询规范化测试方法。
    def test_query_normalizes_legacy_rows_and_preserves_dynamic_columns(self):

        """
        验证网关保留原始字段顺序并为缺失字段补空。

        :return: None。
        :rtype: None
        """

        # 创建历史适配器替身。
        adapter = LegacyPlatformAdapter()

        # 创建统一平台执行网关。
        gateway = PlatformExecutionGateway(adapter)

        # 构造统一日期范围。
        date_range = DateRangeSpec.from_mode("custom", "2026-08-01", "2026-08-31")

        # 执行公共查询调用。
        result = gateway.query("配送流向", date_range)

        # 断言网关向历史适配器传递统一日期范围。
        self.assertEqual(adapter.query_calls, [("配送流向", "2026-08-01", "2026-08-31")])

        # 断言首次出现顺序与动态追加字段均被保留。
        self.assertEqual([column.key for column in result.raw_table.headers], ["客户", "数量", "二级商业"])

        # 断言第二条记录缺失的字段会补充为空值。
        self.assertEqual(result.raw_table.rows[1], {"客户": "乙", "数量": "", "二级商业": "丙"})

        # 断言查询结果保留请求日期范围。
        self.assertEqual((result.requested_start_date, result.requested_end_date), ("2026-08-01", "2026-08-31"))

    # 定义文件产物规范化测试方法。
    def test_artifact_calls_normalize_single_and_multiple_paths(self):

        """
        验证查询和原生导出均返回一致的路径集合契约。

        :return: None。
        :rtype: None
        """

        # 创建统一平台执行网关。
        gateway = PlatformExecutionGateway(LegacyPlatformAdapter())

        # 构造统一日期范围。
        date_range = DateRangeSpec.from_mode("custom", "2026-08-01", "2026-08-31")

        # 执行查询 Excel 文件生成调用。
        query_artifact = gateway.query_to_excel("配送流向", date_range, "输出目录")

        # 执行原生导出文件生成调用。
        export_artifact = gateway.export("配送流向", date_range, "输出目录")

        # 断言查询路径统一为不可变路径集合。
        self.assertEqual(query_artifact.paths, ("输出目录/查询一.xlsx", "输出目录/查询二.xlsx"))

        # 断言单个原生导出路径统一为路径集合。
        self.assertEqual(export_artifact.paths, ("输出目录/原生导出.xlsx",))


# 定义直接运行测试模块入口。
if __name__ == "__main__":

    # 执行本模块单元测试。
    unittest.main()
