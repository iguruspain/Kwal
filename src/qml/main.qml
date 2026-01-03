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
    
    // Enable transparency for the main window
    color: "transparent"

    // Models provided by Python (wallpaperFolderModel context property)

    // Delegate and panels moved to separate QML files:
    // - WallpaperDelegate.qml
    // - SideBar.qml
    // - ContentPreview.qml   
    
    Kirigami.Page {
        id: wallpaperPage
        title: qsTr("Wallpapers")

        // Custom background to ensure content is opaque but header can be transparent
        background: Rectangle {
            color: Kirigami.Theme.backgroundColor
            opacity: 0.8 
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.smallSpacing
            spacing: 0

            Loader {
                id: contentPreviewLoader
                source: "components/ContentPreview.qml"
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.leftMargin: Kirigami.Units.smallSpacing
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
        opacity: 0.8
        //isMenu: true

        actions: [
            Kirigami.Action {
                text: qsTr("Wallpapers")
                icon.name: "edit-image"
                onTriggered: {
                    pageStack.replace(wallpaperPage)
                }
            },
            Kirigami.Action {
                text: qsTr("Settings")
                icon.name: "settings-configure-symbolic"
                onTriggered: {
                    var settingsPageComponent = Qt.createComponent("components/Settings.qml");
                    if (settingsPageComponent.status === Component.Ready) {
                        var settingsPage = settingsPageComponent.createObject(root);
                        pageStack.replace(settingsPage);
                    } else {
                        console.error("Failed to load Settings page:", settingsPageComponent.errorString());
                    }
                }
            }
        ]
    }
}