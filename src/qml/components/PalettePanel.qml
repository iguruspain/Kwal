pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "." as Components

Item {
    id: palettePanelContainer
    required property var lightbox
    required property var pageRef
    required property Item topBar

    Components.ClipboardHelper { id: clipboardHelper }
    anchors.top: topBar.bottom
    anchors.bottom: parent.bottom
    anchors.right: parent.right
    anchors.topMargin: Kirigami.Units.largeSpacing
    anchors.bottomMargin: Kirigami.Units.largeSpacing * 4
    anchors.rightMargin: Kirigami.Units.largeSpacing
    width: Math.min(Kirigami.Units.gridUnit * 20, parent.width * 0.42)
    clip: true

    // Handle/tab attached to the container's left edge, always visible
    Rectangle {
        id: paletteHandle
        anchors.right: palettePanelContainer.left
        anchors.verticalCenter: palettePanelContainer.verticalCenter
        width: Kirigami.Units.gridUnit * 1.6
        height: Kirigami.Units.gridUnit * 4
        radius: Kirigami.Units.smallSpacing
        color: Qt.alpha(Kirigami.Theme.backgroundColor, 0.92)
        border.color: Kirigami.Theme.highlightColor
        border.width: 1
        visible: !lightbox.paletteExpanded

        Kirigami.Icon {
            anchors.centerIn: parent
            source: lightbox.paletteExpanded ? "expand" : "preferences-system-symbolic"
            width: Kirigami.Units.gridUnit
            height: width
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: lightbox.paletteExpanded = true
        }
    }

    Rectangle {
        id: palettePanel
        width: palettePanelContainer.width
        height: palettePanelContainer.height
        x: lightbox.paletteExpanded ? 0 : width
        color: Qt.alpha(Kirigami.Theme.backgroundColor, 0.92)
        border.color: Kirigami.Theme.highlightColor
        border.width: 1
        radius: Kirigami.Units.smallSpacing

        Behavior on x {
            NumberAnimation { duration: 200; easing.type: Easing.InOutQuad }
        }

    ScrollView {
        id: palettePanelScroll
        anchors.fill: parent
        anchors.margins: Kirigami.Units.largeSpacing
        clip: true
        visible: lightbox.paletteExpanded
        opacity: lightbox.paletteExpanded ? 1.0 : 0.0

        Behavior on opacity {
            NumberAnimation { duration: 150 }
        }

        ColumnLayout {
            id: palettePanelLayout
            width: palettePanelScroll.availableWidth
            spacing: Kirigami.Units.largeSpacing

            RowLayout {
                Layout.fillWidth: true
                Label {
                    //text: qsTr("Color Palette")
                    text: qsTr("Settings")
                    font.bold: true
                    Layout.fillWidth: true
                }
                ToolButton {
                    icon.name: "collapse"
                    flat: true
                    display: AbstractButton.IconOnly
                    ToolTip.text: qsTr("Collapse")
                    ToolTip.visible: hovered
                    onClicked: lightbox.paletteExpanded = false
                }
            }

            Kirigami.Separator { Layout.fillWidth: true }

            // Categories
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Label {
                    text: qsTr("Categories")
                    font.bold: true
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Repeater {
                        model: lightbox.categories
                        delegate: Rectangle {
                            id: lbActiveChip
                            required property string modelData
                            readonly property var catInfo: pageRef ? pageRef.categoryInfo(lbActiveChip.modelData) : null
                            implicitWidth: lbChipRow.implicitWidth + Kirigami.Units.largeSpacing
                            implicitHeight: Kirigami.Units.gridUnit * 1.6
                            radius: Kirigami.Units.smallSpacing
                            color: Qt.alpha(lbActiveChip.catInfo ? lbActiveChip.catInfo.hex : "#888888", 0.22)
                            //border.color: lbActiveChip.catInfo.hex
                            border.color: (lbActiveChip.catInfo && lbActiveChip.catInfo.label === "Black/Dark") ? Kirigami.Theme.textColor : (lbActiveChip.catInfo ? lbActiveChip.catInfo.hex : "#888888")
                            border.width: 1

                            RowLayout {
                                id: lbChipRow
                                anchors.centerIn: parent
                                spacing: Kirigami.Units.smallSpacing / 2

                                Rectangle {
                                    Layout.preferredWidth: Kirigami.Units.gridUnit * 0.55
                                    Layout.preferredHeight: width
                                    radius: 2 //width / 2
                                    color: lbActiveChip.catInfo ? lbActiveChip.catInfo.hex : "#888888"
                                    border.color: Qt.alpha("#000000",  0.25)
                                    border.width: 1
                                }

                                Label {
                                    text: lbActiveChip.catInfo ? lbActiveChip.catInfo.label : ""
                                    //color: Kirigami.Theme.textColor
                                    color: (lbActiveChip.catInfo && lbActiveChip.catInfo.label === "Black/Dark") ? Kirigami.Theme.textColor : (lbActiveChip.catInfo ? lbActiveChip.catInfo.hex : "#888888")
                                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                                }

                                Label {
                                    text: "\u2715"
                                    //color: Kirigami.Theme.disabledTextColor
                                    color: (lbActiveChip.catInfo && lbActiveChip.catInfo.label === "Black/Dark") ? Kirigami.Theme.textColor : (lbActiveChip.catInfo ? lbActiveChip.catInfo.hex : "#888888")
                                    font.pointSize: Kirigami.Theme.smallFont.pointSize

                                    TapHandler {
                                        onTapped: lightbox.toggleCategory(lbActiveChip.modelData)
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        id: lbAddChip
                        implicitWidth: lbAddChipRow.implicitWidth + Kirigami.Units.largeSpacing
                        implicitHeight: Kirigami.Units.gridUnit * 1.6
                        radius: Kirigami.Units.smallSpacing
                        color: lbAddChipHover.hovered ? Qt.alpha(Kirigami.Theme.highlightColor, 0.18) : "transparent"
                        border.color: Qt.alpha(Kirigami.Theme.textColor, 0.35)
                        border.width: 1

                        RowLayout {
                            id: lbAddChipRow
                            anchors.centerIn: parent
                            spacing: Kirigami.Units.smallSpacing / 2

                            Label {
                                text: "+"
                                color: Kirigami.Theme.disabledTextColor
                                font.bold: true
                            }
                            Label {
                                text: qsTr("Add")
                                color: Kirigami.Theme.disabledTextColor
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                            }
                        }

                        HoverHandler { id: lbAddChipHover }
                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.LeftButton
                            hoverEnabled: true
                            propagateComposedEvents: false
                            preventStealing: true
                            onPressed: (mouse) => {
                                mouse.accepted = true
                            }
                            onClicked: (mouse) => {
                                mouse.accepted = true
                                lbAddCategoryMenu.popup()
                            }
                        }

                        Menu {
                            id: lbAddCategoryMenu
                            modal: true
                            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                            Repeater {
                                model: (pageRef && pageRef.categoryColorModel)
                                    ? pageRef.categoryColorModel.filter(function (c) {
                                        return (lightbox.categories || []).indexOf(c.name) === -1
                                    })
                                    : []
                                delegate: MenuItem {
                                    required property var modelData
                                    text: modelData.label
                                    onTriggered: lightbox.toggleCategory(modelData.name)

                                    contentItem: RowLayout {
                                        spacing: Kirigami.Units.smallSpacing
                                        Rectangle {
                                            width: Kirigami.Units.gridUnit * 0.6
                                            height: Kirigami.Units.gridUnit * 0.6
                                            color: modelData.hex
                                            border.color: Qt.alpha("#000000",  0.25)
                                            border.width: 1
                                            radius: 2
                                            Layout.preferredWidth: width
                                            Layout.preferredHeight: height
                                        }
                                        Label {
                                            text: modelData.label
                                            Layout.fillWidth: true
                                            Layout.alignment: Qt.AlignVCenter
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Kirigami.Separator { Layout.fillWidth: true }

            Label {
                text: qsTr("Palette")
                font.bold: true
            }

            // Extraction Controls
            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                ComboBox {
                    id: extractMethodCombo
                    model: ["pywal16", "material-you", "imagemagick"]
                    currentIndex: model.indexOf(lightbox.paletteCurrentBackend)
                    Layout.fillWidth: true
                    onActivated: {
                        lightbox.paletteCurrentBackend = currentText
                        lightbox.paletteGenerationActive = false
                        lightbox.paletteSelectedColor = "transparent"
                        lightbox.paletteSelectedIndex = -1
                        lightbox.paletteSelectedSet = ""
                        lightbox.resetPaletteParameters()
                        if (controller && controller.clearPalette) controller.clearPalette()
                    }
                }

                ToolButton {
                    id: extractButton
                    icon.name: "media-playback-start" //"palette-symbolic"
                    ToolTip.text: qsTr("Extract Color Palette")
                    ToolTip.visible: hovered
                    onClicked: {
                        var path = lightbox.paletteSourcePath()
                        if (!path) {
                            applicationWindow().showPassiveNotification(qsTr("No image available to extract from"))
                            return
                        }
                        lightbox.paletteGenerationActive = true
                        lightbox.refreshPalette(path)
                    }
                }
            }

            Kirigami.Separator {
                Layout.fillWidth: true
                visible: lightbox.paletteGenerationActive
            }

            ColumnLayout {
                Layout.fillWidth: true
                visible: lightbox.paletteGenerationActive
                spacing: Kirigami.Units.smallSpacing

                Label {
                    text: qsTr("Palette Colors")
                    font.bold: true
                }

                Grid {
                    id: paletteGrid
                    Layout.fillWidth: true
                    columns: 8
                    spacing: Kirigami.Units.smallSpacing / 6
                    clip: true

                    Repeater {
                        model: (controller.currentPaletteData && controller.currentPaletteData.colors) ? controller.currentPaletteData.colors : []
                        delegate: Item {
                            required property string modelData
                            required property int index
                            width: Kirigami.Units.gridUnit * 1.5
                            height: Kirigami.Units.gridUnit * 1.5

                            Rectangle {
                                anchors.fill: parent
                                anchors.margins: Kirigami.Units.smallSpacing / 2
                                color: parent.modelData
                                border.width: (lightbox.paletteSelectedSet === "palette" && lightbox.paletteSelectedIndex === parent.index) ? 2 : 1
                                border.color: (lightbox.paletteSelectedSet === "palette" && lightbox.paletteSelectedIndex === parent.index) ? Kirigami.Theme.highlightColor : Kirigami.Theme.disabledTextColor
                                radius: 3

                                MouseArea {
                                    id: maPalette
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                                    onClicked: (mouse) => {
                                        if (mouse.button === Qt.RightButton) {
                                            clipboardHelper.copyToClipboard(parent.parent.modelData)
                                            return
                                        }
                                        lightbox.paletteSelectedIndex = parent.parent.index
                                        lightbox.paletteSelectedSet = "palette"
                                        lightbox.paletteSelectedColor = parent.parent.modelData
                                    }
                                }

                                ToolTip.visible: maPalette.containsMouse
                                ToolTip.text: parent.modelData
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.topMargin: Kirigami.Units.smallSpacing
                    spacing: Kirigami.Units.smallSpacing
                    Label {
                        text: qsTr("Accent Colors")
                        font.bold: true
                    }
                }

                Grid {
                    id: accentGrid
                    Layout.fillWidth: true
                    columns: 8
                    spacing: Kirigami.Units.smallSpacing / 6
                    clip: true

                    Repeater {
                        model: (controller.currentPaletteData && controller.currentPaletteData.accents) ? controller.currentPaletteData.accents : []
                        delegate: Item {
                            required property string modelData
                            required property int index
                            width: Kirigami.Units.gridUnit * 1.5
                            height: Kirigami.Units.gridUnit * 1.5

                            Rectangle {
                                id: accentRect
                                anchors.fill: parent
                                anchors.margins: Kirigami.Units.smallSpacing / 2
                                color: parent.modelData
                                border.width: (lightbox.paletteSelectedSet === "accent" && lightbox.paletteSelectedIndex === parent.index) ? 2 : 1
                                border.color: (lightbox.paletteSelectedSet === "accent" && lightbox.paletteSelectedIndex === parent.index) ? Kirigami.Theme.highlightColor : Kirigami.Theme.disabledTextColor
                                radius: 3

                                MouseArea {
                                    id: maAccent
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                                    onClicked: (mouse) => {
                                        if (mouse.button === Qt.LeftButton) {
                                            lightbox.paletteSelectedIndex = parent.parent.index
                                            lightbox.paletteSelectedSet = "accent"
                                            lightbox.paletteSelectedColor = parent.parent.modelData
                                        } else if (mouse.button === Qt.RightButton) {
                                            clipboardHelper.copyToClipboard(parent.parent.modelData)
                                        }
                                    }
                                }

                                ToolTip.visible: maAccent.containsMouse
                                ToolTip.text: parent.modelData
                            }
                        }
                    }
                }
            }

            Kirigami.Separator {
                Layout.fillWidth: true
                visible: lightbox.paletteGenerationActive
            }

            // Aux Controls (for Material You and pywal16)
            ColumnLayout {
                Layout.fillWidth: true
                visible: lightbox.paletteGenerationActive
                spacing: Kirigami.Units.smallSpacing

                Label {
                    text: qsTr("Parameters")
                    font.bold: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    RadioButton {
                        text: qsTr("Dark")
                        checked: lightbox.paletteDarkMode
                        onToggled: {
                            if (checked) {
                                lightbox.paletteDarkMode = true
                                lightbox.triggerPaletteRefresh()
                            }
                        }
                    }
                    RadioButton {
                        text: qsTr("Light")
                        checked: !lightbox.paletteDarkMode
                        onToggled: {
                            if (checked) {
                                lightbox.paletteDarkMode = false
                                lightbox.triggerPaletteRefresh()
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: lightbox.paletteCurrentBackend !== "pywal16"
                    spacing: Kirigami.Units.smallSpacing

                    Label { text: qsTr("Tone:") }
                    ComboBox {
                        Layout.fillWidth: true
                        model: ["TonalSpot", "Vibrant", "Expressive", "Content", "FruitSalad", "Rainbow", "Monochrome", "Neutral", "Fidelity"]
                        currentIndex: model.indexOf(lightbox.paletteSelectedScheme)
                        onActivated: {
                            lightbox.paletteSelectedScheme = currentText
                            if (!lightbox.paletteGenerationActive && lightbox.paletteSourcePath()) {
                                lightbox.paletteGenerationActive = true
                            }
                            lightbox.triggerPaletteRefresh()
                        }
                    }
                    ToolButton {
                        icon.name: "edit-clear"
                        flat: true
                        opacity: (lightbox.paletteSelectedScheme !== "TonalSpot") ? 1.0 : 0.0
                        enabled: (lightbox.paletteSelectedScheme !== "TonalSpot")
                        ToolTip.text: qsTr("Reset to TonalSpot")
                        onClicked: {
                            lightbox.paletteSelectedScheme = "TonalSpot"
                            lightbox.triggerPaletteRefresh()
                        }
                    }
                }

            }

            Item { Layout.preferredHeight: Kirigami.Units.largeSpacing }
        }
    }
    }
}
