# -*- coding: utf-8 -*-
"""
DDI 终端与 Qt Quick 展示层隔离测试。

本模块验证两个入口均绑定公共协议执行服务，且 Qt 展示层不依赖终端入口。
"""

# 导入路径处理模块。
from pathlib import Path

# 导入单元测试模块。
import unittest

# 导入公共单商业执行函数。
from ddi_framework.task_execution import execute_company

# 导入终端入口模块。
import run_ddi


# 定义展示层隔离测试类。
class PresentationIsolationTests(unittest.TestCase):

    """
    验证公共业务层不会被终端或 Qt Quick 展示层反向依赖。

    :return: None。
    :rtype: None
    """

    # 定义终端公共执行绑定测试方法。
    def test_terminal_binds_the_public_company_executor(self):

        """
        验证终端实际执行函数直接绑定公共单商业执行服务。

        :return: None。
        :rtype: None
        """

        # 断言终端执行绑定与公共执行函数为同一对象。
        self.assertIs(run_ddi.run_company, execute_company)

    # 定义公共运行时终端隔离测试方法。
    def test_public_runtime_does_not_import_terminal_entrypoint(self):

        """
        验证公共运行时不通过终端入口间接取得业务执行能力。

        :return: None。
        :rtype: None
        """

        # 读取公共任务运行时源码文本。
        runtime_source = Path("ddi_framework/task_runtime.py").read_text(encoding="utf-8")

        # 断言公共运行时不导入终端入口模块。
        self.assertNotIn("import run_ddi", runtime_source)

    # 定义终端 GUI 依赖隔离测试方法。
    def test_terminal_entrypoint_does_not_import_gui_library(self):

        """
        验证终端入口未引入 Qt 或旧 Tk GUI 运行时依赖。

        :return: None。
        :rtype: None
        """

        # 读取终端入口源码文本。
        terminal_source = Path("run_ddi.py").read_text(encoding="utf-8")

        # 断言终端入口不导入 Qt 图形依赖。
        self.assertNotIn("PySide6", terminal_source)

        # 断言终端入口不导入旧 Tk 图形依赖。
        self.assertNotIn("customtkinter", terminal_source)

    # 定义 GUI 终端依赖隔离测试方法。
    def test_gui_entrypoint_does_not_import_terminal_entrypoint(self):

        """
        验证 GUI 入口只启动 Qt ViewModel，不导入终端入口。

        :return: None。
        :rtype: None
        """

        # 读取 GUI 入口源码文本。
        gui_source = Path("run_ddi_gui.py").read_text(encoding="utf-8")

        # 断言 GUI 入口不导入终端入口模块。
        self.assertNotIn("import run_ddi", gui_source)

        # 断言 GUI 入口使用 Qt 桥接层。
        self.assertIn("from ddi_gui_qt import main", gui_source)

    # 定义 Qt 公共事件消费测试方法。
    def test_qt_view_model_uses_public_runtime_and_bounded_models(self):

        """
        验证 Qt ViewModel 只调用公共运行时并限制事件消费和日志容量。

        :return: None。
        :rtype: None
        """

        # 读取 Qt ViewModel 源码文本。
        view_model_source = Path("ddi_gui_qt.py").read_text(encoding="utf-8")

        # 断言 GUI 调用公共无界面运行时。
        self.assertIn("DdiTaskRuntime", view_model_source)

        # 断言 GUI 关闭后台任务的终端镜像。
        self.assertIn("console_output_enabled=False", view_model_source)

        # 断言硬件扫描通过后台线程执行。
        self.assertIn('name="DDI-Hardware-Profile"', view_model_source)

        # 断言网络历史节点数量受到展示上限控制。
        self.assertIn("network_history_limit", view_model_source)

        # 断言事件消费具有明确时间预算。
        self.assertIn("event_time_budget_seconds = 0.003", view_model_source)

        # 断言可见日志使用增量模型并保持容量边界。
        self.assertIn("GuiLogListModel", view_model_source)

        # 断言增量日志模型限制可见行容量。
        self.assertIn("maximum_rows=3000", view_model_source)

    # 定义 QML 扁平导航状态测试方法。
    def test_qml_uses_explicit_flat_navigation_states(self):

        """
        验证侧栏导航直接绑定按钮状态并采用扁平选中层级。

        :return: None。
        :rtype: None
        """

        # 读取 QML 主界面文本。
        qml_source = Path("gui_qml/Main.qml").read_text(encoding="utf-8")

        # 断言导航委托拥有稳定的按钮标识。
        self.assertIn("id: navButton", qml_source)

        # 断言选中状态直接引用导航按钮的数据模型。
        self.assertIn("window.page === navButton.modelData.key", qml_source)

        # 断言导航内容使用确定的共享左侧内边距。
        self.assertIn("anchors.leftMargin: 24", qml_source)

        # 断言选中指示线在按钮自身的垂直中心定位。
        self.assertIn("anchors.verticalCenter: parent.verticalCenter", qml_source)

        # 断言未选中导航项使用可读的辅助前景色。
        self.assertIn("? textMain : textMuted", qml_source)

        # 断言不再通过嵌套背景父对象读取导航数据。
        self.assertNotIn("window.page === parent.modelData.key", qml_source)

    # 定义 QML 玻璃材质与导航边界测试方法。
    def test_qml_keeps_translucent_acrylic_and_shared_navigation_bounds(self):

        """
        验证原生 Acrylic 与导航内容共享同一控件边界。

        :return: None。
        :rtype: None
        """

        # 读取 QML 主界面文本。
        qml_source = Path("gui_qml/Main.qml").read_text(encoding="utf-8")

        # 读取 Windows 材质适配文本。
        effect_source = Path("gui_windows_effects.py").read_text(encoding="utf-8")

        # 断言应用窗口保留透明底色。
        self.assertIn('color: "transparent"', qml_source)

        # 断言导航行移除默认的垂直内容内边距。
        self.assertIn("topPadding: 0", qml_source)

        # 断言导航行移除默认的底部内容内边距。
        self.assertIn("bottomPadding: 0", qml_source)

        # 断言导航布局使用固定的首选高度。
        self.assertIn("Layout.preferredHeight: 40", qml_source)

        # 断言原生 Acrylic 使用低饱和绿色遮罩色保留后侧可见性。
        self.assertIn("0x2A224A1A", effect_source)

        # 断言文字密集页面使用独立的半透明对比度底层。
        self.assertIn('window.page === "network"', qml_source)

    # 定义 QML 网络能力测试方法。
    def test_qml_declares_global_glass_and_reduced_motion_network(self):

        """
        验证 QML 包含全局玻璃令牌、任务网络与减少动效入口。

        :return: None。
        :rtype: None
        """

        # 读取 QML 主界面文本。
        qml_source = Path("gui_qml/Main.qml").read_text(encoding="utf-8")

        # 断言 QML 使用无边框应用窗口。
        self.assertIn("Qt.FramelessWindowHint", qml_source)

        # 断言应用窗口保留透明底色以显示原生玻璃材质。
        self.assertIn('color: "transparent"', qml_source)

        # 断言 GUI 窗口标题使用产品名称。
        self.assertIn('title: "DDI 逆向神力"', qml_source)

        # 断言侧栏品牌使用产品名称。
        self.assertIn('text: "DDI 逆向神力"', qml_source)

        # 断言 QML 包含全局冰晶玻璃面板令牌。
        self.assertIn("component GlassPanel", qml_source)

        # 断言独立玻璃控件使用渐变材质表现层次。
        self.assertIn("gradient: Gradient", qml_source)

        # 断言界面包含统一的冷色玻璃强调令牌。
        self.assertIn("property color glassCool", qml_source)

        # 断言 QML 不保留全窗动态渐变背景。
        self.assertNotIn("RadialGradient {", qml_source)

    # 定义甘特时间轴声明测试方法。
    def test_qml_gantt_uses_shared_time_axis_geometry(self):

        """
        验证甘特条带由共享时间轴比例而非固定状态进度绘制。

        :return: None。
        :rtype: None
        """

        # 读取 QML 主界面文本。
        qml_source = Path("gui_qml/Main.qml").read_text(encoding="utf-8")

        # 断言甘特页绑定共享时间范围。
        self.assertIn("property var timelineRange: ddiViewModel.timelineRange", qml_source)

        # 断言横轴标签由真实时间格式化生成。
        self.assertIn('Qt.formatTime(new Date(value), "HH:mm:ss")', qml_source)

        # 断言条带横坐标使用阶段开始比例。
        self.assertIn("ganttTrack.rowData.timelineOffset", qml_source)

        # 断言条带宽度使用阶段持续比例。
        self.assertIn("ganttTrack.rowData.timelineSpan", qml_source)

        # 断言 QML 不对公共卡片使用离屏阴影特效。
        self.assertNotIn("MultiEffect", qml_source)

        # 断言 QML 使用统一的可读下拉组件。
        self.assertIn("component GlassCombo", qml_source)

        # 断言 QML 使用紧凑并发数步进器。
        self.assertIn("component CompactStepper", qml_source)

        # 断言 QML 不再使用原生 SpinBox。
        self.assertNotIn("SpinBox {", qml_source)

        # 断言首页不再保留重复跳转按钮。
        self.assertNotIn('text: "配置任务"', qml_source)

        # 断言首页不再保留网络跳转按钮。
        self.assertNotIn('text: "查看网络"', qml_source)

        # 断言任务控制台明确标注关键筛选维度。
        self.assertIn('label: "负责人"', qml_source)

        # 断言任务控制台明确标注启停筛选维度。
        self.assertIn('label: "启停状态"', qml_source)

        # 断言 QML 包含任务网络模型。
        self.assertIn("ddiViewModel.networkNodes", qml_source)

        # 断言 QML 使用单一画布绘制任务网络连线。
        self.assertIn("Canvas {", qml_source)

        # 断言 QML 不再为每条网络连线创建 Shape。
        self.assertNotIn("delegate: Shape", qml_source)

        # 断言 QML 可切换减少动效。
        self.assertIn("ddiViewModel.setReducedMotion", qml_source)

        # 断言任务控制台使用独立商业明细工作区。
        self.assertIn("id: companyWorkspace", qml_source)

        # 断言任务控制台使用横向实时日志工作区。
        self.assertIn("id: realtimeLogWorkspace", qml_source)

        # 断言商业与日志区域跟随任务运行状态调整高度。
        self.assertIn("Layout.fillHeight: ddiViewModel.task.running", qml_source)

        # 断言日志列表自动跟随最新输出。
        self.assertIn("onCountChanged: positionViewAtEnd()", qml_source)

        # 断言任务网络使用中心光核和批量画布渲染。
        self.assertIn("drawNetworkNode", qml_source)

        # 断言任务网络按首次入场时间绘制线条生长。
        self.assertIn("enteredAt", qml_source)

        # 断言网络粒子动效仅在任务运行时推进。
        self.assertIn("network.burstActive || (ddiViewModel.task.running && network.hasFlowingEdges())", qml_source)

        # 断言网络支持以指针位置为中心的深度缩放。
        self.assertIn("function setZoomAt", qml_source)

        # 断言网络文字与节点会跟随缩放比例同步放大。
        self.assertIn("property real readabilityScale", qml_source)

        # 断言网络粒子仅沿运行中任务连线绘制。
        self.assertIn('toNode.status === "运行中"', qml_source)

        # 断言旧的窄竖向观察栏已移除。
        self.assertNotIn("Layout.preferredWidth: window.observeOpen ? 285 : 38", qml_source)
