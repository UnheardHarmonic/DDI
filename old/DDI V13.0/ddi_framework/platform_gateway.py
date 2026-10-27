# -*- coding: utf-8 -*-
"""
平台适配器公共网关。

本模块把历史适配器方法收敛到统一的登录、查询、查询落地和导出边界，
使任务编排层不再直接依赖具体平台的旧式方法名。
"""

# 导入数据类定义工具。
from dataclasses import dataclass, field

# 导入统一查询结果对象。
from ddi_framework.task_core import QueryResult, RawColumn, RawTable


# 定义平台导出结果对象。
@dataclass(frozen=True)
class PlatformArtifactResult:

    """
    描述平台网关产生的文件产物。

    :param data_type: 数据类型名称。
    :type data_type: str
    :param paths: 生成的文件路径集合。
    :type paths: tuple[str, ...]
    :param record_count: 产物包含的记录数。
    :type record_count: int
    :param warnings: 产物生成警告集合。
    :type warnings: tuple[str, ...]
    """

    # 保存数据类型名称。
    data_type: str

    # 保存文件路径集合。
    paths: tuple[str, ...] = ()

    # 保存产物记录数量。
    record_count: int = 0

    # 保存产物生成警告。
    warnings: tuple[str, ...] = field(default_factory=tuple)


# 定义平台执行网关。
class PlatformExecutionGateway:

    """
    为单个商业平台适配器提供统一业务调用边界。

    :param adapter: 已创建的平台适配器实例。
    :type adapter: object
    """

    # 初始化平台执行网关。
    def __init__(self, adapter):

        """
        保存待调用的平台适配器。

        :param adapter: 平台适配器实例。
        :type adapter: object
        :return: None。
        :rtype: None
        """

        # 保存平台适配器实例。
        self.adapter = adapter

    # 执行统一登录调用。
    def login(self):

        """
        调用平台登录协议。

        :return: 平台登录结果。
        :rtype: object
        """

        # 通过适配器执行登录协议。
        return self.adapter.login()

    # 保存平台会话 Cookie。
    def save_cookie(self, output_dir):

        """
        将平台会话保存到运行期目录。

        :param output_dir: Cookie 输出目录。
        :type output_dir: str
        :return: Cookie 文件路径。
        :rtype: str
        """

        # 通过适配器保存会话 Cookie。
        return self.adapter.save_cookie(output_dir)

    # 执行统一原始查询并标准化结果。
    def query(self, data_type, date_range):

        """
        执行查询并转换为公共 QueryResult 契约。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param date_range: 查询日期范围。
        :type date_range: DateRangeSpec
        :return: 标准化查询结果。
        :rtype: QueryResult
        """

        # 调用适配器统一查询入口。
        result = self.adapter.query(data_type, date_range)

        # 保留适配器已经生成的公共查询结果。
        if isinstance(result, QueryResult):

            # 返回适配器提供的标准查询结果。
            return result

        # 将历史列表结果转换为字典行集合。
        rows = list(result or []) if isinstance(result, (list, tuple)) else []

        # 初始化原始字段定义和字段索引。
        columns = []
        known_keys = set()

        # 遍历查询记录收集首次出现字段。
        for row in rows:

            # 忽略非字典记录，避免伪造字段契约。
            if not isinstance(row, dict):

                # 继续处理下一条记录。
                continue

            # 按原始键插入顺序登记字段。
            for key in row:

                # 标准化当前原始字段键。
                normalized_key = str(key)

                # 跳过重复字段键。
                if normalized_key in known_keys:

                    # 继续读取下一个字段。
                    continue

                # 保存原始字段及其首次出现顺序。
                known_keys.add(normalized_key)
                columns.append(RawColumn(normalized_key, normalized_key, "response", len(columns)))

        # 构造统一原始表并保持每行字段对齐。
        raw_table = RawTable(columns, [{column.key: row.get(column.key, "") for column in columns} for row in rows if isinstance(row, dict)])

        # 返回带请求范围的公共查询结果。
        return QueryResult(self.adapter.company_name, self.adapter.account.get("平台", ""), data_type, raw_table, 1 if rows else 0, date_range.start_date, date_range.end_date)

    # 执行统一查询并生成文件产物。
    def query_to_excel(self, data_type, date_range, output_dir):

        """
        调用平台查询落地接口并标准化文件路径。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param date_range: 查询日期范围。
        :type date_range: DateRangeSpec
        :param output_dir: 文件输出目录。
        :type output_dir: str
        :return: 查询产物结果。
        :rtype: PlatformArtifactResult
        """

        # 调用适配器统一查询落地入口。
        result = self.adapter.query_to_excel(data_type, date_range, output_dir)

        # 规范化平台返回的单路径或路径集合。
        paths = self._normalize_paths(result)

        # 返回统一查询产物结果。
        return PlatformArtifactResult(data_type, tuple(paths))

    # 执行统一原生导出并标准化文件路径。
    def export(self, data_type, date_range, output_dir):

        """
        调用平台原生导出接口并标准化文件路径。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param date_range: 查询日期范围。
        :type date_range: DateRangeSpec
        :param output_dir: 文件输出目录。
        :type output_dir: str
        :return: 导出产物结果。
        :rtype: PlatformArtifactResult
        """

        # 调用适配器统一原生导出入口。
        result = self.adapter.export(data_type, date_range, output_dir)

        # 规范化平台返回的导出路径。
        paths = self._normalize_paths(result)

        # 返回统一导出产物结果。
        return PlatformArtifactResult(data_type, tuple(paths))

    # 规范化平台路径返回值。
    @staticmethod
    def _normalize_paths(value):

        """
        将适配器返回值转换为路径列表。

        :param value: 适配器返回的路径值。
        :type value: object
        :return: 文件路径列表。
        :rtype: list[str]
        """

        # 处理平台返回的路径序列。
        if isinstance(value, (list, tuple, set)):

            # 返回非空路径文本集合。
            return [str(path) for path in value if str(path).strip()]

        # 处理平台返回的单一路径。
        return [str(value)] if value is not None and str(value).strip() else []
