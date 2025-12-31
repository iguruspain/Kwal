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


    ListModel {
        id: wallpaperFolderModel
        // Aquí se agregarán los elementos del modelo dinámicamente
        ListElement { name: "Local"; path: "/usr/share/wallpapers" }
        //ListElement { name: "Custom"; path: "/home/user/Pictures/Wallpapers" }
    } 

    // Definimos el delegado para los elementos del modelo
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
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing
                //spacing: 0

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
            color: "transparent"
            //Kirigami.Theme.colorSet: Kirigami.Theme.View
            //color: Kirigami.Theme.alternateBackgroundColor
            //border.width: 1
            //radius: 8

            ScrollView {
                id: scrollView
                anchors.fill: parent
                clip: true
                // Layout.fillWidth: parent
                // Layout.fillHeight: parent
                // anchors.fill: parent

                GridView {
                    id: thumbnailGrid
                    width: scrollView.availableWidth
                    height: scrollView.availableHeight

                    // Calculate how many columns fit (minimum 100px per thumbnail)
                    readonly property int columns: Math.max(2, Math.floor(width / 150))
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

                            color: Kirigami.Theme.alternateBackgroundColor
                            border.width: 1
                            border.color: Kirigami.Theme.textColor
                            radius: 6
                            Text {
                                color: parent.border.color
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
        id: initPage
        title: qsTr("Wallpapers")

        actions: [
            Kirigami.Action {
                id: addAction
                text: qsTr("Add Folder") //i18nc("@action:button", "Add Folder")
                icon.name: "folder-new"
                onTriggered: wallpaperFolderModel.append({"name": "New Folder", "path": "/path/to/new/folder"})
            }
        ]

        // Todo el contenido visual DEBE ir dentro de la Page
        RowLayout {
            anchors.fill: parent
            spacing: 10

            Loader {
                id: leftPanelLoader
                sourceComponent: leftPanelComponent
                Layout.fillHeight: true
                Layout.preferredWidth: 200
                onLoaded: {
                    item.parent = leftPanelLoader
                    console.log("Panel izquierdo cargado")
                }
                active: true
            }
            Item {
                Layout.preferredWidth: Kirigami.Units.smallSpacing
            }
            // Espacio central con grid de thumbnails correspondiente a los wallpapers de la carpeta seleccionada
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
    pageStack.initialPage: initPage
}