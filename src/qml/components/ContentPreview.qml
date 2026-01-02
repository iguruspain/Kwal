import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import org.kde.kirigami as Kirigami

Item {
    id: root
    property bool drawerOpen: false
    property bool panelOpen: false
    Layout.fillWidth: true
    Layout.fillHeight: true

    RowLayout {
        id: mainRow
        anchors.fill: parent
        anchors.margins: Kirigami.Units.smallSpacing
        spacing: Kirigami.Units.smallSpacing

        // Left side panel loader
        Loader {
            id: leftPanelLoader
            Layout.preferredWidth: root.panelOpen ? Kirigami.Units.gridUnit * 10 : 0
            Layout.fillHeight: true
            Layout.rightMargin: root.panelOpen ? Kirigami.Units.smallSpacing : 0
            visible: Layout.preferredWidth > 0
            opacity: root.panelOpen ? 1 : 0
            source: "SideBar.qml"
            active: root.panelOpen
            Behavior on Layout.preferredWidth { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.InOutQuad } }
        }

        // Main content column
        ColumnLayout {
            id: contentArea
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Kirigami.Units.smallSpacing

        RowLayout {
            id: headerRow
            Layout.fillWidth: true
            Layout.margins: Kirigami.Units.smallSpacing
            spacing: Kirigami.Units.smallSpacing

            // header toggle button (restored here)
            ToolButton {
                id: headerShowButton
                icon.name: "view-list-details"
                checkable: true
                checked: root.panelOpen
                onClicked: root.panelOpen = !root.panelOpen
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                Layout.leftMargin: Kirigami.Units.smallSpacing
            }

            // left flexible spacer (keeps header button area clear)
            Item { Layout.fillWidth: true }

            // Centered labels column only (button is now in page header)
            ColumnLayout {
                id: headerLabels
                spacing: Kirigami.Units.smallSpacing / 2
                Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter

                Label {
                    id: selectedLabel
                    text: pyController.selectedWallpaper ? qsTr("%1").arg(pyController.selectedWallpaper.split("/").pop()) : qsTr("")
                    color: Kirigami.Theme.textColor
                    font.bold: true
                    font.pixelSize: Kirigami.Units.smallSpacing * 4
                    wrapMode: Text.WordWrap
                }
                Label {
                    id: selectedResolutionLabel
                    text: (pyController.selectedWallpaper && pyController.selectedWallpaper.length > 0) ? (pyController.selectedWallpaperResolution && pyController.selectedWallpaperResolution.length > 0 ? pyController.selectedWallpaperResolution : qsTr("Unknown")) : qsTr("")
                    color: Kirigami.Theme.disabledTextColor
                    font.pixelSize: Kirigami.Units.smallSpacing * 2
                }
            }

            // right flexible spacer
            Item { Layout.fillWidth: true }
        }
        //Kirigami.Separator { Layout.fillWidth: true }
        Connections {
            target: pyController
            function onSelectedFolderChanged() {
                console.log("QML: pyController.selectedFolder changed ->", pyController.selectedFolder)
            }
            function onSelectedWallpaperChanged() {
                console.log("QML: pyController.selectedWallpaper changed ->", pyController.selectedWallpaper)
                // Open drawer when a wallpaper is selected programmatically
                root.drawerOpen = pyController.selectedWallpaper !== ""
            }
        }

        ScrollView {
            id: scrollView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            GridView {
                id: thumbnailGrid
                width: scrollView.availableWidth
                height: scrollView.availableHeight
                visible: pyController.selectedFolder && pyController.selectedFolder.length > 0

                readonly property real minItemWidth: Kirigami.Units.gridUnit * 10
                readonly property int columns: Math.max(2, Math.floor(width / minItemWidth))
                readonly property real cellSize: width / columns

                cellWidth: cellSize
                cellHeight: cellSize * 0.75
                Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
                
                // Improve scrolling performance
                cacheBuffer: cellHeight * 2

                // Real image model provided by Python
                model: imageModel
                delegate: Item {
                    id: delegateItem
                    width: thumbnailGrid.cellWidth
                    height: thumbnailGrid.cellHeight

                    property bool isSelected: filePath === pyController.selectedWallpaper

                    // Container Frame
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: Kirigami.Units.smallSpacing
                        
                        // Subtle background to define the cell area
                        color: Qt.alpha(Kirigami.Theme.textColor, 0.03)
                        radius: Kirigami.Units.smallSpacing

                        // Border: Standard (subtle) vs Highlighted (accent)
                        border.color: isSelected ? Kirigami.Theme.highlightColor : Qt.alpha(Kirigami.Theme.textColor, 0.15)
                        border.width: isSelected ? 3 : 1
                        
                        // Image inside
                        Image {
                            anchors.fill: parent
                            // Padding inside the frame so image doesn't touch border
                            anchors.margins: Kirigami.Units.smallSpacing
                            
                            source: thumbPath ? "file://" + thumbPath : (filePath ? "file://" + filePath : "")
                            
                            // Optimize loading
                            sourceSize.width: thumbPath ? 0 : width
                            sourceSize.height: 0

                            fillMode: Image.PreserveAspectCrop //PreserveAspectFit
                            cache: true
                            asynchronous: true
                            mipmap: true // Smoother scaling
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                pyController.selectWallpaper(filePath)
                                root.drawerOpen = true
                            }
                        }
                    }
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

    // Inline bottom drawer-like panel shown when an image is selected
    Rectangle {
        id: bottomDrawer
        // size to fit actions
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(parent.width * 0.9, actionsRow.implicitWidth + Kirigami.Units.smallSpacing * 4)
        height: Math.max(actionsRow.implicitHeight + Kirigami.Units.smallSpacing * 2, Kirigami.Units.gridUnit * 3)
        // slide in/out by changing y (drawerOpen controls visibility without clearing selection)
        y: (pyController.selectedWallpaper && pyController.selectedWallpaper.length > 0 && root.drawerOpen) ? parent.height - height : parent.height
        opacity: (pyController.selectedWallpaper && pyController.selectedWallpaper.length > 0 && root.drawerOpen) ? 1.0 : 0.0

        color: "transparent"
        visible: (pyController.selectedWallpaper && pyController.selectedWallpaper.length > 0 && root.drawerOpen)
        Behavior on y { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.InOutQuad } }
        Behavior on opacity { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.InOutQuad } }

        ShaderEffectSource {
            id: backgroundSource
            anchors.fill: parent
            sourceItem: contentArea
            sourceRect: Qt.rect(bottomDrawer.x, bottomDrawer.y, bottomDrawer.width, bottomDrawer.height)
            visible: false
        }

        MultiEffect {
            anchors.fill: parent
            source: backgroundSource
            blurEnabled: true
            blurMax: 32
            blur: 1.0
        }

        Rectangle {
            anchors.fill: parent
            color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g, Kirigami.Theme.backgroundColor.b, 0.7)
            border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.1)
            border.width: 1
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.smallSpacing
            spacing: Kirigami.Units.smallSpacing

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                RowLayout {
                    id: actionsRow
                    Layout.alignment: Qt.AlignRight
                    // do not force fill; we size the drawer to this row

                    ToolButton {
                        text: qsTr("Set as wallpaper")
                        icon.name: "dialog-ok-apply"
                        enabled: pyController.selectedWallpaper !== ""
                        onClicked: {
                            pyController.setAsWallpaper(pyController.selectedWallpaper)
                            // close drawer but keep selection
                            root.drawerOpen = false
                        }
                    }
                    ToolButton {
                        text: qsTr("Close")
                        icon.name: "window-close"
                        onClicked: {
                            // only close drawer; keep selection
                            root.drawerOpen = false
                        }
                    }
                }
            }
        }
    }
}