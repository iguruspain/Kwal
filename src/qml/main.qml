import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root
    visible: true
    width: 800
    height: 550
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
            //anchors.margins: Kirigami.Units.smallSpacing
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
        //titleIcon: Qt.resolvedUrl("../resources/images/kwal.png")
        //width: parent.width / 4
        //opacity: 0.8
        isMenu: true

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
                visible: false
                onTriggered: {
                    var settingsPageComponent = Qt.createComponent("components/Settings.qml");
                    if (settingsPageComponent.status === Component.Ready) {
                        var settingsPage = settingsPageComponent.createObject(root);
                        pageStack.replace(settingsPage);
                    } else {
                        console.error("Failed to load Settings page:", settingsPageComponent.errorString());
                    }
                }
            },
            Kirigami.Action {
                text: qsTr("Settings")
                icon.name: "settings-configure-symbolic"
                onTriggered: {
                    var altSettingsPageComponent = Qt.createComponent("components/AltSettings.qml");
                    if (altSettingsPageComponent.status === Component.Ready) {
                        var altSettingsPage = altSettingsPageComponent.createObject(root);
                        pageStack.replace(altSettingsPage);
                    } else {
                        console.error("Failed to load Alternative Settings page:", altSettingsPageComponent.errorString());
                    }
                }
            }
        ]
    }

    // First-run dialog: offer to install packaged templates to the user's config
    Dialog {
        id: templatesDialog
        title: qsTr("Install templates")
        visible: !pyController.templatesInstalled()
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            // call the controller slot to install templates
            pyController.installTemplates()
            templatesDialog.visible = false
        }
        onRejected: {
            templatesDialog.visible = false
        }
        ColumnLayout {
            anchors.fill: parent
            Label { text: qsTr("Install default templates to your user configuration (~/.config/kwal/templates)?") }
        }
    }

    // Connect passive notifications from Python Controller
    Connections {
        target: pyController
        function onNotification(message, type) {
            if (type === "error" && message !== "") {
                root.showPassiveNotification(message, "short")
            }
        }
    }
}