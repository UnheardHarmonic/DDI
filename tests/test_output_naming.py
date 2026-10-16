# -*- coding: utf-8 -*-
"""导出文件命名语义测试。

锁定库存类统一按导出当天快照日期命名、流向类按查询日期范围命名的统一规则。
"""

# 导入日期时间模块。
from datetime import datetime

# 导入单元测试框架。
import unittest

# 导入平台适配器基类。
from ddi_framework.platforms.base import BasePlatform

# 导入公共下载命名工具。
from ddi_framework.download_watcher import DownloadWatcher


# 定义命名语义测试用例。
class TestOutputNamingSemantics(unittest.TestCase):

    """
    导出文件命名统一语义测试。

    :return: 测试用例实例。
    :rtype: TestOutputNamingSemantics
    """

    # 定义测试环境准备方法。
    def setUp(self):

        """
        构造测试用平台实例。

        :return: None。
        :rtype: None
        """

        # 构造最小账号配置的平台实例。
        self.platform = BasePlatform("测试商业", {"平台": "test"})

        # 记录当天日期文本。
        self.today = datetime.now().strftime("%Y.%m.%d")

    # 定义库存命名测试方法。
    def test_inventory_named_by_export_day_even_with_range(self):

        """
        验证库存类携带完整日期范围时仍按导出当天快照命名。

        :return: None。
        :rtype: None
        """

        # 构建库存文件名。
        name = self.platform.build_output_file_name("库存", "2026-09-01", "2026-09-30")

        # 断言使用当天快照标签而非查询范围。
        self.assertIn(f"快照｜{self.today}", name)

        # 断言不携带查询范围标签。
        self.assertNotIn("2026.09.01~2026.09.30", name)

    # 定义无范围库存命名测试方法。
    def test_inventory_without_dates_uses_today(self):

        """
        验证库存类无日期参数时按导出当天快照命名。

        :return: None。
        :rtype: None
        """

        # 构建无日期库存文件名。
        name = self.platform.build_output_file_name("库存")

        # 断言使用当天快照标签。
        self.assertIn(f"快照｜{self.today}", name)

    # 定义流向命名测试方法。
    def test_flow_named_by_query_range(self):

        """
        验证流向类按查询开始与结束日期范围命名。

        :return: None。
        :rtype: None
        """

        # 构建流向文件名。
        name = self.platform.build_output_file_name("配送流向", "2026-09-01", "2026-09-30")

        # 断言使用范围标签。
        self.assertIn("范围｜2026.09.01~2026.09.30", name)

    # 定义门店库存变体测试方法。
    def test_inventory_variants_share_snapshot_rule(self):

        """
        验证含库存字样的变体类型同样按快照规则命名。

        :return: None。
        :rtype: None
        """

        # 构建门店库存文件名。
        name = self.platform.build_output_file_name("门店库存", "2026-09-01", "2026-09-30")

        # 断言使用当天快照标签。
        self.assertIn(f"快照｜{self.today}", name)

    # 定义整月模式测试方法。
    def test_flow_month_mode_label(self):

        """
        验证整月日期模式使用整月标签。

        :return: None。
        :rtype: None
        """

        # 构建整月模式文件名。
        label = DownloadWatcher("")._format_date_label("配送流向", None, "2026-09-01", "2026-09-30", "previous_month_full")

        # 断言使用整月标签。
        self.assertIn("整月｜", label)


# 运行测试入口。
if __name__ == "__main__":

    # 启动单元测试。
    unittest.main()
