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
            // Start the opaque background below the header if we want the header to be see-through to desktop
            // But Kirigami Page background usually covers everything.
            // Let's make the page background transparent and handle content background separately?
            // Or just make the whole page background slightly translucent?
            opacity: 0.8 
        }

        // Header: place the sidebar toggle in the page header so it's consistent
        header: ToolBar {
            RowLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing

                ToolButton {
                    id: headerShowButton
                    icon.name: "view-list-details"
                    checkable: true
                    // reflect panel state when content is loaded
                    checked: contentPreviewLoader.item ? contentPreviewLoader.item.panelOpen : false
                    onClicked: {
                        if (contentPreviewLoader.item) {
                            contentPreviewLoader.item.panelOpen = !contentPreviewLoader.item.panelOpen
                        }
                    }
                }

                // push the rest of the toolbar items to the right
                Item { Layout.fillWidth: true }

                // optionally mirror other actions here
            }
        }

        RowLayout {
            anchors.fill: parent
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

    // globalDrawer: Kirigami.GlobalDrawer {
    //     id: globalDrawer
    //     title: qsTr("Kwal")
    //     titleIcon: "preferences-desktop-wallpaper"
    //     width: parent.width / 4

    //     actions: [
    //         Kirigami.Action {
    //             text: qsTr("Wallpapers")
    //             icon.name: "edit-image"
    //             onTriggered: {
    //                 pageStack.push(wallpaperPage)
    //             }
    //         }
    //     ]
    // }
}