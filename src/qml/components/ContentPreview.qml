import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Item {
    Layout.fillWidth: true
    Layout.fillHeight: true

    ColumnLayout {
        anchors.fill: parent
        spacing: Kirigami.Units.smallSpacing

        Label {
            id: selectedLabel
            text: (pyController.selectedFolder && pyController.selectedFolder.length > 0)
                    ? qsTr("Selected folder:") + " " + pyController.selectedFolder
                    : qsTr("Selected folder: none")
            //Kirigami.Theme.colorSet: Kirigami.Theme.View
            color: Kirigami.Theme.textColor
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            Layout.margins: Kirigami.Units.smallSpacing
        }

        Connections {
            target: pyController
            function onSelectedFolderChanged() {
                console.log("QML: pyController.selectedFolder changed ->", pyController.selectedFolder)
                selectedLabel.text = (pyController.selectedFolder && pyController.selectedFolder.length > 0)
                                        ? qsTr("Selected folder:") + " " + pyController.selectedFolder
                                        : qsTr("Selected folder: none")
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
}