import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Item {
    Layout.fillWidth: true
    Layout.fillHeight: true

    ColumnLayout {
        id: contentArea
        anchors.fill: parent
        spacing: Kirigami.Units.smallSpacing


        Label {
            id: selectedLabel
            // Show name of selected file
            text: pyController.selectedWallpaper ? qsTr("%1").arg(pyController.selectedWallpaper.split("/").pop()) : qsTr("")
            color: Kirigami.Theme.textColor
            font.bold: true
            Layout.fillWidth: true
            Layout.margins: Kirigami.Units.smallSpacing
            Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
        }
        Label {
            id: selectedResolutionLabel
            // Show resolution of selected file
            text: (pyController.selectedWallpaper && pyController.selectedWallpaper.length > 0) ? (pyController.selectedWallpaperResolution && pyController.selectedWallpaperResolution.length > 0 ? pyController.selectedWallpaperResolution : qsTr("Unknown")) : qsTr("")
            color: Kirigami.Theme.disabledTextColor
            Layout.fillWidth: true
            Layout.margins: Kirigami.Units.smallSpacing
            Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
        }
        Connections {
            target: pyController
            function onSelectedFolderChanged() {
                console.log("QML: pyController.selectedFolder changed ->", pyController.selectedFolder)
            }
            function onSelectedWallpaperChanged() {
                console.log("QML: pyController.selectedWallpaper changed ->", pyController.selectedWallpaper)
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
                    width: thumbnailGrid.cellWidth
                    height: thumbnailGrid.cellHeight

                    property bool isSelected: filePath === pyController.selectedWallpaper

                    Image {
                        id: imgDelegate
                        anchors.fill: parent
                        anchors.margins: Kirigami.Units.smallSpacing
                        source: thumbPath ? "file://" + thumbPath : (filePath ? "file://" + filePath : "")
                        sourceSize.width: width
                        sourceSize.height: height
                        fillMode: Image.PreserveAspectFit
                        cache: true
                        asynchronous: true

                        Rectangle {
                            anchors.centerIn: parent
                            width: imgDelegate.paintedWidth
                            height: imgDelegate.paintedHeight
                            color: "transparent"
                            border.color: isSelected ? Kirigami.Theme.highlightColor : "transparent"
                            border.width: isSelected ? 3 : 0
                            radius: Kirigami.Units.smallSpacing
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            pyController.selectWallpaper(filePath)
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
        // slide in/out by changing y
        y: (pyController.selectedWallpaper && pyController.selectedWallpaper.length > 0) ? parent.height - height : parent.height
        opacity: (pyController.selectedWallpaper && pyController.selectedWallpaper.length > 0) ? 1.0 : 0.0
        color: Qt.rgba(0, 0, 0, 0.6)
        border.color: Qt.rgba(1, 1, 1, 0.08)
        border.width: 1
        visible: (pyController.selectedWallpaper && pyController.selectedWallpaper.length > 0)
        Behavior on y { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.InOutQuad } }
        Behavior on opacity { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.InOutQuad } }

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
                                // hide drawer after action
                                pyController.selectWallpaper("")
                            }
                    }
                    ToolButton {
                        text: qsTr("Close")
                        icon.name: "window-close"
                        onClicked: {
                            pyController.selectWallpaper("")
                        }
                    }
                }
            }
        }
    }
}