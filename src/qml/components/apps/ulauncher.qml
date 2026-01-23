import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import QtWebEngine
import ".." as Components

Kirigami.Page {
    id: ulauncherPage
    title: qsTr("Ulauncher Settings")

    background: Rectangle {
        color: "transparent"
    }

    // Proxy to Python Ulauncher model
    Item {
        id: ulauncherModelProxy
        property var model: (controller && controller.ulauncherModel) ? controller.ulauncherModel : null
        
        property string configPath: model ? model.configPath : ""
        property string templateFolder: model ? model.templateFolder : ""
        
        property var paletteNames: model ? model.paletteNames : []
        property var paletteValues: model ? model.paletteValues : []
        property var paletteKeys: model ? model.paletteKeys : []
        
        property int editSectionIndex: -1
        property int editColorIndex: -1
        
        // Manual Previews Controls - Edit these values directly!
        property real baseScale: 0.95 // Multiplier for the responsive fit (e.g. 0.95 for a small margin)
        property int previewWidth: 1000
        property int previewHeight: 500 // Must match content height to avoid clipping
        
        // This makes the preview resize automatically with the window!
        // We use Math.min to ensure it fits both width and height.
        property real previewScale: {
            if (!livePreviewRect.width || !livePreviewRect.height) return baseScale;
            var sw = (livePreviewRect.width / previewWidth);
            var sh = (livePreviewRect.height / previewHeight);
            return Math.min(sw, sh) * baseScale;
        }
        
        onPreviewScaleChanged: if (model) model.previewScale = previewScale
        onPreviewWidthChanged: if (model) model.previewWidth = 1000 // Render wider window
        
        onModelChanged: {
            if (model) {
                model.previewScale = previewScale
                model.previewWidth = 1000
            }
        }
    }



    function safePaletteKey(proxy, sectionIdx, colorIdx) {
        if (!proxy || !proxy.paletteKeys) return "";
        var pk = proxy.paletteKeys;
        if (!(pk && pk.length > sectionIdx)) return "";
        var inner = pk[sectionIdx];
        if (!inner) return "";
        var v = inner[colorIdx];
        return (v === undefined || v === null) ? "" : v;
    }

    Components.DialogPalette {
        id: paletteDialog
        onAccepted: {
            if (selectedColor !== "transparent") {
                if (ulauncherModelProxy.editSectionIndex >= 0 && ulauncherModelProxy.editColorIndex >= 0 && controller) {
                    controller.ulauncherModel.setPaletteColor(ulauncherModelProxy.editSectionIndex, ulauncherModelProxy.editColorIndex, selectedColor.toString())
                }
            }
        }
    }

    Dialog {
        id: confirmApplyDialog
        title: qsTr("Confirm Apply")
        modal: true
        visible: false
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        
        contentItem: ColumnLayout {
            spacing: Kirigami.Units.smallSpacing
            Label { 
                text: qsTr("This will apply the selected colors to the current theme.\n(Changes are written to ~/.config/ulauncher/)\n\nContinue?")
                wrapMode: Text.WordWrap
                Layout.maximumWidth: 400
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button {
                    text: qsTr("Cancel")
                    onClicked: confirmApplyDialog.close()
                }
                Button {
                    text: qsTr("Apply")
                    onClicked: {
                        confirmApplyDialog.close()
                        if (controller) controller.applyUlauncherConfig()
                    }
                }
            }
        }
    }

    Dialog {
        id: newThemeDialog
        title: qsTr("Create New Theme")
        modal: true
        visible: false
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        
        contentItem: ColumnLayout {
            spacing: Kirigami.Units.smallSpacing
            Label {
                text: qsTr("Provide a name for your new theme:")
                wrapMode: Text.WordWrap
                Layout.maximumWidth: 400
            }
            TextField {
                id: dialogThemeNameInput
                Layout.fillWidth: true
                placeholderText: qsTr("Theme Name")
                text: controller ? controller.ulauncherNewThemeName : ""
                onTextChanged: if(controller) controller.ulauncherNewThemeName = text
                onAccepted: {
                    if (controller && controller.ulauncherNewThemeName.trim().length > 0) {
                        newThemeDialog.close()
                        controller.applyUlauncherConfig()
                    }
                }
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button {
                    text: qsTr("Cancel")
                    onClicked: newThemeDialog.close()
                }
                Button {
                    text: qsTr("Create and Apply")
                    enabled: controller && controller.ulauncherNewThemeName.trim().length > 0
                    highlighted: true
                    onClicked: {
                        newThemeDialog.close()
                        if (controller) controller.applyUlauncherConfig()
                    }
                }
            }
        }
        onOpened: dialogThemeNameInput.forceActiveFocus()
    }

    RowLayout {
        anchors.fill: parent
        spacing: Kirigami.Units.smallSpacing

        // --- Left Pane ---
        Rectangle {
            color: Kirigami.Theme.backgroundColor
            Layout.preferredWidth: 300
            Layout.fillHeight: true
            radius: Kirigami.Units.largeSpacing
            border.color: Kirigami.Theme.alternateBackgroundColor
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.largeSpacing
                spacing: Kirigami.Units.smallSpacing

                Label { text: qsTr("Settings"); font.bold: true; Layout.fillWidth: true }
                MenuSeparator { Layout.fillWidth: true }

                // Template Selection
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: qsTr("Select a theme"); Layout.fillWidth: true }
                    ToolButton {
                        icon.name: "edit-clear"
                        ToolTip.text: qsTr("Reset to current theme")
                        ToolTip.visible: hovered
                        onClicked: { 
                            if (controller) {
                                controller.ulauncherClearSelection()
                                controller.ulauncherModel.refresh()
                            }
                        }
                    }
                }

                ComboBox {
                    id: templateCombo
                    Layout.fillWidth: true
                    textRole: "fileName"
                    
                    model: {
                        if (!controller || !controller.ulauncherModel || !controller.ulauncherTemplateModel) return [];
                        
                        var list = [];
                        // Distinguish between the "editing" path and the "actually applied" path.
                        // We use actualConfigPath to mark the (Current) flag.
                        var actualPath = controller.ulauncherModel.actualConfigPath;
                        var tm = controller.ulauncherTemplateModel;
                        var foundCurrent = false;

                        for (var i = 0; i < tm.rowCount(); i++) {
                            var it = tm.get(i);
                            var isCurrent = (actualPath && it.filePath === actualPath);
                            var name = it.fileName;
                            if (it.isTemplate) name += " (" + qsTr("Template") + ")";
                            if (isCurrent) {
                                name += " (" + qsTr("Current") + ")";
                                foundCurrent = true;
                            }
                            list.push({ 
                                fileName: name, 
                                filePath: it.filePath, 
                                isTemplate: it.isTemplate,
                                isCurrent: isCurrent
                            });
                        }

                        if (!foundCurrent && actualPath) {
                            var parts = actualPath.split("/");
                            var cfgName = parts[parts.length-1] || qsTr("Current Theme");
                            list.unshift({ 
                                fileName: cfgName + " (" + qsTr("Current") + ")", 
                                filePath: actualPath, 
                                isTemplate: false,
                                isCurrent: true
                            });
                        }
                        return list;
                    }

                    // Only sync currentIndex when the model is first loaded or when actualConfigPath significantly changes.
                    // To avoid jumping back when selecting, we can use a Connection or simply check if the current selection
                    // already matches the intent.
                    Component.onCompleted: {
                        if (controller) {
                            controller.ulauncherModel.refresh();
                        }
                    }
                    
                    Connections {
                        target: controller.ulauncherModel
                        function onActualConfigPathChanged() {
                            // When the applied theme changes, we force update the selection to it
                            for (var i = 0; i < templateCombo.model.length; i++) {
                                if (templateCombo.model[i].isCurrent) {
                                    templateCombo.currentIndex = i;
                                    break;
                                }
                            }
                        }
                    }
                    enabled: (controller && !controller.ulauncherIsFileMode)
                    opacity: enabled ? 1.0 : 0.5

                    onActivated: (index) => {
                         if (!controller) return;
                         controller.ulauncherIsFileMode = false;
                         controller.clearSelectedFile();
                         
                         var entry = (model && model.length > index) ? model[index] : null;
                         if (!entry) return;

                         // Map back to template index if it exists in the model
                         var tm = controller.ulauncherTemplateModel;
                         var foundIdx = -1;
                         for (var i = 0; i < tm.rowCount(); i++) {
                             if (tm.get(i).filePath === entry.filePath) {
                                 foundIdx = i;
                                 break;
                             }
                         }
                         controller.ulauncherTemplateIndex = foundIdx;
                         controller.ulauncherModel.refresh(entry.filePath);
                    }

                }

                Label {
                    text: qsTr("New Theme Name")
                    visible: {
                        if (!controller || !controller.ulauncherTemplateModel || templateCombo.currentIndex <= 0) return false;
                        var info = controller.ulauncherTemplateModel.get(controller.ulauncherTemplateIndex);
                        return !!(info && info.isTemplate);
                    }
                }
                TextField {
                    id: newThemeNameInput
                    Layout.fillWidth: true
                    placeholderText: qsTr("Enter name for the new theme...")
                    visible: {
                        if (!controller || !controller.ulauncherTemplateModel || templateCombo.currentIndex <= 0) return false;
                        var info = controller.ulauncherTemplateModel.get(controller.ulauncherTemplateIndex);
                        return !!(info && info.isTemplate);
                    }
                    text: controller ? controller.ulauncherNewThemeName : ""
                    onTextChanged: if(controller) controller.ulauncherNewThemeName = text
                }

                MenuSeparator { Layout.fillWidth: true }

                // Palette Section
                ScrollView {
                    id: paletteScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true 
                    clip: true

                    ColumnLayout {
                        Layout.fillWidth: true
                        width: paletteScroll.availableWidth
                        spacing: Kirigami.Units.largeSpacing

                        // Iterate over Palette Sections (e.g. "manifest", "theme")
                        Repeater {
                            model: ulauncherModelProxy.paletteNames
                            delegate: ColumnLayout {
                                Layout.fillWidth: true
                                spacing: Kirigami.Units.smallSpacing
                                
                                readonly property int sectionIndex: index

                                // Section Header
                                Label { 
                                    text: (modelData === "theme") ? qsTr("Theme Colors") : 
                                          (modelData === "manifest") ? qsTr("Manifest Colors") : modelData
                                    font.bold: true 
                                    Layout.fillWidth: true
                                }
                                MenuSeparator { Layout.fillWidth: true }

                                // Colors in this section
                                Repeater {
                                    id: innerRepeater
                                    model: (ulauncherModelProxy.paletteValues && ulauncherModelProxy.paletteValues.length > sectionIndex) 
                                           ? ulauncherModelProxy.paletteValues[sectionIndex] : []
                                    delegate: RowLayout {
                                        Layout.fillWidth: true
                                        spacing: Kirigami.Units.smallSpacing

                                        Label {
                                            text: ulauncherPage.safePaletteKey(ulauncherModelProxy, sectionIndex, index)
                                            Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }

                                        Rectangle {
                                            id: colorPreview
                                            width: Kirigami.Units.gridUnit * 1.5
                                            height: Kirigami.Units.gridUnit * 1.5
                                            radius: Kirigami.Units.smallSpacing
                                            // Use controller to normalize CSS colors (e.g. rgba) to QML-friendy hex
                                            color: controller ? controller.normalizeColor(modelData) : (modelData || "transparent")
                                            border.width: 1
                                            border.color: Kirigami.Theme.disabledTextColor
                                            
                                            ToolTip.text: controller ? (controller.formatColorWithAlpha(colorPreview.color)) : ""
                                            ToolTip.visible: mouseArea.containsMouse
                                            
                                            MouseArea {
                                                id: mouseArea
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: {
                                                     if (!controller) return;
                                                     var c = controller.openColorDialog(modelData || "transparent")
                                                     if (c) {
                                                         controller.ulauncherModel.setPaletteColor(sectionIndex, index, c)
                                                     }
                                                }
                                            }
                                        }

                                        Button {
                                            icon.name: "color-picker"
                                            ToolTip.text: qsTr("Pick from palette")
                                            ToolTip.visible: hovered
                                            onClicked: {
                                                ulauncherModelProxy.editSectionIndex = sectionIndex
                                                ulauncherModelProxy.editColorIndex = index
                                                paletteDialog.selectedColor = "transparent"
                                                paletteDialog.open()
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        Label {
                            visible: (!ulauncherModelProxy.paletteNames || ulauncherModelProxy.paletteNames.length === 0)
                            text: qsTr("No colors found")
                            font.italic: true
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }
                }

                MenuSeparator { Layout.fillWidth: true }

                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        text: qsTr("Apply Config")
                        Layout.fillWidth: true
                        onClicked: {
                            if (!controller) return;
                            var info = controller.ulauncherTemplateModel.get(controller.ulauncherTemplateIndex);
                            if (info && info.isTemplate) {
                                newThemeDialog.open();
                            } else {
                                confirmApplyDialog.open();
                            }
                        }
                    }
                    Button {
                        text: qsTr("Restore Settings")
                        Layout.fillWidth: true
                        enabled: controller && controller.hasUlauncherBackup
                        onClicked: if (controller) {
                            controller.restoreUlauncherBackup()
                        }
                    }
                }
            }
        }

        // --- Right Pane: Preview ---
        Rectangle {
            color: "transparent"
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.largeSpacing
                spacing: Kirigami.Units.smallSpacing

                Label { text: qsTr("Current Theme:"); font.bold: true }
                
                // Current Theme Preview rendering
                Rectangle {
                    id: currentPreviewRect
                    color: "transparent" //"#00FF00"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.alignment: Qt.AlignHCenter
                    clip: true
                    
                    WebEngineView {
                        id: currentView
                        anchors.fill: parent
                        backgroundColor: "transparent"
                        
                        property string contentHtml: (controller && controller.ulauncherModel) ? controller.ulauncherModel.currentConfigPreviewHtml : ""
                        onContentHtmlChanged: loadHtml(contentHtml, "file:///")
                        Component.onCompleted: loadHtml(contentHtml, "file:///")

                        // Disable interactions to make it feel like a preview
                        settings.javascriptEnabled: false
                        settings.scrollAnimatorEnabled: false
                        settings.localContentCanAccessFileUrls: true
                        settings.allowRunningInsecureContent: true
                    }
                }

                Label {
                    text: qsTr("Live Preview:")
                    font.bold: true
                    wrapMode: Text.WrapAnywhere
                    Layout.fillWidth: true
                }

                // Live Preview rendering
                Rectangle {
                    id: livePreviewRect
                    color: "transparent" //"#00FF00"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.alignment: Qt.AlignHCenter
                    clip: true
                    
                    WebEngineView {
                        id: liveView
                        anchors.fill: parent
                        backgroundColor: "transparent"
                        
                        property string contentHtml: (controller && controller.ulauncherModel) ? controller.ulauncherModel.previewHtml : ""
                        onContentHtmlChanged: loadHtml(contentHtml, "file:///")
                        Component.onCompleted: loadHtml(contentHtml, "file:///")

                        settings.javascriptEnabled: false
                        settings.localContentCanAccessFileUrls: true
                        settings.allowRunningInsecureContent: true
                    }
                }
            }
        }
    }
}