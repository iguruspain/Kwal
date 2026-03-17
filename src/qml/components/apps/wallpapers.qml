pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.Page {
    id: wallpaperPage
    title: qsTr("Wallpapers")
    
    // State for sidebar
    property bool sidePaneOpen: false

    background: Rectangle {
        color: "transparent"
    }

    // --- Main Layout ---

    RowLayout {
        anchors.fill: parent
        spacing: Kirigami.Units.smallSpacing

        // Left Pane
        Rectangle {
            id: leftPaneWallpapers
            //color: Kirigami.Theme.backgroundColor
            color: Qt.alpha(Kirigami.Theme.backgroundColor, 0.80)
            
            // Collapsible logic
            Layout.preferredWidth: wallpaperPage.sidePaneOpen ? 300 : 0
            Layout.fillHeight: true
            radius: Kirigami.Units.largeSpacing
            border.color: Kirigami.Theme.highlightColor
            border.width: 1
            
            visible: Layout.preferredWidth > 0
            opacity: wallpaperPage.sidePaneOpen ? 1 : 0
            clip: true

            Behavior on Layout.preferredWidth { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.InOutQuad } }
            Behavior on opacity { OpacityAnimator { duration: Kirigami.Units.shortDuration } }
       
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.largeSpacing

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing
                    Label {
                        id: foldersLabel
                        text: qsTr("Folders")
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                        font.bold: true                        
                    }

                    ToolButton {
                        icon.name: "folder-new"
                        Layout.preferredWidth: Kirigami.Units.gridUnit * 2
                        ToolTip.text: qsTr("Add a wallpapers folder")
                        ToolTip.visible: hovered
                        onClicked: {controller.openFolderDialog()}               
                    }            
                }
                    
                MenuSeparator { Layout.fillWidth: true }

                Kirigami.CardsListView {
                    id: wallpaperCards
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: Kirigami.Units.smallSpacing
                    leftMargin: Kirigami.Units.smallSpacing
                    rightMargin: Kirigami.Units.smallSpacing
                    model: wallpaperFolderModel
                    delegate: Kirigami.AbstractCard {
                        id: card
                        required property string name
                        required property string path
                        required property int index

                        Layout.fillWidth: true
                        // Visually indicate selection by comparing the folder path with controller.selectedFolder
                        property bool isSelected: path === controller.selectedFolder
                        property bool isHovered: mouseArea.containsMouse

                        // Selection border
                        Rectangle {
                            anchors.fill: parent
                            color: "transparent"
                            border.color: isHovered ? Kirigami.Theme.focusColor : (isSelected ? Kirigami.Theme.highlightColor : Kirigami.Theme.alternateBackgroundColor)
                            border.width: isSelected ? 3 : 1
                            radius: Kirigami.Units.smallSpacing
                            visible: card.isSelected || card.isHovered
                        }

                        contentItem: Item {
                            implicitHeight: delegateLayout.implicitHeight

                            MouseArea {
                                id: mouseArea
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: controller.selectFolder(index)
                                cursorShape: Qt.PointingHandCursor
                            }
                            
                            GridLayout {
                                id: delegateLayout
                                anchors.fill: parent
                                columns: 2
                                columnSpacing: Kirigami.Units.smallSpacing
                                rowSpacing: Kirigami.Units.smallSpacing
                                ColumnLayout {
                                    Kirigami.Heading {
                                        level: 2
                                        text: name
                                    }
                                    Kirigami.Separator {Layout.fillWidth: true; color: Kirigami.Theme.alternateBackgroundColor}
                                    Label {
                                        Layout.fillWidth: true
                                        // wrapMode: Text.WordWrap
                                        text: {
                                            if (name !== "Local") {
                                                return path.replace(controller.homePath, "~\/")
                                            } else {
                                                return path
                                            }
                                        }
                                        color: Kirigami.Theme.disabledTextColor
                                        font.pixelSize: Kirigami.Units.smallSpacing * 3
                                        elide: Text.ElideLeft
                                    }
                                }

                                ToolButton {
                                    id: removeFolderButton
                                    icon.name: "edit-delete"
                                    icon.width: Kirigami.Units.gridUnit
                                    icon.height: Kirigami.Units.gridUnit
                                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                                    // Disable removal for the built-in Local folder
                                    enabled: name !== "Local"
                                    onClicked: {
                                        if (!enabled) return
                                        controller.removeFolder(index)
                                    }
                                    hoverEnabled: true
                                    ToolTip.text: qsTr("Remove this folder")
                                    ToolTip.visible: hovered
                                    ToolTip.delay: Kirigami.Units.toolTipDelay
                                } 
                            }
                        }
                    }
                }
            }
        }
        // Right Pane
        Rectangle {
            id: rightPaneWallpapers
            color: "transparent"
            Layout.fillWidth: true
            Layout.fillHeight: true

            // --- Drawer State ---
            property bool drawerOpen: false

            Connections {
                target: controller
                function onSelectedWallpaperChanged() {
                    rightPaneWallpapers.drawerOpen = (controller.selectedWallpaper !== "")
                }
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing
                spacing: Kirigami.Units.smallSpacing

                // Header Info
                RowLayout {
                    Layout.fillWidth: true
                    //Layout.preferredHeight: Kirigami.Units.gridUnit * 2
                    
                    ToolButton {
                        icon.name: "view-list-details" 
                        checkable: true
                        checked: wallpaperPage.sidePaneOpen
                        onToggled: wallpaperPage.sidePaneOpen = checked
                        ToolTip.text: qsTr("Toggle Folders Panel")
                        ToolTip.visible: hovered
                        display: AbstractButton.IconOnly
                    }

                    Item { Layout.fillWidth: true }
                    
                    ColumnLayout {
                        spacing: 0
                        visible: controller.selectedWallpaper !== ""
                        Layout.fillWidth: true          // ← acota el ancho
                        Layout.maximumWidth: 600        // ← opcional: límite razonable
                    
                        Label {
                            Layout.fillWidth: true      // ← necesario para que elide funcione
                            horizontalAlignment: Text.AlignHCenter
                            text: controller.selectedWallpaper ? controller.selectedWallpaper.split("/").pop() : ""
                            font.bold: true
                            elide: Text.ElideMiddle
                        }
                        Label {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            text: controller.selectedWallpaperResolution
                            color: Kirigami.Theme.disabledTextColor
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                        }
                    }
                    
                    Item { Layout.fillWidth: true }
                    
                }
                Item { Layout.fillHeight: true }
                //Kirigami.Separator {Layout.fillWidth: true; height: Kirigami.Units.smallSpacing; color: Qt.alpha(Kirigami.Theme.textColor, 0.4)}
                MenuSeparator { Layout.fillWidth: true }
                Item { Layout.fillHeight: true }
                // Grid View
                ScrollView {
                    id: scrollView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    GridView {
                        id: thumbnailGrid
                        // Use anchors to bind to the viewport width securely
                        anchors.left: parent.left
                        anchors.right: parent.right
                        // Reserve space for the scrollbar to prevent visual overlap
                        anchors.rightMargin: Kirigami.Units.smallSpacing + Kirigami.Units.largeSpacing 
                        
                        // Use strict integer division to avoid sub-pixel jitter
                        cellWidth: Math.floor(width / 4)
                        cellHeight: cellWidth * 0.75
                        
                        model: imageModel

                        delegate: Item {
                            width: thumbnailGrid.cellWidth
                            height: thumbnailGrid.cellHeight
                            
                            required property string filePath
                            required property string fileName
                            required property string thumbPath

                            property bool isSelected: filePath === controller.selectedWallpaper
                            property bool isHovered: hoverHandler.hovered

                            Rectangle {
                                anchors.fill: parent
                                anchors.margins: Kirigami.Units.smallSpacing
                                color: Qt.alpha(Kirigami.Theme.textColor, 0.05)
                                border.color: isHovered ? Kirigami.Theme.focusColor : (isSelected ? Kirigami.Theme.highlightColor : "transparent")
                                border.width: isSelected ? 3 : 1
                                radius: Kirigami.Units.smallSpacing

                                Image {
                                    anchors.fill: parent
                                    anchors.margins: Kirigami.Units.smallSpacing
                                    source: thumbPath ? "file://" + thumbPath : "file://" + filePath
                                    sourceSize.width: 320
                                    fillMode: Image.PreserveAspectCrop
                                    asynchronous: true
                                    smooth: true
                                }

                                Rectangle {
                                    anchors.right: parent.right
                                    anchors.bottom: parent.bottom
                                    anchors.margins: Kirigami.Units.smallSpacing * 2
                                    radius: Kirigami.Units.cornerRadius
                                    visible: controller.showExtensionBadge
                                    color: Qt.alpha(Kirigami.Theme.backgroundColor, 0.80)
                                    width: extLabel.implicitWidth + Kirigami.Units.smallSpacing * 2
                                    height: extLabel.implicitHeight + Kirigami.Units.smallSpacing
                                    border.color: Kirigami.Theme.highlightColor
                                    border.width: 0.5

                                    Label {
                                        id: extLabel
                                        anchors.centerIn: parent
                                        text: fileName.split(".").pop().toUpperCase()
                                        color: Kirigami.Theme.textColor
                                        font.pointSize: Kirigami.Theme.smallFont.pointSize * 0.8
                                        font.bold: true
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        controller.selectWallpaper(filePath)
                                        rightPaneWallpapers.drawerOpen = true
                                    }
                                }
                                
                                HoverHandler { id: hoverHandler }
                                
                                ToolTip.text: fileName
                                ToolTip.visible: hoverHandler.hovered
                                ToolTip.delay: Kirigami.Units.toolTipDelay
                            }
                        }
                    }
                }
            }
            
            BusyIndicator {
                anchors.centerIn: parent
                running: imageModel.loading
                visible: running
            }

            // Bottom Drawer
            Rectangle {
                id: bottomDrawer
                // Use y position for sliding animation instead of anchors.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                
                //width: parent.width * 0.8
                width: Math.min(parent.width * 0.8, drawerContent.implicitWidth + Kirigami.Units.largeSpacing * 4)
                height: drawerContent.implicitHeight + Kirigami.Units.largeSpacing * 2
                
                property bool isOpen: rightPaneWallpapers.drawerOpen && controller.selectedWallpaper !== "" && controller.selectedWallpaper.length > 0
                property bool commandVisible: false

                // Slide up from bottom
                y: isOpen ? parent.height - height - Kirigami.Units.largeSpacing * 2 : parent.height
                opacity: isOpen ? 1.0 : 0.0
                visible: y < parent.height

                Behavior on y { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic } }
                Behavior on height { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic } }
                Behavior on opacity { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic } }

                radius: Kirigami.Units.largeSpacing
                //color: root.overlayBackgroundColor
                color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g, Kirigami.Theme.backgroundColor.b, 0.95)
                border.color: Kirigami.Theme.highlightColor
                border.width: 1

                ColumnLayout {
                    id: drawerContent
                    anchors.fill: parent
                    anchors.margins: Kirigami.Units.largeSpacing
                    spacing: Kirigami.Units.largeSpacing
                    RowLayout {
                        id: actionsRow
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignHCenter
                        spacing: Kirigami.Units.largeSpacing
                        //Layout.preferredWidth: 400

                        ToolButton {
                            checkable: true
                            Layout.alignment: Qt.AlignLeft
                            checked: bottomDrawer.commandVisible
                            icon.name: bottomDrawer.commandVisible ? "arrow-down" : "arrow-right"
                            onToggled: bottomDrawer.commandVisible = checked
                            ToolTip.text: bottomDrawer.commandVisible ? qsTr("Hide custom command input") : qsTr("Show custom command input")
                            ToolTip.visible: hovered
                            ToolTip.delay: Kirigami.Units.toolTipDelay
                        }
                        Item { Layout.fillWidth: true }

                        ToolButton {
                            text: qsTr("Set as Wallpaper")
                            icon.name: "dialog-ok-apply"
                            icon.color: Kirigami.Theme.positiveTextColor
                            palette.buttonText: Kirigami.Theme.positiveTextColor

                            onClicked: {
                                controller.setAsWallpaper(controller.selectedWallpaper)
                                controller.runCMD(controller.customCommandWallpaper)
                                rightPaneWallpapers.drawerOpen = false
                            }
                        }
                        ToolButton {
                            text: qsTr("Close")
                            icon.name: "dialog-close"
                            icon.color: Kirigami.Theme.negativeTextColor
                            palette.buttonText: Kirigami.Theme.negativeTextColor

                            onClicked: {
                                rightPaneWallpapers.drawerOpen = false
                            }
                        }
                    }
                    Label {
                        text: qsTr("Wallpaper Colors")
                        visible: bottomDrawer.commandVisible
                        font.bold: true
                    }         
                    RowLayout {
                        Layout.alignment: Qt.AlignLeft | Qt.AlignHCenter
                        spacing: Kirigami.Units.smallSpacing
                        visible: bottomDrawer.commandVisible
                        
                        Repeater {
                            model: controller.wallpaperColors
                            delegate: Rectangle {
                                required property string modelData
                                width: Kirigami.Units.gridUnit * 1.5
                                height: Kirigami.Units.gridUnit * 1.5
                                radius: Kirigami.Units.smallSpacing
                                color: modelData
                                border.color: Qt.alpha(Kirigami.Theme.textColor, 0.2)
                                border.width: 1

                                HoverHandler { id: colorHover }
                                ToolTip.text: modelData.toUpperCase()
                                ToolTip.visible: colorHover.hovered
                                ToolTip.delay: Kirigami.Units.toolTipDelay
                            }
                        }
                    }
                    Label {
                        text: qsTr("Custom Command")
                        visible: bottomDrawer.commandVisible
                        font.bold: true
                    }                    
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 400
                        spacing: Kirigami.Units.smallSpacing
                        visible: bottomDrawer.commandVisible
                        TextField {
                            id: commandInput
                            Layout.fillWidth: true
                            placeholderText: qsTr("Enter custom command")
                            text: controller.customCommandWallpaper
                            onTextChanged: controller.customCommandWallpaper = text
                        }
                    }
                }
            }
        }
    }
}