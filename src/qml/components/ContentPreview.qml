import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

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

            // Real image model provided by Python
            model: imageModel
            delegate: Item {
                width: thumbnailGrid.cellWidth
                height: thumbnailGrid.cellHeight

                Image {
                    anchors.fill: parent
                    anchors.margins: Kirigami.Units.smallSpacing
                    source: thumbPath ? "file://" + thumbPath : (filePath ? "file://" + filePath : "")
                    fillMode: Image.PreserveAspectCrop
                    cache: true
                    asynchronous: true
                }
            }
        }
    }
}