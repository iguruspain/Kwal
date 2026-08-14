pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import ".." as Components
//import Qt.labs.folderlistmodel

Kirigami.Page {
    id: fastfetchPage
    title: qsTr("Fastfetch Settings")

    background: Rectangle {
        color: "transparent"
    }

    TextEdit {
        id: clipboardHelper
        visible: false
        function copyToClipboard(text) {
            clipboardHelper.text = text
            clipboardHelper.selectAll()
            clipboardHelper.copy()
            root.notifyClipboard(text)
        }
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

    // Refresh config image when tab becomes visible (to catch external changes)
    onVisibleChanged: {
        if (visible && controller) {
            controller.refreshFastfetchConfigImage();
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
            Label { text: qsTr("A tinted image already exists next to the selected file. Overwrite?") }
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
                            var started = controller.applyTintedImage();
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
            //color: Kirigami.Theme.backgroundColor
            color: Qt.alpha(Kirigami.Theme.backgroundColor, 0.80)
            Layout.preferredWidth: 300
            Layout.fillHeight: true
            radius: Kirigami.Units.largeSpacing
            border.color: Kirigami.Theme.highlightColor
            border.width: 1
       
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.largeSpacing

                Label {
                    text: qsTr("Settings")
                    font.bold: true
                    Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                }

                MenuSeparator { Layout.fillWidth: true }

                // Image Selection Header
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing
                    Label {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                        text: qsTr("Select an image")
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
                            }
                        }
                    }
                }

                // Image Selector
                RowLayout {
                    Layout.fillWidth: true

                    TextField {
                        id: imageField
                        Layout.fillWidth: true
                        placeholderText: qsTr("No image selected")
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
                        ToolTip.text: qsTr("Select an image")
                        ToolTip.visible: hovered
                        ToolTip.delay: Kirigami.Units.toolTipDelay

                        onClicked: {
                            if (!controller) return;
                            controller.openFileDialog();
                            if (controller.selectedFile) {
                                var tint = controller.fastfetchDraftColor;
                                if (tint && tint !== "transparent" && tint !== "") {
                                    controller.generateTintedPreview(controller.selectedFile, tint);
                                }
                            }
                        }
                    }
                }

                Kirigami.Separator { Layout.fillWidth: true; color: Kirigami.Theme.alternateBackgroundColor }

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
                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                            onClicked: (mouse) => {
                                if (mouse.button === Qt.RightButton) {
                                    clipboardHelper.copyToClipboard(controller ? controller.fastfetchDraftColor : colorPreview.color.toString())
                                    return
                                }
                                if (!controller) return;
                                var currentColor = controller.fastfetchDraftColor;
                                var color = controller.openColorDialog(currentColor === "" ? "transparent" : currentColor);
                                if (color) {
                                    controller.fastfetchDraftColor = color;

                                    // Regenerate preview if image is selected
                                    if (controller.selectedFile) {
                                        controller.generateTintedPreview(controller.selectedFile, color);
                                    }
                                }
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }
                MenuSeparator { Layout.fillWidth: true }

                // Action Buttons
                RowLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignHCenter
                    spacing: Kirigami.Units.largeSpacing

                    ToolButton {
                        id: applyTintedButton
                        icon.name: "dialog-ok-apply"
                        ToolTip.text: qsTr("Apply the tinted image to fastfetch config")
                        ToolTip.visible: hovered
                        ToolTip.delay: Kirigami.Units.toolTipDelay
                        enabled: controller && controller.selectedFile && controller.selectedFile !== ""

                        onClicked: {
                            if (!controller) return;

                            if (!controller.selectedFile || controller.selectedFile === "") {
                                controller.resultDialogText = qsTr("No image selected.");
                                controller.resultDialogVisible = true;
                                return;
                            }

                            if (controller.fastfetchTintedExists()) {
                                confirmDialog.visible = true;
                            } else {
                                var started = controller.applyTintedImage();
                                if (!started) {
                                    controller.resultDialogText = qsTr("Failed to start apply operation.");
                                    controller.resultDialogVisible = true;
                                }
                            }
                        }
                    }
                    ToolButton {
                        id: applyOriginalButton
                        icon.name: "document-save"
                        ToolTip.text: qsTr("Apply the selected image directly to fastfetch config (no tint)")
                        ToolTip.visible: hovered
                        ToolTip.delay: Kirigami.Units.toolTipDelay
                        enabled: controller && controller.selectedFile && controller.selectedFile !== ""

                        onClicked: {
                            if (!controller) return;

                            if (!controller.selectedFile || controller.selectedFile === "") {
                                controller.resultDialogText = qsTr("No image selected.");
                                controller.resultDialogVisible = true;
                                return;
                            }

                            var started = controller.applyOriginalImage();
                            if (!started) {
                                controller.resultDialogText = qsTr("Failed to start apply operation.");
                                controller.resultDialogVisible = true;
                            }
                        }
                    }
                    ToolButton {
                        id: restoreBackupButton
                        icon.name: "document-revert"
                        ToolTip.text: (controller && controller.hasFastfetchBackup) ? qsTr("Restore the fastfetch config from the last backup") : qsTr("No backup available to restore")
                        ToolTip.visible: hovered
                        ToolTip.delay: Kirigami.Units.toolTipDelay
                        enabled: controller && controller.hasFastfetchBackup

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
                anchors.margins: Kirigami.Units.largeSpacing
                spacing: Kirigami.Units.largeSpacing

                // Top: Current Config Image
                ColumnLayout {
                    id: previewSectionTop
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Label { text: qsTr("Current (config):"); font.bold: true }
                    // Preview current image path in fastfetch config (clean path, no file:// or ?t=)
                    Label {
                        id: currentConfigPathLabel
                        text: (controller && controller.fastfetchConfigImagePath !== "")
                             ? controller.fastfetchConfigImagePath
                             : qsTr("No image found")
                        font.italic: true
                        wrapMode: Text.WrapAnywhere
                        Layout.fillWidth: true
                    }

                    Image {
                        id: fastfetchCurrentImage
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        fillMode: Image.PreserveAspectFit
                        asynchronous: true
                        cache: false
                        
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
                    id: previewSectionBottom
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: Kirigami.Units.smallSpacing
                    visible: controller ? (controller.selectedFile && controller.selectedFile !== "") : false

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: Kirigami.Units.largeSpacing

                        // Left column: Original Image
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumWidth: 200
                            spacing: Kirigami.Units.smallSpacing

                            Label {
                                text: qsTr("Selected image:")
                                font.bold: true
                            }
                            Label {
                                id: selectedImagePathLabel
                                font.italic: true
                                wrapMode: Text.WrapAnywhere
                                Layout.fillWidth: true
                                text: {
                                    if (!controller || !controller.selectedFile) return ""
                                    var f = controller.selectedFile.replace("file://", "")
                                    //var parts = f.split("/")
                                    //return qsTr("Image: %1").arg(parts[parts.length - 1])
                                    return qsTr("%1").arg(f)
                                }
                            }

                            Rectangle {
                                id: originalPreviewContainer
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.minimumHeight: 200
                                color: "transparent" //Kirigami.Theme.backgroundColor
                                radius: Kirigami.Units.smallSpacing
                                //border.color: Kirigami.Theme.disabledTextColor
                                //border.width: 1

                                Image {
                                    id: fastfetchPreviewOriginal
                                    anchors.fill: parent
                                    anchors.margins: Kirigami.Units.smallSpacing
                                    fillMode: Image.PreserveAspectFit
                                    asynchronous: true
                                    cache: false
                                    source: controller ? controller.selectedFile : ""
                                }

                                Label {
                                    anchors.centerIn: parent
                                    text: qsTr("Loading...")
                                    color: Kirigami.Theme.disabledTextColor
                                    visible: fastfetchPreviewOriginal.status === Image.Loading
                                }
                            }
                        }

                        // Right column: Tinted Preview
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumWidth: 200
                            spacing: Kirigami.Units.smallSpacing

                            Label {
                                font.bold: true
                                text: qsTr("Tinted:")
                            }
                            Label {
                                id: tintedImagePathLabel
                                font.italic: true
                                wrapMode: Text.WrapAnywhere
                                Layout.fillWidth: true
                                text: {
                                    if (!controller || !controller.selectedFile) return ""
                                    var f = controller.selectedFile.replace("file://", "")
                                    var parts = f.split("/")
                                    var tintedName = parts[parts.length - 1].replace(/\.(png|jpg|jpeg|bmp|webp)$/i, "-tinted.$1")
                                    return qsTr("%1").arg(f.replace(parts[parts.length - 1], tintedName))
                                }
                            }

                            Rectangle {
                                id: tintedPreviewContainer
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.minimumHeight: 200
                                color: "transparent" //Kirigami.Theme.backgroundColor
                                radius: Kirigami.Units.smallSpacing
                                //border.color: Kirigami.Theme.disabledTextColor
                                //border.width: 1

                                Image {
                                    id: fastfetchPreviewTinted
                                    anchors.fill: parent
                                    anchors.margins: Kirigami.Units.smallSpacing
                                    fillMode: Image.PreserveAspectFit
                                    asynchronous: true
                                    cache: false

                                    source: {
                                        if (controller && controller.fastfetchTintedPreview && controller.fastfetchTintedPreview !== "")
                                            return controller.fastfetchTintedPreview;
                                        return fastfetchPreviewOriginal.source;
                                    }
                                }

                                BusyIndicator {
                                    anchors.centerIn: parent
                                    running: controller ? controller.fastfetchTinting : false
                                    visible: running
                                }

                                Label {
                                    anchors.centerIn: parent
                                    text: qsTr("Loading...")
                                    color: Kirigami.Theme.disabledTextColor
                                    visible: fastfetchPreviewTinted.status === Image.Loading && !(controller && controller.fastfetchTinting)
                                }
                            }
                        }
                    }
                }
            }
        }
    }


}
