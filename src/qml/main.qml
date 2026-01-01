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

    //Models
    // Definimos el modelo para las carpetas de wallpapers
    ListModel {
        id: wallpaperFolderModel
        // Aquí se agregarán los elementos del modelo dinámicamente
        ListElement { name: "Local"; path: "/usr/share/wallpapers" }
        //ListElement { name: "Custom"; path: "/home/user/Pictures/Wallpapers" }
    }
    
    // Delegates
    // Definimos el delegado para los elementos del modelo de carpetas de wallpapers
    Component {
        id: wallpaperDelegate
        Kirigami.AbstractCard {
            id: card
            Layout.fillWidth: true
            
            contentItem: RowLayout {
                id: delegateLayout
                // Usamos los márgenes estándar de Kirigami
                spacing: Kirigami.Units.smallSpacing

                Label {
                    text: name
                    font.bold: true
                    Layout.fillWidth: true
                    verticalAlignment: Text.AlignVCenter
                    Layout.alignment: Qt.AlignVCenter
                }
                Item {
                    Layout.fillWidth: true
                }
                // ToolButton {
                //     id: openFolderButton
                //     // Configuramos el tamaño del icono directamente
                //     icon.name: "folder-open"
                //     icon.width: Kirigami.Units.gridUnit //* 1.2
                //     icon.height: Kirigami.Units.gridUnit //* 1.2
                    
                //     Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                    
                //     onClicked: console.log("Path: " + path)
                // }
                ToolButton {
                    id: removeFolderButton
                    icon.name: "edit-delete"
                    icon.width: Kirigami.Units.gridUnit //* 1.2
                    icon.height: Kirigami.Units.gridUnit //* 1.2
                    
                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                    
                    onClicked: {
                        console.log("Remove folder: " + path)
                        wallpaperFolderModel.remove(index)
                    }
                }
            }
        }
    }

    // Components de los paneles
    // Definimos los componentes de los paneles fuera para que sean reusables
    Component {
        id: leftPanelComponent

        Rectangle {
            implicitWidth: 250
            //implicitHeight: 400
            Kirigami.Theme.colorSet: Kirigami.Theme.View
            color: Kirigami.Theme.backgroundColor
            //border.width: 1
            radius: 8
            
            ColumnLayout {
                id: sidebarLayout
                anchors.fill: parent
                spacing: Kirigami.Units.smallSpacing // Espaciado consistente entre botón y lista

                // Contenedor del Botón para alineación precisa
                Item {
                    id: buttonContainer
                    Layout.fillWidth: true
                    // Altura preferida basada en el tamaño estándar de controles de Kirigami
                    Layout.preferredHeight: Kirigami.Units.gridUnit * 2
                    
                    // Usamos márgenes que coincidan con los de CardsListView
                    Layout.leftMargin: Kirigami.Units.smallSpacing * 2
                    Layout.rightMargin: Kirigami.Units.smallSpacing * 2
                    Layout.topMargin: Kirigami.Units.smallSpacing

                    Kirigami.ActionToolBar {
                        anchors.fill: parent
                        flat: true // Le da un aspecto de botón real que rellena el espacio
                        actions: [
                            Kirigami.Action {
                                text: qsTr("Add Folder")
                                icon.name: "folder-new"
                                onTriggered: {
                                    wallpaperFolderModel.append({
                                        "name": "New Folder", 
                                        "path": "/path/to/folder"
                                    })
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
                    delegate: wallpaperDelegate
                    spacing: Kirigami.Units.smallSpacing
                    leftMargin: Kirigami.Units.smallSpacing
                    rightMargin: Kirigami.Units.smallSpacing
                }
            }
        }
    }
    Component {
        id: contentPreviewComponent
        
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Kirigami.Theme.colorSet: Kirigami.Theme.View
            color: Kirigami.Theme.alternateBackgroundColor
            //border.width: 1
            //radius: 8

            ScrollView {
                id: scrollView
                anchors.fill: parent
                clip: true

                GridView {
                    id: thumbnailGrid
                    width: scrollView.availableWidth
                    height: scrollView.availableHeight

                    // Calculate how many columns fit (minimum 150px per thumbnail)
                    readonly property real minItemWidth: Kirigami.Units.gridUnit * 10
    
                    readonly property int columns: Math.max(2, Math.floor(width / minItemWidth))
                    readonly property real cellSize: width / columns
                    
                    cellWidth: cellSize
                    cellHeight: cellSize * 0.75
                    Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
                
                    model: 50 // Placeholder, reemplazar con el modelo de wallpapers
                    delegate: Item {
                        width: thumbnailGrid.cellWidth
                        height: thumbnailGrid.cellHeight
                    
                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: Kirigami.Units.smallSpacing
                            Kirigami.Theme.colorSet: Kirigami.Theme.View
                            color: Kirigami.Theme.backgroundColor
                            border.width: 1
                            border.color: Kirigami.Theme.highlightColor
                            radius: 6
                            Text {
                                color: Kirigami.Theme.textColor
                                anchors.centerIn: parent
                                text: "Thumb " + (index + 1)
                            }
                        }
                    }
                    //Aquí se agregarán los thumbnails de los wallpapers dinámicamente
                }
            }
        }            
    }

    Kirigami.Page {
        id: wallpaperPage
        title: qsTr("Wallpapers")

        actions: [
            Kirigami.Action {
                id: showAction
                text: qsTr("Folders") //i18nc("@action:button", "Refresh")
                icon.name: "view-list-details"
                checkable: true // Hacemos que el botón sea un interruptor
                checked: false   // Por defecto no visible
                onTriggered: {}
            }
        ]

        RowLayout {
            anchors.fill: parent
            spacing: 0

            // Panel lateral con la lista de carpetas de wallpapers
            Loader {
                id: leftPanelLoader
                
                // 1. Layout & Positioning
                // Si el botón está marcado, mostramos el panel, si no, ancho 0
                Layout.preferredWidth: showAction.checked ? Kirigami.Units.gridUnit * 10 : 0
                Layout.fillHeight: true
                
                // 2. Visuals
                visible: Layout.preferredWidth > 0
                opacity: showAction.checked ? 1 : 0
                
                // 3. Logic
                sourceComponent: leftPanelComponent
                active: true
                
                // Animación fluida para el panel
                Behavior on Layout.preferredWidth {
                    NumberAnimation {
                        duration: Kirigami.Units.shortDuration
                        easing.type: Easing.InOutQuad
                    }
                }
            }
            
            // Separador que solo aparece si el panel está abierto
            Kirigami.Separator {
                Layout.fillHeight: true
                visible: showAction.checked
            }                     

            // Panel con grid de thumbnails correspondiente a los wallpapers de la carpeta seleccionada
            Loader {
                id: contentPreviewLoader
                sourceComponent: contentPreviewComponent
                Layout.fillWidth: true
                Layout.fillHeight: true
                onLoaded: {
                    item.parent = contentPreviewLoader
                    console.log("Panel de previsualización cargado")
                }
                active: true
            }
        }
    }

    pageStack.initialPage: wallpaperPage

    // Global Drawer
    globalDrawer: Kirigami.GlobalDrawer {
        id: globalDrawer
        title: qsTr("Kwal")
        titleIcon: "preferences-desktop-wallpaper"
        width: parent.width / 4
   
        actions: [
            Kirigami.Action {
                text: qsTr("Wallpapers")
                icon.name: "preferences-desktop-wallpaper"
                onTriggered: {
                    pageStack.push(wallpaperPage)
                }
            }
        ]
    }
}