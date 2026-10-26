# -*- coding: utf-8 -*-
"""
平台适配器注册表。

本模块根据账号配置中的平台标识创建对应的平台协议适配器。
"""

# 导入九州通平台适配器。
from ddi_framework.platforms.jzt import JztPlatform

# 导入国药控股福建平台适配器。
from ddi_framework.platforms.gyfj import GyfjPlatform

# 导入厦门片仔癀宏仁平台适配器。
from ddi_framework.platforms.pzhhr import PzhhrPlatform

# 导入黑龙江阿拉丁平台适配器。
from ddi_framework.platforms.hljald import HljaldPlatform

# 导入广州医药平台适配器。
from ddi_framework.platforms.gzyy import GzyyPlatform

# 导入国药控股吉林平台适配器。
from ddi_framework.platforms.gyjl import GyjlPlatform

# 导入通用技术辽宁医药平台适配器。
from ddi_framework.platforms.tyjsln import TyjslnPlatform

# 导入福建新紫金医药平台适配器。
from ddi_framework.platforms.fjxzj import FjxzjPlatform

# 导入广东五嗣堂医药平台适配器。
from ddi_framework.platforms.gdwst import GdwstPlatform

# 导入HReport 供应商查询系统适配器。
from ddi_framework.platforms.hreport import HreportPlatform

# 导入国大药房流向数据平台适配器。
from ddi_framework.platforms.guoda import GuodaPlatform

# 导入千金供应商系统适配器。
from ddi_framework.platforms.qjdyf import QjdyfPlatform

# 导入重庆医药流向系统适配器。
from ddi_framework.platforms.cqhp import CqhpPlatform

# 导入漱玉平民供应商门户适配器。
from ddi_framework.platforms.sypm import SypmPlatform

# 导入福建九州通中化平台适配器。
from ddi_framework.platforms.fjjztzh import FjjztzhPlatform

# 导入国控国大江门平台适配器。
from ddi_framework.platforms.gkgdjm import GkgdjmPlatform

# 导入大参林平台适配器。
from ddi_framework.platforms.dsl import DslPlatform

# 导入黑龙江大众平安平台适配器。
from ddi_framework.platforms.hljdzpa import HljdzpaPlatform

# 导入大连方大药业平台适配器。
from ddi_framework.platforms.dlfdyy import DlfdyyPlatform

# 导入高济健康 SRM 平台适配器。
from ddi_framework.platforms.gjjk import GjjkPlatform

# 导入江西黄庆仁栈平台适配器。
from ddi_framework.platforms.jxhqrz import JxhqrzPlatform

# 导入河南慧采医药平台适配器。
from ddi_framework.platforms.hnhcyy import HnhcyyPlatform

# 导入山西天泽诚信平台适配器。
from ddi_framework.platforms.sxtzcx import SxtzcxPlatform

# 导入仁和堂内蒙古平台适配器。
from ddi_framework.platforms.rhtnm import RhtnmPlatform

# 导入漳州天健医药平台适配器。
from ddi_framework.platforms.zztj import ZztjPlatform

# 导入海翔供应链平台适配器。
from ddi_framework.platforms.hx import HxPlatform


# 导入 KCShop 流向管理系统适配器。
from ddi_framework.platforms.kcshop import KcshopPlatform


# 导入洪兴流向系统适配器。
from ddi_framework.platforms.hxlx import HxlxPlatform


# 导入国控安徽信息服务平台适配器。
from ddi_framework.platforms.gykgah import GykgahPlatform


# 导入国控山东数据流向服务系统平台适配器。
from ddi_framework.platforms.gksd import GksdPlatform

# 导入青岛同方药业连锁有限公司平台适配器。
from ddi_framework.platforms.qdtfyy import QdtfyyPlatform

# 导入上海汇丰医药药材有限责任公司平台适配器。
from ddi_framework.platforms.shhfyy import ShhfyyPlatform

# 导入四川聚之家医药有限公司聚创供应商系统平台适配器。
from ddi_framework.platforms.scjzj import ScjzjPlatform

# 导入健之佳采购云销售明细查询协议适配器。
from ddi_framework.platforms.jzjcg import JzjcgPlatform

# 导入重庆桐君阁大药房连锁有限责任公司桐君阁供应商流向系统平台适配器。
from ddi_framework.platforms.cqtjg import CqtjgPlatform

# 导入重庆鑫斛药房连锁有限公司数据流向系统平台适配器。
from ddi_framework.platforms.cqxhyf import CqxhyfPlatform

# 导入重庆普健医药有限公司普健数据协同平台适配器。
from ddi_framework.platforms.cqpjyy import CqpjyyPlatform

# 导入燕喜堂 SRM 系统平台适配器。
from ddi_framework.platforms.yanxitang import YanxitangPlatform

# 导入康博士 ABrain 流向查询系统平台适配器。
from ddi_framework.platforms.combrain_jysc import CombrainJyscPlatform


# 导入安徽新聚源活字格直连平台适配器。
from ddi_framework.platforms.xjy import XjyPlatform


# 导入安徽华人健康捷助数据中心平台适配器。
from ddi_framework.platforms.hrjk import HrjkPlatform

# 导入叮当快药 DTP 流向系统平台适配器。
from ddi_framework.platforms.ddky import DdkyPlatform

# 导入国药乐仁堂数据服务中心平台适配器。
from ddi_framework.platforms.gylrt import GylrtPlatform

# 导入江苏恒泰华洋全亿健康 OA 平台适配器。
from ddi_framework.platforms.jshthy import JshthyPlatform

# 导入江苏澳洋 FineReport 数据分析系统平台适配器。
from ddi_framework.platforms.jsay import JsayPlatform

# 导入江苏卫民数据智能管理系统平台适配器。
from ddi_framework.platforms.jswm import JswmPlatform

# 导入恩华和达经典 ASP 查询系统平台适配器。
from ddi_framework.platforms.ehhd import EhhdPlatform

# 导入鸿翔一心堂 SRM FineReport 供应商流向平台适配器。
from ddi_framework.platforms.hxyxt import HxyxtPlatform

# 导入雨诺轻应用知流向同表类型拆分平台适配器。
from ddi_framework.platforms.ynqy import YnqyPlatform

# 导入太极大药房流向查询系统平台适配器。
from ddi_framework.platforms.taiji import TaijiPlatform

# 导入四川华信药业 FineReport 平台适配器。
from ddi_framework.platforms.huaxin import HuaxinPlatform

# 导入西昌东升大药房搜搜电商平台适配器。
from ddi_framework.platforms.sosoyy import SosoyyPlatform

# 导入 ABACUS 供应链系统平台适配器。
from ddi_framework.platforms.abacus import AbacusPlatform

# 导入贝尔康流向采集服务平台适配器。
from ddi_framework.platforms.bellcare import BellcarePlatform

# 导入能手软件 SCM 查询平台适配器。
from ddi_framework.platforms.cox_scm import CoxScmPlatform

# 导入流向卡管理系统平台适配器。
from ddi_framework.platforms.lsjnd import LsjndPlatform

# 导入华润医药商业上游数据服务平台适配器。
from ddi_framework.platforms.crpcg import CrpcgPlatform

# 导入四川本草堂药业协同办公系统平台适配器。
from ddi_framework.platforms.scbct import ScbctPlatform

# 导入药德供应商流向平台适配器。
from ddi_framework.platforms.yaoud import YaoudPlatform

# 导入华润德信行流向查询平台适配器。
from ddi_framework.platforms.dexinxing import DexinxingPlatform

# 导入南京医药国药 DDI 数据直连系统平台适配器。
from ddi_framework.platforms.njyygy import NjyygyPlatform

# 导入成都聚仁堂 FineReport 数据报表系统平台适配器。
from ddi_framework.platforms.jrt import JrtPlatform

# 导入米伦厂商合作平台适配器。
from ddi_framework.platforms.milun import MilunPlatform


# 配置平台标识与平台适配器类的映射关系。
PLATFORM_REGISTRY = {
    "jzt": JztPlatform,
    "gyfj": GyfjPlatform,
    "pzhhr": PzhhrPlatform,
    "hljald": HljaldPlatform,
    "gzyy": GzyyPlatform,
    "gyjl": GyjlPlatform,
    "tyjsln": TyjslnPlatform,
    "fjxzj": FjxzjPlatform,
    "gdwst": GdwstPlatform,
    "hreport": HreportPlatform,
    "guoda": GuodaPlatform,
    "qjdyf": QjdyfPlatform,
    "cqhp": CqhpPlatform,
    "sypm": SypmPlatform,
    "fjjztzh": FjjztzhPlatform,
    "gkgdjm": GkgdjmPlatform,
    "dsl": DslPlatform,
    "hljdzpa": HljdzpaPlatform,
    "dlfdyy": DlfdyyPlatform,
    "gjjk": GjjkPlatform,
    "jxhqrz": JxhqrzPlatform,
    "hnhcyy": HnhcyyPlatform,
    "sxtzcx": SxtzcxPlatform,
    "rhtnm": RhtnmPlatform,
    "zztj": ZztjPlatform,
    "hx": HxPlatform,
    "kcshop": KcshopPlatform,
    "hxlx": HxlxPlatform,
    "gykgah": GykgahPlatform,
    "gksd": GksdPlatform,
    "qdtfyy": QdtfyyPlatform,
    "shhfyy": ShhfyyPlatform,
    "scjzj": ScjzjPlatform,
    "jzjcg": JzjcgPlatform,
    "cqtjg": CqtjgPlatform,
    "cqxhyf": CqxhyfPlatform,
    "cqpjyy": CqpjyyPlatform,
    "yanxitang": YanxitangPlatform,
    "combrain_jysc": CombrainJyscPlatform,
    "xjy": XjyPlatform,
    "hrjk": HrjkPlatform,
    "ddky": DdkyPlatform,
    "gylrt": GylrtPlatform,
    "jshthy": JshthyPlatform,
    "jsay": JsayPlatform,
    "jswm": JswmPlatform,
    "ehhd": EhhdPlatform,
    "hxyxt": HxyxtPlatform,
    "ynqy": YnqyPlatform,
    "taiji": TaijiPlatform,
    "scxh": HuaxinPlatform,
    "sosoyy": SosoyyPlatform,
    # 注册 ABACUS 供应链系统平台适配器。
    "abacus": AbacusPlatform,
    # 注册贝尔康流向采集服务平台适配器。
    "bellcare": BellcarePlatform,
    # 注册能手软件 SCM 查询平台适配器。
    "cox_scm": CoxScmPlatform,
    # 注册流向卡管理系统平台适配器。
    "lsjnd": LsjndPlatform,
    # 注册华润医药商业上游数据服务平台适配器。
    "crpcg": CrpcgPlatform,
    # 注册四川本草堂药业协同办公系统平台适配器。
    "scbct": ScbctPlatform,
    # 注册药德供应商流向平台适配器。
    "yaoud": YaoudPlatform,
    # 注册华润德信行流向查询平台适配器。
    "dexinxing": DexinxingPlatform,
    # 注册南京医药国药 DDI 数据直连系统平台适配器。
    "njyygy": NjyygyPlatform,
    # 注册成都聚仁堂 FineReport 数据报表系统平台适配器。
    "jrt": JrtPlatform,
    # 注册米伦厂商合作平台适配器。
    "milun": MilunPlatform,
}


# 定义平台适配器创建函数。
def create_platform(company_name, account, printer=None):

    """
    创建平台协议适配器实例。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 平台协议适配器实例。
    :rtype: BasePlatform
    """

    # 读取账号配置中的平台标识。
    platform_name = account.get("平台")

    # 校验平台标识是否已经注册。
    if platform_name not in PLATFORM_REGISTRY:

        # 抛出未注册平台异常。
        raise KeyError(f"未注册平台适配器：{platform_name}")

    # 读取平台标识对应的适配器类。
    platform_class = PLATFORM_REGISTRY[platform_name]

    # 创建并返回平台适配器实例。
    return platform_class(company_name, account, printer=printer)
