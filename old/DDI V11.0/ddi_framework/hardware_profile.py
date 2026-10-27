# -*- coding: utf-8 -*-
"""
Windows 硬件信息采集模块。

本模块通过 Windows CIM 读取启动阶段展示的硬件型号信息，并在采集失败时返回可降级的空结果。

:return: 模块提供硬件信息采集与格式化函数。
:rtype: None
"""

# 导入 JSON 编解码模块。
import json

# 导入操作系统接口模块。
import os

# 导入子进程执行模块。
import subprocess

# 导入 URL 拆分与重组工具。
from urllib.parse import urlsplit

# 导入 URL 拆分与重组工具。
from urllib.parse import urlunsplit


# 定义空硬件信息结构。
EMPTY_HARDWARE_PROFILE = {
    "computer_text": "",
    "operating_system_text": "",
    "user_text": "",
    "mcp_url_text": "",
    "baseboard_text": "",
    "bios_text": "",
    "cpu_text": "",
    "memory_installed_text": "",
    "memory_module_texts": [],
    "gpu_texts": [],
    "disk_texts": [],
    "network_texts": [],
    "network_configuration_texts": [],
    "monitor_texts": [],
    "battery_texts": [],
    "sound_texts": [],
}


# 定义文本清理函数。
def clean_hardware_text(value):

    """
    清理硬件字段中的空白字符。

    :param value: 原始字段值。
    :type value: object
    :return: 清理后的字段文本。
    :rtype: str
    """

    # 判断原始字段是否为空。
    if value is None:

        # 返回空文本。
        return ""

    # 转换字段为字符串。
    text = str(value)

    # 合并字段内的连续空白。
    normalized_text = " ".join(text.replace("\x00", " ").split())

    # 返回清理后的字段文本。
    return normalized_text.strip()


# 定义非空文本拼接函数。
def join_hardware_parts(*parts):

    """
    拼接硬件说明字段。

    :param parts: 待拼接字段。
    :type parts: tuple[object, ...]
    :return: 拼接后的硬件说明。
    :rtype: str
    """

    # 初始化文本列表。
    text_parts = []

    # 遍历全部字段。
    for part_value in parts:

        # 清理当前字段文本。
        part_text = clean_hardware_text(part_value)

        # 判断当前字段是否存在。
        if part_text:

            # 追加当前字段文本。
            text_parts.append(part_text)

    # 返回字段拼接结果。
    return " ".join(text_parts)


# 定义字节容量格式化函数。
def format_hardware_capacity(size_bytes):

    """
    将硬件容量字节数格式化为 GB/TB 文本。

    :param size_bytes: 原始字节数。
    :type size_bytes: object
    :return: 容量文本。
    :rtype: str
    """

    # 捕获容量转换异常。
    try:

        # 转换容量为浮点字节数。
        byte_value = float(size_bytes or 0)

    # 处理容量转换失败。
    except (TypeError, ValueError):

        # 返回空容量文本。
        return ""

    # 判断容量是否无效。
    if byte_value <= 0:

        # 返回空容量文本。
        return ""

    # 计算 TB 容量。
    tb_value = byte_value / float(1024 ** 4)

    # 判断容量是否达到 TB 级。
    if tb_value >= 1.0:

        # 返回 TB 容量文本。
        return f"{tb_value:.1f} TB"

    # 计算 GB 容量。
    gb_value = byte_value / float(1024 ** 3)

    # 判断 GB 容量是否接近整数。
    if abs(gb_value - round(gb_value)) < 0.05:

        # 返回整数 GB 文本。
        return f"{int(round(gb_value))} GB"

    # 返回一位小数 GB 文本。
    return f"{gb_value:.1f} GB"


# 定义频率格式化函数。
def format_hardware_clock(speed_mhz):

    """
    将硬件频率格式化为 MHz 文本。

    :param speed_mhz: 频率数值。
    :type speed_mhz: object
    :return: 频率文本。
    :rtype: str
    """

    # 捕获频率转换异常。
    try:

        # 转换频率为整数。
        speed_value = int(float(speed_mhz or 0))

    # 处理频率转换失败。
    except (TypeError, ValueError):

        # 返回空频率文本。
        return ""

    # 判断频率是否无效。
    if speed_value <= 0:

        # 返回空频率文本。
        return ""

    # 返回 MHz 频率文本。
    return f"{speed_value} MHz"


# 定义网络速度格式化函数。
def format_hardware_network_speed(speed_value):

    """
    将网络速率格式化为 Gbps/Mbps 文本。

    :param speed_value: 原始速率。
    :type speed_value: object
    :return: 速率文本。
    :rtype: str
    """

    # 捕获速率转换异常。
    try:

        # 转换速率为浮点数。
        bit_value = float(speed_value or 0)

    # 处理速率转换失败。
    except (TypeError, ValueError):

        # 返回空速率文本。
        return ""

    # 判断速率是否无效。
    if bit_value <= 0:

        # 返回空速率文本。
        return ""

    # 判断速率是否达到 Gbps。
    if bit_value >= 1000000000:

        # 返回 Gbps 速率文本。
        return f"{bit_value / 1000000000:.1f} Gbps"

    # 返回 Mbps 速率文本。
    return f"{bit_value / 1000000:.0f} Mbps"


# 定义列表对象规整函数。
def ensure_hardware_list(value):

    """
    将 CIM JSON 字段规整为列表。

    :param value: JSON 字段值。
    :type value: object
    :return: 字段列表。
    :rtype: list
    """

    # 判断字段是否为空。
    if value is None:

        # 返回空列表。
        return []

    # 判断字段是否已经是列表。
    if isinstance(value, list):

        # 返回原始列表。
        return value

    # 返回单元素列表。
    return [value]


# 定义首个对象读取函数。
def first_hardware_item(value):

    """
    读取 CIM JSON 字段中的首个对象。

    :param value: JSON 字段值。
    :type value: object
    :return: 首个字段对象。
    :rtype: dict
    """

    # 读取规整后的字段列表。
    items = ensure_hardware_list(value)

    # 判断列表是否为空。
    if not items:

        # 返回空字典。
        return {}

    # 读取首个对象。
    first_item = items[0]

    # 返回字典对象或空字典。
    return first_item if isinstance(first_item, dict) else {}


# 定义操作系统文本构建函数。
def build_operating_system_text(operating_system_data):

    """
    构建 Windows 产品与构建号说明。

    :param operating_system_data: Windows 操作系统 CIM 数据。
    :type operating_system_data: dict
    :return: 系统版本说明。
    :rtype: str
    """

    # 读取 Windows 产品名称。
    caption_text = clean_hardware_text(operating_system_data.get("Caption"))

    # 读取 Windows 版本号。
    version_text = clean_hardware_text(operating_system_data.get("Version"))

    # 读取 Windows 构建号。
    build_text = clean_hardware_text(operating_system_data.get("BuildNumber"))

    # 读取系统架构。
    architecture_text = clean_hardware_text(operating_system_data.get("OSArchitecture"))

    # 返回系统版本说明。
    return join_hardware_parts(caption_text, f"版本 {version_text}" if version_text else "", f"Build {build_text}" if build_text else "", architecture_text)


# 定义网络地址筛选函数。
def select_network_addresses(address_values, address_family):

    """
    筛选指定地址族的有效网络地址。

    :param address_values: 网卡配置中的 IP 地址集合。
    :type address_values: object
    :param address_family: 目标地址族。
    :type address_family: str
    :return: 已筛选的地址文本列表。
    :rtype: list[str]
    """

    # 初始化地址文本列表。
    selected_addresses = []

    # 遍历规整后的地址列表。
    for address_value in ensure_hardware_list(address_values):

        # 清理当前地址文本。
        address_text = clean_hardware_text(address_value)

        # 判断当前地址是否为空。
        if not address_text:

            # 跳过空地址。
            continue

        # 判断当前地址是否为 IPv4。
        is_ipv4 = "." in address_text and ":" not in address_text

        # 判断当前地址是否为 IPv6。
        is_ipv6 = ":" in address_text

        # 判断当前地址是否符合目标地址族。
        if (address_family == "IPv4" and is_ipv4) or (address_family == "IPv6" and is_ipv6):

            # 追加当前地址。
            selected_addresses.append(address_text)

    # 返回已筛选地址列表。
    return selected_addresses


# 定义活动网络配置文本构建函数。
def build_network_configuration_texts(network_configuration_items):

    """
    构建活动网络的地址、网关与 DNS 说明。

    :param network_configuration_items: 已启用 IP 的网卡配置数据。
    :type network_configuration_items: list[dict]
    :return: 活动网络配置说明列表。
    :rtype: list[str]
    """

    # 初始化网络配置说明列表。
    configuration_texts = []

    # 遍历已启用 IP 的网络配置。
    for configuration_item in network_configuration_items:

        # 判断当前网络配置是否不是字典。
        if not isinstance(configuration_item, dict):

            # 跳过无效网络配置。
            continue

        # 读取适配器名称。
        adapter_text = clean_hardware_text(configuration_item.get("Description"))

        # 读取 IPv4 地址集合。
        ipv4_texts = select_network_addresses(configuration_item.get("IPAddress"), "IPv4")

        # 读取 IPv6 地址集合。
        ipv6_texts = select_network_addresses(configuration_item.get("IPAddress"), "IPv6")

        # 读取默认网关集合。
        gateway_texts = [clean_hardware_text(value) for value in ensure_hardware_list(configuration_item.get("DefaultIPGateway")) if clean_hardware_text(value)]

        # 读取 DNS 服务器集合。
        dns_texts = [clean_hardware_text(value) for value in ensure_hardware_list(configuration_item.get("DNSServerSearchOrder")) if clean_hardware_text(value)]

        # 构建当前网络配置说明。
        configuration_text = join_hardware_parts(adapter_text, f"IPv4 {', '.join(ipv4_texts)}" if ipv4_texts else "", f"IPv6 {', '.join(ipv6_texts)}" if ipv6_texts else "", f"网关 {', '.join(gateway_texts)}" if gateway_texts else "", f"DNS {', '.join(dns_texts)}" if dns_texts else "")

        # 判断当前网络配置说明是否存在。
        if configuration_text:

            # 追加当前网络配置说明。
            configuration_texts.append(configuration_text)

    # 返回活动网络配置说明列表。
    return configuration_texts


# 定义 MCP 地址脱敏函数。
def sanitize_mcp_url(value):

    """
    移除 MCP 地址中的凭据、查询参数与片段。

    :param value: 原始 MCP 地址。
    :type value: object
    :return: 可安全展示的 MCP 地址。
    :rtype: str
    """

    # 清理原始 MCP 地址文本。
    source_text = clean_hardware_text(value)

    # 判断 MCP 地址是否未配置。
    if not source_text:

        # 返回未配置状态。
        return "未配置"

    # 捕获 URL 解析异常。
    try:

        # 拆分 MCP 地址。
        parsed_url = urlsplit(source_text)

    # 处理无法解析的地址。
    except ValueError:

        # 返回已配置但不可展示的状态。
        return "已配置（地址格式无效）"

    # 判断地址是否缺少协议或主机。
    if not parsed_url.scheme or not parsed_url.hostname:

        # 返回已配置但不可展示的状态。
        return "已配置（地址格式无效）"

    # 读取地址端口。
    try:

        # 获取 URL 端口。
        port_value = parsed_url.port

    # 处理无效端口。
    except ValueError:

        # 返回已配置但不可展示的状态。
        return "已配置（地址格式无效）"

    # 读取地址主机。
    host_text = parsed_url.hostname

    # 判断地址主机是否为 IPv6。
    if ":" in host_text and not host_text.startswith("["):

        # 为 IPv6 主机补充 URL 方括号。
        host_text = f"[{host_text}]"

    # 拼接无凭据的地址网络位置。
    netloc_text = f"{host_text}:{port_value}" if port_value else host_text

    # 返回移除凭据、查询参数和片段后的地址。
    return urlunsplit((parsed_url.scheme, netloc_text, parsed_url.path, "", ""))


# 定义 WMI 字符数组解码函数。
def decode_wmi_char_codes(value):

    """
    解码 WMI MonitorID 字符数组字段。

    :param value: WMI 字符编码数组。
    :type value: object
    :return: 解码后的文本。
    :rtype: str
    """

    # 判断字段是否不是列表。
    if not isinstance(value, list):

        # 返回清理后的普通文本。
        return clean_hardware_text(value)

    # 初始化字符列表。
    characters = []

    # 遍历字符编码。
    for code_value in value:

        # 捕获字符编码转换异常。
        try:

            # 转换字符编码为整数。
            integer_code = int(code_value)

        # 处理字符编码转换失败。
        except (TypeError, ValueError):

            # 跳过无效字符编码。
            continue

        # 跳过字符串结束编码。
        if integer_code == 0:

            # 进入下一编码。
            continue

        # 追加当前字符。
        characters.append(chr(integer_code))

    # 返回解码后的文本。
    return clean_hardware_text("".join(characters))


# 定义 Windows CIM 原始数据读取函数。
def read_windows_cim_hardware():

    """
    读取 Windows CIM 原始硬件数据。

    :return: CIM 原始硬件数据。
    :rtype: dict
    """

    # 判断当前系统是否不是 Windows。
    if os.name != "nt":

        # 返回空硬件数据。
        return {}

    # 定义 PowerShell CIM 读取脚本。
    script_text = r"""
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$ErrorActionPreference = 'SilentlyContinue'
function Read-CimSafe($ClassName, $Namespace = 'root\cimv2') {
    try {
        return @(Get-CimInstance -Namespace $Namespace -ClassName $ClassName -ErrorAction Stop)
    } catch {
        return @()
    }
}
$result = [ordered]@{}
$result.ComputerSystem = @(Read-CimSafe 'Win32_ComputerSystem' | Select-Object -First 1 Manufacturer, Model, SystemType)
$result.BaseBoard = @(Read-CimSafe 'Win32_BaseBoard' | Select-Object -First 1 Manufacturer, Product, Version)
$result.BIOS = @(Read-CimSafe 'Win32_BIOS' | Select-Object -First 1 Manufacturer, SMBIOSBIOSVersion, ReleaseDate)
$result.Processor = @(Read-CimSafe 'Win32_Processor' | Select-Object -First 1 Name, Manufacturer, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed)
$result.Memory = @(Read-CimSafe 'Win32_PhysicalMemory' | Select-Object Manufacturer, PartNumber, ConfiguredClockSpeed, Speed, Capacity, BankLabel, DeviceLocator)
$result.Video = @(Read-CimSafe 'Win32_VideoController' | Select-Object Name, AdapterRAM, DriverVersion, VideoProcessor)
$result.Disk = @(Read-CimSafe 'Win32_DiskDrive' | Select-Object Model, Manufacturer, MediaType, InterfaceType, Size)
$result.Network = @(Read-CimSafe 'Win32_NetworkAdapter' | Where-Object { $_.PhysicalAdapter -eq $true } | Select-Object Name, Manufacturer, AdapterType, Speed)
$result.NetworkConfiguration = @(Read-CimSafe 'Win32_NetworkAdapterConfiguration' | Where-Object { $_.IPEnabled -eq $true } | Select-Object Description, IPAddress, DefaultIPGateway, DNSServerSearchOrder)
$result.OperatingSystem = @(Read-CimSafe 'Win32_OperatingSystem' | Select-Object -First 1 Caption, Version, BuildNumber, OSArchitecture)
$result.Monitor = @(Read-CimSafe 'WmiMonitorID' 'root\wmi' | Select-Object ManufacturerName, ProductCodeID, SerialNumberID, UserFriendlyName)
$result.Battery = @(Read-CimSafe 'Win32_Battery' | Select-Object Name, DeviceID, EstimatedChargeRemaining, BatteryStatus)
$result.Sound = @(Read-CimSafe 'Win32_SoundDevice' | Select-Object Name, Manufacturer)
$result | ConvertTo-Json -Depth 6 -Compress
"""

    # 捕获 PowerShell 执行异常。
    try:

        # 执行 PowerShell CIM 读取脚本。
        completed_process = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script_text], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15, check=False)

    # 处理 PowerShell 执行失败。
    except Exception:

        # 返回空硬件数据。
        return {}

    # 判断 PowerShell 是否没有输出数据。
    if not completed_process.stdout.strip():

        # 返回空硬件数据。
        return {}

    # 捕获 JSON 解析异常。
    try:

        # 返回 CIM JSON 数据。
        return json.loads(completed_process.stdout)

    # 处理 JSON 解析失败。
    except json.JSONDecodeError:

        # 返回空硬件数据。
        return {}


# 定义 CPU 文本构建函数。
def build_cpu_text(processor_data):

    """
    构建 CPU 型号说明。

    :param processor_data: CPU CIM 数据。
    :type processor_data: dict
    :return: CPU 型号说明。
    :rtype: str
    """

    # 读取 CPU 名称。
    cpu_name = clean_hardware_text(processor_data.get("Name"))

    # 读取 CPU 核心数量。
    core_count = clean_hardware_text(processor_data.get("NumberOfCores"))

    # 读取 CPU 线程数量。
    logical_count = clean_hardware_text(processor_data.get("NumberOfLogicalProcessors"))

    # 读取 CPU 最大频率。
    clock_text = format_hardware_clock(processor_data.get("MaxClockSpeed"))

    # 返回 CPU 型号说明。
    return join_hardware_parts(cpu_name, f"{core_count}核" if core_count else "", f"{logical_count}线程" if logical_count else "", clock_text)


# 定义内存条文本构建函数。
def build_memory_texts(memory_items):

    """
    构建内存条型号说明列表。

    :param memory_items: 内存条 CIM 数据列表。
    :type memory_items: list[dict]
    :return: 内存总量文本与内存条说明列表。
    :rtype: tuple[str, list[str]]
    """

    # 初始化内存总字节数。
    total_bytes = 0

    # 初始化内存条说明列表。
    memory_texts = []

    # 遍历内存条数据。
    for memory_item in memory_items:

        # 判断当前内存条数据是否不是字典。
        if not isinstance(memory_item, dict):

            # 进入下一条内存数据。
            continue

        # 读取内存条容量文本。
        capacity_text = format_hardware_capacity(memory_item.get("Capacity"))

        # 捕获容量汇总异常。
        try:

            # 汇总当前内存条容量。
            total_bytes += int(memory_item.get("Capacity") or 0)

        # 处理容量汇总失败。
        except (TypeError, ValueError):

            # 保留当前汇总值。
            total_bytes += 0

        # 读取内存厂商。
        manufacturer_text = clean_hardware_text(memory_item.get("Manufacturer"))

        # 读取内存型号。
        part_number_text = clean_hardware_text(memory_item.get("PartNumber"))

        # 读取内存频率。
        speed_text = format_hardware_clock(memory_item.get("ConfiguredClockSpeed") or memory_item.get("Speed"))

        # 读取内存插槽。
        slot_text = clean_hardware_text(memory_item.get("DeviceLocator") or memory_item.get("BankLabel"))

        # 构建当前内存条说明。
        memory_text = join_hardware_parts(capacity_text, manufacturer_text, part_number_text, speed_text, slot_text)

        # 判断当前内存条说明是否存在。
        if memory_text:

            # 追加当前内存条说明。
            memory_texts.append(memory_text)

    # 返回内存总量和内存条说明。
    return format_hardware_capacity(total_bytes), memory_texts


# 定义显卡文本构建函数。
def build_gpu_texts(video_items):

    """
    构建显卡型号说明列表。

    :param video_items: 显卡 CIM 数据列表。
    :type video_items: list[dict]
    :return: 显卡说明列表。
    :rtype: list[str]
    """

    # 初始化显卡说明列表。
    gpu_texts = []

    # 遍历显卡数据。
    for video_item in video_items:

        # 判断当前显卡数据是否不是字典。
        if not isinstance(video_item, dict):

            # 进入下一条显卡数据。
            continue

        # 读取显卡名称。
        name_text = clean_hardware_text(video_item.get("Name"))

        # 读取显存容量。
        ram_text = format_hardware_capacity(video_item.get("AdapterRAM"))

        # 读取显卡驱动版本。
        driver_text = clean_hardware_text(video_item.get("DriverVersion"))

        # 构建显卡说明。
        gpu_text = join_hardware_parts(name_text, ram_text, f"驱动 {driver_text}" if driver_text else "")

        # 判断显卡说明是否存在。
        if gpu_text:

            # 追加显卡说明。
            gpu_texts.append(gpu_text)

    # 返回显卡说明列表。
    return gpu_texts


# 定义磁盘文本构建函数。
def build_disk_texts(disk_items):

    """
    构建磁盘型号说明列表。

    :param disk_items: 磁盘 CIM 数据列表。
    :type disk_items: list[dict]
    :return: 磁盘说明列表。
    :rtype: list[str]
    """

    # 初始化磁盘说明列表。
    disk_texts = []

    # 遍历磁盘数据。
    for disk_item in disk_items:

        # 判断当前磁盘数据是否不是字典。
        if not isinstance(disk_item, dict):

            # 进入下一条磁盘数据。
            continue

        # 读取磁盘型号。
        model_text = clean_hardware_text(disk_item.get("Model"))

        # 读取磁盘介质类型。
        media_text = clean_hardware_text(disk_item.get("MediaType"))

        # 读取磁盘接口类型。
        interface_text = clean_hardware_text(disk_item.get("InterfaceType"))

        # 读取磁盘容量。
        size_text = format_hardware_capacity(disk_item.get("Size"))

        # 构建磁盘说明。
        disk_text = join_hardware_parts(size_text, model_text, media_text, interface_text)

        # 判断磁盘说明是否存在。
        if disk_text:

            # 追加磁盘说明。
            disk_texts.append(disk_text)

    # 返回磁盘说明列表。
    return disk_texts


# 定义网卡文本构建函数。
def build_network_texts(network_items):

    """
    构建网卡型号说明列表。

    :param network_items: 网卡 CIM 数据列表。
    :type network_items: list[dict]
    :return: 网卡说明列表。
    :rtype: list[str]
    """

    # 初始化网卡说明列表。
    network_texts = []

    # 遍历网卡数据。
    for network_item in network_items:

        # 判断当前网卡数据是否不是字典。
        if not isinstance(network_item, dict):

            # 进入下一条网卡数据。
            continue

        # 读取网卡名称。
        name_text = clean_hardware_text(network_item.get("Name"))

        # 读取网卡厂商。
        manufacturer_text = clean_hardware_text(network_item.get("Manufacturer"))

        # 读取网卡速率。
        speed_text = format_hardware_network_speed(network_item.get("Speed"))

        # 构建网卡说明。
        network_text = join_hardware_parts(name_text, manufacturer_text, speed_text)

        # 判断网卡说明是否存在。
        if network_text:

            # 追加网卡说明。
            network_texts.append(network_text)

    # 返回网卡说明列表。
    return network_texts


# 定义显示器文本构建函数。
def build_monitor_texts(monitor_items):

    """
    构建显示器型号说明列表。

    :param monitor_items: 显示器 CIM 数据列表。
    :type monitor_items: list[dict]
    :return: 显示器说明列表。
    :rtype: list[str]
    """

    # 初始化显示器说明列表。
    monitor_texts = []

    # 遍历显示器数据。
    for monitor_item in monitor_items:

        # 判断当前显示器数据是否不是字典。
        if not isinstance(monitor_item, dict):

            # 进入下一条显示器数据。
            continue

        # 解码显示器厂商。
        manufacturer_text = decode_wmi_char_codes(monitor_item.get("ManufacturerName"))

        # 解码显示器型号。
        product_text = decode_wmi_char_codes(monitor_item.get("ProductCodeID"))

        # 解码显示器名称。
        friendly_text = decode_wmi_char_codes(monitor_item.get("UserFriendlyName"))

        # 构建显示器说明。
        monitor_text = join_hardware_parts(manufacturer_text, friendly_text or product_text)

        # 判断显示器说明是否存在。
        if monitor_text:

            # 追加显示器说明。
            monitor_texts.append(monitor_text)

    # 返回显示器说明列表。
    return monitor_texts


# 定义电池文本构建函数。
def build_battery_texts(battery_items):

    """
    构建电池型号说明列表。

    :param battery_items: 电池 CIM 数据列表。
    :type battery_items: list[dict]
    :return: 电池说明列表。
    :rtype: list[str]
    """

    # 初始化电池说明列表。
    battery_texts = []

    # 遍历电池数据。
    for battery_item in battery_items:

        # 判断当前电池数据是否不是字典。
        if not isinstance(battery_item, dict):

            # 进入下一条电池数据。
            continue

        # 读取电池名称。
        name_text = clean_hardware_text(battery_item.get("Name") or battery_item.get("DeviceID"))

        # 读取电池电量。
        charge_text = clean_hardware_text(battery_item.get("EstimatedChargeRemaining"))

        # 构建电量说明。
        charge_label = f"{charge_text}%" if charge_text else ""

        # 构建电池说明。
        battery_text = join_hardware_parts(name_text, charge_label)

        # 判断电池说明是否存在。
        if battery_text:

            # 追加电池说明。
            battery_texts.append(battery_text)

    # 返回电池说明列表。
    return battery_texts


# 定义声卡文本构建函数。
def build_sound_texts(sound_items):

    """
    构建声卡型号说明列表。

    :param sound_items: 声卡 CIM 数据列表。
    :type sound_items: list[dict]
    :return: 声卡说明列表。
    :rtype: list[str]
    """

    # 初始化声卡说明列表。
    sound_texts = []

    # 遍历声卡数据。
    for sound_item in sound_items:

        # 判断当前声卡数据是否不是字典。
        if not isinstance(sound_item, dict):

            # 进入下一条声卡数据。
            continue

        # 读取声卡名称。
        name_text = clean_hardware_text(sound_item.get("Name"))

        # 读取声卡厂商。
        manufacturer_text = clean_hardware_text(sound_item.get("Manufacturer"))

        # 构建声卡说明。
        sound_text = join_hardware_parts(name_text, manufacturer_text)

        # 判断声卡说明是否存在。
        if sound_text:

            # 追加声卡说明。
            sound_texts.append(sound_text)

    # 返回声卡说明列表。
    return sound_texts


# 定义硬件信息采集函数。
def read_hardware_profile():

    """
    读取当前电脑硬件型号信息。

    :return: 硬件型号信息。
    :rtype: dict
    """

    # 初始化硬件信息结果。
    hardware_profile = dict(EMPTY_HARDWARE_PROFILE)

    # 读取当前 Windows 用户名。
    hardware_profile["user_text"] = clean_hardware_text(os.environ.get("USERNAME") or os.environ.get("USER"))

    # 读取并脱敏当前 MCP 服务地址。
    hardware_profile["mcp_url_text"] = sanitize_mcp_url(os.environ.get("DDI_MCP_URL"))

    # 读取 Windows CIM 原始硬件数据。
    cim_data = read_windows_cim_hardware()

    # 判断原始硬件数据是否为空。
    if not cim_data:

        # 返回空硬件信息。
        return hardware_profile

    # 读取整机数据。
    computer_item = first_hardware_item(cim_data.get("ComputerSystem"))

    # 读取操作系统数据。
    operating_system_item = first_hardware_item(cim_data.get("OperatingSystem"))

    # 读取主板数据。
    baseboard_item = first_hardware_item(cim_data.get("BaseBoard"))

    # 读取 BIOS 数据。
    bios_item = first_hardware_item(cim_data.get("BIOS"))

    # 读取 CPU 数据。
    processor_item = first_hardware_item(cim_data.get("Processor"))

    # 构建整机型号文本。
    hardware_profile["computer_text"] = join_hardware_parts(computer_item.get("Manufacturer"), computer_item.get("Model"), computer_item.get("SystemType"))

    # 构建操作系统版本文本。
    hardware_profile["operating_system_text"] = build_operating_system_text(operating_system_item)

    # 构建主板型号文本。
    hardware_profile["baseboard_text"] = join_hardware_parts(baseboard_item.get("Manufacturer"), baseboard_item.get("Product"), baseboard_item.get("Version"))

    # 构建 BIOS 文本。
    hardware_profile["bios_text"] = join_hardware_parts(bios_item.get("Manufacturer"), bios_item.get("SMBIOSBIOSVersion"))

    # 构建 CPU 文本。
    hardware_profile["cpu_text"] = build_cpu_text(processor_item)

    # 构建内存文本。
    memory_installed_text, memory_module_texts = build_memory_texts(ensure_hardware_list(cim_data.get("Memory")))

    # 写入内存总量文本。
    hardware_profile["memory_installed_text"] = memory_installed_text

    # 写入内存条说明列表。
    hardware_profile["memory_module_texts"] = memory_module_texts

    # 写入显卡说明列表。
    hardware_profile["gpu_texts"] = build_gpu_texts(ensure_hardware_list(cim_data.get("Video")))

    # 写入磁盘说明列表。
    hardware_profile["disk_texts"] = build_disk_texts(ensure_hardware_list(cim_data.get("Disk")))

    # 写入网卡说明列表。
    hardware_profile["network_texts"] = build_network_texts(ensure_hardware_list(cim_data.get("Network")))

    # 写入活动网络配置说明列表。
    hardware_profile["network_configuration_texts"] = build_network_configuration_texts(ensure_hardware_list(cim_data.get("NetworkConfiguration")))

    # 写入显示器说明列表。
    hardware_profile["monitor_texts"] = build_monitor_texts(ensure_hardware_list(cim_data.get("Monitor")))

    # 写入电池说明列表。
    hardware_profile["battery_texts"] = build_battery_texts(ensure_hardware_list(cim_data.get("Battery")))

    # 写入声卡说明列表。
    hardware_profile["sound_texts"] = build_sound_texts(ensure_hardware_list(cim_data.get("Sound")))

    # 返回硬件信息结果。
    return hardware_profile
