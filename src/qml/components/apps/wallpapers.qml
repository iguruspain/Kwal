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

        // --- Left Pane: Controls ---
        Rectangle {
            id: leftPaneWallpapers
            color: Kirigami.Theme.backgroundColor
            
            // Collapsible logic
            Layout.preferredWidth: wallpaperPage.sidePaneOpen ? 250 : 0
            Layout.fillHeight: true
            
            visible: Layout.preferredWidth > 0
            opacity: wallpaperPage.sidePaneOpen ? 1 : 0
            clip: true

            Behavior on Layout.preferredWidth { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.InOutQuad } }
            Behavior on opacity { OpacityAnimator { duration: Kirigami.Units.shortDuration } }
       
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing

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
                        onClicked: {pyController.openFolderDialog()}               
                    }            
                }
                    
                Kirigami.Separator {
                    Layout.fillWidth: true
                }
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
                        property bool isSelected: path === pyController.selectedFolder
                        property bool isHovered: mouseArea.containsMouse

                        // Selection border
                        Rectangle {
                            anchors.fill: parent
                            color: "transparent"
                            border.color: isHovered ? Kirigami.Theme.focusColor : (isSelected ? Kirigami.Theme.highlightColor : Qt.alpha(Kirigami.Theme.textColor, 0.1))
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
                                onClicked: pyController.selectFolder(index)
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
                                    Kirigami.Separator {
                                        Layout.fillWidth: true
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        // wrapMode: Text.WordWrap
                                        text: {
                                            if (name !== "Local") {
                                                return path.replace(pyController.homePath, "~\/")
                                            } else {
                                                return path
                                            }
                                        }
                                        color: Kirigami.Theme.disabledTextColor
                                        font.pixelSize: Kirigami.Units.smallSpacing * 3
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
                                        pyController.removeFolder(index)
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
        // --- Right Pane: Previews ---
        Rectangle {
            id: rightPaneWallpapers
            color: "transparent"
            Layout.fillWidth: true
            Layout.fillHeight: true

            // --- Drawer State ---
            property bool drawerOpen: false

            Connections {
                target: pyController
                function onSelectedWallpaperChanged() {
                    rightPaneWallpapers.drawerOpen = (pyController.selectedWallpaper !== "")
                }
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing
                spacing: Kirigami.Units.smallSpacing

                // Header Info
                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Kirigami.Units.gridUnit * 2
                    
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
                        visible: pyController.selectedWallpaper !== ""
                        Label {
                            Layout.alignment: Qt.AlignHCenter
                            text: pyController.selectedWallpaper ? pyController.selectedWallpaper.split("/").pop() : ""
                            font.bold: true
                            elide: Text.ElideMiddle
                        }
                        Label {
                            Layout.alignment: Qt.AlignHCenter
                            text: pyController.selectedWallpaperResolution
                            color: Kirigami.Theme.disabledTextColor
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                        }
                    }
                    
                    Item { Layout.fillWidth: true }
                }

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

                            property bool isSelected: filePath === pyController.selectedWallpaper
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

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        pyController.selectWallpaper(filePath)
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
                
                width: Math.min(parent.width * 0.8, actionsRow.implicitWidth + Kirigami.Units.largeSpacing * 2)
                height: actionsRow.implicitHeight + Kirigami.Units.largeSpacing
                
                property bool isOpen: rightPaneWallpapers.drawerOpen && pyController.selectedWallpaper !== "" && pyController.selectedWallpaper.length > 0
                
                // Slide up from bottom
                y: isOpen ? parent.height - height - Kirigami.Units.largeSpacing : parent.height
                opacity: isOpen ? 1.0 : 0.0
                visible: y < parent.height

                Behavior on y { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic } }
                Behavior on opacity { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic } }

                radius: Kirigami.Units.largeSpacing
                color: Kirigami.Theme.backgroundColor
                border.color: Kirigami.Theme.textColor
                border.width: 1

                RowLayout {
                    id: actionsRow
                    anchors.centerIn: parent
                    spacing: Kirigami.Units.largeSpacing
                    
                    ToolButton {
                        text: qsTr("Set as Wallpaper")
                        icon.name: "dialog-ok-apply"
                        // Positive color styling
                        icon.color: Kirigami.Theme.positiveTextColor
                        palette.buttonText: Kirigami.Theme.positiveTextColor
                        
                        onClicked: {
                            pyController.setAsWallpaper(pyController.selectedWallpaper)
                            rightPaneWallpapers.drawerOpen = false
                        }
                    }
                    ToolButton {
                        text: qsTr("Close")
                        icon.name: "dialog-close"
                        // Negative color styling
                        icon.color: Kirigami.Theme.negativeTextColor
                        palette.buttonText: Kirigami.Theme.negativeTextColor
                        
                        onClicked: {
                            rightPaneWallpapers.drawerOpen = false
                        }
                    }
                }
            }
        }
    }
}