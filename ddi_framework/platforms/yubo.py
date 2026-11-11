# -*- coding: utf-8 -*-
"""
浙江御博商品流向系统协议适配器。

本模块负责浙江御博商品流向系统（Smobiler SWeb 私有 STTP 协议）的
WebSocket 三段式握手、算术会话密钥派生、UI 事件驱动登录、
菜单导航与商品流向/库存查询及原始字段 Excel 落地。
"""

# 导入哈希模块。
import hashlib

# 导入操作系统路径模块。
import os

# 导入正则表达式模块。
import re

# 导入随机数模块。
import secrets

# 导入二进制打包模块。
import struct

# 导入时间模块。
import time

# 导入 UUID 模块。
import uuid

# 导入 JSON 编解码模块。
import json

# 导入 HTTP 客户端模块。
import http.client

# 导入 WebSocket 客户端。
import websocket

# 导入 RSA 公钥加载函数。
from cryptography.hazmat.primitives.serialization import load_der_public_key

# 导入 RSA PKCS1v15 填充。
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding

# 导入 AES 与 CBC 模式。
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# 导入 PKCS7 填充。
from cryptography.hazmat.primitives import padding as sym_padding

# 导入平台适配器基类。
from ddi_framework import BasePlatform

# 导入 Excel 统一样式函数。
from ddi_framework import apply_standard_excel_style

# 导入日志打印器。
from ddi_framework import PrintHandler

# 导入正式原始 Excel 写入函数。
from ddi_framework.raw_fields import write_formal_raw_excel


# 定义数据类型与菜单标题映射。
DATA_TYPE_CONFIG = {
    "配送流向": "商品流向",
    "库存": "库存查询",
}

# 定义会话密钥的 4 字符尾段字符集。
RANDOM_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789"

# 定义单次登录过程的验证码式重试上限。
MAX_HANDSHAKE_RETRIES = 3


# 定义御博商品流向系统平台适配器。
class YuboPlatform(BasePlatform):

    """
    浙江御博商品流向系统平台协议适配器。

    :param company_name: 商业公司名称。
    :type company_name: str
    :param account: 商业账号配置。
    :type account: dict
    :param printer: 日志打印器。
    :type printer: PrintHandler | None
    :return: 御博商品流向系统平台适配器实例。
    :rtype: YuboPlatform
    """

    # 定义平台适配器初始化方法。
    def __init__(self, company_name, account, printer=None):

        """
        初始化站点地址、会话密钥材料与日志对象。

        :param company_name: 商业公司名称。
        :type company_name: str
        :param account: 商业账号配置。
        :type account: dict
        :param printer: 日志打印器。
        :type printer: PrintHandler | None
        :return: None。
        :rtype: None
        """

        # 调用父类初始化逻辑。
        super().__init__(company_name, account, printer=printer)

        # 初始化公共日志打印器。
        self.ph = printer or PrintHandler()

        # 读取平台 HTTP 服务根地址（含端口）。
        self.hostport = str(account.get("接口根地址", "")).replace("http://", "").replace("https://", "").rstrip("/")

        # 初始化客户端会话 GUID。
        self.guid = ""

        # 初始化 AES 会话密钥。
        self.aes_key = b""

        # 初始化 AES 会话 IV。
        self.aes_iv = b""

        # 初始化 WebSocket 连接。
        self.ws = None

        # 初始化登录状态标识。
        self.logged_in = False

        # 初始化业务页面树缓存（菜单标题 → 页面树文本）。
        self.page_stml_cache = {}

    # 定义平台登录方法。
    def login(self):

        """
        完成 WebSocket 握手、device-info 注册与 UI 事件登录。

        :return: 不含凭据的登录结果摘要。
        :rtype: dict
        """

        # 打印登录阶段分隔线。
        self.ph.section("御博商品流向系统登录", self.ph.kv("商业", self.company_name, "cyan"))

        # 建立 WebSocket 连接并完成三段式握手。
        self.establish_session()

        # 注册设备信息并取得登录页 UI 树。
        page_path, controls = self.register_device()

        # 解析登录控件。
        text_inputs = [i for i, t, p in controls if t == "TextInput"]
        button_id = next(i for i, t, p in controls if t == "Button")
        account_id, password_id = text_inputs[0], text_inputs[1]

        # 发送登录事件序列。
        self.send_event(page_path, {"method": "onEvent", "params": {"id": account_id, "type": "TextChanged", "params": {"value": str(self.account.get("账号", "")), "_params": {"type": "changed", "name": "defaultValue", "notUpdate": True}}}})
        self.send_event(page_path, {"method": "onEvent", "params": {"id": account_id, "type": "TouchLeave", "params": {}}})
        self.send_event(page_path, {"method": "onEvent", "params": {"id": password_id, "type": "TextChanged", "params": {"value": str(self.account.get("密码", "")), "_params": {"type": "changed", "name": "defaultValue", "notUpdate": True}}}})
        self.send_event(page_path, {"method": "onEvent", "params": {"id": password_id, "type": "TouchLeave", "params": {}}})
        time.sleep(0.5)
        self.send_event(page_path, {"method": "onEvent", "params": {"id": button_id, "type": "Press", "params": {"params": {"height": 35, "width": 35, "top": 137, "left": 750, "direction": 3}}}})

        # 排空确认帧并取得主页面 UI 树。
        frames, main_stml = self.drain(quiet_s=3.0, max_s=45, want_ui=True)

        # 判断主页面树缺失。
        if not main_stml:

            # 抛出登录失败异常。
            raise RuntimeError(f"{self.company_name} 登录失败：未收到主页面 UI 树")

        # 缓存主页面树供后续查询解析菜单。
        self.main_stml = main_stml

        # 标记当前协议会话已登录。
        self.logged_in = True

        # 打印不含敏感值的登录成功日志。
        self.ph.success(self.ph.kv("登录状态", "成功", "green"))

        # 返回不含敏感字段的登录结果。
        return {"登录状态": "成功"}

    # 定义会话建立方法。
    def establish_session(self):

        """
        建立 WebSocket 连接并完成三段式密钥握手。

        :return: None。
        :rtype: None
        """

        # 生成客户端会话 GUID。
        self.guid = str(uuid.uuid4())

        # 计算 WS 升级用的 xclientid（GUID 的 MD5）。
        xclientid = hashlib.md5(self.guid.encode()).hexdigest()

        # 建立 WebSocket 连接。
        self.ws = websocket.create_connection(
            f"ws://{self.hostport}/webclient?xclientid={xclientid}",
            timeout=10,
            suppress_origin=True,
            header=[f"Cookie: X-CLIENT-ID={self.guid}", "Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits"],
        )

        # 生成会话密钥材料（rand1 + 4 字符尾段，rand2 由服务器 hello 填入）。
        randomkey = bytearray(12)
        struct.pack_into("<I", randomkey, 0, secrets.randbits(32))
        chars = "".join(secrets.choice(RANDOM_CHARS) for _ in range(4))
        for index, char in enumerate(chars):
            randomkey[8 + index] = ord(char)

        # 构建 Client Hello（36B）。
        hello = bytearray(36)
        hello[0] = 22
        struct.pack_into("<I", hello, 4, 28)
        hello[8] = 1
        struct.pack_into("<I", hello, 12, struct.unpack("<I", randomkey[0:4])[0])
        hello[32] = 2
        hello[33] = 0

        # 发送 Client Hello。
        self.ws.send_binary(bytes(hello))

        # 接收 Server Hello。
        opcode, server_hello = self.ws.recv_data()

        # 填入服务器下发的 rand2（线上原样字节）。
        randomkey[4:8] = server_hello[12:16]

        # 派生会话密钥（必须在 rand2 就位之后）。
        self.aes_key = hashlib.sha256(bytes(randomkey)).digest()
        self.aes_iv = hashlib.md5(bytes(randomkey)).digest()

        # 读取服务器 RSA 公钥。
        pubkey_len = struct.unpack("<I", server_hello[36:40])[0]
        public_key = load_der_public_key(server_hello[40:40 + pubkey_len])

        # 构建 Client Confirm（140B，RSA 加密 4 字符尾段）。
        encrypted = public_key.encrypt(chars.encode("ascii"), asym_padding.PKCS1v15())
        confirm = bytearray(140)
        confirm[0] = 22
        struct.pack_into("<I", confirm, 4, 132)
        confirm[8] = 3
        confirm[12:140] = encrypted

        # 发送 Client Confirm。
        self.ws.send_binary(bytes(confirm))

        # 接收确认回执。
        self.ws.recv_data()

    # 定义设备注册方法。
    def register_device(self):

        """
        发送 device-info 并返回登录页路径与控件清单。

        :return: 登录页路径和控件三元组列表。
        :rtype: tuple[str, list[tuple[str, str, str]]]
        """

        # 读取设备信息 JSON 样张（与浏览器报文一致）。
        device_json = self.build_device_json()

        # 构建并发送 device-info 信封（页面路径为 */，与浏览器报文一致）。
        self.ws.send_binary(self.encrypt_rpc(self.build_envelope("*/", device_json).encode("utf-8")))

        # 排空确认帧并取得登录页 UI 树。
        frames, login_stml = self.drain(quiet_s=3.0, max_s=30, want_ui=True)

        # 判断登录页树缺失。
        if not login_stml:

            # 抛出设备注册失败异常。
            raise RuntimeError(f"{self.company_name} 登录失败：未收到登录页 UI 树")

        # 解析登录页。
        page = json.loads(login_stml[login_stml.find("{"):])
        page_path = page.get("name")

        # 收集控件。
        controls = []
        self.collect_controls(page, controls)

        # 返回页面路径与控件。
        return page_path, controls

    # 定义设备信息构建方法。
    def build_device_json(self):

        """
        构建与服务端当前版本一致的设备信息 JSON。

        :return: 设备信息 JSON 文本。
        :rtype: str
        """

        # 构建设备信息对象（字段与浏览器报文逐字段一致）。
        device = {"deviceOS": "Web", "deviceOSVersion": "unkonw", "deviceModel": "unkonw", "screenSize": {"width": 1280, "height": 720}, "density": 1, "version": "1.3.3", "coreVersion": "120.16519", "autoBuild": False, "isCompany": False, "extraInfo": {"package_name": "unknow", "display_name": "Smobiler", "plugin_msg": None, "low_memory": True, "authPlugins": ["sm_wxApi", "sm_html", "sm_video", "sm_wxEnterpriseApi", "neil_videoplayer", "sm_vlcplayer", "neil_circle", "sm_speech", "sm_pdf", "neil_marquee", "neil_highlightwords", "sm_echarts"], "language": "zh-cn"}}

        # 返回紧凑 JSON 文本。
        return json.dumps(device, ensure_ascii=False, separators=(",", ":"))

    # 定义控件收集方法。
    def collect_controls(self, node, out):

        """
        深度收集 UI 树中的控件三元组。

        :param node: UI 树节点。
        :type node: dict | list
        :param out: 输出列表。
        :type out: list
        :return: None。
        :rtype: None
        """

        # 判断字典节点。
        if isinstance(node, dict):

            # 记录带 id 的控件。
            if node.get("id") is not None:
                props = node.get("props") or {}
                out.append((str(node.get("id")), str(node.get("type") or ""), str(props.get("text") or props.get("placeholder") or "")))

            # 递归子节点。
            for value in node.values():
                self.collect_controls(value, out)

            # 结束字典分支。
            return

        # 判断列表节点。
        if isinstance(node, list):

            # 递归子项。
            for item in node:
                self.collect_controls(item, out)

    # 定义加密方法。
    def encrypt_rpc(self, plaintext):

        """
        按 Smobiler 帧格式加密明文。

        :param plaintext: 明文字节。
        :type plaintext: bytes
        :return: WS 帧载荷。
        :rtype: bytes
        """

        # PKCS7 填充。
        padder = sym_padding.PKCS7(128).padder()
        padded = padder.update(plaintext) + padder.finalize()

        # AES-256-CBC 加密。
        encryptor = Cipher(algorithms.AES(self.aes_key), modes.CBC(self.aes_iv)).encryptor()
        ciphertext = encryptor.update(padded) + encryptor.finalize()

        # 组帧（类型 23 + 长度 + 密文）。
        frame = bytearray(8 + len(ciphertext))
        frame[0] = 23
        struct.pack_into("<I", frame, 4, len(ciphertext))
        frame[8:] = ciphertext

        # 返回帧。
        return bytes(frame)

    # 定义解密方法。
    def decrypt_rpc(self, payload):

        """
        解密 WS 帧载荷并返回文本。

        :param payload: WS 帧载荷。
        :type payload: bytes
        :return: 明文文本。
        :rtype: str
        """

        # 读取长度。
        length = struct.unpack("<I", payload[4:8])[0]

        # 解密。
        decryptor = Cipher(algorithms.AES(self.aes_key), modes.CBC(self.aes_iv)).decryptor()
        padded = decryptor.update(payload[8:8 + length]) + decryptor.finalize()

        # 去填充。
        unpadder = sym_padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded) + unpadder.finalize()

        # 返回文本。
        return plaintext.decode("utf-8", "replace")

    # 定义信封构建方法。
    def build_envelope(self, page_path, body_text):

        """
        构建 STTP/1.0 请求信封。

        :param page_path: 页面路径。
        :type page_path: str
        :param body_text: 正文文本。
        :type body_text: str
        :return: 完整信封文本。
        :rtype: str
        """

        # 拼接信封（Url 行与空行均为服务端必需）。
        return CRLF_LINE.join([
            f"STTP/1.0 GET {self.hostport}/{page_path}",
            f"Url:http://{self.hostport}/",
            "Accept-Encoding:plain",
            f"Content-Length:{len(body_text.encode('utf-8'))}",
            "Content-Type:RPC",
            f"Session:id={self.guid}",
        ]) + CRLF_LINE + CRLF_LINE + body_text

    # 定义事件发送方法。
    def send_event(self, page_path, event_json):

        """
        向当前页面发送 UI 事件。

        :param page_path: 页面路径。
        :type page_path: str
        :param event_json: 事件 JSON 对象。
        :type event_json: dict
        :return: None。
        :rtype: None
        """

        # 发送加密信封。
        self.ws.send_binary(self.encrypt_rpc(self.build_envelope(page_path, json.dumps(event_json, ensure_ascii=False, separators=(",", ":"))).encode("utf-8")))

    # 定义帧排空方法。
    def drain(self, quiet_s=3.0, max_s=45, want_ui=False):

        """
        持续接收帧直至安静超时或拿到 UI 树。

        :param quiet_s: 安静判定秒数。
        :type quiet_s: float
        :param max_s: 最长接收秒数。
        :type max_s: float
        :param want_ui: 是否以 UI 树帧为终止条件。
        :type want_ui: bool
        :return: 帧列表和首个 UI 树文本。
        :rtype: tuple[list[str], str | None]
        """

        # 初始化帧集合。
        frames = []

        # 初始化最近收帧时间。
        last_time = time.time()

        # 初始化绝对截止时间。
        deadline = time.time() + max_s

        # 循环收帧。
        while time.time() < deadline:

            # 设置本轮超时并接收。
            try:
                self.ws.settimeout(max(0.5, min(quiet_s, deadline - time.time())))
                opcode, payload = self.ws.recv_data()

            # 安静超时即结束。
            except websocket.WebSocketTimeoutException:
                if (time.time() - last_time) >= quiet_s:
                    break
                continue

            # 其他异常结束。
            except Exception as error:
                self.ph.warning(f"接收结束: {type(error).__name__}")
                break

            # 刷新最近收帧时间。
            last_time = time.time()

            # 处理加密帧。
            if opcode == 2 and len(payload) > 8 and payload[0] == 23:
                try:
                    text = self.decrypt_rpc(payload)
                    frames.append(text)
                    if want_ui and '"ui"' in text:
                        return frames, text

                # 处理解密失败。
                except Exception as error:
                    self.ph.warning(f"解密失败: {error}")

            # 处理会话失败信令。
            elif opcode == 2 and payload[0] == 0x15:
                self.ph.warning("收到会话失败信令")
                break

        # 返回帧集合。
        return frames, None

    # 定义协议配置解析方法。
    def resolve_config(self, data_type):

        """
        读取数据类型对应的菜单标题。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: 菜单标题。
        :rtype: str
        """

        # 判断数据类型已配置。
        if data_type in DATA_TYPE_CONFIG:

            # 返回菜单标题。
            return DATA_TYPE_CONFIG[data_type]

        # 抛出未接入数据类型异常。
        raise ValueError(f"{self.company_name} 暂不支持数据类型：{data_type}（平台菜单仅提供商品流向与库存查询）")

    # 定义数据类型校验方法。
    def validate_data_type(self, data_type):

        """
        校验数据类型存在协议映射。

        :param data_type: 数据类型名称。
        :type data_type: str
        :return: None。
        :rtype: None
        """

        # 调用协议配置解析完成校验。
        self.resolve_config(data_type)

    # 定义原始数据查询方法。
    def query_flow(self, data_type, start_date=None, end_date=None):

        """
        查询指定数据类型的全部原始业务记录。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 原始记录列表。
        :rtype: list[dict]
        """

        # 执行页面导航与查询并返回行。
        return self.query_rows(data_type, start_date, end_date)

    # 定义查询并生成 Excel 方法。
    def query_flow_to_excel(self, data_type, start_date=None, end_date=None, output_dir=None):

        """
        查询指定数据类型并生成原始字段 Excel。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :param output_dir: Excel 输出目录。
        :type output_dir: str | None
        :return: Excel 文件路径。
        :rtype: str
        """

        # 执行页面导航与查询。
        rows = self.query_rows(data_type, start_date, end_date)

        # 解析当前查询的日期范围。
        resolved_start_date, resolved_end_date = self.resolve_query_dates(start_date, end_date)

        # 解析默认 Excel 输出目录。
        target_directory = output_dir or os.getcwd()

        # 创建 Excel 输出目录。
        os.makedirs(target_directory, exist_ok=True)

        # 构建公共标准 Excel 文件名。
        file_name = self.build_output_file_name(data_type, resolved_start_date, resolved_end_date)

        # 拼接 Excel 完整输出路径。
        output_path = os.path.join(target_directory, file_name)

        # 解析字段清单。
        headers = self.resolve_headers(rows)

        # 写入 Excel。
        self.write_rows_to_excel(rows, headers, output_path, data_type)

        # 打印 Excel 落地结果摘要。
        self.ph.success(self.ph.join(self.ph.kv(f"{data_type} Excel已生成", self.ph.path(output_path), "green"), self.ph.kv("记录数", f"{len(rows)} 条", "cyan"), self.ph.kv("字段数", len(headers), "cyan")))

        # 返回 Excel 输出路径。
        return output_path

    # 定义主页面树缓存字段。
    main_stml = ""

    # 定义行查询主方法。
    def query_rows(self, data_type, start_date, end_date):

        """
        完成菜单导航、日期筛选、查询与数据源拉取。

        :param data_type: 数据类型名称。
        :type data_type: str
        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 原始记录列表。
        :rtype: list[dict]
        """

        # 确保当前会话已登录。
        self.ensure_login()

        # 解析菜单标题。
        menu_title = self.resolve_config(data_type)

        # 解析登录时缓存的主页面树。
        main_page = json.loads(self.main_stml[self.main_stml.find("{"):])
        main_path = main_page.get("name")

        # 动态解析菜单与子项 key。
        menu_id, menu_key = self.find_menu(main_page, menu_title)

        # 判断菜单缺失。
        if not menu_id or not menu_key:

            # 抛出菜单缺失异常。
            raise RuntimeError(f"{self.company_name} 主页面未找到菜单项：{menu_title}")

        # 命中页面树缓存时直接复用（页面已激活，重复导航只回空 ack）。
        if menu_title in self.page_stml_cache:
            page_stml = self.page_stml_cache[menu_title]
            flow_page = json.loads(page_stml[page_stml.find("{"):])
            flow_path = flow_page.get("name")
            flow_controls = []
            self.collect_controls(flow_page, flow_controls)

        # 未命中则导航并缓存页面树。
        else:
            # 发送菜单选择事件。
            self.send_event(main_path, {"method": "onEvent", "params": {"id": menu_id, "type": "onSelect", "params": {"value": menu_key, "selectkeys": [menu_key]}}})

            # 排空确认帧并取得业务页面树。
            frames, page_stml = self.drain(quiet_s=3.0, max_s=60, want_ui=False)

            # 取首个含页面树的大帧。
            page_stml = self.pick_page_stml(frames) or page_stml

            # 判断业务页面缺失。
            if not page_stml:

                # 抛出页面加载失败异常。
                raise RuntimeError(f"{self.company_name} {data_type} 页面加载失败：未收到业务页面 UI 树")

            # 写入缓存。
            self.page_stml_cache[menu_title] = page_stml

            # 解析业务页面。
            flow_page = json.loads(page_stml[page_stml.find("{"):])
            flow_path = flow_page.get("name")
            flow_controls = []
            self.collect_controls(flow_page, flow_controls)

        # 解析日期控件与查询按钮（库存页无日期控件）。
        date_picker = next((i for i, t, p in flow_controls if t == "ChooseDatePicker"), None)
        query_btn = next(i for i, t, p in flow_controls if p == "查询")

        # 发送日期筛选（仅流向页存在日期控件时）。
        if date_picker:
            self.send_event(flow_path, {"method": "onEvent", "params": {"id": date_picker, "type": "ValueChanged", "params": {"value": [f"{start_date} 00:00:00", f"{end_date} 00:00:00"], "_params": {"type": "changed", "name": "date"}}}})

            # 排空日期事件响应。
            self.drain(quiet_s=3.0, max_s=15, want_ui=False)

        # 发送查询 Press。
        self.send_event(flow_path, {"method": "onEvent", "params": {"id": query_btn, "type": "Press", "params": {"params": {"height": 35, "width": 35, "top": 137, "left": 750, "direction": 3}}}})

        # 排空查询响应并提取数据源 URL。
        frames_q, _ = self.drain(quiet_s=0.5, max_s=60, want_ui=False)
        source_url = self.extract_datasource_url(frames_q)

        # 判断数据源缺失。
        if not source_url:

            # 抛出数据源缺失异常。
            raise RuntimeError(f"{self.company_name} {data_type} 查询响应未包含数据源地址")

        # HTTP 拉取数据（0B 退避重试）。
        rows = self.fetch_datasource(source_url)

        # 返回记录列表。
        return rows

    # 定义主页面树缓存字段。
    main_stml = ""

    # 定义登录后主页面树保存逻辑。
    def save_main_stml(self, main_stml):

        """
        缓存登录后的主页面 UI 树。

        :param main_stml: 主页面 UI 树文本。
        :type main_stml: str
        :return: None。
        :rtype: None
        """

        # 缓存。
        self.main_stml = main_stml

    # 定义菜单定位方法。
    def find_menu(self, page, menu_title):

        """
        在主页面树中定位菜单控件与目标子项 key。

        :param page: 主页面树对象。
        :type page: dict
        :param menu_title: 目标子项标题。
        :type menu_title: str
        :return: 菜单控件 id 和子项 key。
        :rtype: tuple[str | None, str | None]
        """

        # 初始化结果容器。
        holder = {"menu_id": None, "menu_key": None}

        # 内部递归。
        def walk(node):
            if isinstance(node, dict):
                if node.get("type") == "PcMenu":
                    holder["menu_id"] = str(node.get("id"))
                    for group in (node.get("props") or {}).get("dataSource") or []:
                        for sub in group.get("sub") or []:
                            if sub.get("title") == menu_title:
                                holder["menu_key"] = sub.get("key")
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        # 执行递归。
        walk(page)

        # 返回结果。
        return holder["menu_id"], holder["menu_key"]

    # 定义大帧挑选方法。
    def pick_page_stml(self, frames):

        """
        从帧集合挑选首个 STML 页面树大帧。

        :param frames: 帧文本集合。
        :type frames: list[str]
        :return: 页面树文本。
        :rtype: str | None
        """

        # 遍历帧。
        for frame in frames:

            # 判断 STML 大帧。
            if "STML/1.0" in frame[:80] and len(frame) > 800:

                # 返回该帧。
                return frame

        # 无匹配返回 None。
        return None

    # 定义数据源 URL 提取方法。
    def extract_datasource_url(self, frames):

        """
        从查询响应帧提取完整数据源 URL。

        :param frames: 帧文本集合。
        :type frames: list[str]
        :return: 数据源 URL。
        :rtype: str | None
        """

        # 遍历帧。
        for frame in frames:

            # 判断无 JSON 体。
            if "{" not in frame:

                # 继续。
                continue

            # 解析 JSON 体。
            try:
                body = json.loads(frame[frame.find("{"):])
            except Exception:
                continue

            # 提取 STML 更新里的 props.data。
            updates = body.get("update") or []
            for item in updates:
                data_url = (item.get("props") or {}).get("data")
                if data_url and "datasource" in data_url:
                    return data_url

            # 提取 ReloadData 事件参数。
            if "ReloadData" in frame:
                try:
                    arr = json.loads(frame[frame.find("["):])
                    for item in arr if isinstance(arr, list) else []:
                        params_value = (item.get("params") or {}).get("params")
                        if isinstance(params_value, str) and "datasource" in params_value:
                            return params_value
                except Exception:
                    pass

        # 无匹配返回 None。
        return None

    # 定义数据源拉取方法。
    def fetch_datasource(self, source_url):

        """
        按数据源 URL 拉取行数组（0B 退避重试）。

        :param source_url: 完整数据源 URL。
        :type source_url: str
        :return: 原始记录列表。
        :rtype: list[dict]
        """

        # 拆解 URL 为路径。
        path = source_url.split(self.hostport, 1)[1] if self.hostport in source_url else source_url

        # 退避重试序列。
        for delay_s, attempt_i in ((0.0, 1), (1.5, 2), (3.0, 3)):

            # 非首次等待。
            if delay_s:
                time.sleep(delay_s)

            # 建立连接并发送请求。
            connection = http.client.HTTPConnection(self.hostport.split(":")[0], int(self.hostport.split(":")[1]), timeout=60)
            connection.request("GET", path, headers={"Cookie": f"X-CLIENT-ID={self.guid}", "X-CLIENT-ID": self.guid, "Accept": "application/json, text/javascript, */*; q=0.01", "X-Requested-With": "XMLHttpRequest", "User-Agent": "Mozilla/5.0", "Referer": f"http://{self.hostport}/"})
            response = connection.getresponse()
            data = response.read()
            connection.close()

            # 打印拉取结果。
            self.ph.info(self.ph.kv(f"数据源拉取(第{attempt_i}次)", f"{response.status} {len(data)}B", "cyan"))

            # 判断非空即成功。
            if len(data) > 0:
                break

        # 解析行数组。
        rows = json.loads(data.decode("utf-8", "replace"))

        # 校验数组。
        if not isinstance(rows, list):

            # 抛出响应结构异常。
            raise RuntimeError(f"{self.company_name} 数据源响应不是行数组")

        # 返回行。
        return rows

    # 定义查询日期解析方法。
    def resolve_query_dates(self, start_date, end_date):

        """
        解析流向查询使用的日期范围。

        :param start_date: 查询开始日期。
        :type start_date: str | None
        :param end_date: 查询结束日期。
        :type end_date: str | None
        :return: 解析后的开始日期和结束日期。
        :rtype: tuple[str, str]
        """

        # 解析流向查询开始日期。
        resolved_start_date = str(start_date or self.resolve_today_text())

        # 解析流向查询结束日期。
        resolved_end_date = str(end_date or resolved_start_date)

        # 校验流向日期范围顺序。
        self.validate_query_range(resolved_start_date, resolved_end_date)

        # 返回流向查询日期范围。
        return resolved_start_date, resolved_end_date

    # 定义当天日期解析方法。
    def resolve_today_text(self):

        """
        生成当前导出日期文本。

        :return: 当天日期文本。
        :rtype: str
        """

        # 导入日期时间模块。
        from datetime import datetime

        # 返回当天日期文本。
        return datetime.now().strftime("%Y-%m-%d")

    # 定义字段元数据解析方法。
    def resolve_headers(self, rows):

        """
        按行序合并全部原始字段。

        :param rows: 原始记录列表。
        :type rows: list[dict]
        :return: 字段标题列表。
        :rtype: list[str]
        """

        # 初始化合并字段。
        merged = []

        # 遍历记录。
        for row in rows:

            # 遍历字段。
            for key in row.keys():

                # 追加新字段。
                if key not in merged:
                    merged.append(key)

        # 返回字段列表。
        return merged

    # 定义 Excel 写入方法。
    def write_rows_to_excel(self, rows, headers, output_path, sheet_name):

        """
        按字段标题与顺序写入原始字段 Excel。

        :param rows: 原始记录列表。
        :type rows: list[dict]
        :param headers: 字段标题列表。
        :type headers: list[str]
        :param output_path: Excel 输出文件路径。
        :type output_path: str
        :param sheet_name: 工作表名称。
        :type sheet_name: str
        :return: None。
        :rtype: None
        """

        # 展平嵌套结构（dict/list 序列化为 JSON 文本）。
        flat_rows = [{key: (json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value) for key, value in row.items()} for row in rows]

        # 装配字段定义列表。
        field_headers = [{"key": title, "title": title} for title in headers]

        # 写入原始字段。
        write_formal_raw_excel(output_path, field_headers, flat_rows, sheet_name=sheet_name)

        # 应用项目统一 Excel 视觉样式。
        apply_standard_excel_style(output_path)


# 定义信封换行常量。
CRLF_LINE = "\r\n"
