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

        // // 2. OPCIÓN NATIVA: Sobrescribir el Tema de esta página
        // // Esto fuerza a que la cabecera por defecto use este color semitransparente
        // Kirigami.Theme.headerBackgroundColor: Qt.rgba(root.baseThemeColor.r, root.baseThemeColor.g, root.baseThemeColor.b, 0.8)
        
        // // También actualizamos el color de fondo base de la página para que coincida
        // Kirigami.Theme.backgroundColor: Qt.rgba(root.baseThemeColor.r, root.baseThemeColor.g, root.baseThemeColor.b, 0.8)
        
        // // Custom background using the theme color we just defined
        // background: Rectangle {
        //     // Usamos el color del tema que acabamos de modificar (ya incluye la transparencia)
        //     color: Kirigami.Theme.backgroundColor
        //     // Nota: Ya no necesitamos 'opacity: 0.8' aquí porque el color en sí mismo es translúcido
        // }

        // Custom background to ensure content is opaque but header can be transparent
        background: Rectangle {
            color: Kirigami.Theme.backgroundColor
            // Start the opaque background below the header if we want the header to be see-through to desktop
            // But Kirigami Page background usually covers everything.
            // Let's make the page background transparent and handle content background separately?
            // Or just make the whole page background slightly translucent?
            opacity: 0.8 
        }

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