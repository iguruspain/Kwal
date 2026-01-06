import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import Qt.labs.folderlistmodel 2.1

Kirigami.Page {
    id: fastfetchPage
    title: qsTr("Fastfetch Settings")
    property bool isFileSelected: false

    background: Rectangle {
        color: "transparent"
    }

    // 1. Model (Static data only) - will be placed/adapted in models.py later
    ListModel {
        id: fastfetchModel
        ListElement {
            config_path: "/home/iguruspain/.config/fastfetch/config.jsonc" //will be populated with config_reader.py logic, currently static for testing
            config_image: "/home/iguruspain/.config/fastfetch/chica-tinted.png" //will be populated with config_reader.py logic, currently static for testing
            template_image_folder: "/home/iguruspain/.config/kwal/templates/fastfetch" //will be populated with target folder from templates installer
        }
    }

    // Dynamic logic for searching template files
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

        // Left Pane
        Rectangle {
            id: leftPaneFastfetch
            color: Kirigami.Theme.backgroundColor
            Layout.preferredWidth: 250
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
                        id: selectTemplateLabel
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter                        
                        text: qsTr("Select a template")
                    }
                    ToolButton {
                        id: clearSelectionButton
                        icon.name: "edit-clear"
                        Layout.preferredWidth: Kirigami.Units.gridUnit * 2
                        opacity: fastfetchPage.isFileSelected ? 1 : 0
                        enabled: fastfetchPage.isFileSelected
                        onClicked: {
                            pyController.clearSelectedFile(); 
                            fastfetchPage.isFileSelected = false;
                        }
                    }              
                }

                GridLayout {
                    columns: 1
                    Layout.fillWidth: true

                    ComboBox {
                        id: templateSelector
                        Layout.fillWidth: true
                        model: templateFilesModel
                        textRole: "fileName"
                        enabled: !fastfetchPage.isFileSelected
                    }

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
                            icon.name: "document-open"
                            Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
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

        // Right Pane
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
                                return pyController.selectedFile;
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