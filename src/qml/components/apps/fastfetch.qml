import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import Qt.labs.folderlistmodel

Kirigami.Page {
    id: fastfetchPage
    title: qsTr("Fastfetch Settings")
    property bool isFileSelected: false
    property string sTintedName: ""
    property string selectedTintColor: "transparent"

    background: Rectangle {
        color: "transparent"
    }

    Dialog {
        id: resultDialog
        visible: (typeof pyController !== "undefined") ? pyController.resultDialogVisible : false
        modal: true
        title: qsTr("Fastfetch")
        onVisibleChanged: {
            if (!visible && typeof pyController !== "undefined") pyController.resultDialogVisible = false;
        }
        contentItem: Label {
            text: (typeof pyController !== "undefined") ? pyController.resultDialogText : ""
            wrapMode: Text.WordWrap
            leftPadding: Kirigami.Units.smallSpacing
            rightPadding: Kirigami.Units.smallSpacing
        }
    }
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
                        var started = pyController.applyTintedImage(pyController.fastfetchDestName);
                        if (!started) {
                            pyController.resultDialogText = qsTr("Failed to start apply operation.");
                            pyController.resultDialogVisible = true;
                        }
                    }
                }
            }
        }
    }
    Component.onCompleted: {
        // Listen for background result signal from controller (guarded)
        var ctrl = (typeof pyController !== "undefined") ? pyController : null;
        if (ctrl && ctrl.fastfetchApplyResult) {
            ctrl.fastfetchApplyResult.connect(function(success, message) {
                ctrl.resultDialogText = message || (success ? qsTr("Operation completed") : qsTr("Operation failed"));
                ctrl.resultDialogVisible = true;
            })
        }
    }

    // Data provided by Python model/controller (FastfetchTemplateModel)
    // The `pyController.fastfetchTemplateModel` is a QAbstractListModel exposed from Python.

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
                        ToolTip.text: qsTr("Clear selection")
                        ToolTip.visible: hovered
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
                        model: fastfetchTemplateModel
                        textRole: "fileName"
                        enabled: !fastfetchPage.isFileSelected && (typeof fastfetchTemplateModel.rowCount === 'function' ? fastfetchTemplateModel.rowCount() > 0 : true)
                        opacity: enabled ? 1.0 : 0.5

                        currentIndex: -1
                        displayText: currentIndex === -1 ? qsTr("Select predefined") : currentText
                        ToolTip.text: qsTr("Select a predefined template")
                        ToolTip.visible: hovered
                        onActivated: {
                            // generate tinted preview for chosen template
                            if (currentIndex !== -1) {
                                var info = fastfetchTemplateModel.get(currentIndex);
                                var url = info ? info.fileUrl : "";
                                if (url && fastfetchPage.selectedTintColor !== "transparent" && fastfetchPage.selectedTintColor !== "") pyController.generateTintedPreview(url, fastfetchPage.selectedTintColor);
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
                                    pyController.generateTintedPreview(pyController.selectedFile, fastfetchPage.selectedTintColor);
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
                MenuSeparator { Layout.fillWidth: true }
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
                            color: fastfetchPage.selectedTintColor
                        border.color: Kirigami.Theme.disabledTextColor
                        border.width: 1
                        radius: Kirigami.Units.smallSpacing
                            ToolTip.text: qsTr("Pick tint color")
                            ToolTip.visible: hovered
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                var color = pyController.openColorDialog(colorPreview.color);
                                if (color) {
                                    fastfetchPage.selectedTintColor = color;
                                    // regenerate tinted preview for current selection
                                    if (pyController.selectedFile) {
                                        pyController.generateTintedPreview(pyController.selectedFile, fastfetchPage.selectedTintColor);
                                    } else if (templateSelector.currentIndex !== -1) {
                                        var info = fastfetchTemplateModel.get(templateSelector.currentIndex);
                                        if (info && info.fileUrl) pyController.generateTintedPreview(info.fileUrl, fastfetchPage.selectedTintColor);
                                    }
                                }
                            }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        id: applyTintedButton
                        text: qsTr("Apply tinted")
                        Layout.fillWidth: true
                        ToolTip.text: qsTr("Apply the tinted image to fastfetch config")
                        ToolTip.visible: hovered
                        enabled: pyController.fastfetchDestName && pyController.fastfetchDestName !== ""
                        onClicked: {
                            console.log("Apply Tinted Image clicked");
                            if (!pyController.fastfetchDestName || pyController.fastfetchDestName === "") {
                                pyController.resultDialogText = qsTr("No destination filename available.");
                                pyController.resultDialogVisible = true;
                                return;
                            }
                            var exists = pyController.fastfetchDestinationExists(pyController.fastfetchDestName);
                            if (exists) {
                                // ask user for confirmation before overwrite
                                confirmDialog.visible = true;
                            } else {
                                var started = pyController.applyTintedImage(pyController.fastfetchDestName);
                                if (!started) {
                                    pyController.resultDialogText = qsTr("Failed to start apply operation. Make sure a tinted preview exists and filename is valid.");
                                    pyController.resultDialogVisible = true;
                                }
                            }
                        }
                    }
                    Button {
                        id: restoreBackupButton
                        text: qsTr("Restore backup")
                        Layout.fillWidth: true
                        enabled: pyController.hasFastfetchBackup
                        ToolTip.text: pyController.hasFastfetchBackup ? qsTr("Restore the fastfetch config from the last backup") : qsTr("No backup available to restore")
                        ToolTip.visible: hovered
                        onClicked: {
                            console.log("Restore Backup clicked");
                            var res = pyController.restoreFastfetchBackup();
                            if (res) {
                                pyController.resultDialogText = res.message || (res.success ? qsTr("Restore succeeded") : qsTr("Restore failed"));
                            } else {
                                pyController.resultDialogText = qsTr("Restore failed: no response from controller");
                            }
                            pyController.resultDialogVisible = true;
                        }
                    }
                }
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
                    Layout.preferredHeight: 6

                    Label { text: qsTr("Current (config):"); font.bold: true }

                    Image {
                        id: fastfetchCurrentImage
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        source: pyController.fastfetchConfigImage !== "" ? pyController.fastfetchConfigImage : (function() {
                            var info = pyController.getFastfetchInfo();
                            return (info && info.config_image) ? ("file://" + info.config_image) : "";
                        })()
                        fillMode: Image.PreserveAspectFit
                        asynchronous: true
                    }
                    Label {
                        id: noCurrentImageLabel
                        text: qsTr("No configured image")
                        visible: fastfetchCurrentImage.source === ""
                        color: Kirigami.Theme.disabledTextColor
                    }
                }
                
                // Preview Section bottom
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: Kirigami.Units.smallSpacing
                    Layout.preferredHeight: 4

                    GridLayout {
                        columns: 2
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Label {
                            id: selectedTemplateLabel
                            text: {
                                    let name = "";
                                    if (fastfetchPage.isFileSelected) {
                                        name = pyController.selectedFile ? pyController.selectedFile.split("/").pop() : "";
                                    } else {
                                        name = templateSelector.currentIndex !== -1 ? templateSelector.currentText : "";
                                    }
                                    if (name !== "") {
                                        var dst = name.replace(".", "-tinted.");
                                        // keep a page-local copy for display
                                        fastfetchPage.sTintedName = dst;
                                        // also set controller's destination name so Apply uses it
                                        pyController.fastfetchDestName = dst;
                                    } else {
                                        fastfetchPage.sTintedName = "";
                                        pyController.fastfetchDestName = "";
                                    }
                                    
                                    return name !== "" ? qsTr("Template: %1").arg(name) : qsTr("Template:");
                                }
                            visible: text !== qsTr("Template:")
                            font.bold: true
                        }
                        Label {
                            id: tintedLabel
                            text: {
                                let name = fastfetchPage.sTintedName;
                                return name !== "" ? qsTr("Tinted: %1").arg(name) : qsTr("Tinted:");
                            } // Placeholder
                            font.bold: true
                            visible: text !== qsTr("Tinted:")
                        }
                        // Left cell: template preview
                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Image {
                                id: fastfetchPreviewTemplate
                                anchors.fill: parent
                                source: {
                                    if (pyController.selectedFile) {
                                        return pyController.selectedFile;
                                    }
                                    if (templateSelector.currentIndex !== -1) {
                                        var info = fastfetchTemplateModel.get(templateSelector.currentIndex);
                                        return info ? info.fileUrl : "";
                                    }
                                    return "";
                                }
                                fillMode: Image.PreserveAspectFit
                            }
                        }

                        // Right cell: tinted preview (falls back to template preview when no tinted image)
                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            Image {
                                id: fastfetchPreviewTinted
                                anchors.fill: parent
                                source: (pyController.fastfetchTintedPreview && pyController.fastfetchTintedPreview !== "") ? pyController.fastfetchTintedPreview : (pyController.selectedFile ? pyController.selectedFile : (templateSelector.currentIndex !== -1 ? (fastfetchTemplateModel.get(templateSelector.currentIndex).fileUrl) : ""))
                                fillMode: Image.PreserveAspectFit
                                cache: false
                            }

                            BusyIndicator {
                                Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
                                running: pyController.fastfetchTinting
                                visible: pyController.fastfetchTinting
                            }
                        }
                    }
                }
            }
        }
    }
}