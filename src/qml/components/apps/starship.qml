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
        property var model: (controller && controller.starshipModel) ? controller.starshipModel : null
        // Index of the palette within the current file to display/edit
        property int paletteIndex: -1
        
        property string configFile: model ? model.configPath : ""
        property string templateFolder: model ? model.templateFolder : ""
        
        property var paletteNames: model ? model.paletteNames : []
        property var paletteValues: model ? model.paletteValues : []
        property var paletteKeys: model ? model.paletteKeys : []
        property bool paletteExpanded: true
        // Editing context for palette dialog
        property int editIndex: -1

        Component.onCompleted: {
            if (model && model.paletteNames && model.paletteNames.length > 0) paletteIndex = 0
        }

        // Update derived properties when local `paletteNames` changes
        onPaletteNamesChanged: {
            if (paletteNames && paletteNames.length > 0) paletteIndex = 0
            else paletteIndex = -1
        }
        onPaletteIndexChanged: {
            if (model && paletteIndex >= 0) {
                try {
                    model.setPreviewPaletteIndex(paletteIndex)
                } catch (e) {}
            }
        }
    }

    // Controller helper like in fastfetch.qml
    readonly property var controller: (typeof pyController !== "undefined") ? pyController : null

    Components.DialogPalette {
        id: paletteDialog
        onAccepted: {
            // explicit toString() for safety when passing to Python
            if (selectedColor != "transparent") {
                // If we have an edit index set, write back using Controller
                if (starshipModelProxy.paletteIndex >= 0 && starshipModelProxy.editIndex >= 0 && controller) {
                    controller.starshipModel.setPaletteColor(starshipModelProxy.paletteIndex, starshipModelProxy.editIndex, selectedColor.toString())
                }
            }
        }
    }

    Dialog {
        id: confirmApplyDialog
        title: qsTr("Confirm overwrite")
        modal: true
        visible: false
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        
        contentItem: ColumnLayout {
            spacing: Kirigami.Units.smallSpacing
            Label { 
                text: {
                    if (!controller) return ""
                    if (controller.hasStarshipConfig) {
                        return qsTr("This will overwrite your current ~/.config/starship.toml configuration.\nAn automatic backup will be created.\n\nContinue?") 
                    } else {
                        return qsTr("No existing configuration found.\nA new ~/.config/starship.toml will be created from your selection.\n\nContinue?")
                    }
                }
                wrapMode: Text.WordWrap
                Layout.maximumWidth: 400
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button {
                    text: qsTr("Cancel")
                    onClicked: { confirmApplyDialog.close() }
                }
                Button {
                    text: qsTr("Apply")
                    onClicked: {
                        confirmApplyDialog.close()
                        if (controller) controller.applyStarshipConfig()
                    }
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
                            ToolTip.text: qsTr("Reset to current config")
                            onClicked: { 
                                if (controller) {
                                    controller.starshipClearSelection();
                                    controller.starshipModel.refresh(); 
                                }
                            }
                    }
                }

                ComboBox {
                    id: templateCombo
                    Layout.fillWidth: true
                    textRole: "fileName"

                    // Build a transient model array where index 0 = Current Config (or "No current config")
                    model: (function() {
                        var list = [];
                        list.push({ fileName: (controller && controller.hasStarshipConfig) ? qsTr("Current Config") : qsTr("No current config"), filePath: "" });
                        if (controller && controller.starshipTemplateModel) {
                            var tm = controller.starshipTemplateModel;
                            for (var i = 0; i < tm.rowCount(); i++) {
                                var it = tm.get(i);
                                // ensure we provide the same shape
                                list.push({ fileName: it.fileName || "", filePath: it.filePath || "" });
                            }
                        }
                        return list;
                    })()

                    // Map controller index (-1 = current config) to combo index (0 = current config)
                    currentIndex: controller ? (controller.starshipTemplateIndex >= 0 ? controller.starshipTemplateIndex + 1 : 0) : 0

                    // Keep original enabled logic based on template model availability
                    enabled: (controller && !controller.starshipIsFileMode) && (controller && controller.starshipTemplateModel ? controller.starshipTemplateModel.rowCount() > 0 : false)
                    opacity: enabled ? 1.0 : 0.5

                    onActivated: {
                        if (!controller) return;
                        controller.starshipIsFileMode = false;
                        controller.clearSelectedFile();

                        if (currentIndex === 0) {
                            // User chose Current Config
                            controller.starshipTemplateIndex = -1;
                            controller.starshipModel.refresh();
                        } else {
                            // Template chosen; adjust index mapping (-1 offset)
                            var tmplIdx = currentIndex - 1;
                            controller.starshipTemplateIndex = tmplIdx;
                            var info = controller.starshipTemplateModel.get(tmplIdx);
                            if (info) controller.starshipModel.refresh(info.filePath);
                        }
                    }

                    Component.onCompleted: {
                        if (!controller) return;
                        // Restore state: if a template was selected, refresh it; otherwise refresh current config
                        if (controller.starshipTemplateIndex >= 0) {
                            var ci = controller.starshipTemplateIndex + 1;
                            currentIndex = ci;
                            var info = controller.starshipTemplateModel.get(controller.starshipTemplateIndex);
                            if (info) controller.starshipModel.refresh(info.filePath);
                        } else {
                            currentIndex = 0;
                            controller.starshipModel.refresh();
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true

                    TextField {
                        id: customTemplateField
                        Layout.fillWidth: true
                        placeholderText: qsTr("Select your own template")
                        readOnly: true
                        text: {
                            if (!controller) return ""
                            if (controller.starshipIsFileMode && controller.selectedFile) {
                                var f = controller.selectedFile.replace("file://", "")
                                var parts = f.split("/")
                                return parts.length > 1 ? "..." + "/" + parts.slice(parts.length - 2).join("/") : f
                            }
                            return ""
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
                            if (!controller) return;
                            controller.openFileDialog();
                            if (controller.selectedFile) {
                                controller.starshipIsFileMode = true; 
                                controller.starshipTemplateIndex = -1;
                                var f = controller.selectedFile.replace("file://", "");
                                controller.starshipModel.refresh(f);
                            }
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
                                id: paletteColorRepeater
                                model: (starshipModelProxy.paletteIndex >= 0) ? starshipModelProxy.paletteValues[starshipModelProxy.paletteIndex] : []
                                delegate: RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Kirigami.Units.smallSpacing

                                    Label {
                                        id: colorNameLabel
                                        text: (starshipModelProxy.paletteKeys.length > 0 && starshipModelProxy.paletteIndex < starshipModelProxy.paletteKeys.length) ? starshipModelProxy.paletteKeys[starshipModelProxy.paletteIndex][index] : ""
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
                                                var currentColor = modelData || "transparent";
                                                var color = controller.openColorDialog(currentColor === "" ? "transparent" : currentColor);
                                                if (color) {
                                                    controller.starshipModel.setPaletteColor(starshipModelProxy.paletteIndex, index, color)
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
                                            // Reset selection state in dialog to prevent stale values
                                            paletteDialog.selectedColor = "transparent"
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
                        id: applyButton
                        text: qsTr("Apply Config")
                        Layout.fillWidth: true
                        onClicked: { 
                            if (controller) confirmApplyDialog.open()
                        }
                    }
                    Button {
                        text: qsTr("Restore Backup")
                        Layout.fillWidth: true
                        enabled: controller && controller.hasStarshipBackup
                        ToolTip.text: (enabled) ? qsTr("Restore starship config from backup") : qsTr("No backup available")
                        ToolTip.visible: hovered
                        onClicked: {
                             if (controller) {
                                controller.restoreStarshipBackup();
                                controller.starshipModel.refresh(); 
                             }
                        }
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
                    
                    Label { text: qsTr("Starship config file:"); font.bold: true }
                    // Preview current config path
                    Label {
                        id: currentConfigPathLabel 
                        text: (controller && controller.hasStarshipConfig) ? starshipModelProxy.configFile : qsTr("No starship.toml found")
                        font.italic: true 
                        wrapMode: Text.WrapAnywhere
                        Layout.fillWidth: true
                    }
                    // Preview rendering
                    Rectangle {
                        id: previewCurrentConfig
                        Kirigami.Theme.colorSet: Kirigami.Theme.View
                        color: (typeof Kirigami.Theme.backgroundColor !== 'undefined') ? Kirigami.Theme.backgroundColor : "transparent"
                        border.width: 1
                        border.color: (typeof Kirigami.Theme.primaryColor !== 'undefined') ? Kirigami.Theme.primaryColor : "transparent"
                        radius: Kirigami.Units.smallSpacing
                        Layout.fillWidth: true
                        Layout.preferredHeight: 36
                        Text {
                            anchors.fill: parent
                            anchors.margins: Kirigami.Units.smallSpacing
                            textFormat: Text.RichText
                            elide: Text.ElideRight
                            font.pointSize: 9
                            text: (controller && controller.starshipModel) ? controller.starshipModel.currentConfigPreviewHtml : ""
                            wrapMode: Text.WordWrap
                        }
                    }
                
                }
                // Bottom: Selection Status
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Label {
                        id: statusLabel
                        text: qsTr("Status:")
                        font.bold: true
                    }
                    
                    Label {
                        id: statusModeLabel
                        text: {
                            if (!controller) return ""
                            if (controller.starshipIsFileMode) return qsTr("Custom File Mode")
                            if (controller.starshipTemplateIndex >= 0) return qsTr("Template Mode")
                            if (!controller.hasStarshipConfig) return qsTr("No current starship.toml")
                            return qsTr("Current Config Mode")
                        }
                    }
                    // Status preview
                    Rectangle {
                        id: previewStatus
                        Kirigami.Theme.colorSet: Kirigami.Theme.View
                        color: (typeof Kirigami.Theme.backgroundColor !== 'undefined') ? Kirigami.Theme.backgroundColor : "transparent"
                        border.width: 1
                        border.color: (typeof Kirigami.Theme.primaryColor !== 'undefined') ? Kirigami.Theme.primaryColor : "transparent"
                        radius: Kirigami.Units.smallSpacing
                        Layout.fillWidth: true
                        Layout.preferredHeight: 36
                        Text {
                            anchors.fill: parent
                            anchors.margins: Kirigami.Units.smallSpacing
                            textFormat: Text.RichText
                            elide: Text.ElideRight
                            font.pointSize: 9
                            text: (controller && controller.starshipModel) ? controller.starshipModel.previewHtml : ""
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
    }
}