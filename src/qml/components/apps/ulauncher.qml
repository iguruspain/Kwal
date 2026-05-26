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
                        controller.ulauncherCreateNewTheme()
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
                    text: qsTr("Create")
                    enabled: controller && controller.ulauncherNewThemeName.trim().length > 0
                    highlighted: true
                    onClicked: {
                        newThemeDialog.close()
                        if (controller) controller.ulauncherCreateNewTheme()
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
                        
                        // Dependency on generation counter to force refresh
                        var _gen = controller.ulauncherTemplatesGeneration;
                        
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
                    
                    Connections {
                        target: controller
                        function onUlauncherTemplateIndexChanged() {
                            if (controller.ulauncherTemplateIndex >= 0 && controller.ulauncherTemplateIndex < templateCombo.count) {
                                templateCombo.currentIndex = controller.ulauncherTemplateIndex
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
                                Kirigami.Separator {Layout.fillWidth: true; height: Kirigami.Units.smallSpacing; color: Qt.alpha(Kirigami.Theme.disabledTextColor, 0.4)}

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
                                                acceptedButtons: Qt.LeftButton | Qt.RightButton
                                                onClicked: (mouse) => {
                                                    if (mouse.button === Qt.RightButton) {
                                                        clipboardHelper.copyToClipboard(modelData)
                                                        return
                                                    }
                                                    if (!controller) return;
                                                    var c = controller.openColorDialog(modelData || "transparent")
                                                    if (c) {
                                                        controller.ulauncherModel.setPaletteColor(sectionIndex, index, c)
                                                    }
                                                }
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
                    Layout.alignment: Qt.AlignHCenter
                    spacing: Kirigami.Units.largeSpacing

                    ToolButton {
                        icon.name: "document-new"
                        ToolTip.text: qsTr("Create New Theme")
                        ToolTip.visible: hovered
                        onClicked: newThemeDialog.open()
                    }

                    ToolButton {
                        icon.name: "document-save"
                        ToolTip.text: qsTr("Save Theme")
                        ToolTip.visible: hovered
                        enabled: {
                            if (templateCombo.currentIndex < 0 || !templateCombo.model) return false;
                            var item = templateCombo.model[templateCombo.currentIndex];
                            // Can save if it is not a template (even if it is current)
                            return item && !item.isTemplate;
                        }
                        onClicked: if(controller) controller.ulauncherSaveTheme()
                    }

                    ToolButton {
                        icon.name: "edit-delete"
                        ToolTip.text: qsTr("Delete Theme")
                        ToolTip.visible: hovered
                        enabled: {
                            if (templateCombo.currentIndex < 0 || !templateCombo.model) return false;
                            var item = templateCombo.model[templateCombo.currentIndex];
                            // Cannot delete template AND cannot delete active theme
                            return item && !item.isTemplate && !item.isCurrent;
                        }
                        onClicked: if(controller) controller.ulauncherDeleteTheme()
                    }

                    ToolButton {
                        icon.name: "dialog-ok-apply" 
                        ToolTip.text: qsTr("Apply to Ulauncher")
                        ToolTip.visible: hovered
                        enabled: {
                            if (templateCombo.currentIndex < 0 || !templateCombo.model) return false;
                            var item = templateCombo.model[templateCombo.currentIndex];
                            // Cannot apply if it is a template or already current
                            return item && !item.isTemplate && !item.isCurrent;
                        }
                        onClicked: if(controller) controller.ulauncherApplyTheme()
                    }

                    ToolButton {
                        icon.name: "document-revert"
                        ToolTip.text: qsTr("Restore Backups")
                        ToolTip.visible: hovered
                        enabled: controller && controller.hasUlauncherBackup
                        onClicked: if(controller) controller.restoreUlauncherBackup()
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
                    
                    Loader {
                        id: currentViewLoader
                        anchors.fill: parent
                        // Only load when page is visible
                        active: ulauncherPage.visible
                        sourceComponent: WebEngineView {
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
                    BusyIndicator {
                        anchors.centerIn: parent
                        running: currentViewLoader.status === Loader.Loading
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
                    
                    Loader {
                        id: liveViewLoader
                        anchors.fill: parent
                        // Only load when page is visible
                        active: ulauncherPage.visible
                        sourceComponent: WebEngineView {
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
                    BusyIndicator {
                        anchors.centerIn: parent
                        running: liveViewLoader.status === Loader.Loading
                    }
                }
            }
        }
    }
}