import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.Page{
    id: starshipPage
    title: qsTr("Starship Settings")

    background: Rectangle {
        color: "transparent"
    }
    // Sample model for Starship settings, later will by replaced and adapted in models.py
    ListModel {
        id: starshipModel
        ListElement {
            configFile: "~/.config/starship.toml" // logic to get current config file in file_utils.py
            templateFolder: "~/.config/kwal/templates/starship/"
            paletteNameColors: []   // Placeholder for future color palette integration
            paletteValuesColors: []  // Placeholder for future color palette integration
            paletteDraftColors: []   // Placeholder for future color palette integration in panel (State Management)
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
                // color settings, will be adapted to the starship model
                // labels (paletteNameColors) + pickers for colors from palettes (paletteValuesColors), Repeater?

                Item { Layout.fillHeight: true }

                // Action Buttons
                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        id: applyColorsButton
                        text: qsTr("Apply colors")
                        Layout.fillWidth: true
                        ToolTip.text: qsTr("Apply the colors to starship config")
                        ToolTip.visible: hovered
                        enabled: true //later based on controller state
                        
                        onClicked: {
                            // Logic to apply colors to starship config
                        }
                    }
                    Button {
                        id: restoreBackupButton
                        text: qsTr("Restore backup")
                        Layout.fillWidth: true
                        enabled: true //later based on controller state
                        ToolTip.text: qsTr("Restore the starship config from the last backup")//(controller && controller.hasStarshipBackup) ? qsTr("Restore the starship config from the last backup") : qsTr("No backup available to restore")
                        ToolTip.visible: hovered
                        
                        onClicked: {
                            // Logic to restore starship config from backup
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