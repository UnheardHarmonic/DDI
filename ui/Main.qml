import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Shapes

ApplicationWindow {
    id: window
    width: 1520
    height: 960
    minimumWidth: 1180
    minimumHeight: 720
    visible: true
    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.Window
    title: "DDI 逆向神力"

    property string page: "overview"
    property bool accountOpen: false
    property bool detailsOpen: false
    property var selectedNode: ({})
    property int workspaceInset: 16
    property color ink: "#0b1711"
    property color glass: "#8c183d2b"
    property color glassStrong: "#a31c4b34"
    property color glassCool: "#762d5a3c"
    property color border: "#6b6f9d7c"
    property color borderBright: "#9ab2d7ab"
    property color textMain: "#eef5f3"
    property color textMuted: "#bdccca"
    property color textDim: "#83999b"
    property color amber: "#e7b469"
    property color amberBright: "#ffd38b"
    property color success: "#72d9ad"
    property color running: "#73d4dc"
    property color failure: "#ff8b9e"
    property color warning: "#f2ca72"

    function statusColor(status) {
        if (status === "成功") return success
        if (status === "运行中") return running
        if (status === "失败" || status === "错误") return failure
        if (status === "警告") return warning
        return textMuted
    }

    component GlassPanel: Rectangle {
        id: panel
        property color tint: window.glass
        property bool framed: false
        color: panel.framed ? panel.tint : "transparent"
        radius: panel.framed ? 8 : 0
        clip: false
        border.width: panel.framed ? 1 : 0
        border.color: Qt.rgba(window.border.r, window.border.g, window.border.b, 0.78)
        gradient: Gradient {
            GradientStop { position: 0.0; color: panel.framed ? Qt.lighter(panel.tint, 1.12) : "transparent" }
            GradientStop { position: 1.0; color: panel.framed ? Qt.darker(panel.tint, 1.08) : "transparent" }
        }
        Rectangle {
            visible: !panel.framed
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: Qt.rgba(window.border.r, window.border.g, window.border.b, 0.58)
        }
    }

    component TaskStatusStrip: Rectangle {
        id: statusStrip
        implicitWidth: 336
        implicitHeight: 44
        radius: 3
        color: ddiViewModel.task.running ? "#4a183f42" : "#35162d32"
        border.width: 1
        border.color: Qt.rgba(window.running.r, window.running.g, window.running.b, ddiViewModel.task.running ? 0.58 : 0.28)
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 8
            Rectangle {
                width: 7
                height: 7
                radius: 3.5
                color: ddiViewModel.task.running ? running : textDim
                SequentialAnimation on opacity {
                    running: ddiViewModel.task.running && !ddiViewModel.reducedMotion
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.35; duration: 700 }
                    NumberAnimation { to: 1.0; duration: 700 }
                }
            }
            ColumnLayout {
                spacing: 0
                Text { text: ddiViewModel.task.running ? "实时任务状态" : "任务待命"; color: textMain; font.pixelSize: 12; font.bold: true }
                Text { text: ddiViewModel.task.status + " · " + ddiViewModel.task.elapsed; color: textDim; font.pixelSize: 10 }
            }
            Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; Layout.topMargin: 8; Layout.bottomMargin: 8; color: border }
            RowLayout {
                spacing: 7
                Text { text: "成 " + ddiViewModel.task.success; color: success; font.pixelSize: 12; font.bold: true }
                Text { text: "败 " + ddiViewModel.task.failure; color: failure; font.pixelSize: 12; font.bold: true }
                Text { text: "运 " + ddiViewModel.task.runningCount; color: running; font.pixelSize: 12; font.bold: true }
                Text { text: "待 " + ddiViewModel.task.pending; color: textMuted; font.pixelSize: 12; font.bold: true }
            }
        }
    }

    component GlassButton: Button {
        id: button
        implicitHeight: 32
        implicitWidth: 76
        font.pixelSize: 12
        font.weight: Font.Medium
        contentItem: Text {
            text: button.text
            color: button.enabled ? textMain : textDim
            font: button.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 3
            color: button.down ? "#34474d" : (button.hovered ? "#26383e" : "transparent")
            border.width: button.activeFocus ? 1 : 0
            border.color: running
        }
    }

    component PrimaryButton: Button {
        id: button
        implicitHeight: 36
        implicitWidth: 92
        font.pixelSize: 13
        font.weight: Font.DemiBold
        contentItem: Text {
            text: button.text
            color: button.enabled ? ink : textDim
            font: button.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 3
            color: button.enabled ? (button.down ? "#c79550" : (button.hovered ? amberBright : amber)) : "#304147"
            border.width: 1
            border.color: button.enabled ? amberBright : border
        }
    }

    component FieldCaption: Text {
        color: textMuted
        font.pixelSize: 11
        font.weight: Font.DemiBold
    }

    component GlassField: TextField {
        id: field
        implicitHeight: 36
        color: textMain
        placeholderTextColor: textDim
        font.pixelSize: 12
        leftPadding: 11
        rightPadding: 11
        background: Rectangle {
            radius: 3
            color: field.activeFocus ? "#1e3036" : "#162229"
            border.width: field.activeFocus ? 2 : 1
            border.color: field.activeFocus ? running : border
        }
    }

    component GlassCombo: ComboBox {
        id: combo
        implicitHeight: 36
        font.pixelSize: 12
        contentItem: Text {
            text: combo.displayText === "" ? "全部" : combo.displayText
            color: textMain
            font: combo.font
            leftPadding: 11
            rightPadding: 28
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        indicator: Text {
            text: "⌄"
            color: textMuted
            font.pixelSize: 17
            x: combo.width - width - 11
            y: (combo.height - height) / 2 - 1
        }
        background: Rectangle {
            radius: 3
            color: combo.pressed ? "#263a40" : (combo.hovered ? "#1d3036" : "#162229")
            border.width: combo.activeFocus ? 2 : 1
            border.color: combo.activeFocus ? running : border
        }
        delegate: ItemDelegate {
            width: combo.width
            height: 34
            contentItem: Text {
                text: modelData === "" ? "全部" : modelData
                color: highlighted ? ink : textMain
                font.pixelSize: 12
                verticalAlignment: Text.AlignVCenter
                leftPadding: 11
                elide: Text.ElideRight
            }
            background: Rectangle {
                radius: 2
                color: highlighted ? amber : "transparent"
            }
        }
        popup: Popup {
            y: combo.height + 5
            width: combo.width
            implicitHeight: Math.min(contentItem.implicitHeight + 10, 260)
            padding: 5
            background: Rectangle {
                radius: 4
                border.width: 1
                border.color: borderBright
                color: "#1b282e"
            }
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: combo.popup.visible ? combo.delegateModel : null
                currentIndex: combo.highlightedIndex
                ScrollIndicator.vertical: ScrollIndicator { }
            }
        }
    }

    component LabeledCombo: ColumnLayout {
        id: root
        property string label: "筛选"
        property var options: []
        property string selectedValue: ""
        signal chosen(string value)
        spacing: 4
        FieldCaption { text: root.label }
        GlassCombo {
            Layout.fillWidth: true
            model: root.options
            currentIndex: Math.max(0, model.indexOf(root.selectedValue))
            onActivated: root.chosen(currentText)
        }
    }

    component MultiTypeSelector: ColumnLayout {
        id: typeSelector
        property var options: []
        property var selectedValues: []
        signal changed(var values)
        spacing: 4
        FieldCaption { text: "数据类型（可多选）" }
        RowLayout {
            Layout.fillWidth: true
            spacing: 4
            GlassButton { text: "全选"; implicitWidth: 48; onClicked: { typeSelector.selectedValues = typeSelector.options.filter(value => value !== "全部"); typeSelector.changed(typeSelector.selectedValues) } }
            GlassButton { text: "清空"; implicitWidth: 48; onClicked: { typeSelector.selectedValues = []; typeSelector.changed(typeSelector.selectedValues) } }
            Text { text: typeSelector.selectedValues.join("、") || "未选择"; color: textMuted; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
        }
        Flow {
            Layout.fillWidth: true
            spacing: 4
            Repeater {
                model: typeSelector.options.filter(value => value !== "全部")
                delegate: GlassCheck {
                    required property string modelData
                    checked: typeSelector.selectedValues.indexOf(modelData) >= 0
                    onToggled: {
                        let values = typeSelector.selectedValues.slice()
                        if (checked && values.indexOf(modelData) < 0) values.push(modelData)
                        if (!checked) values = values.filter(value => value !== modelData)
                        typeSelector.selectedValues = values
                        typeSelector.changed(values)
                    }
                }
            }
        }
    }

    component DataTypeDropdown: Item {
        id: dataTypeDropdown
        property var options: []
        property var selectedValues: []
        signal changed(var values)
        implicitWidth: 208
        implicitHeight: 36
        function toggleValue(value, checked) {
            let values = dataTypeDropdown.selectedValues.slice()
            if (checked && values.indexOf(value) < 0) values.push(value)
            if (!checked) values = values.filter(item => item !== value)
            dataTypeDropdown.selectedValues = values
            dataTypeDropdown.changed(values)
        }
        Button {
            id: trigger
            anchors.fill: parent
            text: ""
            contentItem: RowLayout {
                spacing: 8
                Text { text: dataTypeDropdown.selectedValues.length === 0 ? "选择数据类型" : dataTypeDropdown.selectedValues.length + " 种数据类型"; color: textMain; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                Text { text: dataTypeDropdown.selectedValues.length === 0 ? "未选择" : dataTypeDropdown.selectedValues.slice(0, 2).join("、") + (dataTypeDropdown.selectedValues.length > 2 ? " …" : ""); color: textMuted; font.pixelSize: 10; Layout.preferredWidth: 90; elide: Text.ElideRight }
                Text { text: popup.visible ? "⌃" : "⌄"; color: running; font.pixelSize: 17 }
            }
            background: Rectangle { radius: 3; color: popup.visible ? "#263f3c" : (trigger.hovered ? "#203733" : "#162a28"); border.width: trigger.activeFocus || popup.visible ? 2 : 1; border.color: trigger.activeFocus || popup.visible ? running : border }
            onClicked: popup.open()
            Popup {
                id: popup
                y: trigger.height + 6
                width: Math.max(300, dataTypeDropdown.width)
                padding: 10
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                background: Rectangle { radius: 4; color: "#142c29"; border.width: 1; border.color: borderBright }
                contentItem: ColumnLayout {
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "数据类型"; color: textMain; font.pixelSize: 12; font.bold: true; Layout.fillWidth: true }
                        GlassButton { text: "全选"; implicitWidth: 46; onClicked: { dataTypeDropdown.selectedValues = dataTypeDropdown.options.slice(); dataTypeDropdown.changed(dataTypeDropdown.selectedValues) } }
                        GlassButton { text: "清空"; implicitWidth: 46; onClicked: { dataTypeDropdown.selectedValues = []; dataTypeDropdown.changed([]) } }
                    }
                    Text { text: "全局多选；商业不支持的类型将在执行时跳过并记录警告"; color: textDim; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.Wrap }
                    Rectangle { Layout.fillWidth: true; height: 1; color: border }
                    Flickable {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(190, typeColumn.implicitHeight)
                        contentWidth: width
                        contentHeight: typeColumn.implicitHeight
                        clip: true
                        Column {
                            id: typeColumn
                            width: parent.width
                            spacing: 2
                            Repeater {
                                model: dataTypeDropdown.options
                                delegate: CheckBox {
                                    required property string modelData
                                    width: typeColumn.width
                                    text: modelData
                                    checked: dataTypeDropdown.selectedValues.indexOf(modelData) >= 0
                                    indicator: Rectangle { x: 2; y: 4; width: 18; height: 18; radius: 3; color: parent.checked ? amber : "transparent"; border.width: 1; border.color: parent.checked ? amberBright : border; Text { anchors.centerIn: parent; text: parent.checked ? "✓" : ""; color: ink; font.pixelSize: 12; font.bold: true } }
                                    contentItem: Text { text: parent.text; color: parent.checked ? textMain : textMuted; font.pixelSize: 11; leftPadding: 28; verticalAlignment: Text.AlignVCenter }
                                    onToggled: dataTypeDropdown.toggleValue(modelData, checked)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    component GlassToggle: Switch {
        id: control
        implicitWidth: 42
        implicitHeight: 24
        indicator: Rectangle {
            width: 42
            height: 24
            radius: 12
            color: "transparent"
            border.width: 1
            border.color: control.checked ? running : border
            gradient: Gradient {
                GradientStop { position: 0.0; color: control.checked ? "#7a4d91b6" : "#55305269" }
                GradientStop { position: 1.0; color: control.checked ? "#5b2d668b" : "#3c1d354d" }
            }
            Rectangle {
                width: 18
                height: 18
                radius: 9
                x: control.checked ? 21 : 3
                y: 3
                color: control.checked ? "#f3fbff" : "#9aa8b6"
                Behavior on x { NumberAnimation { duration: 130 } }
            }
        }
        contentItem: Item { }
    }

    component GlassCheck: CheckBox {
        id: control
        implicitWidth: 24
        implicitHeight: 24
        indicator: Rectangle {
            x: 2
            y: 2
            width: 20
            height: 20
            radius: 6
            color: "transparent"
            border.width: 1
            border.color: control.checked ? amberBright : border
            gradient: Gradient {
                GradientStop { position: 0.0; color: control.checked ? amberBright : "#4c284562" }
                GradientStop { position: 1.0; color: control.checked ? "#cb8641" : "#30172b40" }
            }
            Text {
                anchors.centerIn: parent
                text: control.checked ? "✓" : ""
                color: ink
                font.bold: true
            }
        }
        contentItem: Item { }
    }

    component CompactStepper: Item {
        id: stepper
        property int value: 1
        property int from: 1
        property int to: 12
        implicitWidth: 88
        implicitHeight: 36
        function decrease() { value = Math.max(from, value - 1) }
        function increase() { value = Math.min(to, value + 1) }
        Rectangle {
            anchors.fill: parent
            radius: 9
            color: "transparent"
            border.width: 1
            border.color: border
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#56284764" }
                GradientStop { position: 1.0; color: "#38172c43" }
            }
        }
        Button {
            width: 22
            height: 34
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            text: "−"
            enabled: stepper.value > stepper.from
            onClicked: stepper.decrease()
            contentItem: Text { text: parent.text; color: parent.enabled ? textMuted : textDim; font.pixelSize: 17; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            background: Rectangle { color: parent.down ? "#72426d92" : "transparent"; radius: 8 }
        }
        TextField {
            id: stepperInput
            anchors.left: parent.left
            anchors.leftMargin: 22
            anchors.right: parent.right
            anchors.rightMargin: 22
            anchors.verticalCenter: parent.verticalCenter
            height: 34
            text: stepper.value
            color: textMain
            font.pixelSize: 12
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            validator: IntValidator { bottom: stepper.from; top: stepper.to }
            selectByMouse: true
            onEditingFinished: stepper.value = Math.max(stepper.from, Math.min(stepper.to, Number(text) || stepper.from))
            background: Item { }
        }
        Button {
            width: 22
            height: 34
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            text: "+"
            enabled: stepper.value < stepper.to
            onClicked: stepper.increase()
            contentItem: Text { text: parent.text; color: parent.enabled ? textMuted : textDim; font.pixelSize: 17; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            background: Rectangle { color: parent.down ? "#72426d92" : "transparent"; radius: 8 }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#28101f16"
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#351d3b2a" }
            GradientStop { position: 0.56; color: "#20112719" }
            GradientStop { position: 1.0; color: "#32101f16" }
        }
    }

    Item {
        anchors.fill: parent
        Item {
            anchors.fill: parent
            anchors.margins: 12
            RowLayout {
                anchors.fill: parent
                spacing: 12
                Item {
                    Layout.fillHeight: true
                    Layout.preferredWidth: 218
                    Rectangle {
                        anchors.fill: parent
                        color: "#4a183827"
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#5a28513a" }
                            GradientStop { position: 1.0; color: "#3411271b" }
                        }
                        Rectangle {
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            anchors.right: parent.right
                            width: 1
                            color: border
                        }
                    }
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 11
                        RowLayout {
                            Rectangle {
                                width: 24
                                height: 24
                                radius: 3
                                color: "#1e353a"
                                border.width: 1
                                border.color: running
                                Text { anchors.centerIn: parent; text: "◇"; color: amberBright; font.pixelSize: 17 }
                            }
                            ColumnLayout {
                                spacing: 0
                                Text { text: "DDI 逆向神力"; color: textMain; font.pixelSize: 15; font.bold: true }
                                Text { text: "V14.0 · PROTOCOL FIRST"; color: textDim; font.pixelSize: 11 }
                            }
                        }
                        Rectangle { Layout.fillWidth: true; height: 1; color: border }
                        Repeater {
                            model: [
                                { key: "overview", icon: "⌂", title: "启动概览" },
                                { key: "console", icon: "▦", title: "任务控制台" },
                                { key: "gantt", icon: "▤", title: "运行甘特图" },
                                { key: "network", icon: "⌘", title: "任务网络" }
                            ]
                            delegate: Button {
                                id: navButton
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.minimumHeight: 40
                                Layout.preferredHeight: 40
                                Layout.maximumHeight: 40
                                implicitHeight: 40
                                topPadding: 0
                                bottomPadding: 0
                                leftPadding: 0
                                rightPadding: 0
                                onClicked: window.page = modelData.key
                                contentItem: Item {
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 24
                                        anchors.rightMargin: 8
                                        spacing: 11
                                        Text {
                                            text: navButton.modelData.icon
                                            color: window.page === navButton.modelData.key ? amberBright : textMuted
                                            font.pixelSize: 16
                                            Layout.preferredWidth: 18
                                            horizontalAlignment: Text.AlignHCenter
                                        }
                                        Text {
                                            text: navButton.modelData.title
                                            color: window.page === navButton.modelData.key ? textMain : textMuted
                                            font.pixelSize: 13
                                            font.weight: window.page === navButton.modelData.key ? Font.DemiBold : Font.Normal
                                            Layout.fillWidth: true
                                            verticalAlignment: Text.AlignVCenter
                                        }
                                    }
                                }
                                background: Rectangle {
                                    radius: 3
                                    color: window.page === navButton.modelData.key ? "#2d526d73" : (navButton.hovered ? "#1d435d64" : "transparent")
                                    Rectangle {
                                        width: 3
                                        height: 18
                                        anchors.left: parent.left
                                        anchors.leftMargin: 12
                                        anchors.verticalCenter: parent.verticalCenter
                                        visible: window.page === navButton.modelData.key
                                        radius: 1.5
                                        color: amber
                                    }
                                }
                            }
                        }
                        Item { Layout.fillHeight: true }
                        Item {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 70
                            Rectangle {
                                anchors.fill: parent
                                color: "#34224432"
                                border.width: 1
                                border.color: Qt.rgba(border.r, border.g, border.b, 0.58)
                            }
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                Text { text: "界面动效"; color: textMain; font.pixelSize: 11; font.bold: true }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: ddiViewModel.reducedMotion ? "低干扰模式" : "沉浸动效"; color: textMuted; font.pixelSize: 11; Layout.fillWidth: true }
                                    GlassToggle { checked: ddiViewModel.reducedMotion; onToggled: ddiViewModel.setReducedMotion(checked) }
                                }
                            }
                        }
                    }
                }
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Rectangle {
                        anchors.fill: parent
                        color: "#21162f23"
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#30204732" }
                            GradientStop { position: 1.0; color: "#1610271b" }
                        }
                    }
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 11
                        Item {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 58
                            Rectangle { anchors.fill: parent; color: "#351a402c" }
                            Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 1; color: border }
                            DragHandler { onActiveChanged: if (active) window.startSystemMove() }
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                Text {
                                    Layout.fillWidth: true
                                    text: window.page === "overview" ? "启动概览" : (window.page === "console" ? "任务控制台" : (window.page === "gantt" ? "运行甘特图" : "任务网络"))
                                    color: textMain
                                    font.pixelSize: 18
                                    font.bold: true
                                }
                                TaskStatusStrip { }
                                GlassButton { text: "—"; implicitWidth: 34; onClicked: window.showMinimized() }
                                GlassButton { text: "□"; implicitWidth: 34; onClicked: window.visibility = window.visibility === Window.Maximized ? Window.Windowed : Window.Maximized }
                                GlassButton { text: "×"; implicitWidth: 34; onClicked: window.close() }
                            }
                        }
                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Rectangle {
                                anchors.fill: parent
                                color: window.page === "network" ? "#10122d1e" : "#a808170f"
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: window.page === "network" ? "#1a245039" : "#b8123020" }
                                    GradientStop { position: 1.0; color: window.page === "network" ? "#0b102419" : "#9208170f" }
                                }
                            }
                            StackLayout {
                                anchors.fill: parent
                                currentIndex: window.page === "overview" ? 0 : (window.page === "console" ? 1 : (window.page === "gantt" ? 2 : 3))
                                OverviewPage { }
                                ConsolePage { }
                                GanttPage { }
                                NetworkPage { }
                            }
                        }
                        Text { Layout.leftMargin: workspaceInset; Layout.rightMargin: workspaceInset; text: ddiViewModel.notice; color: textMuted; font.pixelSize: 11; leftPadding: 4; elide: Text.ElideRight }
                    }
                }
            }
        }
    }

    component OverviewPage: Item {
        ColumnLayout {
            anchors.fill: parent
            spacing: 12
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 150
                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 2
                    color: amber
                }
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 5
                        Text { text: "本机配置与最近更新"; color: textMain; font.pixelSize: 25; font.bold: true }
                        Text { text: "当前设备能力、已配置商业与版本更新集中展示。"; color: textMuted; font.pixelSize: 13 }
                        RowLayout {
                            Text { text: ddiViewModel.initialData.enabledCount + " 家当前启用"; color: success; font.pixelSize: 13; font.bold: true }
                            Text { text: ddiViewModel.initialData.companyCount + " 家已登记商业"; color: amberBright; font.pixelSize: 13; font.bold: true }
                            Text { text: ddiViewModel.initialData.environment; color: textDim; font.pixelSize: 11 }
                        }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12
                Item {
                    Layout.preferredWidth: 480
                    Layout.fillHeight: true
                    Rectangle { anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom; width: 1; color: border }
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 10
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "设备与运行环境"; color: textMain; font.pixelSize: 16; font.bold: true; Layout.fillWidth: true }
                            Text { text: ddiViewModel.deviceLoading ? "采集中" : "本机信息"; color: amberBright; font.pixelSize: 11; font.bold: true }
                            GlassButton { text: "刷新"; implicitWidth: 52; enabled: !ddiViewModel.deviceLoading; onClicked: ddiViewModel.refreshDeviceDetails() }
                        }
                        Text { text: ddiViewModel.deviceLoading ? "正在后台采集硬件详情，界面可继续使用。" : "仅展示本机运行能力，不包含序列号与 MAC 地址。"; color: textMuted; font.pixelSize: 11 }
                        Rectangle { Layout.fillWidth: true; height: 1; color: border }
                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                            Column {
                                width: parent.width
                                spacing: 5
                                Repeater {
                                    model: ddiViewModel.deviceDetails
                                    delegate: Rectangle {
                                        required property var modelData
                                        width: parent.width
                                        height: Math.max(38, detailText.implicitHeight + 16)
                                        radius: 0
                                        color: "transparent"
                                        border.width: 0
                                        Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 1; color: Qt.rgba(border.r, border.g, border.b, 0.42) }
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 10
                                            anchors.rightMargin: 10
                                            spacing: 10
                                            Text { text: modelData.label; color: textMuted; font.pixelSize: 11; Layout.preferredWidth: 66 }
                                            Text { id: detailText; text: modelData.value; color: textMain; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.Wrap }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 10
                        RowLayout {
                            Layout.fillWidth: true
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text { text: "本版更新"; color: textMain; font.pixelSize: 16; font.bold: true }
                                Text { text: "DDI V14.0 · Qt Quick 深色冰晶工作台"; color: textMuted; font.pixelSize: 11 }
                            }
                        }
                        Rectangle { Layout.fillWidth: true; height: 1; color: border }
                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                            Text {
                                width: parent.width
                                text: ddiViewModel.initialData.changelog || "当前版本暂无更新日志。"
                                color: textMuted
                                font.pixelSize: 12
                                lineHeight: 1.46
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                }
            }
        }
    }

    component ConsolePage: Item {
        id: consolePage
        property string owner: ""
        property string region: ""
        property string province: ""
        property string platform: ""
        property string state: ""
        property string keyword: ""
        property string action: ddiViewModel.initialData.defaultAction
        property var dataTypes: ddiViewModel.initialData.dataTypes.filter(value => value !== "全部")
        property string dateMode: ddiViewModel.initialData.defaultDateMode
        property string startDate: ddiViewModel.initialData.defaultStartDate
        property string endDate: ddiViewModel.initialData.defaultEndDate
        property int workers: ddiViewModel.initialData.defaultWorkers
        property bool copyExcel: true
        function filter() { ddiViewModel.applyFilters({ keyword: keyword, owner: owner, region: region, province: province, platform: platform, status: state }) }
        function start() { ddiViewModel.startTask({ action: action, dataTypes: dataTypes, dateMode: dateMode, startDate: startDate, endDate: endDate, maxWorkers: workers, copyExcel: copyExcel }) }
        ColumnLayout {
            anchors.fill: parent
            spacing: 10
            GlassPanel {
                Layout.fillWidth: true
                Layout.preferredHeight: 82
                tint: glassStrong
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 9
                    ColumnLayout {
                        Layout.preferredWidth: 116
                        spacing: 2
                        Text { text: "任务参数"; color: textMain; font.pixelSize: 15; font.bold: true }
                            Text { text: "公共层统一执行"; color: textDim; font.pixelSize: 11 }
                    }
                    LabeledCombo { Layout.preferredWidth: 112; label: "执行动作"; options: ["query_excel", "query", "export", "login"]; selectedValue: consolePage.action; onChosen: consolePage.action = value }
                    LabeledCombo { Layout.preferredWidth: 154; label: "日期模式"; options: ["previous_month_full", "previous_month_to_today", "custom"]; selectedValue: consolePage.dateMode; onChosen: { consolePage.dateMode = value; if (value !== "custom") { let today = new Date(); let previousLast = new Date(today.getFullYear(), today.getMonth(), 0); let previousFirst = new Date(previousLast.getFullYear(), previousLast.getMonth(), 1); let formatDate = value => value.getFullYear() + "-" + String(value.getMonth() + 1).padStart(2, "0") + "-" + String(value.getDate()).padStart(2, "0"); consolePage.startDate = formatDate(previousFirst); consolePage.endDate = value === "previous_month_full" ? formatDate(previousLast) : formatDate(today) } } }
                    ColumnLayout { Layout.preferredWidth: 208; spacing: 4; FieldCaption { text: "数据类型（多选）" } DataTypeDropdown { Layout.fillWidth: true; options: ddiViewModel.initialData.dataTypes.filter(value => value !== "全部"); selectedValues: consolePage.dataTypes; onChanged: consolePage.dataTypes = values } }
                    ColumnLayout { Layout.preferredWidth: 110; spacing: 4; FieldCaption { text: "开始日期" } GlassField { text: consolePage.startDate; onEditingFinished: { consolePage.startDate = text; consolePage.dateMode = "custom" } } }
                    ColumnLayout { Layout.preferredWidth: 110; spacing: 4; FieldCaption { text: "结束日期" } GlassField { text: consolePage.endDate; onEditingFinished: { consolePage.endDate = text; consolePage.dateMode = "custom" } } }
                    ColumnLayout { Layout.preferredWidth: 88; spacing: 4; FieldCaption { text: "并发数" } CompactStepper { value: consolePage.workers; from: 1; to: 12; onValueChanged: consolePage.workers = value } }
                    ColumnLayout { spacing: 4; FieldCaption { text: "复制用 Excel" } GlassToggle { checked: consolePage.copyExcel; onToggled: consolePage.copyExcel = checked } }
                    Item { Layout.fillWidth: true }
                    PrimaryButton { text: ddiViewModel.task.running ? "任务运行中" : "启动任务"; enabled: !ddiViewModel.task.running; onClicked: consolePage.start() }
                    GlassButton { text: "安全停止"; enabled: ddiViewModel.task.running; onClicked: ddiViewModel.requestStop() }
                }
            }
            GlassPanel {
                Layout.fillWidth: true
                Layout.preferredHeight: 54
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 9
                    spacing: 8
                    Text { text: "快捷方案"; color: textMain; font.pixelSize: 12; font.bold: true }
                    GlassField { id: presetName; Layout.preferredWidth: 155; placeholderText: "方案名称" }
                    GlassButton { text: "保存当前"; onClicked: ddiViewModel.savePreset(presetName.text, { action: consolePage.action, dataTypes: consolePage.dataTypes, dateMode: consolePage.dateMode, startDate: consolePage.startDate, endDate: consolePage.endDate, maxWorkers: consolePage.workers, copyExcel: consolePage.copyExcel }) }
                    GlassCombo { id: presetPicker; Layout.preferredWidth: 240; model: ddiViewModel.presets; textRole: "name" }
                    GlassButton { text: "加载方案"; enabled: presetPicker.currentText.length > 0; onClicked: { let value = ddiViewModel.loadPreset(presetPicker.currentText); consolePage.action = value.action || consolePage.action; consolePage.dataTypes = value.dataTypes || consolePage.dataTypes; consolePage.dateMode = value.dateMode || consolePage.dateMode; consolePage.startDate = value.startDate || consolePage.startDate; consolePage.endDate = value.endDate || consolePage.endDate; consolePage.workers = value.maxWorkers || consolePage.workers; consolePage.copyExcel = value.copyExcel === undefined ? consolePage.copyExcel : value.copyExcel } }
                }
            }
            Item {
                id: consoleWorkspace
                objectName: "consoleWorkspace"
                Layout.fillWidth: true
                Layout.fillHeight: true
                property real splitRatio: 0.68
                property bool splitAdjusted: false
                property bool lastRunning: false
                readonly property real dividerHeight: 10
                function clampRatio(value) { return Math.max(0.18, Math.min(0.82, value)) }
                function splitY() {
                    let availableHeight = Math.max(0, height - dividerHeight)
                    let minimumCompanyHeight = Math.min(220, availableHeight * 0.55)
                    let minimumLogHeight = Math.min(150, availableHeight * 0.38)
                    let maximumCompanyHeight = Math.max(minimumCompanyHeight, availableHeight - minimumLogHeight)
                    return Math.round(Math.max(minimumCompanyHeight, Math.min(maximumCompanyHeight, availableHeight * splitRatio)))
                }
                function applyTaskMode() {
                    if (lastRunning !== ddiViewModel.task.running) {
                        lastRunning = ddiViewModel.task.running
                        splitAdjusted = false
                        splitRatio = lastRunning ? 0.34 : 0.68
                    }
                }
                Connections {
                    target: ddiViewModel
                    function onTaskChanged() { consoleWorkspace.applyTaskMode() }
                }
                Component.onCompleted: {
                    lastRunning = !ddiViewModel.task.running
                    applyTaskMode()
                }

                GlassPanel {
                    id: companyWorkspace
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: consoleWorkspace.splitY()
                    tint: glassStrong
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 13
                    Layout.fillHeight: ddiViewModel.task.running
                    spacing: 8
                    RowLayout { Layout.fillWidth: true; Text { text: "商业选择"; color: textMain; font.pixelSize: 16; font.bold: true; Layout.fillWidth: true } Text { text: ddiViewModel.task.running ? "任务运行时保留筛选与快速定位" : "空闲时优先展示商业明细"; color: textMuted; font.pixelSize: 11 } GlassButton { text: "全选已启用"; onClicked: ddiViewModel.selectEnabledCompanies() } GlassButton { text: "清空选择"; onClicked: ddiViewModel.clearSelection() } }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 7
                        ColumnLayout { Layout.preferredWidth: 194; spacing: 4; FieldCaption { text: "商业名称" } GlassField { placeholderText: "搜索商业名称"; text: consolePage.keyword; onTextChanged: { consolePage.keyword = text; consolePage.filter() } } }
                        LabeledCombo { Layout.preferredWidth: 112; label: "负责人"; options: ddiViewModel.initialData.owners; selectedValue: consolePage.owner; onChosen: { consolePage.owner = value; consolePage.filter() } }
                        LabeledCombo { Layout.preferredWidth: 112; label: "大区"; options: ddiViewModel.initialData.regions; selectedValue: consolePage.region; onChosen: { consolePage.region = value; consolePage.filter() } }
                        LabeledCombo { Layout.preferredWidth: 112; label: "省份"; options: ddiViewModel.initialData.provinces; selectedValue: consolePage.province; onChosen: { consolePage.province = value; consolePage.filter() } }
                        LabeledCombo { Layout.preferredWidth: 104; label: "平台"; options: ddiViewModel.initialData.platforms; selectedValue: consolePage.platform; onChosen: { consolePage.platform = value; consolePage.filter() } }
                        LabeledCombo { Layout.preferredWidth: 104; label: "启停状态"; options: ["", "已启用", "已停用"]; selectedValue: consolePage.state; onChosen: { consolePage.state = value; consolePage.filter() } }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: border }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: ddiViewModel.companies
                        spacing: 5
                        ScrollBar.vertical: ScrollBar { }
                        delegate: Rectangle {
                            required property var modelData
                            width: ListView.view.width
                            height: 57
                            radius: 0
                            color: "transparent"
                            border.width: 0
                            Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 1; color: modelData.selected ? amber : Qt.rgba(border.r, border.g, border.b, 0.48) }
                            Rectangle { anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom; width: 2; visible: modelData.selected; color: amber }
                            MouseArea { id: hover; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 8
                                GlassCheck { checked: modelData.selected; onToggled: ddiViewModel.toggleCompany(modelData.name) }
                                ColumnLayout { Layout.fillWidth: true; spacing: 2; Text { text: modelData.name; color: textMain; font.pixelSize: 13; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true } Text { text: modelData.platform + " · " + modelData.owner + " · " + modelData.region + " / " + modelData.province; color: textMuted; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true } }
                                Text { text: modelData.enabled ? "已启用" : "已停用"; color: modelData.enabled ? success : textDim; font.pixelSize: 11; font.bold: true }
                                GlassToggle { checked: modelData.enabled; onToggled: ddiViewModel.setCompanyEnabled(modelData.name, checked) }
                                GlassButton { text: "网络"; implicitWidth: 52; onClicked: { ddiViewModel.focusNetworkNode("company:" + modelData.name); window.page = "network" } }
                                GlassButton { text: "账号"; implicitWidth: 52; onClicked: { ddiViewModel.openAccount(modelData.name); window.accountOpen = true } }
                            }
                        }
                    }
                }
            }

                Rectangle {
                    id: consoleDivider
                    objectName: "consoleDivider"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    y: consoleWorkspace.splitY()
                    height: consoleWorkspace.dividerHeight
                    color: "transparent"
                    Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; height: 1; color: Qt.rgba(borderBright.r, borderBright.g, borderBright.b, 0.60) }
                    Rectangle { anchors.horizontalCenter: parent.horizontalCenter; anchors.verticalCenter: parent.verticalCenter; width: 42; height: 4; radius: 2; color: Qt.rgba(amber.r, amber.g, amber.b, 0.62) }
                    MouseArea {
                        objectName: "consoleDividerHandle"
                        anchors.fill: parent
                        cursorShape: Qt.SizeVerCursor
                        property real pressWorkspaceY: 0
                        property real pressRatio: 0
                        onPressed: {
                            pressWorkspaceY = mapToItem(consoleWorkspace, mouse.x, mouse.y).y
                            pressRatio = consoleWorkspace.splitRatio
                            consoleWorkspace.splitAdjusted = true
                        }
                        onPositionChanged: if (pressed) {
                            let availableHeight = Math.max(1, consoleWorkspace.height - consoleWorkspace.dividerHeight)
                            let currentWorkspaceY = mapToItem(consoleWorkspace, mouse.x, mouse.y).y
                            consoleWorkspace.splitRatio = consoleWorkspace.clampRatio(pressRatio + (currentWorkspaceY - pressWorkspaceY) / availableHeight)
                        }
                    }
                }

                GlassPanel {
                    id: realtimeLogWorkspace
                    anchors.left: parent.left
                    anchors.right: parent.right
                    y: consoleDivider.y + consoleDivider.height
                    height: Math.max(0, parent.height - y)
                    tint: ddiViewModel.task.running ? glassCool : glass
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 7
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "实时日志"; color: textMain; font.pixelSize: 15; font.bold: true }
                        Text { text: ddiViewModel.task.running ? "任务运行中 · 横向实时输出" : "等待任务输出"; color: ddiViewModel.task.running ? running : textMuted; font.pixelSize: 11; Layout.fillWidth: true }
                        Text { text: "总 " + ddiViewModel.task.total; color: amberBright; font.pixelSize: 12; font.bold: true }
                        Text { text: "运行 " + ddiViewModel.task.runningCount; color: running; font.pixelSize: 12; font.bold: true }
                        Text { text: "完成 " + ddiViewModel.task.completed; color: textMain; font.pixelSize: 12; font.bold: true }
                        Text { text: "失败 " + ddiViewModel.task.failure; color: failure; font.pixelSize: 12; font.bold: true }
                        GlassButton { text: "打开任务日志"; implicitWidth: 92; onClicked: ddiViewModel.openTaskLog() }
                    }
                    Text { Layout.fillWidth: true; text: ddiViewModel.task.status; color: statusColor(ddiViewModel.task.running ? "运行中" : "就绪"); font.pixelSize: 11; elide: Text.ElideRight }
                    Rectangle { Layout.fillWidth: true; height: 1; color: border }
                    ListView {
                        id: realtimeLogList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: ddiViewModel.logs
                        spacing: 3
                        cacheBuffer: 0
                        ScrollBar.vertical: ScrollBar { }
                        // onCountChanged: positionViewAtEnd()
                        onCountChanged: { positionViewAtEnd(); realtimeLogScrollTimer.restart() }
                        delegate: RowLayout {
                            required property string time
                            required property string company
                            required property string message
                            required property string status
                            width: ListView.view.width
                            spacing: 8
                            Text { text: "[" + time + "]"; color: textDim; font.pixelSize: 11; font.family: "Consolas" }
                            Text { visible: company.length > 0; text: company; color: amberBright; font.pixelSize: 11; font.bold: true; Layout.preferredWidth: visible ? 126 : 0; elide: Text.ElideRight }
                            Text { Layout.fillWidth: true; text: message; color: statusColor(status); font.pixelSize: ddiViewModel.task.running ? 12 : 11; wrapMode: Text.Wrap; lineHeight: 1.18 }
                        }
                    }
                    Timer {
                        id: realtimeLogScrollTimer
                        interval: 110
                        repeat: false
                        onTriggered: realtimeLogList.positionViewAtEnd()
                    }
                }
                }
            }
        }
    }

    component GanttPage: Item {
        id: ganttPage
        property var rows: ddiViewModel.timelineRows
        property var timelineRange: ddiViewModel.timelineRange

        function tickLabel(index) {
            let rangeStart = Number(timelineRange.startEpoch || 0)
            let rangeEnd = Number(timelineRange.endEpoch || 0)
            if (rangeStart <= 0 || rangeEnd <= rangeStart) return "—"
            let value = rangeStart + (rangeEnd - rangeStart) * index / 5
            return Qt.formatTime(new Date(value), "HH:mm:ss")
        }

        GlassPanel {
            anchors.fill: parent
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text { text: "运行甘特图"; color: textMain; font.pixelSize: 18; font.bold: true }
                        Text { text: "每家商业一条主时间线 · 阶段事件仅更新最新状态与记录数"; color: textMuted; font.pixelSize: 11 }
                    }
                    Text { text: "● 成功"; color: success; font.pixelSize: 11 }
                    Text { text: "● 运行"; color: running; font.pixelSize: 11 }
                    Text { text: "● 失败"; color: failure; font.pixelSize: 11 }
                    Button {
                        id: ganttTaskLogButton
                        implicitWidth: 156
                        implicitHeight: 32
                        enabled: String(ddiViewModel.task.logPath || "").length > 0
                        text: enabled ? "打开当前 logs.xlsx" : "日志生成中"
                        onClicked: ddiViewModel.openTaskLog()
                        ToolTip.visible: hovered && !enabled
                        ToolTip.text: "任务完成后将生成并保存当前 logs.xlsx"
                        contentItem: Text {
                            text: ganttTaskLogButton.text
                            color: ganttTaskLogButton.enabled ? ink : textDim
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                        background: Rectangle {
                            radius: 3
                            color: ganttTaskLogButton.enabled ? (ganttTaskLogButton.down ? "#c79550" : (ganttTaskLogButton.hovered ? amberBright : amber)) : "#243d4148"
                            border.width: 1
                            border.color: ganttTaskLogButton.enabled ? amberBright : Qt.rgba(border.r, border.g, border.b, 0.72)
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 30
                    spacing: 10
                    Text { text: "商业 / 平台 / 数据类型"; color: textMuted; font.pixelSize: 11; Layout.preferredWidth: 242 }
                    Item {
                        id: ganttAxis
                        Layout.fillWidth: true
                        Layout.preferredHeight: 30
                        Repeater {
                            model: 6
                            delegate: Item {
                                required property int index
                                x: ganttAxis.width * index / 5
                                width: 1
                                height: ganttAxis.height
                                Rectangle { anchors.top: parent.top; anchors.bottom: parent.bottom; width: 1; color: Qt.rgba(border.r, border.g, border.b, 0.56) }
                                Text { anchors.top: parent.top; anchors.topMargin: 2; anchors.horizontalCenter: parent.horizontalCenter; text: ganttPage.tickLabel(index); color: textDim; font.pixelSize: 10 }
                            }
                        }
                    }
                    Text { text: "记录数 / 状态 / 阶段"; color: textMuted; font.pixelSize: 11; Layout.preferredWidth: 148; horizontalAlignment: Text.AlignRight }
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: border }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: ganttPage.visible ? ganttPage.rows : []
                    spacing: 0
                    ScrollBar.vertical: ScrollBar { }
                    delegate: Item {
                        id: ganttRow
                        required property var modelData
                        width: ListView.view.width
                        height: 64
                        Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 1; color: Qt.rgba(border.r, border.g, border.b, 0.48) }
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 9
                            anchors.rightMargin: 9
                            spacing: 10
                            Rectangle { width: 3; height: 34; color: statusColor(modelData.status) }
                            ColumnLayout {
                                Layout.preferredWidth: 229
                                spacing: 2
                                Text { text: modelData.company; color: textMain; font.pixelSize: 12; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                                Text { text: (modelData.platform || "") + " · " + (modelData.dataType || ""); color: textMuted; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                            }
                            Item {
                                id: ganttTrack
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.minimumWidth: 280
                                Layout.preferredWidth: 520
                                property var rowData: ganttRow.modelData
                                Repeater {
                                    model: 6
                                    delegate: Rectangle {
                                        required property int index
                                        x: ganttTrack.width * index / 5
                                        y: 0
                                        width: 1
                                        height: ganttTrack.height
                                        color: Qt.rgba(border.r, border.g, border.b, 0.28)
                                    }
                                }
                                Rectangle {
                                    visible: Number(ganttTrack.rowData.timelineOffset === undefined ? -1 : ganttTrack.rowData.timelineOffset) >= 0
                                    x: ganttTrack.width * Number(ganttTrack.rowData.timelineOffset || 0)
                                    y: 22
                                    width: Math.max(8, ganttTrack.width * Number(ganttTrack.rowData.timelineSpan || 0))
                                    height: 12
                                    radius: 3
                                    color: statusColor(ganttTrack.rowData.status)
                                    opacity: ganttTrack.rowData.status === "运行中" ? 0.86 : 0.72
                                    Rectangle { anchors.fill: parent; anchors.margins: 2; radius: 2; color: "#7fffffff"; opacity: 0.34 }
                                }
                                Text {
                                    visible: Number(ganttTrack.rowData.timelineOffset === undefined ? -1 : ganttTrack.rowData.timelineOffset) >= 0
                                    x: ganttTrack.width * Number(ganttTrack.rowData.timelineOffset || 0)
                                    y: 38
                                    text: modelData.startedAt || "等待开始"
                                    color: textDim
                                    font.pixelSize: 10
                                }
                            }
                            ColumnLayout {
                                Layout.preferredWidth: 138
                                spacing: 2
                                Text { text: modelData.recordCount ? modelData.recordCount + " 条" : ""; color: textMuted; font.pixelSize: 10; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                                Text { text: modelData.status + " · " + modelData.stage; color: statusColor(modelData.status); font.pixelSize: 11; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                            }
                        }
                    }
                }
            }
        }
    }

    component NetworkPage: Item {
        id: network
        objectName: "networkPage"
        property real zoom: 1
        property point pan: Qt.point(0, 0)
        property point dragStart: Qt.point(0, 0)
        property var nodeIndex: ({})
        property var levelCounts: [1, 1, 1, 1]
        property double animationClock: Date.now()
        property bool burstActive: false
        property bool autoFrameEnabled: true
        property real worldWidth: 2400
        property real worldHeight: 1800
        property real readabilityScale: Math.min(1.16, Math.max(0.84, Math.sqrt(zoom)))
        property int maxAnimatedEdges: 10
        property var nodes: []
        property var edges: []
        property var visibleNodes: []
        property var visibleEdges: []
        property var animatedEdges: []
        property var childNodes: ({})
        property var rawPositions: ({})
        property bool entryAnimationActive: false

        function clamp(value, minimum, maximum) { return Math.max(minimum, Math.min(maximum, value)) }

        function easeOut(value) { let inverse = 1 - clamp(value, 0, 1); return 1 - inverse * inverse * inverse }

        function nodeTone(status) {
            if (status === "成功") return "#72d9ad"
            if (status === "运行中") return "#73d4dc"
            if (status === "失败" || status === "错误") return "#ff8b9e"
            if (status === "停止") return "#83999b"
            return "#e7b469"
        }

        function rebuildNodeIndex() {
            let nextIndex = ({})
            let nextCounts = [0, 0, 0, 0]
            let nextChildren = ({})
            for (let index = 0; index < nodes.length; index++) {
                let node = nodes[index]
                let childKey = String(node.parent || "") + ":" + Number(node.level)
                nextIndex[node.id] = node
                nextCounts[clamp(Number(node.level), 0, 3)]++
                if (!nextChildren[childKey]) nextChildren[childKey] = []
                nextChildren[childKey].push(node)
            }
            for (let level = 0; level < nextCounts.length; level++) nextCounts[level] = Math.max(1, nextCounts[level])
            nodeIndex = nextIndex
            levelCounts = nextCounts
            childNodes = nextChildren
            rawPositions = ({})
        }

        function worldCenter() { return Qt.point(worldWidth / 2, worldHeight / 2) }

        function isLabelVisible(node) {
            if (node.kind === "root" || node.kind === "idle" || node.id === window.selectedNode.id) return true
            if (zoom < 0.42) return node.kind === "aggregate"
            if (zoom < 0.96) return node.kind === "company" || node.kind === "aggregate"
            return true
        }

        function isDetailVisible(node) {
            return node.id === window.selectedNode.id || (zoom >= 1.12 && (node.kind === "root" || node.kind === "company" || node.kind === "aggregate"))
        }

        function isInsideViewport(point, padding) {
            return point.x >= -padding && point.x <= viewport.width + padding && point.y >= -padding && point.y <= viewport.height + padding
        }

        function nodeProgress(node) {
            if (ddiViewModel.reducedMotion) return 1
            return easeOut((animationClock - Number(node.enteredAt || 0)) / 420)
        }

        function directChildren(parentId, level) {
            return childNodes[String(parentId || "") + ":" + Number(level)] || []
        }

        function radialRadius(level, siblingCount) {
            if (level === 1) return Math.max(280, 220 + siblingCount * 10)
            if (level === 2) return Math.max(190, 150 + siblingCount * 9)
            if (level === 3) return Math.max(126, 102 + siblingCount * 6)
            return 0
        }

        function rawNodePosition(node) {
            if (rawPositions[node.id]) return rawPositions[node.id]
            let level = clamp(Number(node.level), 0, 3)
            if (level === 0) {
                rawPositions[node.id] = worldCenter()
                return rawPositions[node.id]
            }
            let parent = nodeIndex[node.parent] || nodeIndex.root
            let parentPoint = parent && parent.id !== "root" ? rawNodePosition(parent) : worldCenter()
            let siblings = directChildren(parent ? parent.id : "root", level)
            let siblingIndex = 0
            for (let index = 0; index < siblings.length; index++) {
                if (siblings[index].id === node.id) { siblingIndex = index; break }
            }
            let siblingCount = Math.max(1, siblings.length)
            let angle = -Math.PI / 2
            if (!parent || parent.id === "root") {
                angle += Math.PI * 2 * siblingIndex / siblingCount
            } else {
                let grand = nodeIndex[parent.parent]
                let grandPoint = grand ? rawNodePosition(grand) : worldCenter()
                let baseAngle = Math.atan2(parentPoint.y - grandPoint.y, parentPoint.x - grandPoint.x)
                let spread = Math.min(1.20, Math.max(0.56, (siblingCount - 1) * 0.18))
                angle = baseAngle + (siblingCount === 1 ? 0 : (siblingIndex - (siblingCount - 1) / 2) * spread / (siblingCount - 1))
            }
            let radius = radialRadius(level, siblingCount)
            rawPositions[node.id] = Qt.point(parentPoint.x + Math.cos(angle) * radius, parentPoint.y + Math.sin(angle) * radius)
            return rawPositions[node.id]
        }

        function nodePosition(node) {
            let raw = rawNodePosition(node)
            let center = worldCenter()
            return Qt.point(viewport.width / 2 + (raw.x - center.x) * zoom + pan.x, viewport.height / 2 + (raw.y - center.y) * zoom + pan.y)
        }

        function setZoomAt(nextZoom, focusX, focusY) {
            let boundedZoom = clamp(nextZoom, 0.10, 4.80)
            let scaleFactor = boundedZoom / zoom
            pan = Qt.point(focusX - viewport.width / 2 - (focusX - viewport.width / 2 - pan.x) * scaleFactor, focusY - viewport.height / 2 - (focusY - viewport.height / 2 - pan.y) * scaleFactor)
            zoom = boundedZoom
            autoFrameEnabled = false
            repaintScene()
        }

        function frameWorldBounds(predicate) {
            let left = Infinity
            let top = Infinity
            let right = -Infinity
            let bottom = -Infinity
            for (let index = 0; index < nodes.length; index++) {
                let node = nodes[index]
                if (!predicate(node)) continue
                let point = rawNodePosition(node)
                left = Math.min(left, point.x)
                top = Math.min(top, point.y)
                right = Math.max(right, point.x)
                bottom = Math.max(bottom, point.y)
            }
            if (!isFinite(left)) return { left: 0, top: 0, right: worldWidth, bottom: worldHeight }
            return { left: left - 130, top: top - 110, right: right + 190, bottom: bottom + 110 }
        }

        function frameBounds(bounds) {
            let width = Math.max(1, bounds.right - bounds.left)
            let height = Math.max(1, bounds.bottom - bounds.top)
            let nextZoom = clamp(Math.min((viewport.width - 80) / width, (viewport.height - 80) / height), 0.10, 1.18)
            let center = worldCenter()
            let contentCenter = Qt.point((bounds.left + bounds.right) / 2, (bounds.top + bounds.bottom) / 2)
            zoom = nextZoom
            pan = Qt.point(-(contentCenter.x - center.x) * zoom, -(contentCenter.y - center.y) * zoom)
            repaintScene()
        }

        function showOverview() {
            autoFrameEnabled = true
            frameBounds(frameWorldBounds(function(node) { return true }))
        }

        function scheduleOverview() {
            if (autoFrameEnabled) overviewTimer.restart()
        }

        function focusRunningNodes() {
            autoFrameEnabled = false
            frameBounds(frameWorldBounds(function(node) { return node.status === "运行中" || node.kind === "root" }))
        }

        function hasFlowingEdges() {
            for (let index = 0; index < edges.length; index++) {
                let edge = edges[index]
                let targetNode = nodeIndex[edge.to]
                if (targetNode && targetNode.status === "运行中") return true
            }
            return false
        }

        function hasIdleFlow() {
            for (let index = 0; index < nodes.length; index++) {
                if (nodes[index].kind === "idle") return true
            }
            return false
        }

        function curveControls(fromPoint, toPoint) {
            let deltaX = toPoint.x - fromPoint.x
            let deltaY = toPoint.y - fromPoint.y
            let length = Math.max(1, Math.sqrt(deltaX * deltaX + deltaY * deltaY))
            let midpoint = Qt.point((fromPoint.x + toPoint.x) / 2, (fromPoint.y + toPoint.y) / 2)
            let normalX = -deltaY / length
            let normalY = deltaX / length
            let centerX = viewport.width / 2 + pan.x
            let centerY = viewport.height / 2 + pan.y
            let outwardX = midpoint.x - centerX
            let outwardY = midpoint.y - centerY
            if (normalX * outwardX + normalY * outwardY < 0) { normalX = -normalX; normalY = -normalY }
            let offset = Math.min(150, Math.max(20, length * 0.22))
            let control = Qt.point(midpoint.x + normalX * offset, midpoint.y + normalY * offset)
            return { first: control, second: control }
        }

        function curvePoint(fromPoint, toPoint, progress) {
            let t = clamp(progress, 0, 1)
            let inverse = 1 - t
            let controls = curveControls(fromPoint, toPoint)
            let controlOne = controls.first
            let controlTwo = controls.second
            return Qt.point(inverse * inverse * inverse * fromPoint.x + 3 * inverse * inverse * t * controlOne.x + 3 * inverse * t * t * controlTwo.x + t * t * t * toPoint.x, inverse * inverse * inverse * fromPoint.y + 3 * inverse * inverse * t * controlOne.y + 3 * inverse * t * t * controlTwo.y + t * t * t * toPoint.y)
        }

        function drawCurve(context, fromPoint, toPoint, progress) {
            let clippedProgress = clamp(progress, 0, 1)
            let controls = curveControls(fromPoint, toPoint)
            context.beginPath()
            context.moveTo(fromPoint.x, fromPoint.y)
            if (clippedProgress >= 0.999) {
                context.bezierCurveTo(controls.first.x, controls.first.y, controls.second.x, controls.second.y, toPoint.x, toPoint.y)
            } else {
                let segments = 5
                for (let step = 1; step <= segments; step++) {
                    let point = curvePoint(fromPoint, toPoint, clippedProgress * step / segments)
                    context.lineTo(point.x, point.y)
                }
            }
            context.stroke()
        }

        function drawGlow(context, point, radius, tone, alpha) {
            context.fillStyle = tone
            context.globalAlpha = alpha * 0.18
            context.beginPath()
            context.arc(point.x, point.y, radius, 0, Math.PI * 2)
            context.fill()
            context.globalAlpha = alpha * 0.48
            context.beginPath()
            context.arc(point.x, point.y, Math.max(2, radius * 0.36), 0, Math.PI * 2)
            context.fill()
        }

        function drawLayerGuides(context) {
            let center = Qt.point(viewport.width / 2 + pan.x, viewport.height / 2 + pan.y)
            let ringRadii = [radialRadius(1, levelCounts[1]), radialRadius(2, levelCounts[2]), radialRadius(3, levelCounts[3])]
            context.strokeStyle = "#62af9d"
            context.lineWidth = 1
            context.globalAlpha = 0.18
            for (let index = 0; index < ringRadii.length; index++) {
                context.beginPath()
                context.arc(center.x, center.y, ringRadii[index] * zoom, 0, Math.PI * 2)
                context.stroke()
            }
            context.font = "600 11px sans-serif"
            context.textAlign = "center"
            context.fillStyle = "#b9cbbf"
            context.globalAlpha = 0.76
            context.fillText("调度核心", center.x, center.y - 58 * zoom)
        }

        function drawWorldGrid(context) {
            let spacing = Math.max(54, 180 * zoom)
            let offsetX = ((pan.x % spacing) + spacing) % spacing
            let offsetY = ((pan.y % spacing) + spacing) % spacing
            context.strokeStyle = "#2f75665c"
            context.lineWidth = 1
            context.globalAlpha = 0.17
            for (let x = offsetX; x < viewport.width; x += spacing) {
                context.beginPath()
                context.moveTo(x, 0)
                context.lineTo(x, viewport.height)
                context.stroke()
            }
            for (let y = offsetY; y < viewport.height; y += spacing) {
                context.beginPath()
                context.moveTo(0, y)
                context.lineTo(viewport.width, y)
                context.stroke()
            }
        }

        function drawNetworkNode(context, node, point, progress) {
            let rootNode = node.kind === "root"
            let tone = rootNode ? amberBright : nodeTone(node.status)
            let visualScale = Math.min(1.70, Math.max(0.54, Math.sqrt(zoom)))
            let radius = (rootNode ? 17 : (node.kind === "company" ? 8 : (node.kind === "aggregate" ? 11 : (node.kind === "idle" ? 10 : (node.kind === "slot" ? 6 : 4))))) * visualScale
            let pulse = 1
            let illuminated = rootNode || node.status === "运行中" || node.kind === "aggregate" || node.kind === "idle"
            context.globalAlpha = progress
            if (illuminated) drawGlow(context, point, rootNode ? 62 * visualScale * pulse : radius * 4.8, tone, rootNode ? 0.25 : 0.18)
            if (rootNode) {
                context.strokeStyle = tone
                context.lineWidth = 1
                context.globalAlpha = 0.30 * progress
                context.beginPath()
                context.arc(point.x, point.y, 33 * pulse, 0, Math.PI * 2)
                context.stroke()
                context.globalAlpha = 0.16 * progress
                context.beginPath()
                context.arc(point.x, point.y, 48 * pulse, 0, Math.PI * 2)
                context.stroke()
            }
            context.fillStyle = tone
            context.globalAlpha = (rootNode ? 0.92 : 0.82) * progress
            context.beginPath()
            context.arc(point.x, point.y, radius * (0.82 + 0.18 * progress), 0, Math.PI * 2)
            context.fill()
            context.fillStyle = "#fff8e8"
            context.globalAlpha = 0.88 * progress
            context.beginPath()
            context.arc(point.x - radius * 0.22, point.y - radius * 0.22, Math.max(1.5, radius * 0.23), 0, Math.PI * 2)
            context.fill()
        }

        function rebuildRenderCache() {
            let nextNodes = []
            let nextEdges = []
            let nextAnimatedEdges = []
            for (let index = 0; index < nodes.length; index++) {
                let node = nodes[index]
                let progress = nodeProgress(node)
                if (progress <= 0) continue
                let point = nodePosition(node)
                if (!isInsideViewport(point, 80)) continue
                let illuminated = node.kind === "root" || node.status === "运行中" || node.kind === "aggregate" || node.kind === "idle"
                nextNodes.push({ node: node, point: point, progress: progress, illuminated: illuminated })
            }
            for (let index = 0; index < edges.length; index++) {
                let edge = edges[index]
                let fromNode = nodeIndex[edge.from]
                let toNode = nodeIndex[edge.to]
                if (!fromNode || !toNode) continue
                let fromPoint = nodePosition(fromNode)
                let toPoint = nodePosition(toNode)
                if (!isInsideViewport(fromPoint, 90) && !isInsideViewport(toPoint, 90)) continue
                let growth = nodeProgress(toNode)
                if (growth <= 0) continue
                let targetRunning = toNode.status === "运行中"
                let edgeData = { edge: edge, fromPoint: fromPoint, toPoint: toPoint, growth: growth, tone: nodeTone(toNode.status), flowing: ddiViewModel.task.running || targetRunning || (!ddiViewModel.task.running && toNode.kind === "idle") }
                nextEdges.push(edgeData)
                if (!ddiViewModel.reducedMotion && edgeData.flowing && growth > 0.05 && nextAnimatedEdges.length < maxAnimatedEdges) nextAnimatedEdges.push(edgeData)
            }
            visibleNodes = nextNodes
            visibleEdges = nextEdges
            animatedEdges = nextAnimatedEdges
        }

        function drawAnimatedOverlay(context) {
            for (let index = 0; index < animatedEdges.length; index++) {
                let edgeData = animatedEdges[index]
                let flow = ((animationClock / (ddiViewModel.task.running ? 1500 : 3300)) + index * 0.173) % 1
                let spark = curvePoint(edgeData.fromPoint, edgeData.toPoint, flow * edgeData.growth)
                drawGlow(context, spark, edgeData.edge.level === 1 ? 8 : 5, edgeData.tone, 0.74)
            }
            for (let index = 0; index < visibleNodes.length; index++) {
                let nodeData = visibleNodes[index]
                if (!nodeData.illuminated) continue
                let node = nodeData.node
                let rootNode = node.kind === "root"
                let visualScale = Math.min(1.70, Math.max(0.54, Math.sqrt(zoom)))
                let radius = (rootNode ? 17 : (node.kind === "company" ? 8 : (node.kind === "aggregate" ? 11 : (node.kind === "idle" ? 10 : (node.kind === "slot" ? 6 : 4))))) * visualScale
                let pulse = 0.84 + 0.16 * Math.sin(animationClock / 480 + Number(node.order))
                let tone = nodeTone(node.status)
                drawGlow(context, nodeData.point, rootNode ? 52 * visualScale * pulse : radius * 3.2 * pulse, tone, rootNode ? 0.20 : 0.14)
                if (rootNode) {
                    context.strokeStyle = tone
                    context.lineWidth = 1
                    context.globalAlpha = 0.22
                    context.beginPath()
                    context.arc(nodeData.point.x, nodeData.point.y, 33 * pulse, 0, Math.PI * 2)
                    context.stroke()
                    context.globalAlpha = 0.12
                    context.beginPath()
                    context.arc(nodeData.point.x, nodeData.point.y, 48 * pulse, 0, Math.PI * 2)
                    context.stroke()
                }
            }
            context.globalAlpha = 1
        }

        function refreshStaticScene() {
            animationClock = Date.now()
            rebuildRenderCache()
            staticCanvas.requestPaint()
            animationCanvas.requestPaint()
        }

        function scheduleStaticScene() {
            if (!staticSceneTimer.running) staticSceneTimer.start()
        }

        function repaintScene() {
            if (!visible) return
            animationClock = Date.now()
            scheduleStaticScene()
            animationCanvas.requestPaint()
        }

        onZoomChanged: repaintScene()
        onPanChanged: repaintScene()
        onWidthChanged: if (visible) { rebuildNodeIndex(); scheduleOverview(); scheduleStaticScene() }
        onHeightChanged: if (visible) { rebuildNodeIndex(); scheduleOverview(); scheduleStaticScene() }
        onVisibleChanged: if (visible) { rebuildNodeIndex(); showOverview(); refreshStaticScene() }
        Component.onCompleted: {
            nodes = ddiViewModel.networkNodes
            edges = ddiViewModel.networkEdges
            if (visible) {
                rebuildNodeIndex()
                scheduleOverview()
            }
        }

        Connections {
            target: ddiViewModel
            function onNetworkChanged() {
                network.nodes = ddiViewModel.networkNodes
                network.edges = ddiViewModel.networkEdges
                if (!network.visible) return
                network.rebuildNodeIndex()
                network.burstActive = true
                network.settleTimer.restart()
                network.entryAnimationActive = true
                network.entryAnimationTimer.restart()
                if (network.autoFrameEnabled) network.scheduleOverview()
                else network.repaintScene()
            }
            function onReducedMotionChanged() { if (network.visible) network.repaintScene() }
        }

        Timer {
            id: overviewTimer
            interval: 48
            repeat: false
            onTriggered: if (network.autoFrameEnabled) network.showOverview()
        }

        Timer {
            id: animationTimer
            interval: ddiViewModel.task.runningCount >= 6 ? 50 : 33
            repeat: true
            running: network.visible && !ddiViewModel.reducedMotion && (network.entryAnimationActive || network.burstActive || (ddiViewModel.task.running && network.hasFlowingEdges()) || network.hasIdleFlow())
            onTriggered: {
                network.animationClock = Date.now()
                if (network.entryAnimationActive) network.refreshStaticScene()
                else animationCanvas.requestPaint()
            }
        }

        Timer {
            id: staticSceneTimer
            interval: 16
            repeat: false
            onTriggered: if (network.visible) network.refreshStaticScene()
        }

        Timer {
            id: entryAnimationTimer
            interval: 1800
            repeat: false
            onTriggered: {
                network.entryAnimationActive = false
                if (network.visible) network.refreshStaticScene()
            }
        }

        Timer {
            id: settleTimer
            interval: 2100
            repeat: false
            onTriggered: network.burstActive = false
        }

        Item {
            anchors.fill: parent
            ColumnLayout {
                anchors.fill: parent
                anchors.topMargin: 4
                spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 35
                    Text { text: "任务网络"; color: textMain; font.pixelSize: 18; font.bold: true; Layout.preferredWidth: 92 }
                    Text { text: ddiViewModel.reducedMotion ? "静态模式" : (ddiViewModel.task.running ? "实时绽放中" : "总览已就绪"); color: ddiViewModel.task.running ? running : textMuted; font.pixelSize: 11; font.bold: true }
                    Item { Layout.fillWidth: true }
                    GlassButton { text: "−"; implicitWidth: 28; onClicked: network.setZoomAt(network.zoom / 1.22, viewport.width / 2, viewport.height / 2) }
                    Text { text: Math.round(network.zoom * 100) + "%"; color: textMuted; font.pixelSize: 11; font.bold: true; Layout.preferredWidth: 42; horizontalAlignment: Text.AlignHCenter }
                    GlassButton { text: "+"; implicitWidth: 28; onClicked: network.setZoomAt(network.zoom * 1.22, viewport.width / 2, viewport.height / 2) }
                    GlassButton { text: "总览"; onClicked: network.showOverview() }
                    GlassButton { text: "聚焦运行"; onClicked: network.focusRunningNodes() }
                }
                Rectangle {
                    id: viewport
                    objectName: "networkViewport"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 0
                    clip: true
                    color: "#172f2a38"
                    border.width: 0
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#28473c4d" }
                        GradientStop { position: 0.52; color: "#173a3140" }
                        GradientStop { position: 1.0; color: "#0d282431" }
                    }
                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.LeftButton
                        onPressed: network.dragStart = Qt.point(mouse.x, mouse.y)
                        onPositionChanged: if (pressed) {
                            network.pan = Qt.point(network.pan.x + mouse.x - network.dragStart.x, network.pan.y + mouse.y - network.dragStart.y)
                            network.dragStart = Qt.point(mouse.x, mouse.y)
                            network.autoFrameEnabled = false
                            network.repaintScene()
                        }
                        onWheel: network.setZoomAt(network.zoom * (wheel.angleDelta.y > 0 ? 1.18 : 0.85), wheel.x, wheel.y)
                    }
                    Canvas {
                        id: staticCanvas
                        anchors.fill: parent
                        onPaint: {
                            let context = getContext("2d")
                            context.reset()
                            if (!network.visible) return
                            if (network.visibleEdges.length === 0 && network.edges.length > 0) network.rebuildRenderCache()
                            network.drawWorldGrid(context)
                            network.drawLayerGuides(context)
                            for (let index = 0; index < network.visibleEdges.length; index++) {
                                let edgeData = network.visibleEdges[index]
                                context.strokeStyle = edgeData.edge.level === 1 ? amber : edgeData.tone
                                context.lineWidth = (edgeData.edge.level === 1 ? 1.5 : 1) * Math.min(1.7, network.readabilityScale)
                                context.globalAlpha = edgeData.edge.level === 1 ? 0.58 : 0.34
                                network.drawCurve(context, edgeData.fromPoint, edgeData.toPoint, edgeData.growth)
                            }
                            for (let index = 0; index < network.visibleNodes.length; index++) {
                                let nodeData = network.visibleNodes[index]
                                network.drawNetworkNode(context, nodeData.node, nodeData.point, nodeData.progress)
                            }
                            context.globalAlpha = 1
                        }
                        onWidthChanged: if (network.visible) network.scheduleStaticScene()
                        onHeightChanged: if (network.visible) network.scheduleStaticScene()
                    }
                    Canvas {
                        id: animationCanvas
                        anchors.fill: parent
                        z: 1
                        onPaint: {
                            let context = getContext("2d")
                            context.reset()
                            if (network.visible && !ddiViewModel.reducedMotion) network.drawAnimatedOverlay(context)
                        }
                        onWidthChanged: requestPaint()
                        onHeightChanged: requestPaint()
                    }
                    Repeater {
                        model: network.visible ? network.nodes : []
                        delegate: Item {
                            required property var modelData
                            property point location: network.nodePosition(modelData)
                            property bool majorNode: modelData.kind === "root" || modelData.kind === "company" || modelData.kind === "aggregate" || modelData.kind === "idle"
                            property bool aggregateNode: modelData.kind === "aggregate"
                            property bool labelVisible: network.isLabelVisible(modelData)
                            property bool detailVisible: network.isDetailVisible(modelData)
                            width: (modelData.kind === "idle" ? 156 : (majorNode ? 186 : 132)) * network.readabilityScale
                            height: (detailVisible ? 42 : 22) * network.readabilityScale
                            x: location.x + (modelData.kind === "root" ? 27 : 12) * network.readabilityScale
                            y: location.y - height / 2
                            z: 2
                            opacity: labelVisible ? 1 : 0
                            visible: labelVisible
                            Behavior on opacity { NumberAnimation { duration: 140 } }
                            Rectangle {
                                anchors.fill: parent
                                visible: parent.aggregateNode
                                radius: 2
                                color: "#5b432b66"
                                border.width: 1
                                border.color: Qt.rgba(statusColor(modelData.status).r, statusColor(modelData.status).g, statusColor(modelData.status).b, 0.40)
                            }
                            Column {
                                anchors.fill: parent
                                anchors.margins: parent.aggregateNode ? 7 : 2
                                spacing: 1
                                Text { width: parent.width; text: modelData.title; color: textMain; font.pixelSize: (modelData.kind === "root" ? 12 : 11) * network.readabilityScale; font.bold: true; elide: Text.ElideRight }
                                Text { visible: modelData.id === window.selectedNode.id || (network.zoom >= 1.12 && (modelData.kind === "root" || modelData.kind === "company" || modelData.kind === "aggregate")); width: parent.width; text: modelData.detail; color: textMuted; font.pixelSize: 10 * network.readabilityScale; elide: Text.ElideRight }
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: { ddiViewModel.focusNetworkNode(modelData.id); window.selectedNode = modelData; window.detailsOpen = true }
                                onWheel: {
                                    let focus = parent.mapToItem(viewport, wheel.x, wheel.y)
                                    network.setZoomAt(network.zoom * (wheel.angleDelta.y > 0 ? 1.18 : 0.85), focus.x, focus.y)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

        GlassPanel {
            id: accountDrawer
        visible: window.accountOpen
        width: 400
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.margins: 20
            tint: glassStrong
            framed: true
        border.color: borderBright
        z: 10
        property var values: ({})
        function refresh() { let next = ({}); let fields = ddiViewModel.account.fields || []; for (let i = 0; i < fields.length; i++) next[fields[i].name] = fields[i].value; values = next }
        onVisibleChanged: if (visible) refresh()
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 10
            RowLayout { Layout.fillWidth: true; Text { text: "账号维护"; color: textMain; font.pixelSize: 18; font.bold: true; Layout.fillWidth: true } GlassButton { text: "关闭"; onClicked: window.accountOpen = false } }
            Text { text: ddiViewModel.account.company || ""; color: amberBright; font.pixelSize: 12; font.bold: true }
            Text { text: "平台：" + (ddiViewModel.account.platform || ""); color: textMuted; font.pixelSize: 11 }
            Rectangle { Layout.fillWidth: true; height: 1; color: border }
            Repeater { model: ddiViewModel.account.fields || []; delegate: ColumnLayout { required property var modelData; Layout.fillWidth: true; spacing: 4; FieldCaption { text: modelData.name } GlassField { Layout.fillWidth: true; text: accountDrawer.values[modelData.name] === undefined ? modelData.value : accountDrawer.values[modelData.name]; echoMode: modelData.secret ? TextInput.Password : TextInput.Normal; onTextChanged: { let next = accountDrawer.values; next[modelData.name] = text; accountDrawer.values = next } } } }
            Item { Layout.fillHeight: true }
            RowLayout { Layout.fillWidth: true; GlassButton { text: "恢复默认"; onClicked: { ddiViewModel.restoreAccount(ddiViewModel.account.company); accountDrawer.refresh() } } Item { Layout.fillWidth: true } PrimaryButton { text: "保存修改"; onClicked: ddiViewModel.saveAccount(ddiViewModel.account.company, accountDrawer.values) } }
        }
    }

    GlassPanel {
        visible: window.detailsOpen
        width: 470
        height: 390
        anchors.centerIn: parent
        tint: glassStrong
        framed: true
        border.color: borderBright
        z: 20
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 19
            spacing: 10
            RowLayout { Layout.fillWidth: true; Text { text: "节点详情"; color: textMain; font.pixelSize: 16; font.bold: true; Layout.fillWidth: true } GlassButton { text: "关闭"; implicitWidth: 52; onClicked: window.detailsOpen = false } }
            RowLayout {
                Layout.fillWidth: true
                Text { text: window.selectedNode.title || ""; color: amberBright; font.pixelSize: 18; font.bold: true; wrapMode: Text.Wrap; Layout.fillWidth: true }
                Rectangle { width: 58; height: 22; radius: 2; color: Qt.rgba(statusColor(window.selectedNode.status || "").r, statusColor(window.selectedNode.status || "").g, statusColor(window.selectedNode.status || "").b, 0.18); border.width: 1; border.color: Qt.rgba(statusColor(window.selectedNode.status || "").r, statusColor(window.selectedNode.status || "").g, statusColor(window.selectedNode.status || "").b, 0.56); Text { anchors.centerIn: parent; text: window.selectedNode.status || "未知"; color: statusColor(window.selectedNode.status || ""); font.pixelSize: 11; font.bold: true } }
            }
            Text { text: window.selectedNode.detail || ""; color: textMuted; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
            Rectangle { Layout.fillWidth: true; height: 1; color: border }
            RowLayout { Layout.fillWidth: true; Text { text: "网络层级"; color: textDim; font.pixelSize: 11; Layout.preferredWidth: 60 } Text { text: window.selectedNode.level === 0 ? "调度核心" : (window.selectedNode.level === 1 ? "并发分发" : (window.selectedNode.level === 2 ? "商业执行" : "数据任务")); color: textMain; font.pixelSize: 12; font.bold: true } }
            Text { text: "运行诊断"; color: textMain; font.pixelSize: 12; font.bold: true }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                Text { width: parent.width; text: window.selectedNode.diagnostics || "当前节点暂无额外诊断信息。"; color: textMuted; font.pixelSize: 12; lineHeight: 1.45; wrapMode: Text.Wrap }
            }
        }
    }
}
