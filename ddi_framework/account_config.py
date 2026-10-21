# -*- coding: utf-8 -*-
"""
商业账号公开模板。

本模块保存可提交的商业平台元数据与空白账号密码字段。
真实账号密码必须只保存在同目录的 account_config_local.py 中；该私有文件由 Git 忽略且不会上传到 GitHub。
"""

# 导入 JSON 编解码模块。
import json

# 导入对象深拷贝模块。
import copy

# 导入操作系统路径模块。
import os

# 导入临时文件创建模块。
import tempfile

# 导入系统信息模块。
import sys

# 导入文件系统路径处理模块。
from pathlib import Path


# 配置所有商业平台公开元数据。
ACCOUNTS = {
    "辽宁九州通医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FH7", "FLJ"],
        "日志机构编码": "FH7",
        "操作员名称": "辽宁中联医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "大连九州通医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FTD"],
        "日志机构编码": "FTD",
        "操作员名称": "大连九州通医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "福建九州通医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FDB", "FC1", "FGP", "FJJ", "FK1", "FK3", "FK5", "FZH"],
        "日志机构编码": "FDB",
        "操作员名称": "福建九州通医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "海南九州通医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FN9"],
        "日志机构编码": "FN9",
        "操作员名称": "海南九州通医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "广东九州通医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FDS", "FB2", "FD7", "FH0", "FN9", "FZQ", "G00"],
        "日志机构编码": "FDS",
        "操作员名称": "广东九州通医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "广东九州通医药有限公司1": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FDS", "FB2", "FD7", "FH0", "FN9", "FP5", "FQL", "FZQ", "G00"],
        "日志机构编码": "FDS",
        "操作员名称": "广东九州通医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "九州通医药集团股份有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FDG","FC5","FH1","FD4","FD3","FD5","FB9","FK9","FL5","FWZ","FX6","FY5","FI9","R80","FRL","A01","A03","A04","A11","A49","A58","A15"],
        "日志机构编码": "FDG",
        "操作员名称": "九州通医药集团股份有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "河南九州通医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FDW", "FB5", "FGU", "FH9", "FLY", "FM5", "FPD", "FPE", "FR9", "FRK", "FSC", "FVZ", "FW1", "FXC", "FZA", "FZM"],
        "日志机构编码": "FDW",
        "操作员名称": "河南九州通医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "内蒙古九州通医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FH6"],
        "日志机构编码": "FH6",
        "操作员名称": "内蒙古九州通医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "赤峰九州通医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FWF"],
        "日志机构编码": "FWF",
        "操作员名称": "赤峰九州通医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "安徽九州通医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FWA", "FAK"],
        "日志机构编码": "FWA",
        "操作员名称": "安徽九州通医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "北京九州通医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FDJ", "TH2"],
        "日志机构编码": "FDJ",
        "操作员名称": "北京九州通医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "河北九州通医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FHJ", "FM9", "R21"],
        "日志机构编码": "FHJ",
        "操作员名称": "河北九州通医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "广西九州通医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FC6"],
        "日志机构编码": "FC6",
        "操作员名称": "广西九州通医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "贵州九州通达医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FX8"],
        "日志机构编码": "FX8",
        "操作员名称": "贵州九州通达医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "江苏九州通医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FDC", "FEF", "FGF", "FH2", "FLC", "FMA", "FPT", "FRX", "FW9"],
        "日志机构编码": "FDC",
        "操作员名称": "江苏九州通医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "山东九州通医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FDQ", "D02", "FBK", "FDZ", "FF9", "FFW", "FH3", "FH4", "FS2", "FWD"],
        "日志机构编码": "FDQ",
        "操作员名称": "山东九州通医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "湖南九州通医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FHL", "FMJ", "FSY", "FY8"],
        "日志机构编码": "FHL",
        "操作员名称": "湖南九州通医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    # 配置重庆九州通医药有限公司流向查询账号。
    "重庆九州通医药有限公司": {
        # 声明商业使用的九州通公共平台标识。
        "平台": "jzt",
        # 保存平台登录账号。
        "账号": "",
        # 保存平台登录密码。
        "密码": "",
        # 保存平台登录页面地址。
        "登录页": "https://flow.jztit.com/user/login.html",
        # 保存平台查询接口路径。
        "查询接口": "/_yvanui/query",
        # 保存平台日志接口路径。
        "日志接口": "/_yvanui/execute",
        # 保存平台导出接口路径。
        "导出接口": "/api/flowquery/export",
        # 保存账号可查询的机构范围。
        "机构": ["FDM", "FCW", "FKL"],
        # 保存平台操作日志使用的主体机构编码。
        "日志机构编码": "FDM",
        # 保存平台操作日志使用的操作员名称。
        "操作员名称": "重庆九州通医药有限公司",
        # 声明商业可执行的数据类型顺序。
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        # 启用当前商业任务。
        "启用": True,
    },
    "青岛同方药业连锁有限公司": {
        "平台": "qdtfyy",
        "账号": "",
        "密码": "",
        "登录页": "http://erp.qingdaotfyy.com:8070/SRM/",
        "接口根地址": "http://erp.qingdaotfyy.com:8070/SRM",
        "操作员名称": "青岛同方药业连锁有限公司",
        "数据类型列表": ["购进流向", "配送流向", "纯销流向", "总部库存", "门店库存"],
        "启用": True,
    },
    "上海汇丰医药药材有限责任公司": {
        "平台": "shhfyy",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.dyyy.com.cn/wxquery/coframe/auth/login/login.jsp",
        "接口根地址": "https://flow.dyyy.com.cn/wxquery",
        "首页": "https://flow.dyyy.com.cn/wxquery/coframe/auth/skin1/index.jsp",
        "登录接口": "https://flow.dyyy.com.cn/wxquery/coframe/auth/login/org.gocom.components.coframe.auth.LoginManager.login.biz.ext",
        "菜单接口": "https://flow.dyyy.com.cn/wxquery/coframe/auth/login/org.gocom.components.coframe.auth.LoginManager.getMenuData.biz.ext",
        "写会话接口": "https://flow.dyyy.com.cn/wxquery/com.wx.utils.publicMemer.SysRoute.writeSession.biz.ext",
        "查询接口": "https://flow.dyyy.com.cn/wxquery/OnLineDevelopProFiles/DataFlowQuery/cjcx/com.wx.utils.publicMemer.JDBCComponent.dbPageQuery.biz.ext",
        "员工编号": "4106",
        "公司编号": "81",
        "公司代码": "002-HUIFENG",
        "公司名称": "汇丰",
        "部门编号": "3026",
        "部门代码": "GLHNW-532",
        "部门名称": "桂林华诺威",
        "分页大小": 500,
        "数据类型列表": ["购进流向", "库存", "配送流向"],
        "启用": True,
    },
    "四川聚之家医药有限公司": {
        "平台": "scjzj",
        "账号": "",
        "密码": "",
        "登录页": "https://srm.tyaow.com/login",
        "接口根地址": "https://prod-srm-api.tyaow.com",
        "登录主体": "广东健元药业有限公司",
        "登录主体ID": 980,
        "流向卡ID": 1585,
        "流向卡编号": "LXK00003160",
        "流向卡名称": "人表皮10g",
        "分页大小": 500,
        "操作员名称": "四川聚之家医药有限公司",
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "云南健之佳重庆勤康药业有限公司": {
        "平台": "jzjcg",
        "账号": "",
        "密码": "",
        "登录页": "http://220.163.118.50:9994/index/login.html",
        "接口根地址": "http://220.163.118.50:9994",
        "登录接口": "http://220.163.118.50:9994/srm/base/api/login/userName",
        "区间接口": "http://220.163.118.50:9994/srm/customer/api/cellInfo/getSection",
        "查询接口": "http://220.163.118.50:9994/srm/customer/api/cellSupplierInfo/getListForPageSellSupplier",
        "分页大小": 500,
        "操作员名称": "云南健之佳重庆勤康药业有限公司",
        "数据类型列表": ["配送流向"],
        "启用": True,
    },
    "四川勤康健之佳医药有限责任公司": {
        "平台": "jzjcg",
        "账号": "",
        "密码": "",
        "登录页": "http://220.163.118.50:9994/index/login.html",
        "接口根地址": "http://220.163.118.50:9994",
        "登录接口": "http://220.163.118.50:9994/srm/base/api/login/userName",
        "区间接口": "http://220.163.118.50:9994/srm/customer/api/cellInfo/getSection",
        "查询接口": "http://220.163.118.50:9994/srm/customer/api/cellSupplierInfo/getListForPageSellSupplier",
        "分页大小": 500,
        "操作员名称": "四川勤康健之佳医药有限责任公司",
        "数据类型列表": ["配送流向"],
        "启用": True,
    },
    "健之佳医药连锁集团股份有限公司": {
        "平台": "jzjcg",
        "账号": "",
        "密码": "",
        "登录页": "http://220.163.118.50:9994/index/login.html",
        "接口根地址": "http://220.163.118.50:9994",
        "登录接口": "http://220.163.118.50:9994/srm/base/api/login/userName",
        "区间接口": "http://220.163.118.50:9994/srm/customer/api/cellInfo/getSection",
        "查询接口": "http://220.163.118.50:9994/srm/customer/api/cellSupplierInfo/getListForPageSellSupplier",
        "分页大小": 500,
        "操作员名称": "健之佳医药连锁集团股份有限公司",
        "数据类型列表": ["配送流向"],
        "启用": True,
    },
    "江药集团(四川)有限公司": {
        "平台": "combrain_jysc",
        "账号": "",
        "密码": "",
        "登录页": "http://47.99.244.155:8189/intelsys_service_abrain/home",
        "站点根地址": "http://47.99.244.155:8189/intelsys_service_abrain",
        "数据源": "YYB",
        "数据源编码": "user",
        "分页大小": 500,
        "操作员名称": "江药集团(四川)有限公司",
        "数据类型列表": ["配送流向", "库存", "购进流向"],
        "启用": True,
    },
    "重庆桐君阁大药房连锁有限责任公司": {
        "平台": "cqtjg",
        "账号": "",
        "密码": "",
        "登录页": "http://tjgpf.taiji.com:8999/gwtapp/",
        "接口根地址": "http://tjgpf.taiji.com:8999",
        "登录接口": "http://tjgpf.taiji.com:8999/gwtapp/user/login",
        "查询接口": "http://tjgpf.taiji.com:8999/gwtapp/saflow/dataService",
        "GWT模块地址": "http://tjgpf.taiji.com:8999/gwtapp/saflow/",
        "GWT序列化策略": "850DF97B2D318D65FFDC591212C49567",
        "GWT强名称": "97246FD42C3EEA52AB9C2FF29A5E7C25",
        "角色类型": "查询代理",
        "角色类型编码": "6",
        "密码前缀": "*&^%Ybghs154.",
        "分页大小": 300,
        "操作员名称": "重庆桐君阁大药房连锁有限责任公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "纯销"],
        "启用": True,
    },
    "重庆鑫斛药房连锁有限公司": {
        "平台": "cqxhyf",
        "账号": "",
        "密码": "",
        "登录页": "http://xcx.azmks.com/index/dataflow/login.html?spm=",
        "接口根地址": "http://xcx.azmks.com",
        "登录接口": "http://xcx.azmks.com/index/dataflow/login.html?spm=",
        "数据页根路径": "/index/dataflow",
        "库存类型编码": "1",
        "最大分页页数": 500,
        "操作员名称": "重庆鑫斛药房连锁有限公司",
        "数据类型列表": ["购进流向", "配送流向", "库存", "纯销流向"],
        "启用": True,
    },
    "重庆万鑫药房连锁有限公司": {
        "平台": "hreport",
        "账号": "",
        "密码": "",
        "登录页": "http://222.177.143.25:7070/hreport-manager/login",
        "登录接口": "http://222.177.143.25:7070/hreport-manager/j_spring_security_check",
        "登录成功路径": "/hreport-manager/login/loginCheck",
        "登录失败路径": "/hreport-manager/login?error=1",
        "首页": "http://222.177.143.25:7070/hreport-manager/login/loginCheck",
        "报表页": "http://222.177.143.25:7070/hreport-manager/pages/supplierManager/reportMgrQueryInfo.jsp",
        "报表参数接口": "http://222.177.143.25:7070/hreport-manager/vendorReportMgr/qryParamList",
        "查询接口": "http://222.177.143.25:7070/hreport-manager/vendorReportMgr/qryReportMeanInfo",
        "报表功能编号": {"购进流向": "37", "配送流向": "45", "连锁库存": "10001", "门店库存": "10002"},
        "查询字段模板": {
            "配送流向": {"beginDate": "{start_date}", "endDate": "{end_date}", "buyer": "", "wareid": "", "billname": "", "userid": "", "factoryname": "", "funcId": "{func_id}"},
        },
        "数据类型列表": ["购进流向", "配送流向", "连锁库存", "门店库存"],
        "启用": True,
    },
    "重庆普健医药有限公司": {
        "平台": "cqpjyy",
        "账号": "",
        "密码": "",
        "登录页": "https://data.pujian.com",
        "接口根地址": "https://data.pujian.com/pjyy-deepexi-datanalysis-center",
        "登录接口路径": "/login/loginAccount",
        "刷新令牌接口路径": "/login/refreshToken",
        "系统类型": 2,
        "分页大小": 200,
        "操作员名称": "重庆普健医药有限公司",
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "重庆唐氏药业有限公司": {
        "平台": "hreport",
        "账号": "",
        "密码": "",
        "登录页": "http://222.178.91.242:7171/hreport-manager/login",
        "登录接口": "http://222.178.91.242:7171/hreport-manager/j_spring_security_check",
        "登录成功路径": "/hreport-manager/login/loginCheck",
        "登录失败路径": "/hreport-manager/login?error=1",
        "首页": "http://222.178.91.242:7171/hreport-manager/login/loginCheck",
        "报表页": "http://222.178.91.242:7171/hreport-manager/pages/supplierManager/reportMgrQueryInfo.jsp",
        "报表参数接口": "http://222.178.91.242:7171/hreport-manager/vendorReportMgr/qryParamList",
        "查询接口": "http://222.178.91.242:7171/hreport-manager/vendorReportMgr/qryReportMeanInfo",
        "报表功能编号": {"购进流向": "37", "库存": "44", "配送流向": "10002"},
        "查询字段模板": {
            "购进流向": {"execdate": "{start_date}", "execdate1": "{end_date}", "buyer": "", "userid": "", "billcode": "", "warecode": "", "funcId": "{func_id}"},
            "库存": {"userid": "", "warecode": "", "busno": "", "vencuscode": "", "funcId": "{func_id}"},
            "配送流向": {"begin_execdate": "{start_date}", "end_execdate": "{end_date}", "billname": "", "vencusno": "", "busno": "", "warecode": "", "userid": "", "funcId": "{func_id}"},
        },
        "使用平台导出": False,
        "数据类型列表": ["购进流向", "库存", "配送流向"],
        "启用": True,
    },
    "重庆鸿翔一心堂药业有限公司": {
        "平台": "hxyxt",
        "账号": "",
        "子账号": "1004",
        "密码": "",
        "站点根地址": "https://yxt-srm.hxyxt.com",
        "登录页": "https://yxt-srm.hxyxt.com/user/login?redirect=%2Fhome",
        "公钥接口": "https://yxt-srm.hxyxt.com/els/account/noToken/getEncryptedKey",
        "登录接口": "https://yxt-srm.hxyxt.com/els/account/login",
        "报表跳转接口": "https://yxt-srm.hxyxt.com/els/saleMaterialFlow/saleMaterialFlowHead/toFine",
        "配送流向报表入口": "/WebReport/decision/v10/entry/access/old-platform-reportlet-entry-941",
        "决策路径": "/decision",
        "公司代码": "1005",
        "公司代码名称": "重庆公司",
        "供应商参数": "20407502",
        "商品列表参数": "156115",
        "纸张宽度": 754,
        "纸张高度": 779,
        "最大查询天数": 90,
        "操作员名称": "重庆鸿翔一心堂药业有限公司",
        "数据类型列表": ["配送流向"],
        "启用": True,
    },
    "一心堂药业集团股份有限公司": {
        "平台": "hxyxt",
        "账号": "",
        "子账号": "1003",
        "密码": "",
        "站点根地址": "https://yxt-srm.hxyxt.com",
        "登录页": "https://yxt-srm.hxyxt.com/user/login?redirect=%2Fhome",
        "公钥接口": "https://yxt-srm.hxyxt.com/els/account/noToken/getEncryptedKey",
        "登录接口": "https://yxt-srm.hxyxt.com/els/account/login",
        "报表跳转接口": "https://yxt-srm.hxyxt.com/els/saleMaterialFlow/saleMaterialFlowHead/toFine",
        "配送流向报表入口": "/WebReport/decision/v10/entry/access/old-platform-reportlet-entry-941",
        "决策路径": "/decision",
        "公司代码": "1002",
        "公司代码名称": "云南公司",
        "供应商参数": "10068103",
        "商品列表参数": "633029','156115",
        "纸张宽度": 564,
        "纸张高度": 779,
        "最大查询天数": 90,
        "操作员名称": "一心堂药业集团股份有限公司",
        "数据类型列表": ["配送流向"],
        "启用": True,
    },
    "四川一心堂医药连锁有限公司": {
        "平台": "hxyxt",
        "账号": "",
        "子账号": "1003",
        "密码": "",
        "站点根地址": "https://yxt-srm.hxyxt.com",
        "登录页": "https://yxt-srm.hxyxt.com/user/login?redirect=%2Fhome",
        "公钥接口": "https://yxt-srm.hxyxt.com/els/account/noToken/getEncryptedKey",
        "登录接口": "https://yxt-srm.hxyxt.com/els/account/login",
        "报表跳转接口": "https://yxt-srm.hxyxt.com/els/saleMaterialFlow/saleMaterialFlowHead/toFine",
        "配送流向报表入口": "/WebReport/decision/v10/entry/access/old-platform-reportlet-entry-941",
        "决策路径": "/decision",
        "公司代码": "",
        "公司代码名称": "",
        "公司代码列表": [
            {"公司代码": "1003", "公司代码名称": "攀枝花公司", "商品列表参数": "156115"},
            {"公司代码": "1006", "公司代码名称": "四川公司", "商品列表参数": "156115"},
        ],
        "供应商参数": "32545202",
        "商品列表参数": "156115",
        "纸张宽度": 754,
        "纸张高度": 779,
        "最大查询天数": 90,
        "操作员名称": "四川一心堂医药连锁有限公司",
        "数据类型列表": ["配送流向"],
        "启用": True,
    },
    "一心堂药业(贵州)有限公司": {
        "平台": "hxyxt",
        "账号": "",
        "子账号": "1005",
        "密码": "",
        "站点根地址": "https://yxt-srm.hxyxt.com",
        "登录页": "https://yxt-srm.hxyxt.com/user/login?redirect=%2Fhome",
        "公钥接口": "https://yxt-srm.hxyxt.com/els/account/noToken/getEncryptedKey",
        "登录接口": "https://yxt-srm.hxyxt.com/els/account/login",
        "报表跳转接口": "https://yxt-srm.hxyxt.com/els/saleMaterialFlow/saleMaterialFlowHead/toFine",
        "配送流向报表入口": "/WebReport/decision/v10/entry/access/old-platform-reportlet-entry-941",
        "决策路径": "/decision",
        "公司代码": "1002",
        "公司代码名称": "贵州公司",
        "供应商参数": "20407503",
        "商品列表参数": "156115",
        "纸张宽度": 754,
        "纸张高度": 779,
        "最大查询天数": 90,
        "操作员名称": "一心堂药业(贵州)有限公司",
        "数据类型列表": ["配送流向"],
        "启用": True,
    },
    "广西鸿翔一心堂药业有限责任公司": {
        "平台": "hxyxt",
        "账号": "",
        "子账号": "1002",
        "密码": "",
        "站点根地址": "https://yxt-srm.hxyxt.com",
        "登录页": "https://yxt-srm.hxyxt.com/user/login?redirect=%2Fhome",
        "公钥接口": "https://yxt-srm.hxyxt.com/els/account/noToken/getEncryptedKey",
        "登录接口": "https://yxt-srm.hxyxt.com/els/account/login",
        "报表跳转接口": "https://yxt-srm.hxyxt.com/els/saleMaterialFlow/saleMaterialFlowHead/toFine",
        "配送流向报表入口": "/WebReport/decision/v10/entry/access/old-platform-reportlet-entry-941",
        "决策路径": "/decision",
        "公司代码": "1001",
        "公司代码名称": "广西公司",
        "供应商参数": "10815701",
        "商品列表参数": "156115",
        "纸张宽度": 754,
        "纸张高度": 779,
        "最大查询天数": 90,
        "操作员名称": "广西鸿翔一心堂药业有限责任公司",
        "数据类型列表": ["配送流向"],
        "启用": True,
    },
    "重庆市开州区医药有限责任公司": {
        "平台": "ynqy",
        "账号": "",
        "密码": "",
        "登录页": "http://58.144.199.103:8064/",
        "接口根地址": "http://58.144.199.103:8063/",
        "企业号": "001",
        "签名企业编码": "null",
        "报表名称": "总部进销存",
        "报表标识": "MobileCommerce_SupplyFLow_006",
        "请求重试次数": 3,
        "操作员名称": "重庆市开州区医药有限责任公司",
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "上海九州通医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FDL"],
        "日志机构编码": "FDL",
        "操作员名称": "上海九州通医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "天津九州通达医药有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "查询接口": "/_yvanui/query",
        "日志接口": "/_yvanui/execute",
        "导出接口": "/api/flowquery/export",
        "机构": ["FC2"],
        "日志机构编码": "FC2",
        "操作员名称": "天津九州通达医药有限公司",
        "数据类型列表": ["配送流向", "购进流向", "库存", "报损流向"],
        "启用": True,
    },
    "国药控股福建有限公司": {
        "平台": "gyfj",
        "账号": "",
        "密码": "",
        "登录页": "http://spfj.sinopharm-fj.com:8001",
        "登录接口": "http://spfj.sinopharm-fj.com:8001/api/login",
        "查询接口": "http://spfj.sinopharm-fj.com:8001/api/query",
        "货主名称": "国控福建",
        "货主编码": "1",
        "数据类型列表": ["购进流向", "配送流向", "库存", "报损流向"],
        "启用": True,
    },
    "安徽新聚源医药科技有限公司": {
        "平台": "xjy",
        "账号": "",
        "密码": "",
        "登录页": "http://120.193.90.144:10006/directdata/",
        "接口根地址": "http://120.193.90.144:10006",
        "首页地址": "http://120.193.90.144:10006/directdata/%E6%9F%A5%E8%AF%A2%E9%A6%96%E9%A1%B5",
        "页面映射": {
            "购进流向": {"页面名称": "入库查询", "路径": "%E6%9F%A5%E8%AF%A2%E5%85%A5%E5%BA%93%E6%98%8E%E7%BB%86", "查询按钮": "r3c47p_btn", "导出按钮": "r5c47p_btn"},
            "配送流向": {"页面名称": "出库查询", "路径": "%E6%9F%A5%E8%AF%A2%E5%87%BA%E5%BA%93%E6%98%8E%E7%BB%86", "查询按钮": "r3c47p_btn", "导出按钮": "r5c47p_btn"},
            "库存": {"页面名称": "库存查询", "路径": "%E6%9F%A5%E8%AF%A2%E5%BA%93%E5%AD%98%E6%98%8E%E7%BB%86", "查询按钮": "r3c44p_btn", "导出按钮": "r5c44p_btn"},
        },
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "国药控股安徽华宁医药有限公司": {
        "平台": "gykgah",
        "账号": "",
        "密码": "",
        "登录页": "https://www.gykgah.com:9027/",
        "接口根地址": "https://www.gykgah.com:9027",
        "首页地址": "https://www.gykgah.com:9027/Index.aspx",
        "页面映射": {
            "购进流向": {"页面名称": "采购查询", "路径": "/FlowSystem/PurDataQuery.aspx"},
            "配送流向": {"页面名称": "销售查询", "路径": "/FlowSystem/SaleDataQuery.aspx"},
            "库存": {"页面名称": "库存查询", "路径": "/FlowSystem/StockDataQuery.aspx"},
        },
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "临时浏览器兜底": True,
        "启用": True,
    },
    "国药控股济南有限公司": {
        "平台": "gksd",
        "账号": "",
        "密码": "",
        "登录页": "http://222.173.24.186:9090/",
        "接口根地址": "http://222.173.24.186:9090",
        "货主编号": "20",
        "货主名称": "国药控股济南有限公司",
        "表单编码": "gb2312",
        "响应编码": "gb2312",
        "页面映射": {
            "购进流向": {"页面名称": "采购入库查询", "路径": "/web_flow/flow_pur_query.aspx", "需要日期": True, "日期字段": "创建日期"},
            "配送流向": {"页面名称": "销售出库查询", "路径": "/web_flow/flow_sale_query.aspx", "需要日期": True, "日期字段": "开单日期", "日期口径": "开单日期"},
            "库存": {"页面名称": "药品库存查询", "路径": "/web_flow/flow_inv_query.aspx", "需要日期": False},
        },
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "安徽华人健康医药股份有限公司": {
        "平台": "hrjk",
        "账号": "",
        "密码": "",
        "登录页": "http://idc.fastjz.com:2022/jzapi/",
        "接口根地址": "http://idc.fastjz.com:2022/jzapi",
        "验证码接口": "http://idc.fastjz.com:2022/jzapi/init/verificationCode",
        "登录接口": "http://idc.fastjz.com:2022/jzapi/login",
        "查询接口": "http://idc.fastjz.com:2022/jzapi/sys/query/getFrameValue",
        "页面映射": {
            "购进流向": {"页面名称": "采购数据查询", "查询名称": "flowPurchaseSelect"},
            "配送流向": {"页面名称": "销售数据查询", "查询名称": "flowSalesSelect"},
            "库存": {"页面名称": "仓库库存查询", "查询名称": "flowStockSelect"},
        },
        "分页大小": 100,
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "仁和药房网(北京)医药科技有限公司": {
        "平台": "ddky",
        "账号": "",
        "密码": "",
        "登录页": "https://flowsails.ddky.com:11443/user/login",
        "接口根地址": "https://flowsails.ddky.com:11443",
        "验证码接口": "https://flowsails.ddky.com:11443/api/kcone/auth/captcha",
        "登录接口": "https://flowsails.ddky.com:11443/api/kcone/auth/login",
        "初始化接口": "https://flowsails.ddky.com:11443/api/kcone/system/init",
        "页面映射": {
            "购进流向": {"页面名称": "采购数据", "路径": "/dtp/V_JXXGYY_FLOW_PUR/list"},
            "配送流向": {"页面名称": "配送数据", "路径": "/dtp/V_JXXGYY_FLOW_DIS/list"},
            "库存": {"页面名称": "库存数据", "路径": "/dtp/V_JXXGYY_FLOW_STK/list", "处理方式": "pass"},
        },
        "分页大小": 100,
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "国药乐仁堂(廊坊)医药贸易有限公司": {
        "平台": "gylrt",
        "账号": "",
        "密码": "",
        "首页地址": "http://61.182.253.84:8090/dw/",
        "登录页": "http://61.182.253.84:8090/dw/login",
        "接口根地址": "http://61.182.253.84:8090",
        "验证码接口": "http://61.182.253.84:8090/ds/login/validateCode",
        "登录接口": "http://61.182.253.84:8090/ds/auth/login",
        "库存接口": "http://61.182.253.84:8090/ds/flow/listInventoryView",
        "采购销售接口": "http://61.182.253.84:8090/ds/flow/listPurchaseView",
        "页面映射": {
            "库存": {"页面名称": "库存查询", "路径": "/dw/flow/InventoryList"},
            "购进流向": {"页面名称": "采购销售", "路径": "/dw/flow/PurchaseList", "单据类型": ["采购订单", "采购更正", "采退订单"]},
            "配送流向": {"页面名称": "采购销售", "路径": "/dw/flow/PurchaseList", "单据类型": ["销售订单", "销退订单", "销售更正"]},
        },
        "分页大小": 200,
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "江苏恒泰华洋医药有限公司": {
        "平台": "jshthy",
        "账号": "",
        "密码": "",
        "登录页": "http://oa.myquanyi.com/wui/index.html#/login?type=2&_key=8piqgn",
        "接口根地址": "http://oa.myquanyi.com",
        "登录表单接口": "http://oa.myquanyi.com/api/hrm/login/getLoginForm",
        "RSA参数接口": "http://oa.myquanyi.com/rsa/weaver.rsa.GetRsaInfo",
        "登录接口": "http://oa.myquanyi.com/api/hrm/login/checkLogin",
        "语言编号": "7",
        "登录类型": "2",
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": False,
    },
    "江苏澳洋医药物流有限公司": {
        "平台": "jsay",
        "账号": "",
        "密码": "",
        "登录页": "http://fr.aoyang.com/WebReport/decision/login",
        "接口根地址": "http://fr.aoyang.com",
        "应用路径": "/WebReport/decision",
        "流向入口ID": "10870e87-35d4-487b-8906-1a849438f19c",
        "页面映射": {
            "库存": {"页面名称": "库存", "reportIndex": 0},
            "购进流向": {"页面名称": "购进", "reportIndex": 1},
            "配送流向": {"页面名称": "销售", "reportIndex": 2},
        },
        "最大查询天数": 90,
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "江苏元弘医药有限公司": {
        "平台": "jswm",
        "账号": "",
        "密码": "",
        "登录页": "http://117.89.85.216:8053/trunk/platform/jsp/relogin.jsp",
        "首页": "http://117.89.85.216:8053/trunk/platform/jsp/v2.jsp",
        "接口根地址": "http://117.89.85.216:8053",
        "应用路径": "/decision",
        "登录接口": "http://117.89.85.216:8053/LoginAction/dologin.do",
        "菜单接口": "http://117.89.85.216:8053/AjaxAction/getMenuTree.do",
        "页面映射": {
            "购进流向": {"页面名称": "商品采购流向", "reportlet": "sp/yhpurin.cpt", "纸张宽度": 865, "纸张高度": 658},
            "配送流向": {"页面名称": "商品销售流向(明细)", "reportlet": "sp/yhjoinout.cpt", "纸张宽度": 800, "纸张高度": 658},
            "库存": {"页面名称": "商品库存查询", "reportlet": "sp/yhbalance.cpt", "纸张宽度": 800, "纸张高度": 700},
        },
        "最大查询天数": 90,
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "江苏恩华和达医药有限公司（连锁）": {
        "平台": "ehhd",
        "账号": "",
        "密码": "",
        "登录页": "http://58.218.188.74:88/Login.asp",
        "登录接口": "http://58.218.188.74:88/Login.asp",
        "首页": "http://58.218.188.74:88/default.asp",
        "接口根地址": "http://58.218.188.74:88",
        "表单编码": "gbk",
        "响应编码": "gbk",
        "页面映射": {
            "购进流向": {"页面名称": "采购明细", "查询路径": "purchasedetail.asp", "导出路径": "purchasedetailtoexcel.asp", "需要日期": True},
            "配送流向": {"页面名称": "配送明细", "查询路径": "distributiondetail.asp", "导出路径": "distributiondetailtoexcel.asp", "需要日期": True},
            "纯销流向": {"页面名称": "销售明细", "查询路径": "salesdetail.asp", "导出路径": "salesdetailtoexcel.asp", "需要日期": True},
            "库存": {"页面名称": "库存明细", "查询路径": "stockdetail.asp", "导出路径": "stockdetailtoexcel.asp", "需要日期": False},
        },
        "最大查询天数": 90,
        "数据类型列表": ["购进流向", "配送流向", "纯销流向", "库存"],
        "启用": True,
    },
    "江苏恩华和达医药有限公司（和达）": {
        "平台": "ehhd",
        "账号": "",
        "密码": "",
        "登录页": "http://58.218.188.74:88/Login.asp",
        "登录接口": "http://58.218.188.74:88/Login.asp",
        "首页": "http://58.218.188.74:88/default.asp",
        "接口根地址": "http://58.218.188.74:88",
        "表单编码": "gbk",
        "响应编码": "gbk",
        "页面映射": {
            "购进流向": {"页面名称": "采购明细", "查询路径": "hdpurchasedetail.asp", "导出路径": "hdpurchasedetailtoexcel.asp", "需要日期": True},
            "纯销流向": {"页面名称": "销售明细", "查询路径": "hdsalesdetail.asp", "导出路径": "hdsalesdetailtoexcel.asp", "需要日期": True},
            "库存": {"页面名称": "库存明细", "查询路径": "hdstockdetail.asp", "导出路径": "hdstockdetailtoexcel.asp", "需要日期": False},
        },
        "最大查询天数": 90,
        "数据类型列表": ["购进流向", "纯销流向", "库存"],
        "启用": True,
    },
    "江苏恩华和达医药有限公司（大药房）": {
        "平台": "ehhd",
        "账号": "",
        "密码": "",
        "登录页": "http://58.218.188.74:88/Login.asp",
        "登录接口": "http://58.218.188.74:88/Login.asp",
        "首页": "http://58.218.188.74:88/default.asp",
        "接口根地址": "http://58.218.188.74:88",
        "表单编码": "gbk",
        "响应编码": "gbk",
        "页面映射": {
            "购进流向": {"页面名称": "采购明细", "查询路径": "dyfpurchasedetail.asp", "导出路径": "dyfpurchasedetailtoexcel.asp", "需要日期": True},
            "纯销流向": {"页面名称": "销售明细", "查询路径": "dyfsalesdetail.asp", "导出路径": "dyfsalesdetailtoexcel.asp", "需要日期": True},
            "库存": {"页面名称": "库存明细", "查询路径": "dyfstockdetail.asp", "导出路径": "dyfstockdetailtoexcel.asp", "需要日期": False},
        },
        "最大查询天数": 90,
        "数据类型列表": ["购进流向", "纯销流向", "库存"],
        "启用": True,
    },
    "厦门片仔癀宏仁医药有限公司": {
        "平台": "pzhhr",
        "账号": "",
        "密码": "",
        "登录页": "https://zlcx.hrpzh.com/drugqc/home/login?type=flowLogin",
        "登录接口": "https://zlcx.hrpzh.com/drugqc/home/flowLogin",
        "验证码接口": "https://zlcx.hrpzh.com/drugqc/home/captcha.jpg",
        "首页": "https://zlcx.hrpzh.com/drugqc/home/index?type=flow",
        "公司名称": "厦门片仔癀宏仁医药有限公司",
        "公司编码": "1",
        "数据类型列表": ["配送流向", "购进流向", "库存"],
        "启用": True,
    },
    "黑龙江省阿拉丁医药有限公司": {
        "平台": "hljald",
        "账号": "",
        "密码": "",
        "登录页": "http://flow.hljbnfk.com/login?redirect=%2Findex",
        "验证码接口": "http://flow.hljbnfk.com/prod-api/captchaImage",
        "登录接口": "http://flow.hljbnfk.com/prod-api/login",
        "采购进项接口": "http://flow.hljbnfk.com/prod-api/PurFlow/flowp/list",
        "销售流向接口": "http://flow.hljbnfk.com/prod-api/SaleFlow/flow/list",
        "库存接口": "http://flow.hljbnfk.com/prod-api/InvFlow/flowi/list",
        "数据类型列表": ["配送流向", "购进流向", "库存"],
        "启用": True,
    },
    "广州医药股份有限公司": {
        "平台": "gzyy",
        "账号": "",
        "密码": "",
        "登录页": "https://sip.gzmpc.com/user/login",
        "登录接口": "https://tccloud-gateway.gzmpc.com/sip-usercenter/v1/user/login",
        "进货入库接口": "https://tccloud-gateway.gzmpc.com/sip-dataflow/api/ebbms/su/suPage",
        "销售出库接口": "https://tccloud-gateway.gzmpc.com/sip-dataflow/api/ebbms/sa/saleOutPage",
        "即时库存接口": "https://tccloud-gateway.gzmpc.com/sip-dataflow/api/ebbms/immediate/page",
        "数据类型列表": ["配送流向", "购进流向", "库存"],
        "启用": True,
    },
    "国药控股吉林有限公司": {
        "平台": "gyjl",
        "账号": "",
        "密码": "",
        "登录页": "https://www.sinopharm-jilin.com/lxlogin.php",
        "登录接口": "https://www.sinopharm-jilin.com/lxlogin_action.php",
        "查询页": "https://www.sinopharm-jilin.com/lxinfo.php?code=JH-03429&data=1",
        "查询接口": "https://www.sinopharm-jilin.com/lxinfo_action.php",
        "货主名称": "国控吉林",
        "货主编码": "2",
        "数据类型列表": ["配送流向", "购进流向", "库存"],
        "启用": True,
    },
    "通用技术辽宁医药有限公司": {
        "平台": "tyjsln",
        "账号": "",
        "密码": "",
        "登录页": "https://zhsckh.gt.cn/login",
        "验证码接口": "https://zhsckh.gt.cn/api/blade-auth/oauth/captcha",
        "登录接口": "https://zhsckh.gt.cn/api/blade-auth/oauth/token",
        "租户ID": "000000",
        "OAuth认证头": "Basic c2FiZXI6c2FiZXJfc2VjcmV0",
        "数据类型列表": ["配送流向", "购进流向", "库存"],
        "启用": True,
    },
    "福建新紫金医药有限公司": {
        "平台": "fjxzj",
        "账号": "",
        "密码": "",
        "登录页": "https://provider.kbjcn.com/user/login",
        "验证码接口": "https://provider.kbjcn.com/provider-admin/api/account/captcha",
        "登录接口": "https://provider.kbjcn.com/provider-admin/api/account/login",
        "查询接口": "https://provider.kbjcn.com/provider-admin/api/goods_detail/list",
        "采购商编码": "1",
        "分页大小": 100,
        "数据类型列表": ["配送流向", "购进流向", "报损流向"],
        "启用": True,
    },
    "广东五嗣堂医药有限公司": {
        "平台": "gdwst",
        "账号": "",
        "密码": "",
        "登录页": "http://219.128.255.166:14212/#/login",
        "验证码接口": "http://219.128.255.166:14212/api/auth/captcha",
        "登录接口": "http://219.128.255.166:14212/api/auth/login",
        "数据类型列表": ["配送流向", "购进流向", "库存"],
        "启用": True,
    },
    "深圳市南北医药集团有限公司": {
        "平台": "hreport",
        "账号": "",
        "密码": "",
        "登录页": "http://121.15.7.106:7006/hreport-manager/login",
        "登录接口": "http://121.15.7.106:7006/hreport-manager/j_spring_security_check",
        "登录成功路径": "/hreport-manager/login/loginCheck",
        "登录失败路径": "/hreport-manager/login?error=1",
        "数据类型列表": ["配送流向", "购进流向", "库存"],
        "启用": True,
    },
    "福建九州通中化医药有限公司": {
        "平台": "fjjztzh",
        "账号": "",
        "密码": "",
        "登录页": "http://112.5.108.165:8088/zh/",
        "登录接口": "http://112.5.108.165:8088/zh/sysuser/validate",
        "采购明细接口": "http://112.5.108.165:8088/zh/buybillidx/search",
        "销售明细接口": "http://112.5.108.165:8088/zh/salebillidx/search",
        "当前库存接口": "http://112.5.108.165:8088/zh/storehouse/search",
        "数据类型列表": ["配送流向", "购进流向", "库存"],
        "启用": True,
    },
    "湖南千金大药房连锁有限公司": {
        "平台": "qjdyf",
        "账号": "",
        "密码": "",
        "站点地址": "https://wx.qjdyf.cn",
        "登录页": "https://wx.qjdyf.cn/supplier-front-2.0/#/login",
        "登录接口": "https://wx.qjdyf.cn/supplier/pc/system/user/newVersionLogin",
        "数据类型列表": [],
        "启用": False,
    },
    "重庆和平药房连锁有限责任公司医药保健品分公司": {
        "平台": "cqhp",
        "账号": "",
        "密码": "",
        "租户ID": "Yf20262026",
        "认证站点地址": "https://cqp-sxy-sso.cq-p.com.cn",
        "数据站点地址": "https://new-data-flow.cq-p.com.cn:8080",
        "登录页": "https://cqp-sxy-sso.cq-p.com.cn/#/login",
        "登录接口": "https://cqp-sxy-sso.cq-p.com.cn/api/cqp-sxy-sso-server/blade/doLogin",
        "验证码接口": "https://cqp-sxy-sso.cq-p.com.cn/api/blade-auth/oauth/captcha",
        "数据类型列表": [],
        "启用": False,
    },
    "广西好药师大药房连锁有限公司": {
        "平台": "jzt",
        "账号": "",
        "密码": "",
        "登录页": "https://flow.jztit.com/user/login.html",
        "操作员名称": "桂林华诺威基因药业股份有限公司",
        "机构": ["FC6"],
        "日志机构编码": "FC6",
        "视图查询配置": {
            "配送流向": {
                "sqlId": "/hyschainsalequery/hyschainsalequery@query",
                "参数": {"appUserName": "{login_name}", "startDate": "{start_date}", "endDate": "{end_date}", "chainHeadName": "广西好药师大药房连锁有限公司", "storeName": "", "splitBill": 0},
            },
            "购进流向": {
                "sqlId": "/hyschainpurquery/hyschainpurquery@query",
                "参数": {"appUserName": "{login_name}", "startDate": "{start_date}", "endDate": "{end_date}"},
            },
            "库存": {
                "sqlId": "/hyschaininvquery/hyschaininvquery@query",
                "参数": {"appUserName": "{login_name}"},
            },
        },
        "数据类型列表": ["配送流向", "购进流向", "库存"],
        "启用": True,
    },
    "娄底市健康南门医药零售连锁有限公司": {
        "平台": "hreport",
        "账号": "",
        "密码": "",
        "登录页": "http://gys.jknmyd.com:8077/hreport-manager/login",
        "登录接口": "http://gys.jknmyd.com:8077/hreport-manager/j_spring_security_check",
        "登录成功路径": "/hreport-manager/login/loginCheck",
        "登录失败路径": "/hreport-manager/login?error=1",
        "首页": "http://gys.jknmyd.com:8077/hreport-manager/login/loginCheck",
        "报表页": "http://gys.jknmyd.com:8077/hreport-manager/pages/supplierManager/reportMgrQueryInfo.jsp",
        "报表参数接口": "http://gys.jknmyd.com:8077/hreport-manager/vendorReportMgr/qryParamList",
        "查询接口": "http://gys.jknmyd.com:8077/hreport-manager/vendorReportMgr/qryReportMeanInfo",
        "报表功能编号": {"配送流向": "65", "库存": "44"},
        "查询字段模板": {
            "配送流向": {"wareid": "", "begindate": "{start_date}", "enddate": "{end_date}", "userid": "", "funcId": "{func_id}"},
            "库存": {"busNo": "", "wareid": "", "userid": "", "funcId": "{func_id}"},
        },
        "使用平台导出": False,
        "数据类型列表": ["配送流向", "库存"],
        "启用": True,
    },
    "国药控股国大药房广西连锁有限公司": {
        "平台": "guoda",
        "账号": "",
        "密码": "",
        "站点地址": "https://gdedi.sinopharmgroup.net",
        "登录页": "https://gdedi.sinopharmgroup.net/",
        "登录接口": "https://gdedi.sinopharmgroup.net/EDI/CheckLogin",
        "验证码接口": "https://gdedi.sinopharmgroup.net/EDI/CheckCode?ID=1",
        "数据类型列表": ["配送流向", "购进流向", "库存"],
        "启用": True,
    },
    "国控国大(江门)医药有限公司": {
        "平台": "gkgdjm",
        "账号": "",
        "密码": "",
        "登录页": "http://jmgdlx.jmgdyf.com/#/login",
        "登录接口": "http://jmgdlx.jmgdyf.com/api/user/login",
        "购进流向接口": "http://jmgdlx.jmgdyf.com/api/lx/pur",
        "门店销售接口": "http://jmgdlx.jmgdyf.com/api/lx/sale",
        "配送流向接口": "http://jmgdlx.jmgdyf.com/api/lx/dist",
        "仓库库存接口": "http://jmgdlx.jmgdyf.com/api/lx/storestock",
        "门店库存接口": "http://jmgdlx.jmgdyf.com/api/lx/storebusi",
        "分页大小": 200,
        "数据类型列表": ["购进流向", "纯销流向", "配送流向", "仓库库存", "门店库存"],
        "启用": True,
    },
    "大参林医药集团股份有限公司": {
        "平台": "dsl",
        "账号": "",
        "密码": "",
        "供应商编码": "105330",
        "登录页": "https://srm.dslyy.com/user/login?redirect=%2F",
        "登录接口": "https://srm.dslyy.com/els/supply/account/supplier-login/login",
        "采购查询接口": "https://srm.dslyy.com/els/flow/supplier/orderList",
        "仓库库存查询接口": "https://srm.dslyy.com/els/flow/supplier/whStockList",
        "配送查询接口": "https://srm.dslyy.com/els/flow/supplier/tsfList",
        "门店库存查询接口": "https://srm.dslyy.com/els/flow/supplier/storeStockList",
        "销售查询接口": "https://srm.dslyy.com/els/flow/supplier/storeSaleList",
        "授权编号": {
            "购进流向": "1955707291290304512",
            "仓库库存": "1955707291084783616",
            "配送流向": "1955707290937982976",
            "门店库存": "1955707291055423488",
            "纯销流向": "1955707291181252608",
        },
        "分页大小": 1000,
        "数据类型列表": ["购进流向", "仓库库存", "配送流向", "门店库存", "纯销流向"],
        "启用": False,
    },
    "黑龙江省大众平安医药连锁有限公司": {
        "平台": "hljdzpa",
        "账号": "",
        "密码": "",
        "登录页": "http://123.57.178.31:58066/#/login",
        "接口根地址": "http://123.57.178.31:8084",
        "验证码接口": "http://123.57.178.31:8084/sys/getCode",
        "登录接口": "http://123.57.178.31:8084/sys/login",
        "查询接口": "http://123.57.178.31:8084/form/generate/list",
        "表单编号": {
            "购进流向": "1904401001234894849",
            "配送流向": "1904910563260043265",
            "库存": "1904914380655497218",
        },
        "分页大小": 1000,
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "大连方大药业有限公司": {
        "平台": "dlfdyy",
        "账号": "",
        "密码": "",
        "登录页": "http://dlfdyy.vicp.net:8088/fdweb/fdbus/index.w",
        "登录接口": "http://dlfdyy.vicp.net:8088/baas/fdbus/username/userdl",
        "登录日志接口": "http://dlfdyy.vicp.net:8088/baas/fdbus/username/dlrz",
        "购进流向接口": "http://dlfdyy.vicp.net:8088/baas/fdbus/splx/splxCxjgKhCg",
        "配送流向接口": "http://dlfdyy.vicp.net:8088/baas/fdbus/splx/splxCxjgKhXs",
        "库存接口": "http://dlfdyy.vicp.net:8088/baas/fdbus/splx/splxCxjgKhKc",
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "江西黄庆仁栈医药物流有限公司": {
        "平台": "jxhqrz",
        "账号": "",
        "密码": "",
        "登录页": "http://m.jxncyy.com/HHWLSaleFlowWeb/Login/Index",
        "应用根地址": "http://m.jxncyy.com/HHWLSaleFlowWeb",
        "登录接口": "http://m.jxncyy.com/HHWLSaleFlowWeb/Login/CheckLogin",
        "首页": "http://m.jxncyy.com/HHWLSaleFlowWeb/Home/Index",
        "购进流向接口": "http://m.jxncyy.com/HHWLSaleFlowWeb/TH_FlowDirection/PurchaseDetail/GetPageList",
        "配送流向接口": "http://m.jxncyy.com/HHWLSaleFlowWeb/TH_FlowDirection/SalesDetail1/GetPageList",
        "库存接口": "http://m.jxncyy.com/HHWLSaleFlowWeb/TH_FlowDirection/StockDetail/GetPageList",
        "分页大小": 100,
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "江西盛锦医药有限公司": {
        "平台": "hxlx",
        "账号": "",
        "密码": "",
        "登录页": "http://117.40.251.4:8099/MainForm.html",
        "接口根地址": "http://117.40.251.4:8099",
        "分页大小": 5000,
        "页面映射": {
            "总部库存": {"页面名称": "总仓库存", "路径": "/admin/Form_KC.aspx"},
            "购进流向": {"页面名称": "购进", "路径": "/admin/Form_GJ.aspx"},
            "配送流向": {"页面名称": "批发配送", "路径": "/admin/Form_PFPS.aspx"},
            "门店库存": {"页面名称": "门店库存", "路径": "/admin/Form_MDKC.aspx"},
            "纯销流向": {"页面名称": "门店销售", "路径": "/admin/Form_MDLS.aspx"},
            "报损流向": {"页面名称": "总仓损益", "路径": "/admin/Form_ZCSY.aspx"},
        },
        "数据类型列表": ["总部库存", "购进流向", "配送流向", "门店库存", "纯销流向", "报损流向"],
        "启用": True,
    },
    "河南省慧采医药有限公司": {
        "平台": "hnhcyy",
        "账号": "",
        "密码": "",
        "登录页": "http://1.192.219.160:61334/index.html#/login",
        "接口根地址": "http://1.192.219.160:61334",
        "登录接口": "http://1.192.219.160:61334/actionapi/Users/UserLogin",
        "购进流向接口": "http://1.192.219.160:61334/actionapi/Users/jhrkDataSearch",
        "配送流向接口": "http://1.192.219.160:61334/actionapi/Users/pfckDataSearch",
        "库存接口": "http://1.192.219.160:61334/actionapi/Users/sphwphDataSearch",
        "用户ID": 37,
        "分页大小": 100,
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "漳州市天健医药有限公司": {
        "平台": "zztj",
        "账号": "",
        "密码": "",
        "登录页": "https://zz.wan2.x-tj.cn:18116/index.html?id=1",
        "接口根地址": "https://zz.wan2.x-tj.cn:18116",
        "核心接口": "https://zz.wan2.x-tj.cn:18116/CoreAPI.php",
        "分页大小": 500,
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "福建蜂鸟医药有限公司": {
        "平台": "hx",
        "账号": "",
        "密码": "",
        "登录页": "http://fn.seaflysoft.com/",
        "接口根地址": "http://fn.seaflysoft.com",
        "登录接口": "http://fn.seaflysoft.com/login.do",
        "报表接口": "http://fn.seaflysoft.com/getreportdata.do",
        "报表页": "http://fn.seaflysoft.com/report?reportName=rp_supplierflow_dz",
        "报表名称": "rp_supplierflow_dz",
        "账套版本": "企业版",
        "账套版本编码": "17",
        "账套": "蜂鸟医药",
        "账套编号": "2",
        "登录机构": "总公司",
        "分页大小": 200,
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "山西天泽诚信药业有限公司": {
        "平台": "sxtzcx",
        "账号": "",
        "密码": "",
        "登录页": "http://sxtzcx.xin:8089/login",
        "登录接口": "http://sxtzcx.xin:8089/loginCheck",
        "查询页": "http://sxtzcx.xin:8089/Design_index?gnbh=1093",
        "查询接口": "http://sxtzcx.xin:8089/designquerydata",
        "分页大小": 5000,
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "仁和堂(内蒙古)医药有限公司": {
        "平台": "rhtnm",
        "账号": "",
        "密码": "",
        "允许空密码": True,
        "登录页": "http://flow.renhetang.cn/login?redirect=/index",
        "验证码接口": "http://flow.renhetang.cn/prod-api/captchaImage",
        "登录接口": "http://flow.renhetang.cn/prod-api/login",
        "分页大小": 200,
        "数据类型列表": ["购进流向", "配送流向", "库存", "纯销流向"],
        "启用": True,
    },
    "内蒙古天力药业有限公司": {
        "平台": "hreport",
        "账号": "",
        "密码": "",
        "登录页": "http://www.nmgtlyy.com:8988/hreport-manager/login",
        "登录接口": "http://www.nmgtlyy.com:8988/hreport-manager/j_spring_security_check",
        "登录成功路径": "/hreport-manager/login/loginCheck",
        "登录失败路径": "/hreport-manager/login?error=1",
        "首页": "http://www.nmgtlyy.com:8988/hreport-manager/login/loginCheck",
        "报表页": "http://www.nmgtlyy.com:8988/hreport-manager/pages/supplierManager/reportMgrQueryInfo.jsp",
        "报表参数接口": "http://www.nmgtlyy.com:8988/hreport-manager/vendorReportMgr/qryParamList",
        "查询接口": "http://www.nmgtlyy.com:8988/hreport-manager/vendorReportMgr/qryReportMeanInfo",
        "报表功能编号": {"购进流向": "40", "库存": "44", "配送流向": "45"},
        "查询字段模板": {
            "购进流向": {"vendorno": "", "wareid": "", "beginDate": "{start_date}", "endDate": "{end_date}", "userId": "", "funcId": "{func_id}"},
            "库存": {"busNo": "", "wareid": "", "userId": "", "funcId": "{func_id}"},
            "配送流向": {"wareid": "", "beginDate": "{start_date}", "endDate": "{end_date}", "userId": "", "funcId": "{func_id}"},
        },
        "使用平台导出": False,
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "江苏康济大药房连锁有限公司": {
        "平台": "hreport",
        "账号": "",
        "密码": "",
        "登录页": "http://180.110.63.4:18080/hreport-manager/login",
        "登录接口": "http://180.110.63.4:18080/hreport-manager/j_spring_security_check",
        "登录成功路径": "/hreport-manager/login/loginCheck",
        "登录失败路径": "/hreport-manager/login?error=1",
        "首页": "http://180.110.63.4:18080/hreport-manager/login/loginCheck",
        "报表页": "http://180.110.63.4:18080/hreport-manager/pages/supplierManager/reportMgrQueryInfo.jsp",
        "报表参数接口": "http://180.110.63.4:18080/hreport-manager/vendorReportMgr/qryParamList",
        "查询接口": "http://180.110.63.4:18080/hreport-manager/vendorReportMgr/qryReportMeanInfo",
        "报表功能编号": {"购进流向": "37", "库存": "44", "配送流向": "45"},
        "查询字段模板": {
            "购进流向": {"billcode": "", "beginDate": "{start_date}", "endDate": "{end_date}", "warecode": "", "makeno": "", "batid": "", "userid": "", "funcId": "{func_id}"},
            "库存": {"userid": "", "warecode": "", "busno": "", "funcId": "{func_id}"},
            "配送流向": {"beginDate": "{start_date}", "endDate": "{end_date}", "warecode": "", "makeno": "", "busno": "", "batid": "", "funcId": "{func_id}"},
        },
        "使用平台导出": True,
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        "启用": True,
    },
    "江苏卉全医药有限公司": {
        "平台": "hreport",
        "账号": "",
        "密码": "",
        "登录页": "http://106.14.239.32:8080/hreport-manager/login",
        "登录接口": "http://106.14.239.32:8080/hreport-manager/j_spring_security_check",
        "登录成功路径": "/hreport-manager/login/loginCheck",
        "登录失败路径": "/hreport-manager/login?error=1",
        "登录验证码字段": "yzmcode",
        "登录验证码固定值": "abcd",
        "首页": "http://106.14.239.32:8080/hreport-manager/login/loginCheck",
        "报表页": "http://106.14.239.32:8080/hreport-manager/pages/supplierManager/reportMgrQueryInfo.jsp",
        "报表参数接口": "http://106.14.239.32:8080/hreport-manager/vendorReportMgr/qryParamList",
        "查询接口": "http://106.14.239.32:8080/hreport-manager/vendorReportMgr/qryReportMeanInfo",
        "报表功能编号": {"购进流向": "10002", "库存": "10016", "纯销流向": "10017", "配送流向": "10018"},
        "查询字段模板": {
            "购进流向": {"userid": "", "warecode": "", "begindate": "{start_date}", "enddate": "{end_date}", "funcId": "{func_id}"},
            "库存": {"userid": "", "busno": "", "warecode": "", "funcId": "{func_id}"},
            "纯销流向": {"userid": "", "busno": "", "wareid": "", "begindate": "{start_date}", "enddate": "{end_date}", "funcId": "{func_id}"},
            "配送流向": {"userid": "", "busno": "", "warecode": "", "begindate": "{start_date}", "enddate": "{end_date}", "funcId": "{func_id}"},
        },
        "使用平台导出": False,
        "数据类型列表": ["购进流向", "库存", "纯销流向", "配送流向"],
        "启用": True,
    },
    "广州市宝芝林大药房连锁有限公司": {
        "平台": "gjjk",
        "账号": "",
        "密码": "",
        "登录页": "https://srm.cowellhealth.com/user/login",
        "接口根地址": "https://api-retail.cowellhealth.com",
        "验证码初始化接口": "https://api-retail.cowellhealth.com/store/api/noauth/img/getCode",
        "滑块图片接口": "https://api-retail.cowellhealth.com/store/api/noauth/img/getvalidateimg",
        "滑块校验接口": "https://api-retail.cowellhealth.com/store/api/noauth/img/tovalidateimg",
        "登录接口": "https://api-retail.cowellhealth.com/api/loginWithVerifyCode",
        "下载任务接口": "https://api-retail.cowellhealth.com/purchase-sync/api/srm/datacenter/getExport",
        "下载中心列表接口": "https://api-retail.cowellhealth.com/scrm/api/fileDownloadTaskList",
        "下载签名接口": "https://api-retail.cowellhealth.com/purchase/api/getSignUrl",
        "下载中心页": "https://srm.cowellhealth.com/download/downloadCenter",
        "下载任务等待秒数": 180,
        "下载任务轮询秒数": 5,
        "密码加密密钥": "abcdefgabcdefg12",
        "数据类型列表": ["购进流向", "配送流向", "纯销流向", "库存"],
        "启用": False,
    },
    "广东省东莞国药集团有限公司": {
        "平台": "kcshop",
        "账号": "",
        "密码": "",
        "登录页": "https://dongguanguoyao.kcshop.vip/",
        "接口根地址": "https://api.dongguanguoyao.kcshop.vip",
        "验证码接口": "https://api.dongguanguoyao.kcshop.vip/captcha.html",
        "登录接口": "https://api.dongguanguoyao.kcshop.vip/api/user/login",
        "分页大小": 1000,
        "查询超时秒数": 30,
        "数据类型列表": ["配送流向", "购进流向", "总部库存", "门店库存", "纯销流向"],
        "启用": True,
    },
    "威海市天福医药有限公司": {
        "平台": "yanxitang",
        "账号": "",
        "密码": "",
        "ELS账号": "100004244",
        "登录类型": "els",
        "登录页": "https://srm.sdyanxitang.com/ELSServer_YXT/login/login.html",
        "接口根地址": "https://srm.sdyanxitang.com/ELSServer_YXT",
        "验证码接口": "https://srm.sdyanxitang.com/ELSServer_YXT/image/identifyingCode.img",
        "登录接口": "https://srm.sdyanxitang.com/ELSServer_YXT/rest/AccountService/login",
        "报表查询接口": "https://srm.sdyanxitang.com/ELSServer_YXT/rest/reportForm/ReportCommonService/queryReportByType",
        "验证码重试次数": 8,
        "分页大小": 50,
        "报表类型映射": {
            "配送流向": "2",
            "购进流向": "1",
            "纯销流向": "4",
            "大仓库存": "3",
            "门店库存": "3",
        },
        "库存类型映射": {
            "大仓库存": "1",
            "门店库存": "2",
        },
        "数据类型列表": ["配送流向", "购进流向", "纯销流向", "大仓库存", "门店库存"],
        "启用": True,
    },
    "四川太极大药房连锁有限公司": {
        "平台": "taiji",
        "账号": "",
        "密码": "",
        "登录页": "http://222.178.193.127:15002/inout_query/",
        "接口根地址": "http://222.178.193.127:15002/inout_query",
        "登录接口": "http://222.178.193.127:15002/inout_query/Login.do",
        "货品ID": "",
        "查询超时秒": 300,
        "页面映射": {
            "购进流向": {"页面名称": "购进明细", "查询页": "show_su.jsp", "详情页": "show_su_detail.jsp", "需要日期": True},
            "纯销流向": {"页面名称": "分门店销售明细", "查询页": "show_sa.jsp", "详情页": "show_sa_detail.jsp", "需要日期": True},
            "配送流向": {"页面名称": "配送明细", "查询页": "show_place.jsp", "详情页": "show_place_detail.jsp", "需要日期": True},
            "库存": {"页面名称": "库存查询", "查询页": "show_st.jsp", "详情页": "show_st_detail.jsp", "需要日期": False},
        },
        "数据类型列表": ["购进流向", "纯销流向", "配送流向", "库存"],
        "启用": True,
    },
    "四川华信药业有限责任公司": {
        "平台": "scxh",
        "账号": "",
        "密码": "",
        "登录页": "https://college.scxinglin.com/xl/ReportServer/login",
        "接口根地址": "https://college.scxinglin.com/xl/ReportServer",
        "登录接口": "https://college.scxinglin.com/xl/ReportServer/login",
        "查询超时秒": 180,
        "数据类型列表": ["购进流向", "库存", "配送流向"],
        "启用": True,
    },
    "西昌东升大药房连锁有限责任公司": {
        "平台": "sosoyy",
        "账号": "",
        "密码": "",
        "登录页": "http://scdsdylfsyxzrgs117053.sosoyy.com/Account/Index",
        "接口根地址": "http://scdsdylfsyxzrgs117053.sosoyy.com",
        "登录接口": "http://scdsdylfsyxzrgs117053.sosoyy.com/Account",
        "分页大小": 500,
        "查询超时秒": 180,
        "数据类型列表": ["纯销流向", "库存", "购进流向", "配送流向"],
        "启用": True,
    },
    # 配置四川圣杰药业有限公司的 ABACUS 供应链系统账号。
    "四川圣杰药业有限公司": {
        # 声明商业使用的公共平台标识。
        "平台": "abacus",
        # 保存平台登录账号。
        "账号": "",
        # 保存平台登录密码。
        "密码": "",
        # 保存平台登录页面地址。
        "登录页": "http://182.130.246.142:9050/scm/login",
        # 保存平台 HTTP 服务根地址。
        "接口根地址": "http://182.130.246.142:9050",
        # 保存统一 JSON RPC 查询接口地址。
        "查询接口": "http://182.130.246.142:9050/scmapi/api",
        # 配置协议查询请求超时秒数。
        "查询超时秒": 180,
        # 配置页面名称、协议方法和日期筛选能力。
        "页面映射": {
            # 定义总部库存快照查询页面与协议方法。
            "总部库存": {"页面名称": "总部库存", "查询方法": "warequery", "查询页": "/scm/inventoryList", "需要日期": False},
            # 定义门店库存快照查询页面与协议方法。
            "门店库存": {"页面名称": "门店库存", "查询方法": "storequery", "查询页": "/scm/storeInventoryList", "需要日期": False},
            # 定义门店销售对应的纯销流向查询页面与协议方法。
            "纯销流向": {"页面名称": "门店销售", "查询方法": "salequery", "查询页": "/scm/saleList", "需要日期": True},
            # 定义配送流向查询页面与协议方法。
            "配送流向": {"页面名称": "配送查询", "查询方法": "stkotquery", "查询页": "/scm/distribution", "需要日期": True},
            # 定义收货对应的购进流向查询页面与协议方法。
            "购进流向": {"页面名称": "收货查询", "查询方法": "stkinquery", "查询页": "/scm/receiving", "需要日期": True},
        },
        # 配置总部库存页面展示字段标题、字段来源和列顺序。
        "页面原始列": {
            # 定义总部库存页面展示字段。
            "总部库存": [{"标题": "行号", "字段": "__row_number__"}, {"标题": "商品编码", "字段": "gdsid"}, {"标题": "商品名称", "字段": "gdsdes"}, {"标题": "规格", "字段": "spc"}, {"标题": "单位", "字段": "unit"}, {"标题": "生产厂家", "字段": "mfcfct"}, {"标题": "批号", "字段": "bthno"}, {"标题": "有效期至", "字段": "vlddat"}, {"标题": "数量", "字段": "qty"}],
            # 定义门店库存页面展示字段。
            "门店库存": [{"标题": "行号", "字段": "__row_number__"}, {"标题": "门店名称", "字段": "dptdes"}, {"标题": "商品编码", "字段": "gdsid"}, {"标题": "商品名称", "字段": "gdsdes"}, {"标题": "规格", "字段": "spc"}, {"标题": "单位", "字段": "unit"}, {"标题": "生产厂家", "字段": "mfcfct"}, {"标题": "批号", "字段": "bthno"}, {"标题": "有效期至", "字段": "vlddat"}, {"标题": "数量", "字段": "qty"}],
            # 定义门店销售页面展示字段。
            "纯销流向": [{"标题": "行号", "字段": "__row_number__"}, {"标题": "门店名称", "字段": "dptdes"}, {"标题": "商品编码", "字段": "gdsid"}, {"标题": "商品名称", "字段": "gdsdes"}, {"标题": "规格", "字段": "spc"}, {"标题": "生产厂家", "字段": "mfcfct"}, {"标题": "批号", "字段": "bthno"}, {"标题": "发生日期", "字段": "actdat"}, {"标题": "有效期至", "字段": "vlddat"}, {"标题": "数量", "字段": "qty"}],
            # 定义配送查询页面展示字段。
            "配送流向": [{"标题": "行号", "字段": "__row_number__"}, {"标题": "门店名称", "字段": "dptdes"}, {"标题": "商品编码", "字段": "gdsid"}, {"标题": "商品名称", "字段": "gdsdes"}, {"标题": "规格", "字段": "spc"}, {"标题": "生产厂家", "字段": "mfcfct"}, {"标题": "发生日期", "字段": "actdat"}, {"标题": "批号", "字段": "bthno"}, {"标题": "有效期至", "字段": "vlddat"}, {"标题": "数量", "字段": "qty"}],
            # 定义收货查询页面展示字段。
            "购进流向": [{"标题": "行号", "字段": "__row_number__"}, {"标题": "供应商", "字段": "prvempdes"}, {"标题": "门店名称", "字段": "dptdes"}, {"标题": "商品编码", "字段": "gdsid"}, {"标题": "商品名称", "字段": "gdsdes"}, {"标题": "规格", "字段": "spc"}, {"标题": "生产厂家", "字段": "mfcfct"}, {"标题": "发生日期", "字段": "actdat"}, {"标题": "批号", "字段": "bthno"}, {"标题": "有效期至", "字段": "vlddat"}, {"标题": "数量", "字段": "qty"}],
        },
        # 声明商业可执行的数据类型顺序。
        "数据类型列表": ["总部库存", "门店库存", "纯销流向", "配送流向", "购进流向"],
        # 启用当前商业任务。
        "启用": True,
    },
    # 配置四川贝尔康大药房连锁有限公司的流向采集服务平台账号。
    "四川贝尔康大药房连锁有限公司": {
        # 声明商业使用的公共平台标识。
        "平台": "bellcare",
        # 保存平台登录账号。
        "账号": "",
        # 保存平台登录密码。
        "密码": "",
        # 保存平台登录页面地址。
        "登录页": "http://hnflow.0285173.com/views/user/user/1005.html",
        # 保存平台 HTTP 服务根地址。
        "接口根地址": "http://hnflow.0285173.com",
        # 保存登录前密码加密接口地址。
        "密码加密接口": "http://hnflow.0285173.com/management/api/login/md.php",
        # 保存登录接口地址。
        "登录接口": "http://hnflow.0285173.com/management/api/login/login",
        # 配置稳定的单页查询数量。
        "分页大小": 1000,
        # 声明商业可执行的数据类型顺序。
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        # 启用当前商业任务。
        "启用": True,
    },
    # 配置成都高济良元大药房连锁有限公司的能手软件 SCM 查询账号。
    "成都高济良元大药房连锁有限公司": {
        # 声明商业使用的公共平台标识。
        "平台": "cox_scm",
        # 保存平台登录账号。
        "账号": "",
        # 保存平台登录密码。
        "密码": "",
        # 保存 COX OA 登录服务根地址。
        "登录接口根地址": "http://171.221.236.8:1314",
        # 保存动态报表服务根地址。
        "报表接口根地址": "http://xcx.cox1314.com:1316",
        # 保存商业编号。
        "商业编号": "KH03311",
        # 保存 COX OA 登录租户编号。
        "租户": "0",
        # 保存 COX OA 登录密码签名密钥。
        "登录密码密钥": "5B42C292068EAE007520F17A6E9FDD9B",
        # 保存页面使用的系统名称。
        "系统名称": "SCMSCCJ",
        # 配置稳定的单页查询数量。
        "分页大小": 500,
        # 声明商业可执行的数据类型顺序。
        "数据类型列表": ["配送流向", "购进流向", "库存"],
        # 启用当前商业任务。
        "启用": True,
    },
    # 配置凉山佳能达医药贸易有限责任公司的流向卡管理系统账号。
    "凉山佳能达医药贸易有限责任公司": {
        # 声明商业使用的公共平台标识。
        "平台": "lsjnd",
        # 保存平台登录账号。
        "账号": "",
        # 保存平台登录密码。
        "密码": "",
        # 保存平台 HTTP 服务根地址。
        "接口根地址": "http://www.lsjnd.com.cn:6501",
        # 保存当前账号对应的流向卡名称。
        "流向卡名称": "v_cj_1237",
        # 配置稳定的单页查询数量。
        "分页大小": 100,
        # 配置普通图片验证码长度。
        "验证码长度": 5,
        # 配置图片验证码自动重试次数。
        "验证码重试次数": 6,
        # 配置查询限流重试次数。
        "限流重试次数": 3,
        # 声明商业可执行的数据类型顺序。
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        # 启用当前商业任务。
        "启用": True,
    },
    # 配置华润湖南新特药有限公司的上游数据服务平台账号。
    "华润湖南新特药有限公司": {
        # 声明商业使用的公共平台标识。
        "平台": "crpcg",
        # 保存平台登录账号。
        "账号": "",
        # 保存平台登录密码。
        "密码": "",
        # 保存平台登录页面地址。
        "登录页": "https://lxdata.crpcg.com/auth/index",
        # 保存平台 HTTP 服务根地址。
        "接口根地址": "https://lxdata.crpcg.com",
        # 保存平台租户标识。
        "租户": "guanbi",
        # 保存稳定的单页查询数量。
        "分页大小": 1000,
        # 保存数据类型与页面卡片映射关系。
        "页面映射": {"库存": "流向查询-库存_湖南区域（新）", "购进流向": "流向查询-采购_湖南区域（新）", "配送流向": "流向查询-销售_湖南区域（新）"},
        # 声明商业可执行的数据类型顺序。
        "数据类型列表": ["购进流向", "配送流向", "库存"],
        # 启用当前商业任务。
        "启用": True,
    },
    # 配置四川本草堂药业有限公司协同办公系统账号。
    "四川本草堂药业有限公司": {
        # 声明商业使用的公共平台标识。
        "平台": "scbct",
        # 保存平台登录账号。
        "账号": "",
        # 保存平台登录密码。
        "密码": "",
        # 保存平台登录页面地址。
        "登录页": "https://flow.scbct.com/login",
        # 保存平台 HTTP 服务根地址。
        "接口根地址": "https://flow.scbct.com",
        # 保存验证码接口地址。
        "验证码接口": "https://flow.scbct.com/api/login/captcha",
        # 保存登录接口地址。
        "登录接口": "https://flow.scbct.com/api/login/login",
        # 配置平台单页最大查询数量。
        "分页大小": 400,
        # 配置图片验证码重试次数。
        "验证码重试次数": 8,
        # 声明平台数据类型顺序。
        "数据类型列表": ["配送流向", "购进流向", "库存"],
        # 启用当前商业任务。
        "启用": True,
    },
    # 配置绵阳安康药业连锁有限公司的 HReport 供应商查询系统账号。
    "绵阳安康药业连锁有限公司": {
        # 声明商业使用的公共平台标识。
        "平台": "hreport",
        # 保存平台登录账号。
        "账号": "",
        # 保存平台登录密码。
        "密码": "",
        # 保存平台登录页地址。
        "登录页": "http://47.109.140.89:8080/hreport-manager/login",
        # 保存 Spring Security 登录接口地址。
        "登录接口": "http://47.109.140.89:8080/hreport-manager/j_spring_security_check",
        # 保存登录成功跳转路径。
        "登录成功路径": "/hreport-manager/login/loginCheck",
        # 保存登录失败跳转路径。
        "登录失败路径": "/hreport-manager/login?error=1",
        # 保存登录成功后的首页地址。
        "首页": "http://47.109.140.89:8080/hreport-manager/login/loginCheck",
        # 保存报表页面地址。
        "报表页": "http://47.109.140.89:8080/hreport-manager/pages/supplierManager/reportMgrQueryInfo.jsp",
        # 保存报表表头参数接口地址。
        "报表参数接口": "http://47.109.140.89:8080/hreport-manager/vendorReportMgr/qryParamList",
        # 保存报表查询接口地址。
        "查询接口": "http://47.109.140.89:8080/hreport-manager/vendorReportMgr/qryReportMeanInfo",
        # 保存用户页面中的报表功能编号。
        "报表功能编号": {"库存": "44", "配送流向": "45"},
        # 保存页面实际提交的查询字段模板。
        "查询字段模板": {
            # 配置库存分布报表查询字段。
            "库存": {"busNo": "", "wareid": "", "userId": "", "funcId": "{func_id}"},
            # 配置业务流向报表查询字段。
            "配送流向": {"wareid": "", "beginDate": "{start_date}", "endDate": "{end_date}", "userId": "", "funcId": "{func_id}"},
        },
        # 保存标准字段前置映射并保留全部原始字段。
        "标准字段映射": {
            # 配置库存分布报表标准字段。
            "库存": [
                ("供应商编码", "供应商编码"),
                ("供应商名称", "供应商名称"),
                ("业务机构", "业务机构"),
                ("业务机构编码", "业务机构编码"),
                ("商品编码", "商品编码"),
                ("商品名称", "商品名称"),
                ("规格", "规格"),
                ("库存数量", "库存数量"),
                ("单价", "单价"),
                ("批号", "批号"),
                ("采购员", "采购员"),
                ("生产企业", "生产企业"),
                ("单位", "单位"),
                ("有效期", "有效期"),
            ],
            # 配置业务流向报表标准字段。
            "配送流向": [
                ("配送日期", "时间"),
                ("单据类型", "单据类型"),
                ("业务机构编码", "业务机构编码"),
                ("业务机构", "业务机构"),
                ("供应商编码", "供应商编码"),
                ("供应商名称", "供应商名称"),
                ("商品编码", "商品编码"),
                ("商品名称", "商品名称"),
                ("规格", "规格"),
                ("单位", "单位"),
                ("生产企业", "生产企业"),
                ("入数量", "入数量"),
                ("出数量", "出数量"),
                ("批号", "批号"),
            ],
        },
        # 指定配送流向的业务日期范围校验字段。
        "业务日期字段": {"配送流向": "时间"},
        # 使用协议查询和本地 Excel，保留页面全部字段。
        "使用平台导出": False,
        # 声明商业可执行的数据类型。
        "数据类型列表": ["库存", "配送流向"],
        # 启用当前商业任务。
        "启用": True,
    },
}


# 定义商业组织维度配置。
ACCOUNT_DIMENSIONS = {
    "辽宁九州通医药有限公司": {"大区": "西北东北", "省份": "辽宁省", "负责人": "覃祝燕"},
    "大连九州通医药有限公司": {"大区": "西北东北", "省份": "辽宁省", "负责人": "覃祝燕"},
    "福建九州通医药有限公司": {"大区": "华南", "省份": "福建省", "负责人": "覃祝燕"},
    "海南九州通医药有限公司": {"大区": "华南", "省份": "海南省", "负责人": "覃祝燕"},
    "广东九州通医药有限公司": {"大区": "华南", "省份": "广东省", "负责人": "覃祝燕"},
    "广东九州通医药有限公司1": {"大区": "华南", "省份": "广东省", "负责人": "覃祝燕"},
    "九州通医药集团股份有限公司": {"大区": "西南华中", "省份": "湖北省", "负责人": "晏惟学"},
    "河南九州通医药有限公司": {"大区": "西北东北", "省份": "河南省", "负责人": "晏惟学"},
    "内蒙古九州通医药有限公司": {"大区": "西北东北", "省份": "内蒙古自治区", "负责人": "晏惟学"},
    "赤峰九州通医药有限公司": {"大区": "西北东北", "省份": "内蒙古自治区", "负责人": "晏惟学"},
    "安徽九州通医药有限公司": {"大区": "华东华北", "省份": "安徽省", "负责人": "陈诗雅"},
    "北京九州通医药有限公司": {"大区": "华东华北", "省份": "北京市", "负责人": "陈诗雅"},
    "河北九州通医药有限公司": {"大区": "华东华北", "省份": "河北省", "负责人": "陈诗雅"},
    "江苏九州通医药有限公司": {"大区": "华东华北", "省份": "江苏省", "负责人": "陈诗雅"},
    "山东九州通医药有限公司": {"大区": "华东华北", "省份": "山东省", "负责人": "陈诗雅"},
    "上海九州通医药有限公司": {"大区": "华东华北", "省份": "上海市", "负责人": "陈诗雅"},
    "天津九州通达医药有限公司": {"大区": "华东华北", "省份": "天津市", "负责人": "陈诗雅"},
    "国药控股福建有限公司": {"大区": "华南", "省份": "福建省", "负责人": "覃祝燕"},
    "安徽新聚源医药科技有限公司": {"大区": "华东华北", "省份": "安徽省", "负责人": "陈诗雅"},
    "国药控股安徽华宁医药有限公司": {"大区": "华东华北", "省份": "安徽省", "负责人": "陈诗雅"},
    "国药控股济南有限公司": {"大区": "华东华北", "省份": "山东省", "负责人": "陈诗雅"},
    "青岛同方药业连锁有限公司": {"大区": "华东华北", "省份": "山东省", "负责人": "陈诗雅"},
    "上海汇丰医药药材有限责任公司": {"大区": "华东华北", "省份": "上海市", "负责人": "陈诗雅"},
    "安徽华人健康医药股份有限公司": {"大区": "华东华北", "省份": "安徽省", "负责人": "陈诗雅"},
    "仁和药房网(北京)医药科技有限公司": {"大区": "华东华北", "省份": "北京市", "负责人": "陈诗雅"},
    "国药乐仁堂(廊坊)医药贸易有限公司": {"大区": "华东华北", "省份": "河北省", "负责人": "陈诗雅"},
    "江苏澳洋医药物流有限公司": {"大区": "华东华北", "省份": "江苏省", "负责人": "陈诗雅"},
    "江苏恩华和达医药有限公司（连锁）": {"大区": "华东", "省份": "江苏省", "负责人": "昊惟学"},
    "江苏恩华和达医药有限公司（和达）": {"大区": "华东", "省份": "江苏省", "负责人": "昊惟学"},
    "江苏恩华和达医药有限公司（大药房）": {"大区": "华东", "省份": "江苏省", "负责人": "昊惟学"},
    "江苏元弘医药有限公司": {"大区": "华东华北", "省份": "江苏省", "负责人": "陈诗雅"},
    "江苏恒泰华洋医药有限公司": {"大区": "华东华北", "省份": "江苏省", "负责人": "陈诗雅"},
    "江苏康济大药房连锁有限公司": {"大区": "华东华北", "省份": "江苏省", "负责人": "陈诗雅"},
    "江苏卉全医药有限公司": {"大区": "华东华北", "省份": "江苏省", "负责人": "陈诗雅"},
    "云南健之佳重庆勤康药业有限公司": {"大区": "西南华中", "省份": "重庆市", "负责人": "梁彬彬"},
    "四川勤康健之佳医药有限责任公司": {"大区": "西南华中", "省份": "四川省", "负责人": "梁彬彬"},
    "健之佳医药连锁集团股份有限公司": {"大区": "西南华中", "省份": "云南省", "负责人": "梁彬彬"},
    "江药集团(四川)有限公司": {"大区": "西南华中", "省份": "四川省", "负责人": "梁彬彬"},
    "重庆桐君阁大药房连锁有限责任公司": {"大区": "西南华中", "省份": "重庆市", "负责人": "梁彬彬"},
    "重庆鑫斛药房连锁有限公司": {"大区": "西南华中", "省份": "重庆市", "负责人": "梁彬彬"},
    "重庆普健医药有限公司": {"大区": "西南华中", "省份": "重庆市", "负责人": "梁彬彬"},
    "重庆万鑫药房连锁有限公司": {"大区": "西南华中", "省份": "重庆市", "负责人": "梁彬彬"},
    "重庆唐氏药业有限公司": {"大区": "西南华中", "省份": "重庆市", "负责人": "梁彬彬"},
    "重庆鸿翔一心堂药业有限公司": {"大区": "西南华中", "省份": "重庆市", "负责人": "梁彬彬"},
    "一心堂药业集团股份有限公司": {"大区": "西南华中", "省份": "云南省", "负责人": "梁彬彬"},
    "四川一心堂医药连锁有限公司": {"大区": "西南华中", "省份": "四川省", "负责人": "梁彬彬"},
    "一心堂药业(贵州)有限公司": {"大区": "西南华中", "省份": "贵州省", "负责人": "梁彬彬"},
    "广西鸿翔一心堂药业有限责任公司": {"大区": "西南华中", "省份": "广西壮族自治区", "负责人": "梁彬彬"},
    "重庆市开州区医药有限责任公司": {"大区": "西南华中", "省份": "重庆市", "负责人": "梁彬彬"},
    "成都高济良元大药房连锁有限公司": {"大区": "西南华中", "省份": "四川省", "负责人": "梁彬彬"},
    "凉山佳能达医药贸易有限责任公司": {"大区": "西南华中", "省份": "四川省", "负责人": "梁彬彬"},
    "绵阳安康药业连锁有限公司": {"大区": "西南华中", "省份": "四川省", "负责人": "梁彬彬"},
    "厦门片仔癀宏仁医药有限公司": {"大区": "华南", "省份": "福建省", "负责人": "覃祝燕"},
    "黑龙江省阿拉丁医药有限公司": {"大区": "西北东北", "省份": "黑龙江省", "负责人": "覃祝燕"},
    "广州医药股份有限公司": {"大区": "华南", "省份": "广东省", "负责人": "覃祝燕"},
    "国药控股吉林有限公司": {"大区": "西北东北", "省份": "吉林省", "负责人": "覃祝燕"},
    "通用技术辽宁医药有限公司": {"大区": "西北东北", "省份": "辽宁省", "负责人": "覃祝燕"},
    "福建新紫金医药有限公司": {"大区": "华南", "省份": "福建省", "负责人": "覃祝燕"},
    "广东五嗣堂医药有限公司": {"大区": "华南", "省份": "广东省", "负责人": "覃祝燕"},
    "深圳市南北医药集团有限公司": {"大区": "华南", "省份": "广东省", "负责人": "覃祝燕"},
    "福建九州通中化医药有限公司": {"大区": "华南", "省份": "福建省", "负责人": "覃祝燕"},
    "国控国大(江门)医药有限公司": {"大区": "华南", "省份": "广东省", "负责人": "覃祝燕"},
    "国药控股国大药房广西连锁有限公司": {"大区": "西南华中", "省份": "广西壮族自治区", "负责人": "梁彬彬"},
    "湖南千金大药房连锁有限公司": {"大区": "西南华中", "省份": "湖南省", "负责人": "晏惟学"},
    "广西好药师大药房连锁有限公司": {"大区": "西南华中", "省份": "广西壮族自治区", "负责人": "梁彬彬"},
    "重庆和平药房连锁有限责任公司医药保健品分公司": {"大区": "西南华中", "省份": "重庆市", "负责人": "梁彬彬"},
    "娄底市健康南门医药零售连锁有限公司": {"大区": "西南华中", "省份": "湖南省", "负责人": "晏惟学"},
    "大参林医药集团股份有限公司": {"大区": "KA", "省份": "大参林", "负责人": "晏惟学"},
    "黑龙江省大众平安医药连锁有限公司": {"大区": "西北东北", "省份": "黑龙江省", "负责人": "覃祝燕"},
    "大连方大药业有限公司": {"大区": "西北东北", "省份": "辽宁省", "负责人": "覃祝燕"},
    "江西黄庆仁栈医药物流有限公司": {"大区": "西南华中", "省份": "江西省", "负责人": "晏惟学"},
    "江西盛锦医药有限公司": {"大区": "西南华中", "省份": "江西省", "负责人": "晏惟学"},
    "河南省慧采医药有限公司": {"大区": "西北东北", "省份": "河南省", "负责人": "晏惟学"},
    "漳州市天健医药有限公司": {"大区": "华南", "省份": "福建省", "负责人": "覃祝燕"},
    "福建蜂鸟医药有限公司": {"大区": "华南", "省份": "福建省", "负责人": "覃祝燕"},
    "山西天泽诚信药业有限公司": {"大区": "西北东北", "省份": "山西省", "负责人": "晏惟学"},
    "仁和堂(内蒙古)医药有限公司": {"大区": "西北东北", "省份": "内蒙古自治区", "负责人": "晏惟学"},
    "内蒙古天力药业有限公司": {"大区": "西北东北", "省份": "内蒙古自治区", "负责人": "晏惟学"},
    "广州市宝芝林大药房连锁有限公司": {"大区": "华南", "省份": "广东省", "负责人": "覃祝燕"},
    "广东省东莞国药集团有限公司": {"大区": "华南", "省份": "广东省", "负责人": "覃祝燕"},
    "威海市天福医药有限公司": {"大区": "华东华北", "省份": "山东省", "负责人": "陈诗雅"},
    "四川太极大药房连锁有限公司": {"大区": "西南华中", "省份": "四川省", "负责人": "梁彬彬"},
    "四川华信药业有限责任公司": {"大区": "西南华中", "省份": "四川省", "负责人": "梁彬彬"},
    "西昌东升大药房连锁有限责任公司": {"大区": "西南华中", "省份": "四川省", "负责人": "梁彬彬"},
    # 配置四川圣杰药业有限公司的组织筛选维度。
    "四川圣杰药业有限公司": {"大区": "西南华中", "省份": "四川省", "负责人": "梁彬彬"},
    # 配置四川贝尔康大药房连锁有限公司的组织筛选维度。
    "四川贝尔康大药房连锁有限公司": {"大区": "西南华中", "省份": "四川省", "负责人": "梁彬彬"},
    "四川聚之家医药有限公司": {"大区": "西南华中", "省份": "四川省", "负责人": "梁彬彬"},
    "华润湖南新特药有限公司": {"大区": "西南华中", "省份": "湖南省", "负责人": "晏惟学"},
    "湖南九州通医药有限公司": {"大区": "西南华中", "省份": "湖南省", "负责人": "晏惟学"},
    "重庆九州通医药有限公司": {"大区": "西南华中", "省份": "重庆市", "负责人": "梁彬彬"},
    "四川本草堂药业有限公司": {"大区": "西南华中", "省份": "四川省", "负责人": "梁彬彬"},
    "广西九州通医药有限公司": {"大区": "西南华中", "省份": "广西壮族自治区", "负责人": "梁彬彬"},
    "贵州九州通达医药有限公司": {"大区": "西南华中", "省份": "贵州省", "负责人": "梁彬彬"},
}


# 判断当前是否运行在 PyInstaller 打包环境。
if getattr(sys, "frozen", False):

    # 解析可执行文件同目录的本机私有账号配置路径。
    exe_side_config_path = Path(sys.executable).with_name("account_config_local.py")

    # 判断调用方是否在可执行文件旁放置了覆盖用的私有账号配置。
    if exe_side_config_path.is_file():

        # 优先使用可执行文件旁的私有账号配置。
        LOCAL_ACCOUNT_CONFIG_PATH = exe_side_config_path

    # 处理未提供覆盖文件的情况。
    else:

        # 打包运行时读取内嵌到可执行文件中的私有账号配置。
        LOCAL_ACCOUNT_CONFIG_PATH = Path(getattr(sys, "_MEIPASS", "")) / "account_config_local.py"

# 处理源码运行环境。
else:

    # 源码运行时读取模块同目录的本机私有账号配置。
    LOCAL_ACCOUNT_CONFIG_PATH = Path(__file__).with_name("account_config_local.py")


# 定义本机私有账号配置加载函数。
def load_local_account_credentials():

    """
    从本机私有配置文件覆盖公开模板中的账号密码。

    :return: None。
    :rtype: None
    """

    # 判断本机私有账号配置是否存在。
    if not LOCAL_ACCOUNT_CONFIG_PATH.is_file():

        # 结束缺少私有账号配置时的覆盖流程。
        return

    # 导入 Python 抽象语法树解析模块。
    import ast

    # 读取私有账号配置源文件文本。
    local_source = LOCAL_ACCOUNT_CONFIG_PATH.read_text(encoding="utf-8")

    # 解析私有账号配置源文件的抽象语法树。
    local_tree = ast.parse(local_source, filename=str(LOCAL_ACCOUNT_CONFIG_PATH))

    # 初始化私有账号配置字典。
    local_accounts = {}

    # 遍历私有账号配置的模块级节点。
    for node in local_tree.body:

        # 判断当前节点是否为 ACCOUNTS 赋值语句。
        if not isinstance(node, ast.Assign) or not any(isinstance(target, ast.Name) and target.id == "ACCOUNTS" for target in node.targets):

            # 继续检查下一个模块级节点。
            continue

        # 将 ACCOUNTS 字典字面量转换为 Python 对象。
        local_accounts = ast.literal_eval(node.value)

        # 结束私有账号配置字典搜索。
        break

    # 判断私有账号配置是否为字典。
    if not isinstance(local_accounts, dict):

        # 抛出私有账号配置格式异常。
        raise RuntimeError("本机私有账号配置中的 ACCOUNTS 必须为字典")

    # 遍历公开模板内的全部商业。
    for company_name, account in ACCOUNTS.items():

        # 读取当前商业的私有账号配置。
        local_account = local_accounts.get(company_name, {})

        # 判断当前商业私有配置是否为字典。
        if not isinstance(local_account, dict):

            # 继续处理下一家商业。
            continue

        # 遍历允许由私有配置覆盖的账号字段。
        for field_name in ("账号", "密码"):

            # 判断私有配置是否包含当前账号字段。
            if field_name not in local_account:

                # 继续处理下一个账号字段。
                continue

            # 将私有账号字段写入当前商业配置。
            account[field_name] = local_account[field_name]


# 加载本机私有账号密码覆盖配置。
load_local_account_credentials()


# 定义历史负责人名称到当前名称的映射。
RESPONSIBLE_PERSON_NAME_MAP = {"昊惟学": "晏惟学"}


# 定义账号组织维度写入函数。
def apply_account_dimensions():
    """
    将组织维度配置写入商业账号配置。

    :return: None。
    :rtype: None
    """

    # 遍历商业组织维度配置。
    for company_name, dimension_config in ACCOUNT_DIMENSIONS.items():

        # 判断商业账号是否存在。
        if company_name not in ACCOUNTS:

            # 进入下一项组织维度配置。
            continue

        # 写入当前商业的大区配置。
        ACCOUNTS[company_name]["大区"] = dimension_config.get("大区", "")

        # 写入当前商业的省份配置。
        ACCOUNTS[company_name]["省份"] = dimension_config.get("省份", "")

        # 读取当前商业负责人名称。
        responsible_person = dimension_config.get("负责人", "")

        # 写入标准化后的负责人配置。
        ACCOUNTS[company_name]["负责人"] = RESPONSIBLE_PERSON_NAME_MAP.get(responsible_person, responsible_person)


# 定义账号维度取值列表函数。
def list_account_dimension_values(dimension_name):
    """
    读取指定账号维度下的可选取值。

    :param dimension_name: 账号维度名称。
    :type dimension_name: str
    :return: 维度取值列表。
    :rtype: list[str]
    """

    # 读取全部账号中的维度取值集合。
    dimension_values = {account.get(dimension_name, "") for account in ACCOUNTS.values() if account.get(dimension_name, "")}

    # 返回按文本排序后的维度取值列表。
    return sorted(dimension_values)


# 定义账号维度商业筛选函数。
def filter_account_names_by_dimension(dimension_name, dimension_value):
    """
    按账号维度筛选商业名称。

    :param dimension_name: 账号维度名称。
    :type dimension_name: str
    :param dimension_value: 账号维度取值。
    :type dimension_value: str
    :return: 商业名称列表。
    :rtype: list[str]
    """

    # 返回匹配指定维度取值的商业名称列表。
    return [company_name for company_name, account in ACCOUNTS.items() if account.get(dimension_name, "") == dimension_value]


# 写入账号组织维度配置。
apply_account_dimensions()


# 定义运行配置目录名。
RUNTIME_CONFIG_DIR_NAME = "config"

# 定义运行期账号覆盖配置键名。
RUNTIME_ACCOUNT_OVERRIDE_KEY = "账号覆盖"

# 定义账号密码编辑字段集合。
RUNTIME_ACCOUNT_CREDENTIAL_FIELD_NAMES = {"账号", "密码"}

# 定义可编辑连接字段的名称关键字。
RUNTIME_ACCOUNT_CONNECTION_FIELD_KEYWORDS = ("地址", "接口", "路径", "页")


# 定义默认运行配置文件名。
RUNTIME_CONFIG_FILE_NAME = "account_runtime.json"


# 定义运行配置路径解析函数。
def resolve_runtime_config_path(project_root=None):
    """
    解析运行期账号启停配置文件路径。

    :param project_root: 项目根目录。
    :type project_root: str | None
    :return: 运行期配置文件路径。
    :rtype: str
    """

    # 判断调用方是否传入项目根目录。
    if project_root:

        # 返回项目配置目录下的运行期配置文件路径。
        return os.path.join(project_root, RUNTIME_CONFIG_DIR_NAME, RUNTIME_CONFIG_FILE_NAME)

    # 返回当前工作目录配置目录下的运行期配置文件路径。
    return os.path.join(os.getcwd(), RUNTIME_CONFIG_DIR_NAME, RUNTIME_CONFIG_FILE_NAME)


# 定义运行期账号配置读取函数。
def load_runtime_account_config(project_root=None):
    """
    读取运行期账号启停配置。

    :param project_root: 项目根目录。
    :type project_root: str | None
    :return: 运行期账号启停配置。
    :rtype: dict
    """

    # 解析运行期配置文件路径。
    config_path = resolve_runtime_config_path(project_root)

    # 判断运行期配置文件是否存在。
    if not os.path.exists(config_path):

        # 返回空运行期配置。
        return {}

    # 打开运行期配置文件。
    with open(config_path, "r", encoding="utf-8") as file_obj:

        # 读取 JSON 配置内容。
        config_data = json.load(file_obj)

    # 判断配置根对象是否为字典。
    if not isinstance(config_data, dict):

        # 返回空运行期配置。
        return {}

    # 返回运行期配置内容。
    return config_data


# 定义运行期账号配置保存函数。
def save_runtime_account_config(config_data, project_root=None):
    """
    保存运行期账号启停配置。

    :param config_data: 运行期账号启停配置。
    :type config_data: dict
    :param project_root: 项目根目录。
    :type project_root: str | None
    :return: 运行期配置文件路径。
    :rtype: str
    """

    # 解析运行期配置文件路径。
    config_path = resolve_runtime_config_path(project_root)

    # 创建配置文件所在目录。
    os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)

    # 创建配置文件同目录的临时文件。
    file_descriptor, temporary_path = tempfile.mkstemp(prefix="account_runtime_", suffix=".tmp", dir=os.path.dirname(os.path.abspath(config_path)))

    # 将临时文件描述符转换为 UTF-8 文本文件对象。
    with os.fdopen(file_descriptor, "w", encoding="utf-8") as file_obj:

        # 序列化运行期配置。
        json.dump(config_data, file_obj, ensure_ascii=False, indent=2)

    # 使用完整临时文件原子替换目标配置文件。
    os.replace(temporary_path, config_path)

    # 返回运行期配置文件路径。
    return config_path


# 定义商业账号可编辑字段读取函数。
def get_runtime_editable_account_fields(account):
    """
    获取商业账号允许写入运行期覆盖的字段名。

    :param account: 商业默认账号配置。
    :type account: dict
    :return: 按源码配置顺序返回的可编辑字段名。
    :rtype: list[str]
    """

    # 初始化可编辑字段名称列表。
    editable_fields = []

    # 遍历当前商业默认配置中的全部字段。
    for field_name, field_value in account.items():

        # 标准化当前字段名称。
        normalized_field_name = str(field_name)

        # 判断当前字段是否为账号密码字段。
        is_credential_field = normalized_field_name in RUNTIME_ACCOUNT_CREDENTIAL_FIELD_NAMES

        # 判断当前字段是否为字符串连接字段。
        is_connection_field = isinstance(field_value, str) and any(keyword in normalized_field_name for keyword in RUNTIME_ACCOUNT_CONNECTION_FIELD_KEYWORDS)

        # 判断当前字段是否允许编辑。
        if not is_credential_field and not is_connection_field:

            # 跳过当前只读字段。
            continue

        # 记录当前可编辑字段名称。
        editable_fields.append(normalized_field_name)

    # 返回按账号原始配置顺序整理的字段列表。
    return editable_fields


# 定义运行期账号覆盖读取函数。
def get_runtime_account_overrides(runtime_config):
    """
    从运行期配置中读取有效的商业账号覆盖集合。

    :param runtime_config: 运行期账号配置。
    :type runtime_config: dict
    :return: 商业名称到账号覆盖字段的映射。
    :rtype: dict[str, dict]
    """

    # 读取账号覆盖配置对象。
    override_config = runtime_config.get(RUNTIME_ACCOUNT_OVERRIDE_KEY, {}) if isinstance(runtime_config, dict) else {}

    # 判断账号覆盖配置是否为字典。
    if not isinstance(override_config, dict):

        # 返回空账号覆盖集合。
        return {}

    # 初始化标准化账号覆盖集合。
    normalized_overrides = {}

    # 遍历全部商业账号覆盖配置。
    for company_name, override_fields in override_config.items():

        # 跳过字段结构无效的商业配置。
        if not isinstance(override_fields, dict):

            # 进入下一项商业覆盖配置。
            continue

        # 保存当前商业的深拷贝覆盖配置。
        normalized_overrides[str(company_name)] = copy.deepcopy(override_fields)

    # 返回标准化后的账号覆盖集合。
    return normalized_overrides


# 定义指定商业有效账号构建函数。
def get_effective_account(company_name, project_root=None, runtime_config=None):
    """
    构建包含运行期覆盖的指定商业账号配置副本。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param project_root: 项目根目录。
    :type project_root: str | None
    :param runtime_config: 可选的已读取运行期配置。
    :type runtime_config: dict | None
    :return: 不修改源码配置的有效商业账号配置。
    :rtype: dict
    :raises KeyError: 商业名称未配置时抛出。
    """

    # 读取当前商业的源码默认配置。
    default_account = ACCOUNTS[company_name]

    # 深拷贝默认配置以隔离运行期写入。
    effective_account = copy.deepcopy(default_account)

    # 读取调用方提供或本地加载的运行期配置。
    current_runtime_config = runtime_config if isinstance(runtime_config, dict) else load_runtime_account_config(project_root)

    # 读取全部商业账号覆盖配置。
    all_overrides = get_runtime_account_overrides(current_runtime_config)

    # 读取当前商业的账号覆盖字段。
    account_override = all_overrides.get(company_name, {})

    # 读取当前商业允许编辑的字段集合。
    editable_fields = set(get_runtime_editable_account_fields(default_account))

    # 遍历当前商业的运行期覆盖字段。
    for field_name, field_value in account_override.items():

        # 跳过不在可编辑范围内的覆盖字段。
        if field_name not in editable_fields:

            # 进入下一项账号覆盖字段。
            continue

        # 跳过类型不匹配的覆盖字段。
        if not isinstance(field_value, str):

            # 进入下一项账号覆盖字段。
            continue

        # 写入当前允许的账号覆盖字段。
        effective_account[field_name] = field_value

    # 返回合并后的有效账号配置。
    return effective_account


# 定义全部有效账号构建函数。
def get_effective_accounts(project_root=None, runtime_config=None):
    """
    构建包含运行期覆盖的全部商业账号配置副本。

    :param project_root: 项目根目录。
    :type project_root: str | None
    :param runtime_config: 可选的已读取运行期配置。
    :type runtime_config: dict | None
    :return: 商业名称到有效账号配置的映射。
    :rtype: dict[str, dict]
    """

    # 读取调用方提供或本地加载的运行期配置。
    current_runtime_config = runtime_config if isinstance(runtime_config, dict) else load_runtime_account_config(project_root)

    # 初始化全部有效账号配置映射。
    effective_accounts = {}

    # 遍历全部已配置商业名称。
    for company_name in ACCOUNTS:

        # 构建当前商业的有效账号配置副本。
        effective_accounts[company_name] = get_effective_account(company_name, project_root, current_runtime_config)

    # 返回全部有效账号配置映射。
    return effective_accounts


# 定义运行期账号覆盖保存函数。
def save_runtime_account_override(company_name, override_fields, project_root=None):
    """
    保存指定商业允许字段的运行期账号覆盖。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param override_fields: 需要保存的账号覆盖字段。
    :type override_fields: dict
    :param project_root: 项目根目录。
    :type project_root: str | None
    :return: 账号覆盖保存后的运行期配置路径。
    :rtype: str
    :raises ValueError: 覆盖字段、字段类型或账号密码内容无效时抛出。
    """

    # 判断目标商业是否已经配置。
    if company_name not in ACCOUNTS:

        # 抛出商业名称无效异常。
        raise ValueError(f"商业配置不存在：{company_name}")

    # 判断账号覆盖字段是否为字典。
    if not isinstance(override_fields, dict):

        # 抛出账号覆盖结构无效异常。
        raise ValueError("账号覆盖必须为字段字典")

    # 读取当前商业默认账号配置。
    default_account = ACCOUNTS[company_name]

    # 读取当前商业允许编辑的字段集合。
    editable_fields = set(get_runtime_editable_account_fields(default_account))

    # 初始化标准化账号覆盖字段。
    normalized_fields = {}

    # 遍历待保存的账号覆盖字段。
    for field_name, field_value in override_fields.items():

        # 标准化当前字段名称。
        normalized_field_name = str(field_name)

        # 判断当前字段是否允许编辑。
        if normalized_field_name not in editable_fields:

            # 抛出只读字段写入异常。
            raise ValueError(f"字段不允许运行期编辑：{normalized_field_name}")

        # 判断当前字段值是否为字符串。
        if not isinstance(field_value, str):

            # 抛出字段类型无效异常。
            raise ValueError(f"字段必须为文本：{normalized_field_name}")

        # 读取当前字段的保存值。
        normalized_field_value = field_value if normalized_field_name == "密码" else field_value.strip()

        # 判断账号字段是否为空。
        if normalized_field_name == "账号" and not normalized_field_value:

            # 抛出账号为空异常。
            raise ValueError("账号不能为空")

        # 判断密码字段是否不允许为空。
        if normalized_field_name == "密码" and not normalized_field_value and not bool(default_account.get("允许空密码", False)):

            # 抛出密码为空异常。
            raise ValueError("当前商业不允许空密码")

        # 判断当前值是否与源码默认值不同。
        if normalized_field_value != default_account.get(normalized_field_name, ""):

            # 保存与默认值不同的账号覆盖字段。
            normalized_fields[normalized_field_name] = normalized_field_value

    # 读取当前运行期配置。
    runtime_config = load_runtime_account_config(project_root)

    # 读取全部账号覆盖配置。
    all_overrides = get_runtime_account_overrides(runtime_config)

    # 判断当前商业是否仍有有效覆盖字段。
    if normalized_fields:

        # 写入当前商业的账号覆盖字段。
        all_overrides[company_name] = normalized_fields

    # 处理当前商业全部字段均恢复默认的情况。
    else:

        # 删除当前商业已有的账号覆盖配置。
        all_overrides.pop(company_name, None)

    # 写回账号覆盖配置集合。
    runtime_config[RUNTIME_ACCOUNT_OVERRIDE_KEY] = all_overrides

    # 保存并返回运行期配置文件路径。
    return save_runtime_account_config(runtime_config, project_root)


# 定义运行期账号覆盖清除函数。
def clear_runtime_account_override(company_name, project_root=None):
    """
    清除指定商业的运行期账号覆盖并恢复源码默认值。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param project_root: 项目根目录。
    :type project_root: str | None
    :return: 账号覆盖清除后的运行期配置路径。
    :rtype: str
    :raises ValueError: 商业名称未配置时抛出。
    """

    # 判断目标商业是否已经配置。
    if company_name not in ACCOUNTS:

        # 抛出商业名称无效异常。
        raise ValueError(f"商业配置不存在：{company_name}")

    # 读取当前运行期配置。
    runtime_config = load_runtime_account_config(project_root)

    # 读取全部账号覆盖配置。
    all_overrides = get_runtime_account_overrides(runtime_config)

    # 删除当前商业的账号覆盖配置。
    all_overrides.pop(company_name, None)

    # 写回账号覆盖配置集合。
    runtime_config[RUNTIME_ACCOUNT_OVERRIDE_KEY] = all_overrides

    # 保存并返回运行期配置文件路径。
    return save_runtime_account_config(runtime_config, project_root)


# 定义运行期启用状态读取函数。
def resolve_runtime_enabled(company_name, account, runtime_config):
    """
    解析商业账号运行期启用状态。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param runtime_config: 运行期账号启停配置。
    :type runtime_config: dict
    :return: 商业账号是否启用。
    :rtype: bool
    """

    # 读取运行期商业配置集合。
    companies_config = runtime_config.get("商业启停", {})

    # 判断运行期商业配置是否为字典。
    if not isinstance(companies_config, dict):

        # 使用源码默认启用状态。
        return bool(account.get("启用", True))

    # 判断当前商业是否存在运行期覆盖配置。
    if company_name in companies_config:

        # 返回运行期覆盖后的启用状态。
        return bool(companies_config[company_name])

    # 使用源码默认启用状态。
    return bool(account.get("启用", True))


# 定义运行期配置模板写入函数。
def ensure_runtime_account_config(project_root=None):
    """
    确保运行期账号启停配置文件存在。

    :param project_root: 项目根目录。
    :type project_root: str | None
    :return: 运行期配置文件路径。
    :rtype: str
    """

    # 解析运行期配置文件路径。
    config_path = resolve_runtime_config_path(project_root)

    # 构建运行期商业启停模板。
    companies_config = {company_name: bool(account.get("启用", True)) for company_name, account in ACCOUNTS.items()}

    # 判断运行期配置文件是否已经存在。
    if os.path.exists(config_path):

        # 读取已有运行期配置。
        config_data = load_runtime_account_config(project_root)

        # 读取已有商业启停配置。
        existing_companies_config = config_data.get("商业启停", {})

        # 初始化配置写入需求状态。
        should_save_config = False

        # 读取已有账号覆盖配置。
        existing_account_overrides = config_data.get(RUNTIME_ACCOUNT_OVERRIDE_KEY, {})

        # 判断已有账号覆盖配置是否缺失或不是字典。
        if RUNTIME_ACCOUNT_OVERRIDE_KEY not in config_data or not isinstance(existing_account_overrides, dict):

            # 使用空账号覆盖配置。
            existing_account_overrides = {}

            # 标记运行期配置需要保存。
            should_save_config = True

        # 判断已有商业启停配置是否为字典。
        if not isinstance(existing_companies_config, dict):

            # 使用空商业启停配置。
            existing_companies_config = {}

            # 标记运行期配置需要保存。
            should_save_config = True

        # 遍历源码账号配置补齐缺失商业。
        for company_name, enabled_status in companies_config.items():

            # 判断当前商业是否缺少运行期配置。
            if company_name not in existing_companies_config:

                # 写入当前商业默认启停状态。
                existing_companies_config[company_name] = enabled_status

                # 标记运行期配置需要保存。
                should_save_config = True

        # 写回补齐后的商业启停配置。
        config_data["商业启停"] = existing_companies_config

        # 写回标准化后的账号覆盖配置。
        config_data[RUNTIME_ACCOUNT_OVERRIDE_KEY] = existing_account_overrides

        # 判断运行期配置是否不需要保存。
        if not should_save_config:

            # 返回已有配置文件路径。
            return config_path

        # 保存运行期配置文件。
        save_runtime_account_config(config_data, project_root)

        # 返回已有配置文件路径。
        return config_path

    # 构建运行期配置对象。
    config_data = {"说明": "打包 exe 后可修改本文件控制商业是否执行，true 表示启用，false 表示关闭；账号覆盖用于保存账号、密码和连接项的运行期改写。", "商业启停": companies_config, RUNTIME_ACCOUNT_OVERRIDE_KEY: {}}

    # 创建配置文件所在目录。
    os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)

    # 保存运行期配置文件。
    save_runtime_account_config(config_data, project_root)

    # 返回运行期配置文件路径。
    return config_path


# 定义指定商业账号读取函数。
def get_account(company_name, project_root=None):
    """
    获取指定商业账号配置。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param project_root: 项目根目录。
    :type project_root: str | None
    :return: 商业账号配置。
    :rtype: dict
    """

    # 返回指定商业的有效账号配置副本。
    return get_effective_account(company_name, project_root)


# 定义启用商业账号遍历函数。
def iter_enabled_accounts(project_root=None):
    """
    遍历已启用的商业账号配置。

    :param project_root: 项目根目录。
    :type project_root: str | None
    :return: 商业名称与账号配置迭代器。
    :rtype: Iterator[tuple[str, dict]]
    """

    # 读取运行期账号启停配置。
    runtime_config = load_runtime_account_config(project_root)

    # 构建全部有效账号配置副本。
    effective_accounts = get_effective_accounts(project_root, runtime_config)

    # 遍历账号配置字典中的商业账号。
    for company_name, account in effective_accounts.items():

        # 跳过运行期关闭的商业账号。
        if not resolve_runtime_enabled(company_name, account, runtime_config):

            # 进入下一个商业账号。
            continue

        # 产出当前启用商业的名称和配置。
        yield company_name, account
