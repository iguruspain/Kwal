import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.Page{
    id: ulauncherPage
    title: qsTr("ulauncher Settings")

    background: Rectangle {
        color: "transparent"
    }
    // Sample model for ulauncher settings, later will by replaced and adapted in models.py
    ListModel {
        id: ulauncherModel
        ListElement {
            configFile: "~/.config//ulauncher/settings.json" // logic to get current config file in file_utils.py
            configCurrentTheme: "KDE_theme" // logic to get current theme name from settings.json in file_utils.py ("theme_name": "KDE_theme")
            templateFolder: "~/.config/kwal/templates/ulauncher/"
            paletteThemeNameColors: []   // Placeholder for future color palette integration
            paletteManifestNameColors: []   // Placeholder for future color palette integration
            paletteThemeValuesColors: []  // Placeholder for future color palette integration
            paletteManifestValuesColors: []  // Placeholder for future color palette integration
            paletteDraftColors: []   // Placeholder for future color palette integration in panel (State Management)
            targetThemeName: "" // Placeholder for future target theme name when applying colors
            targetThemeFolder: "" // Placeholder for future target theme folder when applying colors
        }
    }

   // --- Main Layout ---

    RowLayout {
        anchors.fill: parent
        spacing: Kirigami.Units.smallSpacing

        // --- Left Pane: Controls ---
        Rectangle {
            id: leftPaneUlauncher
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
                // Label
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
                            // Logic to clear template selection
                        }
                    }              
                }
                // Templates, provided template or current config
                // ComboBox for selecting templates provided
                // Current config option

                MenuSeparator { Layout.fillWidth: true }
                // color settings, will be adapted to the ulauncher model
                // labels (paletteNameColors) + pickers for colors from palettes (paletteValuesColors), Repeater?

                Item { Layout.fillHeight: true }

                // Action Buttons
                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        id: applyColorsButton
                        text: qsTr("Apply colors")
                        Layout.fillWidth: true
                        ToolTip.text: qsTr("Apply the colors to ulauncher config")
                        ToolTip.visible: hovered
                        enabled: true //later based on controller state
                        
                        onClicked: {
                            // Logic to apply colors to ulauncher config
                        }
                    }
                    Button {
                        id: restoreBackupButton
                        text: qsTr("Restore backup")
                        Layout.fillWidth: true
                        enabled: true //later based on controller state
                        ToolTip.text: qsTr("Restore the ulauncher config from the last backup")//(controller && controller.hasUlauncherBackup) ? qsTr("Restore the ulauncher config from the last backup") : qsTr("No backup available to restore")
                        ToolTip.visible: hovered
                        
                        onClicked: {
                            // Logic to restore ulauncher config from backup
                        }
                    }
                }
            }
        }
        // --- Right Pane: Previews ---
        Rectangle {
            id: rightPaneUlauncher
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