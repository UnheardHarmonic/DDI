# -*- coding: utf-8 -*-
"""
DDI Windows 原生毛玻璃窗口适配模块。

本模块仅为 Qt 窗口启用 Windows DWM 材质与圆角，不参与任务执行或展示业务数据。
"""

# 导入 ctypes Windows API 访问工具。
import ctypes

# 导入操作系统识别工具。
import os


# 定义 DWM 深色模式窗口属性编号。
DWMWA_USE_IMMERSIVE_DARK_MODE = 20

# 定义 DWM 窗口圆角偏好属性编号。
DWMWA_WINDOW_CORNER_PREFERENCE = 33

# 定义圆角窗口偏好值。
DWMWCP_ROUND = 2

# 定义 Acrylic 模糊强调状态。
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4


# 定义 Windows 强调策略结构。
class AccentPolicy(ctypes.Structure):

    """
    表示 SetWindowCompositionAttribute 使用的强调策略。

    :return: None。
    :rtype: None
    """

    # 声明强调策略字段布局。
    _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int), ("GradientColor", ctypes.c_uint), ("AnimationId", ctypes.c_int)]


# 定义 Windows 窗口合成属性数据结构。
class WindowCompositionAttributeData(ctypes.Structure):

    """
    表示 SetWindowCompositionAttribute 的属性载荷。

    :return: None。
    :rtype: None
    """

    # 声明窗口合成属性字段布局。
    _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.c_void_p), ("SizeOfData", ctypes.c_size_t)]


# 定义 Windows 原生玻璃启用函数。
def enable_native_glass(window):

    """
    为已创建的 Qt 窗口启用 DWM Acrylic 毛玻璃效果。

    :param window: 已显示或已创建原生句柄的 Qt 窗口。
    :type window: object
    :return: 是否成功调用至少一个 Windows 外观 API。
    :rtype: bool
    """

    # 判断当前平台不支持 Windows DWM。
    if os.name != "nt":

        # 返回未启用结果。
        return False

    # 捕获原生窗口句柄或 DWM 调用异常。
    try:

        # 读取 Qt 窗口原生句柄。
        window_handle = ctypes.c_void_p(int(window.winId()))

        # 读取 DWM API 动态库。
        dwmapi = ctypes.WinDLL("dwmapi")

        # 读取用户窗口 API 动态库。
        user32 = ctypes.WinDLL("user32")

        # 创建启用深色窗口模式的值。
        dark_mode = ctypes.c_int(1)

        # 设置深色模式窗口标题栏与系统材质基调。
        dwmapi.DwmSetWindowAttribute(window_handle, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))

        # 创建圆角窗口偏好值。
        corner_preference = ctypes.c_int(DWMWCP_ROUND)

        # 设置 Windows 11 原生圆角偏好。
        dwmapi.DwmSetWindowAttribute(window_handle, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(corner_preference), ctypes.sizeof(corner_preference))

        # 创建保留桌面可见性与冰晶亮度的深靛 Acrylic 渐变颜色值。
        acrylic_policy = AccentPolicy(ACCENT_ENABLE_ACRYLICBLURBEHIND, 0, 0x2A224A1A, 0)

        # 创建 Acrylic 合成属性载荷。
        acrylic_data = WindowCompositionAttributeData(19, ctypes.cast(ctypes.byref(acrylic_policy), ctypes.c_void_p), ctypes.sizeof(acrylic_policy))

        # 尝试调用 Windows 10 兼容的 Acrylic 合成 API。
        try:

            # 调用当前系统提供的 Acrylic 合成函数。
            acrylic_result = user32.SetWindowCompositionAttribute(window_handle, ctypes.byref(acrylic_data))

        # 处理系统未导出 Acrylic 合成函数的情况。
        except AttributeError:

            # 标记 Acrylic 当前不可用。
            acrylic_result = False

        # 判断 Acrylic 已成功启用。
        if acrylic_result:

            # 返回 Acrylic 启用成功结果。
            return True

        # 返回 Qt 透明窗口降级结果。
        return False

    # 处理不支持 API、远程桌面或窗口句柄不可用场景。
    except (AttributeError, OSError, TypeError, ValueError):

        # 返回 Qt 半透明降级结果。
        return False
