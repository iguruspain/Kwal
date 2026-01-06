import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import Qt.labs.folderlistmodel 2.1

Kirigami.Page {
    id: fastfetchPage
    title: qsTr("Fastfetch Settings")
    property bool isFileSelected: false
    property string sFileSelected: ""

    background: Rectangle {
        color: "transparent"
    }

    // 1. EL MODELO (Solo datos estáticos)
    ListModel {
        id: fastfetchModel
        ListElement {
            config_path: "/home/iguruspain/.config/fastfetch/config.jsonc"
            config_image: "/home/iguruspain/.config/fastfetch/chica-tinted.png"
            template_image_folder: "/home/iguruspain/.config/kwal/templates/fastfetch"
        }
    }

    // 2. EL BUSCADOR DE ARCHIVOS (Lógica dinámica)
    // Este objeto leerá la carpeta definida en el modelo
    FolderListModel {
        id: templateFilesModel

        folder: "file://" + fastfetchModel.get(0).template_image_folder
        nameFilters: [ "*.png", "*.jpg", "*.jpeg", "*.bmp", "*.svg" ]
        showDirs: false
        showFiles: true
        sortField: FolderListModel.Name
    }


    RowLayout {
        anchors.fill: parent
        spacing: Kirigami.Units.smallSpacing

        // --- Panel Izquierdo ---
        Rectangle {
            id: leftPaneFastfetch
            color: Kirigami.Theme.backgroundColor
            Layout.preferredWidth: 250 // Un poco más ancho para los paths
            Layout.fillHeight: true
       
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing

                Label {
                    text: qsTr("Settings")
                    font.bold: true
                    Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                }

                MenuSeparator { Layout.fillWidth: true }

                RowLayout{
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing
                    Label {
                        text: qsTr("Select Fastfetch Template")
                        Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                    }
                    ToolButton {
                        id: clearSelectionButton
                        icon.name: "edit-clear"
                        visible: fastfetchPage.isFileSelected
                        onClicked: {
                            pyController.selectedFile = ""; // Asumiendo que puedes resetearlo en Python
                            fastfetchPage.isFileSelected = false;
                        }
                    }              
                }

                GridLayout {
                    columns: 1
                    Layout.fillWidth: true

                    //Label { text: qsTr("Default:") }
                    // Selector para elegir entre los archivos encontrados en la carpeta
                    ComboBox {
                        id: templateSelector
                        Layout.fillWidth: true
                        model: templateFilesModel
                        textRole: "fileName"
                        enabled: !fastfetchPage.isFileSelected
                    }
                    //Label { text: qsTr("Custom:") }
                    RowLayout {
                        Layout.fillWidth: true

                        TextField {
                            id: customTemplateField
                            Layout.fillWidth: true
                            placeholderText: qsTr("Select a custom image")
                            readOnly: true
                            text: {
                                if (!pyController.selectedFile) return ""
                                var f = pyController.selectedFile.replace("file://", "")
                                var parts = f.split("/")
                                return parts.length > 1 ? "..." + "/" + parts.slice(parts.length - 1).join("/") : f
                            }
                        }
                        ToolButton {
                            id: openFileButton
                            //text: qsTr("Add Folder")
                            icon.name: "document-open"
                            Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                            //text: qsTr("Add Folder")
                            onClicked: {
                                pyController.openFileDialog();
                                if (pyController.selectedFile) {
                                    fastfetchPage.isFileSelected = true;
                                } else {
                                    fastfetchPage.isFileSelected = false;
                                }
                            }
                            hoverEnabled: true
                            ToolTip.text: qsTr("Select a custom image")
                            ToolTip.visible: hovered
                            ToolTip.delay: Kirigami.Units.toolTipDelay
                        }     
                    }
                }
                
                Item { Layout.fillHeight: true }
            }
        }

        // --- Panel Derecho (Previews) ---
        Rectangle {
            id: rightPaneFastfetch
            color: Kirigami.Theme.backgroundColor
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing

                Text {
                    text: qsTr("Fastfetch Previews")
                    font.bold: true
                    color: Kirigami.Theme.textColor
                }

                GridLayout {
                    columns: 2
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Label { text: qsTr("Current"); font.bold: true }
                    Item { Layout.fillHeight: true; Layout.fillWidth: true }

                    Image {
                        id: fastfetchCurrentImage
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        // Usamos file:// para asegurar que cargue de disco local
                        source: "file://" + fastfetchModel.get(0).config_image
                        fillMode: Image.PreserveAspectFit
                    }

                    Item { Layout.fillHeight: true; Layout.fillWidth: true }

                    Label { text: qsTr("Template:"); font.bold: true }
                    Label { text: qsTr("Tinted:"); font.bold: true }

                    Image {
                        id: fastfetchPreviewTemplate
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        source: {
                            if (pyController.selectedFile) {
                                return pyController.selectedFile; // Ya debería ser una URL válida
                            }
                            return templateSelector.currentValue ? (templateFilesModel.folder + "/" + templateSelector.currentText) : ""
                        }
                        fillMode: Image.PreserveAspectFit
                    }

                    Image {
                        id: fastfetchPreviewTinted
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        source: fastfetchPreviewTemplate.source // Placeholder
                        fillMode: Image.PreserveAspectFit
                    }
                }
            }
        }
    }
}