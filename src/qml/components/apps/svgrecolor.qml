pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import ".." as Components

Kirigami.Page {
    id: svgRecolorPage
    title: qsTr("SVG Recolor")

    // -1 = monochrome slot; 0-5 = gradient index
    property int _editColorIndex: -2


    background: Rectangle {
        color: "transparent"
    }

    Components.ClipboardHelper {
        id: clipboardHelper
    }
    RowLayout {
        anchors.fill: parent
        spacing: Kirigami.Units.smallSpacing

        // ─────────────────────────────────────────────────────────────────
        // Left Pane: Settings
        // ─────────────────────────────────────────────────────────────────
        Rectangle {
            color: Qt.alpha(Kirigami.Theme.backgroundColor, 0.80)
            Layout.preferredWidth: 300
            Layout.fillHeight: true
            radius: Kirigami.Units.largeSpacing
            border.color: Kirigami.Theme.highlightColor
            border.width: 1
            clip: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.largeSpacing
                spacing: Kirigami.Units.smallSpacing

                Label {
                    text: qsTr("Settings")
                    font.bold: true
                    Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                }

                MenuSeparator { Layout.fillWidth: true }

                // ── Directory ─────────────────────────────────────────────
                Label {
                    text: qsTr("SVG directory")
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    TextField {
                        id: directoryField
                        Layout.fillWidth: true
                        readOnly: true
                        text: controller ? controller.svgDirectory : ""
                        placeholderText: qsTr("No folder selected")
                        ToolTip.text: directoryField.text
                        ToolTip.visible: hovered && directoryField.text !== ""
                    }

                    ToolButton {
                        icon.name: "folder-open"
                        ToolTip.text: qsTr("Browse…")
                        ToolTip.visible: hovered
                        onClicked: {
                            if (controller) controller.svgBrowseDirectory()
                        }
                    }
                }

                MenuSeparator { Layout.fillWidth: true }

                // ── Color count ───────────────────────────────────────────
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Label {
                        text: qsTr("Gradient colors:")
                        Layout.fillWidth: true
                    }

                    SpinBox {
                        id: colorCountSpin
                        from: 2
                        to: 6
                        value: controller ? controller.svgColorCount : 5
                        onValueModified: {
                            if (controller) controller.svgSetColorCount(value)
                        }
                    }
                }

                // ── Color list (scrollable) ───────────────────────────────
                ScrollView {
                    id: colorScrollView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded

                    ColumnLayout {
                        width: colorScrollView.availableWidth
                        spacing: Kirigami.Units.smallSpacing

                        // Gradient colors
                        Repeater {
                            model: controller ? controller.svgGradientColors : []
                            delegate: RowLayout {
                                required property int index
                                required property string modelData

                                Layout.fillWidth: true
                                spacing: Kirigami.Units.smallSpacing
                                opacity: index < (controller ? controller.svgColorCount : 6) ? 1.0 : 0.3

                                Label {
                                    text: qsTr("Color %1").arg(index + 1)
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }

                                Rectangle {
                                    id: gradColorRect
                                    width: Kirigami.Units.gridUnit * 1.5
                                    height: Kirigami.Units.gridUnit * 1.5
                                    radius: Kirigami.Units.smallSpacing
                                    color: modelData !== "" ? modelData : "transparent"
                                    border.color: Kirigami.Theme.disabledTextColor
                                    border.width: 1

                                    ToolTip.text: controller ? controller.formatColorWithAlpha(gradColorRect.color) : ""
                                    ToolTip.visible: gradColorMouse.containsMouse

                                    MouseArea {
                                        id: gradColorMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        enabled: index < (controller ? controller.svgColorCount : 6)
                                        cursorShape: Qt.PointingHandCursor
                                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                                        onClicked: (mouse) => {
                                            if (mouse.button === Qt.RightButton) {
                                                clipboardHelper.copyToClipboard(modelData)
                                                return
                                            }
                                            if (!controller) return
                                            var result = controller.openColorDialog(parent.color)
                                            if (result !== "") {
                                                controller.svgSetGradientColor(index, result)
                                            }
                                        }
                                    }
                                }

                            }
                        }

                        Kirigami.Separator {
                            Layout.fillWidth: true
                            height: 1
                        }

                        // Monochrome color
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Label {
                                text: qsTr("System icons color")
                                Layout.fillWidth: true
                            }

                            Rectangle {
                                id: monoColorSquare
                                width: Kirigami.Units.gridUnit * 1.5
                                height: Kirigami.Units.gridUnit * 1.5
                                radius: Kirigami.Units.smallSpacing
                                color: controller ? controller.svgMonoColor : "#ACACAC"
                                border.color: Kirigami.Theme.disabledTextColor
                                border.width: 1

                                ToolTip.text: controller ? controller.formatColorWithAlpha(monoColorSquare.color) : ""
                                ToolTip.visible: monoColorMouse.containsMouse

                                MouseArea {
                                    id: monoColorMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                                    onClicked: (mouse) => {
                                        if (mouse.button === Qt.RightButton) {
                                            clipboardHelper.copyToClipboard(controller.svgMonoColor)
                                            return
                                        }
                                        if (!controller) return
                                        var result = controller.openColorDialog(parent.color)
                                        if (result !== "") {
                                            controller.svgSetMonoColor(result)
                                        }
                                    }
                                }
                            }

                        }
                    }
                }
                MenuSeparator { Layout.fillWidth: true }

                // ── Action buttons ────────────────────────────────────────
                RowLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignHCenter
                    spacing: Kirigami.Units.largeSpacing

                    ToolButton {
                        icon.name: "media-playback-start"
                        ToolTip.text: qsTr("Start processing")
                        ToolTip.visible: hovered
                        enabled: controller
                            && !controller.svgProcessing
                            && controller.svgDirectory !== ""
                        onClicked: if (controller) controller.svgStartProcessing()
                    }

                    ToolButton {
                        icon.name: "media-playback-stop"
                        ToolTip.text: qsTr("Stop processing")
                        ToolTip.visible: hovered
                        enabled: controller && controller.svgProcessing
                        onClicked: if (controller) controller.svgStopProcessing()
                    }

                    ToolButton {
                        icon.name: "dialog-ok-apply"
                        ToolTip.text: qsTr("Apply changes")
                        ToolTip.visible: hovered
                        enabled: controller
                            && !controller.svgProcessing
                            && controller.svgHasPreview
                        onClicked: if (controller) controller.svgApplyChanges()
                    }

                    ToolButton {
                        icon.name: "edit-undo"
                        ToolTip.text: qsTr("Undo changes")
                        ToolTip.visible: hovered
                        enabled: controller
                            && !controller.svgProcessing
                            && controller.svgHasBackup
                        onClicked: if (controller) controller.svgUndoChanges()
                    }
                }
            }
        }

        // ─────────────────────────────────────────────────────────────────
        // Right Pane: Preview + Log
        // ─────────────────────────────────────────────────────────────────
        Rectangle {
            color: "transparent"
            Layout.fillWidth: true
            Layout.fillHeight: true
            //radius: Kirigami.Units.largeSpacing
            //border.color: Kirigami.Theme.highlightColor
            //border.width: 1
            //clip: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.largeSpacing
                spacing: Kirigami.Units.smallSpacing

                // ── Preview area ─────────────────────────────────────────
                Label { text: qsTr("Preview:"); font.bold: true }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: 3

                    BusyIndicator {
                        anchors.centerIn: parent
                        running: controller ? controller.svgProcessing : false
                        visible: running
                    }

                    Image {
                        id: svgPreviewImage
                        anchors.centerIn: parent
                        width: Math.min(parent.width - Kirigami.Units.largeSpacing * 2, 256)
                        height: Math.min(parent.height - Kirigami.Units.largeSpacing * 2 - Kirigami.Units.gridUnit * 2.5, 256)
                        fillMode: Image.PreserveAspectFit
                        asynchronous: false
                        cache: false
                        visible: !controller.svgProcessing && source !== ""
                        source: {
                            if (!controller) return ""
                            var f = controller.svgCurrentPreviewFile
                            if (f === "") return ""
                            return "image://svgprovider" + f + "?t=" + controller.svgPreviewTimestamp
                        }
                    }

                    Label {
                        anchors.centerIn: parent
                        visible: !controller.svgProcessing && svgPreviewImage.source === ""
                        text: qsTr("No preview")
                        color: Kirigami.Theme.disabledTextColor
                    }

                    // Navigation row anchored to bottom
                    RowLayout {
                        anchors.bottom: parent.bottom
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: Kirigami.Units.smallSpacing

                        ToolButton {
                            id: prevBtn
                            icon.name: "arrow-left"
                            enabled: controller && controller.svgPreviewIndex > 0
                            ToolTip.text: qsTr("Previous")
                            ToolTip.visible: hovered
                            onClicked: if (controller) controller.svgNavigatePreview(-1)
                        }

                        Label {
                            text: {
                                if (!controller || controller.svgPreviewCount === 0) return "0 / 0"
                                return (controller.svgPreviewIndex + 1) + " / " + controller.svgPreviewCount
                            }
                            Layout.minimumWidth: Kirigami.Units.gridUnit * 3
                            horizontalAlignment: Text.AlignHCenter
                        }

                        ToolButton {
                            id: nextBtn
                            icon.name: "arrow-right"
                            enabled: controller && controller.svgPreviewIndex < controller.svgPreviewCount - 1
                            ToolTip.text: qsTr("Next")
                            ToolTip.visible: hovered
                            onClicked: if (controller) controller.svgNavigatePreview(1)
                        }
                    }
                }

                // ── Log area ─────────────────────────────────────────────
                Label { text: qsTr("Log:"); font.bold: true }

                ScrollView {
                    id: logScrollView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: 2
                    clip: true
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded

                    TextArea {
                        id: logArea
                        readOnly: true
                        wrapMode: TextEdit.Wrap
                        font.family: "monospace"
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        text: controller ? controller.svgLogText : ""
                        background: Rectangle {
                            color: Qt.rgba(0, 0, 0, 0.18)
                            radius: Kirigami.Units.smallSpacing
                        }

                        // Auto-scroll to bottom when log updates
                        onTextChanged: {
                            logScrollView.ScrollBar.vertical.position = 1.0
                        }
                    }
                }

            }
        }
    }
}
