# -*- coding: utf-8 -*-
"""
DDI 公共框架包入口。

包根只导出稳定的基础能力和领域对象；平台适配器由平台注册表按需加载，
避免导入任意公共服务时同步初始化全部商业协议模块。
"""

# 导入平台适配器基类。
from ddi_framework.platforms.base import BasePlatform

# 导入协议响应类型。
from ddi_framework.http_client import HttpResult

# 导入协议请求客户端。
from ddi_framework.http_client import ProtocolHttpClient

# 导入验证码识别器。
from ddi_framework.captcha_solver import AesEcbEncryptor, CaptchaSolver

# 导入下载监听器。
from ddi_framework.download_watcher import DownloadWatcher

# 导入 Excel 标准样式函数。
from ddi_framework.excel_style import apply_standard_excel_style

# 导入授权基础能力。
from ddi_framework.license_guard import DEFAULT_LICENSE_VERSION
from ddi_framework.license_guard import LICENSE_FILE_NAME
from ddi_framework.license_guard import LicenseError
from ddi_framework.license_guard import build_license_payload_bytes
from ddi_framework.license_guard import build_runtime_identity
from ddi_framework.license_guard import ensure_runtime_license

# 导入日志打印器。
from ddi_framework.print_handler import PrintHandler

# 导入任务领域对象。
from ddi_framework.task_core import DataTypeSelection
from ddi_framework.task_core import DateRangeSpec
from ddi_framework.task_core import QueryResult
from ddi_framework.task_core import RawColumn
from ddi_framework.task_core import RawTable
from ddi_framework.task_core import TaskCoordinator
from ddi_framework.task_core import TaskEvent
from ddi_framework.task_core import TaskRequest

# 导入动态字段服务。
from ddi_framework.raw_fields import DynamicFieldCollector
from ddi_framework.raw_fields import DynamicFieldTable
from ddi_framework.raw_fields import write_dynamic_raw_excel

# 导入通用协议加密函数。
from ddi_framework.reverse_utils import aes_cbc_pkcs7_base64
from ddi_framework.reverse_utils import md5_hex
from ddi_framework.reverse_utils import sha256_hex
from ddi_framework.reverse_utils import triple_des_cbc_pkcs7_base64


# 定义历史平台类按需加载映射。
_LAZY_PLATFORM_EXPORTS = {
    "JztPlatform": ("jzt", "JztPlatform"),
    "GyfjPlatform": ("gyfj", "GyfjPlatform"),
    "PzhhrPlatform": ("pzhhr", "PzhhrPlatform"),
    "HljaldPlatform": ("hljald", "HljaldPlatform"),
    "GzyyPlatform": ("gzyy", "GzyyPlatform"),
    "GyjlPlatform": ("gyjl", "GyjlPlatform"),
    "TyjslnPlatform": ("tyjsln", "TyjslnPlatform"),
    "FjxzjPlatform": ("fjxzj", "FjxzjPlatform"),
    "GdwstPlatform": ("gdwst", "GdwstPlatform"),
    "HreportPlatform": ("hreport", "HreportPlatform"),
    "FjjztzhPlatform": ("fjjztzh", "FjjztzhPlatform"),
    "GkgdjmPlatform": ("gkgdjm", "GkgdjmPlatform"),
    "DslPlatform": ("dsl", "DslPlatform"),
    "HljdzpaPlatform": ("hljdzpa", "HljdzpaPlatform"),
    "DlfdyyPlatform": ("dlfdyy", "DlfdyyPlatform"),
    "GjjkPlatform": ("gjjk", "GjjkPlatform"),
    "JxhqrzPlatform": ("jxhqrz", "JxhqrzPlatform"),
    "HnhcyyPlatform": ("hnhcyy", "HnhcyyPlatform"),
    "SxtzcxPlatform": ("sxtzcx", "SxtzcxPlatform"),
    "RhtnmPlatform": ("rhtnm", "RhtnmPlatform"),
    "ZztjPlatform": ("zztj", "ZztjPlatform"),
    "HxPlatform": ("hx", "HxPlatform"),
    "KcshopPlatform": ("kcshop", "KcshopPlatform"),
    "HxlxPlatform": ("hxlx", "HxlxPlatform"),
    "GykgahPlatform": ("gykgah", "GykgahPlatform"),
    "GksdPlatform": ("gksd", "GksdPlatform"),
    "QdtfyyPlatform": ("qdtfyy", "QdtfyyPlatform"),
    "ShhfyyPlatform": ("shhfyy", "ShhfyyPlatform"),
    "ScjzjPlatform": ("scjzj", "ScjzjPlatform"),
    "JzjcgPlatform": ("jzjcg", "JzjcgPlatform"),
    "CqtjgPlatform": ("cqtjg", "CqtjgPlatform"),
    "CqxhyfPlatform": ("cqxhyf", "CqxhyfPlatform"),
    "CqpjyyPlatform": ("cqpjyy", "CqpjyyPlatform"),
    "YanxitangPlatform": ("yanxitang", "YanxitangPlatform"),
    "CombrainJyscPlatform": ("combrain_jysc", "CombrainJyscPlatform"),
    "XjyPlatform": ("xjy", "XjyPlatform"),
    "HrjkPlatform": ("hrjk", "HrjkPlatform"),
    "DdkyPlatform": ("ddky", "DdkyPlatform"),
    "GylrtPlatform": ("gylrt", "GylrtPlatform"),
    "JshthyPlatform": ("jshthy", "JshthyPlatform"),
    "JsayPlatform": ("jsay", "JsayPlatform"),
    "JswmPlatform": ("jswm", "JswmPlatform"),
    "EhhdPlatform": ("ehhd", "EhhdPlatform"),
    "HxyxtPlatform": ("hxyxt", "HxyxtPlatform"),
    "YnqyPlatform": ("ynqy", "YnqyPlatform"),
    "TaijiPlatform": ("taiji", "TaijiPlatform"),
    "HuaxinPlatform": ("huaxin", "HuaxinPlatform"),
    "SosoyyPlatform": ("sosoyy", "SosoyyPlatform"),
    "AbacusPlatform": ("abacus", "AbacusPlatform"),
    "BellcarePlatform": ("bellcare", "BellcarePlatform"),
    "CoxScmPlatform": ("cox_scm", "CoxScmPlatform"),
    "LsjndPlatform": ("lsjnd", "LsjndPlatform"),
    "CrpcgPlatform": ("crpcg", "CrpcgPlatform"),
    "ScbctPlatform": ("scbct", "ScbctPlatform"),
}

# 定义公共服务兼容懒加载映射。
_LAZY_SERVICE_EXPORTS = {
    "execute_company": ("ddi_framework.task_execution", "execute_company"),
    "DdiTaskRuntime": ("ddi_framework.task_runtime", "DdiTaskRuntime"),
    "ENTRY_DETAIL_FIELDS": ("ddi_framework.entry_detail", "ENTRY_DETAIL_FIELDS"),
    "generate_entry_summary_excel": ("ddi_framework.entry_detail", "generate_entry_summary_excel"),
    "load_entry_detail_mapping": ("ddi_framework.entry_detail", "load_entry_detail_mapping"),
    "validate_entry_detail_mapping": ("ddi_framework.entry_detail", "validate_entry_detail_mapping"),
    "collect_entry_summary_blocks": ("ddi_framework.entry_detail", "collect_entry_summary_blocks"),
}


# 定义平台类兼容懒加载函数。
def __getattr__(name):

    """
    按需加载历史平台类导出，保持旧调用方兼容。

    :param name: 被访问的包根属性名称。
    :type name: str
    :return: 延迟加载的平台适配器类。
    :rtype: type
    :raises AttributeError: 属性不是已登记的平台类时抛出。
    """

    # 读取平台类的模块和属性定义。
    platform_module_name, platform_class_name = _LAZY_PLATFORM_EXPORTS.get(name, (None, None))

    # 按需读取历史公共服务导出。
    if not platform_module_name:

        # 读取公共服务模块和属性定义。
        service_module_name, service_attribute_name = _LAZY_SERVICE_EXPORTS.get(name, (None, None))

        # 拒绝访问未登记的包根属性。
        if not service_module_name:

            # 抛出标准属性不存在异常。
            raise AttributeError(f"module 'ddi_framework' has no attribute {name!r}")

        # 动态导入目标公共服务模块。
        module = __import__(service_module_name, fromlist=[service_attribute_name])

        # 读取公共服务并缓存到包根属性。
        service = getattr(module, service_attribute_name)
        globals()[name] = service

        # 返回兼容调用方所需的公共服务。
        return service

    # 动态导入目标平台模块。
    module = __import__(f"ddi_framework.platforms.{platform_module_name}", fromlist=[platform_class_name])

    # 读取平台类并缓存到包根属性。
    platform_class = getattr(module, platform_class_name)
    globals()[name] = platform_class

    # 返回兼容调用方所需的平台类。
    return platform_class
