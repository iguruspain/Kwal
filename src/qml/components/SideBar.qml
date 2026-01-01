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
        Layout.leftMargin: Kirigami.Units.smallSpacing * 2
        Layout.rightMargin: Kirigami.Units.smallSpacing * 2
        Layout.topMargin: Kirigami.Units.smallSpacing

        Kirigami.ActionToolBar {
            anchors.fill: parent
            flat: true
            actions: [
                Kirigami.Action {
                    text: qsTr("Add Folder")
                    icon.name: "folder-new"
                    onTriggered: {
                        pyController.addFolder("New Folder", "/path/to/folder")
                    }
                }
            ]
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

