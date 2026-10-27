# -*- coding: utf-8 -*-
"""
DDI 协议直连框架包。

DDI/
  run_ddi.py                         # 总入口：按商业名称或批量 enabled 运行
  ddi_framework/
    account_config.py                # 商业名称、账号、密码、平台配置字典
    platform_registry.py             # 根据 platform 派发适配器
    http_client.py                   # 协议请求、Cookie 管理
    print_handler.py                 # 控制台标准日志、颜色、阶段分隔线与路径展示
    captcha_solver.py                # 普通验证码、滑块验证码、点选验证码预留
    download_watcher.py              # 下载目录监听与重命名
    reverse_utils.py                 # 全项目通用逆向能力库
    flow_cleaner.py                  # 配送流向与纯销流向复制用标准 Excel 生成
    hardware_profile.py              # 启动阶段 Windows 硬件型号采集与格式化
    license_guard.py                 # 本地授权文件签名校验与运行准入控制
    task_log.py                      # 本次运行 Excel 日志、脱敏阶段时间线记录与样式生成
    task_core.py                     # 无 GUI 依赖的任务请求、事件、筛选、预设与受控调度接口
    task_execution.py                # 无界面公共单商业协议执行、查询、导出与 Excel 落地服务
    task_runtime.py                  # 无界面公共任务运行时，连接授权、调度、日志与公共执行服务
    startup_changelog.py             # 启动阶段 V1 至 V8 更新日志配置与当前版本展示文本
  tools/
    license_tool.py                  # 本地授权文件签名生成工具
    platforms/
      base.py                        # 平台适配器基类
      jzt.py                         # 九州通平台登录适配器
      gyfj.py                        # 国药控股福建平台登录适配器
      pzhhr.py                       # 厦门片仔癀宏仁平台登录适配器
      hljald.py                      # 黑龙江阿拉丁平台登录适配器
      gzyy.py                        # 广州医药平台登录适配器
      gyjl.py                        # 国药控股吉林平台协议适配器
      tyjsln.py                      # 通用技术辽宁医药平台协议适配器
      fjxzj.py                       # 福建新紫金医药平台协议适配器
      gdwst.py                       # 广东五嗣堂医药平台协议适配器
      hreport.py                     # HReport 供应商查询系统协议适配器（含前端验证码字段与汇总类流向）
      fjjztzh.py                     # 福建九州通中化平台协议适配器
      gkgdjm.py                      # 国控国大江门平台协议适配器
      dsl.py                         # 大参林平台协议适配器
      hljdzpa.py                     # 黑龙江大众平安平台协议适配器
      dlfdyy.py                      # 大连方大药业平台协议适配器
      qdtfyy.py                      # 青岛同方药业连锁有限公司活字格平台适配器
      shhfyy.py                      # 上海汇丰医药药材有限责任公司数据服务云平台协议适配器
      scjzj.py                       # 四川聚之家医药有限公司聚创供应商系统协议适配器
      jzjcg.py                       # 健之佳采购云销售明细查询协议适配器
      cqtjg.py                       # 重庆桐君阁大药房连锁有限责任公司桐君阁供应商流向系统协议适配器
      cqxhyf.py                       # 重庆鑫斛药房连锁有限公司数据流向系统协议适配器
      cqpjyy.py                       # 重庆普健医药有限公司普健数据协同平台协议适配器
      yanxitang.py                   # 燕喜堂 SRM 系统协议适配器
      combrain_jysc.py               # 康博士 ABrain 流向查询系统协议适配器
      gjjk.py                        # 高济健康 SRM 平台协议适配器
      jxhqrz.py                      # 江西黄庆仁栈平台协议适配器
      hnhcyy.py                      # 河南慧采医药平台协议适配器
      sxtzcx.py                      # 山西天泽诚信平台协议适配器
      rhtnm.py                       # 仁和堂内蒙古平台协议适配器
      zztj.py                        # 漳州天健医药平台协议适配器
      hx.py                          # 海翔供应链平台协议适配器
      kcshop.py                      # KCShop 流向管理系统协议适配器
      hxlx.py                        # 洪兴流向系统协议适配器
      gykgah.py                      # 国控安徽信息服务平台协议适配器
      gksd.py                        # 国控山东数据流向服务系统协议适配器
      ddky.py                        # 叮当快药DTP流向系统协议适配器
      gylrt.py                       # 国药乐仁堂数据服务中心协议适配器
      jshthy.py                      # 江苏恒泰华洋全亿健康 OA 平台协议适配器
      jsay.py                        # 江苏澳洋 FineReport 数据分析系统协议适配器
      jswm.py                        # 江苏卫民数据智能管理系统协议适配器
      ehhd.py                        # 恩华和达经典 ASP 查询系统协议适配器
    hxyxt.py                       # 鸿翔一心堂 SRM FineReport 供应商流向平台协议适配器
    ynqy.py                        # 雨诺轻应用知流向同表类型拆分协议适配器
    taiji.py                       # 四川太极大药房连锁有限公司 JSP 表单流向查询协议适配器
    huaxin.py                      # 四川华信药业有限责任公司 FineReport 协议适配器
    sosoyy.py                      # 西昌东升大药房连锁有限公司搜搜电商协议适配器
    abacus.py                      # 四川圣杰药业有限公司 ABACUS 供应链系统协议适配器
    bellcare.py                    # 四川贝尔康大药房连锁有限公司流向采集服务平台协议适配器
    cox_scm.py                     # 成都高济良元大药房连锁有限公司能手软件 SCM 查询平台协议适配器
    lsjnd.py                       # 凉山佳能达医药贸易有限责任公司流向卡管理系统协议适配器
    startup_avatar_art.py            # 启动像素头像 ANSI 色块输出
"""

# 导入平台适配器基类。
from ddi_framework.platforms.base import BasePlatform

# 导入协议请求客户端。
from ddi_framework.http_client import HttpResult

# 导入协议请求客户端。
from ddi_framework.http_client import ProtocolHttpClient

# 导入验证码识别器。
from ddi_framework.captcha_solver import CaptchaSolver

# 导入 AES-ECB 加密器。
from ddi_framework.captcha_solver import AesEcbEncryptor

# 导入下载监听器。
from ddi_framework.download_watcher import DownloadWatcher

# 导入 Excel 样式函数。
from ddi_framework.excel_style import apply_standard_excel_style

# 导入授权签名载荷构建函数。
from ddi_framework.license_guard import build_license_payload_bytes

# 导入运行环境身份构建函数。
from ddi_framework.license_guard import build_runtime_identity

# 导入默认授权版本。
from ddi_framework.license_guard import DEFAULT_LICENSE_VERSION

# 导入授权文件默认名称。
from ddi_framework.license_guard import LICENSE_FILE_NAME

# 导入授权校验异常类型。
from ddi_framework.license_guard import LicenseError

# 导入运行授权校验函数。
from ddi_framework.license_guard import ensure_runtime_license

# 导入日志打印器。
from ddi_framework.print_handler import PrintHandler

# 导入无界面任务请求对象。
from ddi_framework.task_core import TaskRequest

# 导入无界面任务事件对象。
from ddi_framework.task_core import TaskEvent

# 导入无界面任务协调器。
from ddi_framework.task_core import TaskCoordinator

# 导入 MD5 摘要函数。
from ddi_framework.reverse_utils import md5_hex

# 导入 SHA256 摘要函数。
from ddi_framework.reverse_utils import sha256_hex

# 导入 AES-CBC 加密函数。
from ddi_framework.reverse_utils import aes_cbc_pkcs7_base64

# 导入 3DES-CBC 加密函数。
from ddi_framework.reverse_utils import triple_des_cbc_pkcs7_base64

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

# 导入 HReport 平台适配器。
from ddi_framework.platforms.hreport import HreportPlatform

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

# 导入高济健康平台适配器。
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

# 导入 KCShop 平台适配器。
from ddi_framework.platforms.kcshop import KcshopPlatform

# 导入洪兴流向系统平台适配器。
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

# 导入公共单商业协议执行函数。
from ddi_framework.task_execution import execute_company

# 导入无界面 DDI 运行时。
from ddi_framework.task_runtime import DdiTaskRuntime
