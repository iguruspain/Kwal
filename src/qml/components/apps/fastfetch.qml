import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import Qt.labs.folderlistmodel 2.1

Kirigami.Page {
    id: fastfetchPage
    title: qsTr("Fastfetch Settings")
    property bool isFileSelected: false
    property string sTintedName: ""

    background: Rectangle {
        color: "transparent"
    }

    // 1. Model (Static data only) - will be placed/adapted in models.py later
    ListModel {
        id: fastfetchModel
        ListElement {
            config_path: "/home/iguruspain/.config/fastfetch/config.jsonc" //will be populated with file_utils.py logic, currently static for testing
            config_image: "/home/iguruspain/.config/fastfetch/chica-tinted.png" //will be populated with file_utils.py logic, currently static for testing
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
        onCountChanged: {
            if (count > 0 && !fastfetchPage.isFileSelected) {
                templateSelector.currentIndex = -1;
            }
        }
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
                        //opacity: fastfetchPage.isFileSelected ? 1 : 0
                        //enabled: fastfetchPage.isFileSelected
                        onClicked: {
                            pyController.clearSelectedFile(); 
                            fastfetchPage.isFileSelected = false;
                            templateSelector.currentIndex = -1;
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

                        currentIndex: -1
                        displayText: currentIndex === -1 ? qsTr("Select predefined") : currentText
                        onActivated: {}                        
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        TextField {
                            id: customTemplateField
                            Layout.fillWidth: true
                            placeholderText: qsTr("Select your own image")
                            readOnly: true
                            text: {
                                if (!pyController.selectedFile) return ""
                                var f = pyController.selectedFile.replace("file://", "")
                                var parts = f.split("/")
                                return parts.length > 1 ? "..." + "/" + parts.slice(parts.length - 2).join("/") : f
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
            color: "transparent" //Kirigami.Theme.backgroundColor
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing
                spacing: Kirigami.Units.largeSpacing

                // Preview Section top
                ColumnLayout {
                    id: previewSectionTop
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: 7

                    Label { text: qsTr("Current (config):"); font.bold: true }

                    Image {
                        id: fastfetchCurrentImage
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        source: "file://" + fastfetchModel.get(0).config_image
                        fillMode: Image.PreserveAspectFit
                        asynchronous: true
                    }
                }
                
                // Preview Section bottom
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: Kirigami.Units.smallSpacing
                    Layout.preferredHeight: 3

                    // Labels row
                    RowLayout {
                        Layout.fillWidth: true
                    
                        Label {
                            id: selectedTemplateLabel
                            text: {
                                    let name = "";
                                    if (fastfetchPage.isFileSelected) {
                                        name = pyController.selectedFile ? pyController.selectedFile.split("/").pop() : "";
                                    } else {
                                        name = templateSelector.currentIndex !== -1 ? templateSelector.currentText : "";
                                    }
                                    //sTintedName = name !== "" ? replace(name, ".", "-tinted.") : "";
                                    // update tinted name property
                                    if (name !== "") {
                                        fastfetchPage.sTintedName = name.replace(".", "-tinted.");
                                    } else {
                                        fastfetchPage.sTintedName = "";
                                    }
                                    
                                    return name !== "" ? qsTr("Template: %1").arg(name) : qsTr("Template:");
                                }
                            visible: text !== qsTr("Template:")
                            font.bold: true
                        }
                        Item { Layout.fillWidth: true }
                        Label {
                            id: tintedLabel
                            text: {
                                let name = fastfetchPage.sTintedName;
                                return name !== "" ? qsTr("Tinted: %1").arg(name) : qsTr("Tinted:");
                            } // Placeholder
                            font.bold: true
                            visible: text !== qsTr("Tinted:")
                        }
                    }
                    // Images row
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: Kirigami.Units.mediumSpacing
                    
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
                            source: fastfetchPreviewTemplate.source // Placeholder, will be replaced with tinted version logic (controller and color_utils.py)
                            fillMode: Image.PreserveAspectFit
                            cache: false
                        }
                    }
                }
            }
        }
    }
}