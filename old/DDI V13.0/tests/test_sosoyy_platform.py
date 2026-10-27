# -*- coding: utf-8 -*-
"""
搜搜电商流向明细协议适配器测试。

本模块验证 JSON 筛选字段、原始字段元数据和 Excel 落地行为。

:return: 模块提供搜搜电商平台协议适配器测试。
:rtype: None
"""

# 导入临时目录模块。
import tempfile

# 导入单元测试模块。
import unittest

# 导入 Excel 工作簿读取函数。
from openpyxl import load_workbook

# 导入搜搜电商平台适配器。
from ddi_framework.platforms.sosoyy import SosoyyPlatform


# 定义搜搜电商平台适配器测试类。
class SosoyyPlatformTests(unittest.TestCase):

    """
    验证 JSON 请求体、字段元数据解析和 Excel 原始字段保留。

    :return: None。
    :rtype: None
    """

    # 定义销售请求体日期参数测试方法。
    def test_sales_payload_writes_only_sales_date_range(self):

        """
        验证销售查询将日期写入服务端真实销售字段。

        :return: None。
        :rtype: None
        """

        # 创建最小平台适配器。
        platform = SosoyyPlatform("测试商业", {"平台": "sosoyy", "接口根地址": "http://example.test"})

        # 构建销售查询请求体。
        payload = platform.build_query_payload("纯销流向", "2026-06-01", "2026-06-30", 2)

        # 断言销售开始日期字段正确。
        self.assertEqual(payload["saleDateBegin"], "2026-06-01")

        # 断言销售结束日期字段正确。
        self.assertEqual(payload["saleDateEnd"], "2026-06-30")

        # 断言采购日期字段保持空值。
        self.assertIsNone(payload["purchaseDateBegin"])

        # 断言当前分页页码正确。
        self.assertEqual(payload["pageIndex"], 2)

    # 定义四类接口端点映射测试方法。
    def test_all_data_types_resolve_distinct_protocol_endpoints(self):

        """
        验证四类业务数据均指向独立的页面实际 JSON 接口。

        :return: None。
        :rtype: None
        """

        # 创建最小平台适配器。
        platform = SosoyyPlatform("测试商业", {"平台": "sosoyy", "接口根地址": "http://example.test"})

        # 构建四类数据请求体集合。
        payloads = {data_type: platform.build_query_payload(data_type, "2026-06-01", "2026-06-30", 1) for data_type in ("纯销流向", "库存", "购进流向", "配送流向")}

        # 断言库存请求不写入流向日期。
        self.assertIsNone(payloads["库存"]["saleDateBegin"])

        # 断言购进请求写入采购日期。
        self.assertEqual(payloads["购进流向"]["purchaseDateBegin"], "2026-06-01")

        # 断言配送请求写入配送日期。
        self.assertEqual(payloads["配送流向"]["deliveryDateEnd"], "2026-06-30")

    # 定义字段元数据与 Excel 原始字段保留测试方法。
    def test_metadata_preserves_raw_fields_in_excel(self):

        """
        验证页面 fields 元数据决定正式原始字段标题和顺序。

        :return: None。
        :rtype: None
        """

        # 创建最小平台适配器。
        platform = SosoyyPlatform("测试商业", {"平台": "sosoyy", "接口根地址": "http://example.test"})

        # 构建页面字段元数据。
        data_block = {"fields": [{"dataIndex": "saleDate", "title": "销售时间"}, {"dataIndex": "drugsBase_Number", "title": "商品编码"}, {"dataIndex": "salesVolume", "title": "销售数量"}]}

        # 构建一条服务端原始记录。
        rows = [{"saleDate": "2026-06-30 20:49:19", "drugsBase_Number": "8166603", "salesVolume": 1}]

        # 解析服务端字段元数据。
        headers = platform.resolve_headers(data_block, rows)

        # 创建临时 Excel 输出目录。
        with tempfile.TemporaryDirectory() as output_dir:

            # 拼接临时 Excel 输出路径。
            output_path = f"{output_dir}/sosoyy.xlsx"

            # 写入正式原始字段。
            platform.write_rows_to_excel(rows, headers, "纯销流向", output_path)

            # 以只读模式打开生成的 Excel。
            workbook = load_workbook(output_path, read_only=True)

            # 读取活动工作表。
            worksheet = workbook.active

            # 读取 Excel 表头行。
            excel_headers = [cell.value for cell in next(worksheet.iter_rows(min_row=1, max_row=1))]

            # 读取 Excel 首条数据行。
            excel_row = [cell.value for cell in next(worksheet.iter_rows(min_row=2, max_row=2))]

            # 关闭 Excel 工作簿。
            workbook.close()

        # 断言 Excel 标题严格保持接口元数据文本和顺序。
        self.assertEqual(excel_headers, ["销售时间", "商品编码", "销售数量"])

        # 断言 Excel 数据严格保持接口原始字段值。
        self.assertEqual(excel_row, ["2026-06-30 20:49:19", "8166603", 1])
