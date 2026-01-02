import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami



ColumnLayout {
    id: sidebarLayout
    anchors.fill: parent
    spacing: Kirigami.Units.smallSpacing

    Item {
        id: buttonContainer
        Layout.fillWidth: true
        Layout.preferredHeight: Kirigami.Units.gridUnit * 2
        //Layout.leftMargin: Kirigami.Units.smallSpacing * 2
        //Layout.rightMargin: Kirigami.Units.smallSpacing * 2
        //Layout.topMargin: Kirigami.Units.smallSpacing

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            ToolButton {
                text: qsTr("Add Folder")
                icon.name: "folder-new"
                Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                //text: qsTr("Add Folder")
                onClicked: {pyController.openFolderDialog()}
            }            
        }
    }
    Kirigami.Separator {
        Layout.fillWidth: true
    }
    Kirigami.CardsListView {
        id: wallpaperCards
        Layout.fillWidth: true
        Layout.fillHeight: true
        model: wallpaperFolderModel
        delegate: WallpaperDelegate {}
        spacing: Kirigami.Units.smallSpacing
        leftMargin: Kirigami.Units.smallSpacing
        rightMargin: Kirigami.Units.smallSpacing
    }
}
