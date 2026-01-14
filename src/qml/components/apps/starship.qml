import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import QtWebEngine
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

        // Preview scaling controls
        property real baseScale: 0.9
        property int previewWidth: 800
        property int previewHeight: 150
        
        property real previewScale: {
            if (!previewCurrentConfig.width || !previewCurrentConfig.height) return baseScale;
            var sw = (previewCurrentConfig.width / previewWidth);
            var sh = (previewCurrentConfig.height / previewHeight);
            return Math.min(sw, sh) * baseScale;
        }
        
        onPreviewScaleChanged: if (model) model.previewScale = previewScale
        onPreviewWidthChanged: if (model) model.previewWidth = previewWidth
        
        onModelChanged: {
            if (model) {
                model.previewScale = previewScale
                model.previewWidth = previewWidth
            }
        }

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

    // Utility: return a safe palette key string or empty string to avoid assigning undefined to QString
    function safePaletteKey(proxy, idx) {
        if (!proxy || !proxy.paletteKeys) return "";
        var pk = proxy.paletteKeys;
        var pi = proxy.paletteIndex;
        if (!(pk && pk.length > 0)) return "";
        if (pi === undefined || pi === null || pi < 0 || pi >= pk.length) return "";
        var inner = pk[pi];
        if (!inner) return "";
        var v = inner[idx];
        return (v === undefined || v === null) ? "" : v;
    }

    Components.DialogPalette {
        id: paletteDialog
        onAccepted: {
            // explicit toString() for safety when passing to Python
            if (selectedColor !== "transparent") {
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
                    ToolTip.text: qsTr("Cancel and return without applying")
                    ToolTip.visible: hovered
                    ToolTip.delay: Kirigami.Units.toolTipDelay
                }
                Button {
                    text: qsTr("Apply")
                    onClicked: {
                        confirmApplyDialog.close()
                        if (controller) controller.applyStarshipConfig()
                    }
                    ToolTip.text: qsTr("Overwrite current starship.toml with the selected configuration")
                    ToolTip.visible: hovered
                    ToolTip.delay: Kirigami.Units.toolTipDelay
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
            Layout.preferredWidth: 250
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
                            ToolTip.visible: hovered
                            ToolTip.delay: Kirigami.Units.toolTipDelay
                            onClicked: { 
                                if (controller) {
                                    controller.starshipClearSelection();
                                    controller.starshipModel.refresh(); 
                                    // Force ComboBox visual update to index 0 (current config)
                                    templateCombo.currentIndex = 0
                                }
                            }
                    }
                }

                ComboBox {
                    id: templateCombo
                    Layout.fillWidth: true
                    textRole: "fileName"

                    // Build a transient model array where the first entry is the
                    // actual starship.toml (if present) followed by all template files.
                    // This ensures ComboBox indices align with the controller's
                    // template indices (index 0 == current config file).
                    model: (function() {
                        var list = [];
                        var cfgPath = (controller && controller.starshipModel && controller.starshipModel.configPath) ? controller.starshipModel.configPath : "";
                        var cfgName = cfgPath ? cfgPath.split("/").pop() : qsTr("No starship.toml");
                        list.push({ fileName: cfgName, filePath: cfgPath, fileUrl: cfgPath ? "file://" + cfgPath : "" });
                        if (controller && controller.starshipTemplateModel) {
                            var tm = controller.starshipTemplateModel;
                            for (var i = 0; i < tm.rowCount(); i++) {
                                var it = tm.get(i);
                                // ensure we provide the same shape
                                list.push({ fileName: it.fileName || "", filePath: it.filePath || "", fileUrl: it.fileUrl || "" });
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
                        // Determine selected entry's filePath from the transient model
                        var entry = (model && model.length > currentIndex) ? model[currentIndex] : null;
                        var selectedPath = entry && entry.filePath ? entry.filePath : "";

                        if (currentIndex === 0) {
                            // User chose the actual config file (index 0)
                            controller.starshipTemplateIndex = -1;
                            // Refresh explicitly using the config path (or default if empty)
                            controller.starshipModel.refresh(selectedPath || undefined);
                        } else {
                            // Template chosen; adjust index mapping (-1 offset)
                            var tmplIdx = currentIndex - 1;
                            controller.starshipTemplateIndex = tmplIdx;
                            // Refresh using the selected template file path
                            controller.starshipModel.refresh(selectedPath || undefined);
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
                            Label {
                                text: qsTr("Palette: " + (starshipModelProxy.paletteIndex >= 0 ? starshipModelProxy.paletteNames[starshipModelProxy.paletteIndex] : ""))
                                font.bold: true
                            }
                            Item { Layout.fillWidth: true }
                            ToolButton {
                                icon.name: starshipModelProxy.paletteExpanded ? "arrow-down" : "arrow-right"
                                onClicked: starshipModelProxy.paletteExpanded = !starshipModelProxy.paletteExpanded
                                ToolTip.text: starshipModelProxy.paletteExpanded ? qsTr("Collapse palettes") : qsTr("Expand palettes")
                                ToolTip.visible: hovered
                                ToolTip.delay: Kirigami.Units.toolTipDelay
                            }
                        }
                        MenuSeparator { Layout.fillWidth: true }

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
                                        text: safePaletteKey(starshipModelProxy, index)
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
                        ToolTip.text: qsTr("Apply selected configuration to your Starship config (starship.toml)")
                        ToolTip.visible: hovered
                        ToolTip.delay: Kirigami.Units.toolTipDelay
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
                        color: "transparent"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 120
                        clip: true
                        
                        WebEngineView {
                            anchors.fill: parent
                            backgroundColor: "transparent"
                            
                            property string contentHtml: (controller && controller.starshipModel) ? controller.starshipModel.currentConfigPreviewHtml : ""
                            onContentHtmlChanged: loadHtml(contentHtml, "file:///")
                            Component.onCompleted: loadHtml(contentHtml, "file:///")
                            
                            settings.javascriptEnabled: false
                            settings.localContentCanAccessFileUrls: true
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
                        Layout.fillWidth: true
                        Layout.maximumWidth: parent ? parent.width : undefined
                        text: {
                            if (!controller) return ""
                            if (controller.starshipIsFileMode) return qsTr("Custom File Mode: "+ controller.selectedFile.replace("file://", ""))
                            if (controller.starshipTemplateIndex >= 0) return qsTr("Template Mode: "+ starshipModelProxy.templateFolder + "/" + controller.starshipTemplateModel.get(controller.starshipTemplateIndex).fileName)
                            if (!controller.hasStarshipConfig) return qsTr("No current starship.toml")
                            return qsTr("Local Config Mode: "+ starshipModelProxy.configFile)
                        }
                        elide: Text.ElideMiddle
                        wrapMode: Text.ElideRight
                    }
                    // Status preview
                    Rectangle {
                        id: previewStatus
                        color: "transparent"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 120
                        clip: true
                        
                        WebEngineView {
                            anchors.fill: parent
                            backgroundColor: "transparent"
                            
                            property string contentHtml: (controller && controller.starshipModel) ? controller.starshipModel.previewHtml : ""
                            onContentHtmlChanged: loadHtml(contentHtml, "file:///")
                            Component.onCompleted: loadHtml(contentHtml, "file:///")
                            
                            settings.javascriptEnabled: false
                            settings.localContentCanAccessFileUrls: true
                        }
                    }
                }
            }
        }
    }
}