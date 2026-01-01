import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root
    visible: true
    width: 800
    height: 600
    title: "Kwal"

    // Models provided by Python (wallpaperFolderModel context property)

    // Delegate and panels moved to separate QML files:
    // - WallpaperDelegate.qml
    // - SideBar.qml
    // - ContentPreview.qml

    Kirigami.Page {
        id: wallpaperPage
        title: qsTr("Wallpapers")

        actions: [
            Kirigami.Action {
                id: showAction
                //text: qsTr("Folders")
                icon.name: "view-list-details"
                checkable: true
                checked: false
                onTriggered: {}
            }
        ]

        RowLayout {
            anchors.fill: parent
            spacing: 0

            Loader {
                id: leftPanelLoader
                Layout.preferredWidth: showAction.checked ? Kirigami.Units.gridUnit * 10 : 0
                Layout.fillHeight: true
                Layout.rightMargin: showAction.checked ? Kirigami.Units.smallSpacing : 0
                visible: Layout.preferredWidth > 0
                opacity: showAction.checked ? 1 : 0
                source: "components/SideBar.qml"
                active: true
                Behavior on Layout.preferredWidth {
                    NumberAnimation {
                        duration: Kirigami.Units.shortDuration
                        easing.type: Easing.InOutQuad
                    }
                }
            }

            Kirigami.Separator {
                Layout.fillHeight: true
                visible: showAction.checked
            }

            Loader {
                id: contentPreviewLoader
                source: "components/ContentPreview.qml"
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.leftMargin: showAction.checked ? Kirigami.Units.smallSpacing : 0
                onLoaded: {
                    item.parent = contentPreviewLoader
                    console.log("Panel de previsualización cargado")
                }
                active: true
            }
        }
    }

    pageStack.initialPage: wallpaperPage

    globalDrawer: Kirigami.GlobalDrawer {
        id: globalDrawer
        title: qsTr("Kwal")
        titleIcon: "preferences-desktop-wallpaper"
        width: parent.width / 4

        actions: [
            Kirigami.Action {
                text: qsTr("Wallpapers")
                icon.name: "edit-image"
                onTriggered: {
                    pageStack.push(wallpaperPage)
                }
            }
        ]
    }
}