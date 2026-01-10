import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import ".." as Components

Kirigami.Page{
    id: starshipPage
    title: qsTr("Starship Settings")

    background: Rectangle {
        color: "transparent"
    }
    // Proxy to Python Starship model exposed by Controller (pyController.starshipModel)
    Item {
        id: starshipModelProxy
        // Underlying Python QObject
        property var model: (pyController && pyController.starshipModel) ? pyController.starshipModel : null
        property int selectedIndex: -1
        property string configFile: model ? model.configPath : "~/.config/starship.toml"
        property string templateFolder: model ? model.templateFolder : "~/.config/kwal/templates/starship/"
        property var paletteNames: model ? model.paletteNames : []
        property var paletteValues: model ? model.paletteValues : []
        property var paletteKeys: model ? model.paletteKeys : []
        property bool paletteExpanded: true
        // Editing context for palette dialog
        property int editIndex: -1
        property string editSet: "palette"

        Component.onCompleted: {
            if (model && model.refresh) model.refresh()
            if (model && model.paletteNames && model.paletteNames.length > 0) selectedIndex = 0
        }

        // Update derived properties when local `paletteNames` changes
        onPaletteNamesChanged: {
            if (paletteNames && paletteNames.length > 0) selectedIndex = 0
            else selectedIndex = -1
        }
    }

    // Controller helper like in fastfetch.qml
    readonly property var controller: (typeof pyController !== "undefined") ? pyController : null

    Components.DialogPalette {
        id: paletteDialog
        onAccepted: {
            if (selectedColor && selectedColor !== "transparent") {
                // If we have an edit index set, write back into the model proxy
                if (starshipModelProxy.selectedIndex >= 0 && starshipModelProxy.editIndex >= 0) {
                    starshipModelProxy.paletteValues[starshipModelProxy.selectedIndex][starshipModelProxy.editIndex] = selectedColor
                }
            }
        }
    }

   // --- Main Layout ---

    RowLayout {
        anchors.fill: parent
        spacing: Kirigami.Units.smallSpacing

        // --- Left Pane: Controls ---
        Rectangle {
            id: leftPaneStarship
            color: Kirigami.Theme.backgroundColor
            Layout.preferredWidth: 280
            Layout.fillHeight: true

            ColumnLayout {
                id: leftColumn
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing
                spacing: Kirigami.Units.smallSpacing

                Label {
                    text: qsTr("Settings")
                    font.bold: true
                    Layout.fillWidth: true
                }

                MenuSeparator { Layout.fillWidth: true }

                RowLayout {
                    Layout.fillWidth: true                
                    Label {
                        text: qsTr("Select a template")
                        Layout.fillWidth: true
                    }
                    ToolButton {
                            icon.name: "edit-clear"
                            onClicked: { /* logic to be implemented, like fastfetch.qml, reset all */ }
                    }
                }

                ComboBox {
                    //All here is wrong, must display ["Current config","*All templates in kwal templates starship*"], to be fixed
                    id: templateCombo
                    Layout.fillWidth: true
                    model: starshipModelProxy.paletteNames
                    currentIndex: starshipModelProxy.selectedIndex
                    onCurrentIndexChanged: starshipModelProxy.selectedIndex = currentIndex
                }

                RowLayout {
                    Layout.fillWidth: true

                    TextField {
                        id: customTemplateField
                        Layout.fillWidth: true
                        placeholderText: qsTr("Select your own config")
                        readOnly: true
                        text: {
                            if (!controller || !controller.selectedFile) return ""
                            var f = controller.selectedFile.replace("file://", "")
                            var parts = f.split("/")
                            return parts.length > 1 ? "..." + "/" + parts.slice(parts.length - 2).join("/") : f
                        }
                    }
                    ToolButton {
                        id: openFileButton
                        icon.name: "document-open"
                        Layout.alignment: Qt.AlignRight
                        hoverEnabled: true
                        ToolTip.text: qsTr("Select a custom config")
                        ToolTip.visible: hovered
                        ToolTip.delay: Kirigami.Units.toolTipDelay
                        
                        onClicked: {
                            // if (!controller) return;
                            // controller.openFileDialog();
                            // if (controller.selectedFile) {
                            //     controller.starshipIsFileMode = true; // missing in controller, to be implemented
                            //     //Here logic to read the custom file and update the model
                            // }
                        }
                    }     
                }

                MenuSeparator { Layout.fillWidth: true }

                ScrollView {
                    id: paletteScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true 
                    clip: true

                    ColumnLayout {
                        width: paletteScroll.availableWidth

                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: qsTr("Palette colors"); font.bold: true }
                            Item { Layout.fillWidth: true }
                            ToolButton {
                                icon.name: starshipModelProxy.paletteExpanded ? "arrow-down" : "arrow-right"
                                onClicked: starshipModelProxy.paletteExpanded = !starshipModelProxy.paletteExpanded
                            }
                        }

                        ColumnLayout {
                            id: paletteContent
                            visible: starshipModelProxy.paletteExpanded
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Repeater {
                                model: (starshipModelProxy.selectedIndex >= 0) ? starshipModelProxy.paletteValues[starshipModelProxy.selectedIndex] : []
                                delegate: RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Kirigami.Units.smallSpacing

                                    Label {
                                        id: colorNameLabel
                                        text: (starshipModelProxy.paletteKeys.length > 0) ? starshipModelProxy.paletteKeys[starshipModelProxy.selectedIndex][index] : ""
                                        Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                                        // Layout.maximumWidth: 120
                                        elide: Text.ElideRight
                                    }

                                    Item { Layout.fillWidth: true }

                                    Rectangle {
                                        id: colorValuePreview
                                        width: Kirigami.Units.gridUnit * 1.5
                                        height: Kirigami.Units.gridUnit * 1.5
                                        radius: Kirigami.Units.smallSpacing
                                        color: modelData || "transparent"
                                        border.width: 1
                                        border.color: Kirigami.Theme.disabledTextColor
                                        Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                                        // Bind to controller property
                                        //color: controller ? (controller.starshipDraftColor === "" ? "transparent" : controller.starshipDraftColor) : "transparent"
                                        
                                        ToolTip.text: {
                                            if (!controller) return qsTr("Pick color")
                                            var t = controller.formatColorWithAlpha(colorValuePreview.color)
                                            return t && t !== "" ? t : qsTr("Pick color")
                                        }
                                        ToolTip.delay: Kirigami.Units.toolTipDelay
                                        ToolTip.visible: colorPreviewMouse.containsMouse

                                        MouseArea {
                                            id: colorPreviewMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                if (!controller) return;
                                                //var currentColor = controller.starshipDraftColor;
                                                var currentColor = modelData || "transparent";
                                                var color = controller.openColorDialog(currentColor === "" ? "transparent" : currentColor);
                                                if (color) {
                                                    controller.starshipDraftColor = color;
                                                    
                                                    // Regenerate preview
                                                    if (controller.selectedFile) {
                                                        controller.generateTintedPreview(controller.selectedFile, color);
                                                    } else if (controller.starshipTemplateIndex !== -1 && templateSelector.model) {
                                                        var info = templateSelector.model.get(controller.starshipTemplateIndex);
                                                        if (info && info.fileUrl) {
                                                            controller.generateTintedPreview(info.fileUrl, color);
                                                        }
                                                    }
                                                }
                                            }
                                        }                                        
                                    }

                                    Button {
                                        id: paletteColorButton
                                        icon.name: "color-picker"
                                        Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                                        ToolTip.text: qsTr("Open color palette")
                                        ToolTip.visible: hovered
                                        onClicked: {
                                            starshipModelProxy.editIndex = index
                                            paletteDialog.open()
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                MenuSeparator { Layout.fillWidth: true }

                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        text: qsTr("Apply colors")
                        Layout.fillWidth: true
                        onClicked: { /* ... */ }
                    }
                    Button {
                        text: qsTr("Restore")
                        Layout.fillWidth: true
                        onClicked: { /* ... */ }
                    }
                }
            }
        }
        // --- Right Pane: Previews ---
        Rectangle {
            id: rightPaneStarship
            color: "transparent"
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing
                spacing: Kirigami.Units.largeSpacing
                
                // Top: Current Config Preview
                ColumnLayout {
                    id: previewSectionTop
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    //Layout.preferredHeight: 6

                    Label { text: qsTr("Current (config):"); font.bold: true }
                    // Preview current config
                    Label { text: starshipModelProxy.configFile; font.italic: true }
                
                }
                // Bottom: Selection & Preview
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: Kirigami.Units.smallSpacing
                    //Layout.preferredHeight: 4

                        
                    Label {
                        id: selectedTemplateLabel
                        visible: text !== qsTr("Template:")
                        font.bold: true
                    }
                    // Preview with selected template applied
                    Label {
                        id: withColorsAppliedLabel
                        visible: text !== qsTr("Template with colors:")
                        font.bold: true
                    }                    
                    // Preview with selected template and colors applied            
                }
            }
        }
    }
}