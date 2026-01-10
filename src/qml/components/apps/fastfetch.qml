import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import ".." as Components
//import Qt.labs.folderlistmodel

Kirigami.Page {
    id: fastfetchPage
    title: qsTr("Fastfetch Settings")
    
    // Properties
    // Local ephemeral properties derived from controller
    property string sTintedName: ""

    // Controller Helper
    // Safe access to pyController in case it's not injected yet (though it should be)
    readonly property var controller: (typeof pyController !== "undefined") ? pyController : null

    background: Rectangle {
        color: "transparent"
    }

    // Signals Handling
    Connections {
        target: controller
        function onFastfetchApplyResult(success, message) {
            if (controller) {
                controller.resultDialogText = message || (success ? qsTr("Operation completed") : qsTr("Operation failed"));
                controller.resultDialogVisible = true;
            }
        }
    }

    // Initial Setup
    Component.onCompleted: {
        // Initialize config image if needed
        if (controller) {
             // Maybe force a refresh logic if the property is empty?
             // For now relying on bindings.
        }
    }

    // --- Dialogs ---

    // resultDialog moved to main.qml for global access

    Dialog {
        id: confirmDialog
        title: qsTr("Confirm overwrite")
        modal: true
        visible: false
        contentItem: ColumnLayout {
            spacing: Kirigami.Units.smallSpacing
            Label { text: qsTr("A tinted image with that name already exists. Overwrite?") }
            RowLayout {
                Button {
                    text: qsTr("Cancel")
                    onClicked: { confirmDialog.visible = false }
                }
                Button {
                    text: qsTr("Overwrite")
                    onClicked: {
                        confirmDialog.visible = false
                        if (controller) {
                            var started = controller.applyTintedImage(controller.fastfetchDestName);
                            if (!started) {
                                controller.resultDialogText = qsTr("Failed to start apply operation.");
                                controller.resultDialogVisible = true;
                            }
                        }
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

                // Template Selection Header
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
                        ToolTip.text: qsTr("Clear selection")
                        ToolTip.visible: hovered
                        onClicked: {
                            if (controller) {
                                controller.clearSelectedFile(); 
                                controller.fastfetchIsFileMode = false;
                                controller.fastfetchTemplateIndex = -1;
                            }
                        }
                    }              
                }

                // Inputs
                GridLayout {
                    columns: 1
                    Layout.fillWidth: true

                    ComboBox {
                        id: templateSelector
                        Layout.fillWidth: true
                        // Access model directly
                        model: (typeof fastfetchTemplateModel !== "undefined") ? fastfetchTemplateModel : null
                        textRole: "fileName"
                        
                        // Binding to controller
                        currentIndex: controller ? controller.fastfetchTemplateIndex : -1
                        onCurrentIndexChanged: {
                            if (controller && moving && currentIndex !== controller.fastfetchTemplateIndex) {
                                controller.fastfetchTemplateIndex = currentIndex;
                            }
                        }
                        
                        // Simplify enabled check
                        enabled: (controller && !controller.fastfetchIsFileMode) && (model ? model.rowCount() > 0 : false)
                        opacity: enabled ? 1.0 : 0.5

                        displayText: currentIndex === -1 ? qsTr("Select predefined") : currentText
                        ToolTip.text: qsTr("Select a predefined template")
                        ToolTip.visible: hovered
                        
                        onActivated: {
                            if (currentIndex !== -1 && model && controller) {
                                // Sync Index first
                                controller.fastfetchTemplateIndex = currentIndex;
                                
                                var info = model.get(currentIndex);
                                var url = info ? info.fileUrl : "";
                                var tint = controller.fastfetchDraftColor;
                                if (url && tint !== "transparent" && tint !== "") {
                                    controller.generateTintedPreview(url, tint);
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        TextField {
                            id: customTemplateField
                            Layout.fillWidth: true
                            placeholderText: qsTr("Select your own image")
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
                            ToolTip.text: qsTr("Select a custom image")
                            ToolTip.visible: hovered
                            ToolTip.delay: Kirigami.Units.toolTipDelay
                            
                            onClicked: {
                                if (!controller) return;
                                controller.openFileDialog();
                                if (controller.selectedFile) {
                                    controller.fastfetchIsFileMode = true;
                                    var tint = controller.fastfetchDraftColor;
                                    controller.generateTintedPreview(controller.selectedFile, tint);
                                } else {
                                    // kept previous state if cancelled? Or force false?
                                    // Usually dialog cancel returns empty string but doesn't signify "unselect"
                                    // But if clearSelectedFile wasn't called, selectedFile remains.
                                }
                            }
                        }     
                    }
                }

                MenuSeparator { Layout.fillWidth: true }

                // Color Picker
                RowLayout {
                    Layout.fillWidth: true

                    Label {
                        text: qsTr("Tint Color:")
                        Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                    }
                    Item { Layout.fillWidth: true }
                    Rectangle {
                        id: colorPreview
                        Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                        width: Kirigami.Units.gridUnit * 1.5
                        height: Kirigami.Units.gridUnit * 1.5
                        
                        // Bind to controller property
                        color: controller ? (controller.fastfetchDraftColor === "" ? "transparent" : controller.fastfetchDraftColor) : "transparent"
                        
                        border.color: Kirigami.Theme.disabledTextColor
                        border.width: 1
                        radius: Kirigami.Units.smallSpacing
                        
                        ToolTip.text: {
                            if (!controller) return qsTr("Pick color")
                            var t = controller.formatColorWithAlpha(controller.fastfetchDraftColor)
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
                                var currentColor = controller.fastfetchDraftColor;
                                var color = controller.openColorDialog(currentColor === "" ? "transparent" : currentColor);
                                if (color) {
                                    controller.fastfetchDraftColor = color;
                                    
                                    // Regenerate preview
                                    if (controller.selectedFile) {
                                        controller.generateTintedPreview(controller.selectedFile, color);
                                    } else if (controller.fastfetchTemplateIndex !== -1 && templateSelector.model) {
                                        var info = templateSelector.model.get(controller.fastfetchTemplateIndex);
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
                            // Identify current image being previewed
                            var currentImg = "";
                            if (controller.selectedFile && controller.selectedFile !== "") {
                                currentImg = controller.selectedFile;
                            } else if (controller.fastfetchConfigImage && controller.fastfetchConfigImage !== "") {
                                currentImg = controller.fastfetchConfigImage.replace("file://", "");
                            }
                            
                            paletteDialog.sourceImage = currentImg;
                            paletteDialog.open();
                        }                                                   
                    }
                }

                Item { Layout.fillHeight: true }

                // Action Buttons
                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        id: applyTintedButton
                        text: qsTr("Apply tinted")
                        Layout.fillWidth: true
                        ToolTip.text: qsTr("Apply the tinted image to fastfetch config")
                        ToolTip.visible: hovered
                        enabled: controller && controller.fastfetchDestName && controller.fastfetchDestName !== ""
                        
                        onClicked: {
                            if (!controller) return;
                            
                            if (!controller.fastfetchDestName || controller.fastfetchDestName === "") {
                                controller.resultDialogText = qsTr("No destination filename available.");
                                controller.resultDialogVisible = true;
                                return;
                            }
                            
                            if (controller.fastfetchDestinationExists(controller.fastfetchDestName)) {
                                confirmDialog.visible = true;
                            } else {
                                var started = controller.applyTintedImage(controller.fastfetchDestName);
                                if (!started) {
                                    controller.resultDialogText = qsTr("Failed to start apply operation. Check filename.");
                                    controller.resultDialogVisible = true;
                                }
                            }
                        }
                    }
                    Button {
                        id: restoreBackupButton
                        text: qsTr("Restore backup")
                        Layout.fillWidth: true
                        enabled: controller && controller.hasFastfetchBackup
                        ToolTip.text: (controller && controller.hasFastfetchBackup) ? qsTr("Restore the fastfetch config from the last backup") : qsTr("No backup available to restore")
                        ToolTip.visible: hovered
                        
                        onClicked: {
                            if (!controller) return;
                            var res = controller.restoreFastfetchBackup();
                            if (res) {
                                controller.resultDialogText = res.message || (res.success ? qsTr("Restore succeeded") : qsTr("Restore failed"));
                            } else {
                                controller.resultDialogText = qsTr("Restore failed: no response from controller");
                            }
                            controller.resultDialogVisible = true;
                        }
                    }
                }
            }
        }

        // --- Right Pane: Previews ---
        Rectangle {
            id: rightPaneFastfetch
            color: "transparent"
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing
                spacing: Kirigami.Units.largeSpacing

                // Top: Current Config Image
                ColumnLayout {
                    id: previewSectionTop
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: 6

                    Label { text: qsTr("Current (config):"); font.bold: true }

                    Image {
                        id: fastfetchCurrentImage
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        fillMode: Image.PreserveAspectFit
                        asynchronous: true
                        
                        // Cleaner binding: property access preferred, immediate fallback handled by property value
                        source: (controller && controller.fastfetchConfigImage !== "") 
                                ? controller.fastfetchConfigImage 
                                : "" 
                        
                        // If no image is set via property yet, we could trigger a refresh on loading,
                        // but logic is better handled in controller init.
                    }
                    Label {
                        id: noCurrentImageLabel
                        text: qsTr("No configured image")
                        visible: fastfetchCurrentImage.source === ""
                        color: Kirigami.Theme.disabledTextColor
                    }
                }
                
                // Bottom: Selection & Preview
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: Kirigami.Units.smallSpacing
                    Layout.preferredHeight: 4
                    visible: controller ? (controller.fastfetchIsFileMode || controller.fastfetchTemplateIndex !== -1) : false

                    GridLayout {
                        columns: 2
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        
                        Label {
                            id: selectedTemplateLabel
                            visible: text !== qsTr("Template:")
                            font.bold: true
                            
                            // Logic to compute names and side-effect update controller
                            text: {
                                if (!controller) return qsTr("Template:");
                                
                                let name = "";
                                if (controller.fastfetchIsFileMode) {
                                    name = controller.selectedFile ? controller.selectedFile.split("/").pop() : "";
                                } else {
                                    // Using templateSelector.currentText directly works, but cleaner to use model+index
                                    // However, currentText is convenient.
                                    name = templateSelector.currentIndex !== -1 ? templateSelector.currentText : "";
                                }
                                
                                if (name !== "") {
                                    var dst = name.replace(/\.[^/.]+$/, "") + "-tinted.png"; // safer replace extension
                                    fastfetchPage.sTintedName = dst;
                                    if (controller.fastfetchDestName !== dst) {
                                        controller.fastfetchDestName = dst;
                                    }
                                } else {
                                    fastfetchPage.sTintedName = "";
                                    controller.fastfetchDestName = "";
                                }
                                
                                return name !== "" ? qsTr("Template: %1").arg(name) : qsTr("Template:");
                            }
                        }
                        
                        Label {
                            id: tintedLabel
                            font.bold: true
                            visible: text !== qsTr("Tinted:")
                            text: fastfetchPage.sTintedName !== "" ? qsTr("Tinted: %1").arg(fastfetchPage.sTintedName) : qsTr("Tinted:")
                        }

                        // Left cell: Original Template Preview
                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Image {
                                id: fastfetchPreviewTemplate
                                anchors.fill: parent
                                fillMode: Image.PreserveAspectFit
                                source: {
                                    if (!controller) return "";
                                    if (controller.fastfetchIsFileMode && controller.selectedFile) return controller.selectedFile;
                                    
                                    if (!controller.fastfetchIsFileMode && templateSelector.currentIndex !== -1 && templateSelector.model) {
                                        var info = templateSelector.model.get(templateSelector.currentIndex);
                                        return info ? info.fileUrl : "";
                                    }
                                    return "";
                                }
                            }
                        }

                        // Right cell: Tinted Preview
                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            Image {
                                id: fastfetchPreviewTinted
                                anchors.fill: parent
                                fillMode: Image.PreserveAspectFit
                                cache: false
                                
                                // Source Logic: Tinted -> Selected File -> Template -> Empty
                                source: {
                                    if (controller && controller.fastfetchTintedPreview && controller.fastfetchTintedPreview !== "")
                                        return controller.fastfetchTintedPreview;
                                        
                                    // Fallback to original if no tint available
                                    return fastfetchPreviewTemplate.source;
                                }
                            }

                            BusyIndicator {
                                anchors.centerIn: parent
                                running: controller ? controller.fastfetchTinting : false
                                visible: running
                            }
                        }
                    }
                }
            }
        }
    }

    Components.DialogPalette {
        id: paletteDialog
        onAccepted: {
            if (selectedColor != "transparent") {
                controller.fastfetchDraftColor = selectedColor
                
                // Refresh preview logic same as color picker
                if (controller.selectedFile) {
                    controller.generateTintedPreview(controller.selectedFile, selectedColor);
                } else if (controller.fastfetchTemplateIndex !== -1 && templateSelector.model) {
                    var info = templateSelector.model.get(controller.fastfetchTemplateIndex);
                    if (info && info.fileUrl) {
                        controller.generateTintedPreview(info.fileUrl, selectedColor);
                    }
                }
            }
        }
    }
}
