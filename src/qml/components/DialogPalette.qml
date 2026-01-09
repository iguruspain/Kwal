import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Dialog {
    id: root
    title: qsTr("Select Color Palette")
    standardButtons: Dialog.Ok | Dialog.Cancel
    
    // Properties
    property string appSelectedWallpaper: (pyController && pyController.selectedWallpaper) ? pyController.selectedWallpaper : ""
    
    // Internal state
    property string sourceImage: "" 
    property color selectedColor: "transparent"
    property string currentBackend: "pywal16"
    property int sourceMode: 0 // 0: App (Wallpapers Tab), 1: Custom/System
    property bool darkMode: true
    property real contrastValue: 0.0
    
    // Dimensions
    width: Kirigami.Units.gridUnit * 32
    height: Kirigami.Units.gridUnit * 45

    onOpened: {
        // Logic to determine initial image variable state on open
        var sys = ""
        
        if (sourceMode === 0) {
            // App Wallpaper Mode is default
             if (appSelectedWallpaper === "") {
                // If nothing selected in app, maybe fallback or just leave empty
                // We do NOT auto-switch sourceMode here to avoid confusion unless user wants it
                // But user might want to see system wallpaper by default if app is empty
                sys = pyController.getCurrentSystemWallpaper()
                if (sys !== "") {
                    root.sourceMode = 1
                    root.sourceImage = sys
                }
             }
        } else {
            // System Wallpaper Mode
            if (sourceImage === "") {
                sys = pyController.getCurrentSystemWallpaper()
                if (sys !== "") {
                    root.sourceImage = sys
                }
            }
        }
        // NOTE: Automatic palette generation is DISABLED as requested.
        // User must click "Extract".
    }

    // --- Helper Functions ---

    function refreshPalette(path) {
        if (path !== "") {
             var params = {
                 "dark_mode": root.darkMode,
                 "contrast": root.contrastValue
             }
             pyController.generatePalette(path, currentBackend, params)
        }
    }

    Connections {
        target: pyController
        function onPaletteGenerationError(msg) {
            applicationWindow().showPassiveNotification("Error: " + msg)
        }
    }

    contentItem: ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        // 1. Wallpaper Selection Row
        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.largeSpacing
            
            Label { text: qsTr("Source:") }
            
            ComboBox {
                id: sourceCombo
                model: [qsTr("Selected in App"), qsTr("System Wallpaper")]
                currentIndex: root.sourceMode
                Layout.fillWidth: true
                onActivated: {
                    root.sourceMode = currentIndex
                    if (currentIndex === 1) {
                         // Fetch system wallpaper immediately when switching to this mode
                         var sys = pyController.getCurrentSystemWallpaper()
                         if (sys !== "") root.sourceImage = sys
                    }
                }
            }
        }

        // 2. Wallpaper Preview
        Item {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: Kirigami.Units.gridUnit * 12
            Layout.preferredHeight: Kirigami.Units.gridUnit * 12
            
            Image {
                anchors.fill: parent
                // Show what we *would* extract from
                source: {
                    var finalPath = (root.sourceMode === 0) ? root.appSelectedWallpaper : root.sourceImage
                    if (finalPath) return "file://" + finalPath
                    return ""
                }
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                cache: false 
                
                Rectangle {
                    anchors.fill: parent
                    color: "transparent"
                    border.color: Kirigami.Theme.highlightColor
                    border.width: 1
                    visible: parent.status === Image.Ready
                }
                
                Label {
                    anchors.centerIn: parent
                    text: qsTr("No Image")
                    visible: parent.status !== Image.Ready
                }
            }
        }

        // 3. Extraction Controls (Combo | Mode | Button)
        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.largeSpacing
            
            // Backend
            ComboBox {
                id: backendCombo
                model: ["pywal16", "material-you", "imagemagick"]
                currentIndex: 0
                Layout.preferredWidth: Kirigami.Units.gridUnit * 8
                onActivated: root.currentBackend = currentText
            }
            
            // Mode (Dark/Light)
            RowLayout {
                spacing: Kirigami.Units.smallSpacing
                RadioButton {
                    text: qsTr("Dark")
                    checked: root.darkMode
                    onToggled: if (checked) root.darkMode = true
                }
                RadioButton {
                    text: qsTr("Light")
                    checked: !root.darkMode
                    onToggled: if (checked) root.darkMode = false
                }
            }

            // Extract Button
            Button {
                text: qsTr("Extract")
                icon.name: "color-picker"
                Layout.fillWidth: true
                onClicked: {
                    var path = (root.sourceMode === 0) ? root.appSelectedWallpaper : root.sourceImage
                    if (!path && root.sourceMode === 0 && root.appSelectedWallpaper === "") {
                         // Fallback warning or check logic
                         applicationWindow().showPassiveNotification("No wallpaper selected in App")
                         return
                    }
                    if (!path && root.sourceMode === 1 && root.sourceImage === "") {
                         // Try to fetch system
                         var sys = pyController.getCurrentSystemWallpaper()
                         if (sys) {
                             root.sourceImage = sys
                             path = sys
                         } else {
                             applicationWindow().showPassiveNotification("Could not detect system wallpaper")
                             return
                         }
                    }

                    if (path) {
                        root.refreshPalette(path)
                    }
                }
            }
        }
        
        // 3b. Aux Controls (Contrast only for Material You)
        RowLayout {
            Layout.fillWidth: true
            visible: root.currentBackend === "material-you"
            spacing: Kirigami.Units.largeSpacing
            
            Label { text: qsTr("Contrast:") }
            Slider {
                Layout.fillWidth: true
                from: -1.0
                to: 1.0
                value: root.contrastValue
                stepSize: 0.1
                onMoved: root.contrastValue = value
            }
            Label { text: root.contrastValue.toFixed(1) }
        }

        // 4. Palette Colors
        Label { 
            text: qsTr("Palette Colors")
            font.bold: true 
        }

        GridView {
            id: paletteGrid
            Layout.fillWidth: true
            // Dynamic height calculation might be tricky if items flow, 
            // but we know we usually get ~16 colors. 
            // 8 per row = 2 rows.
            Layout.preferredHeight: Kirigami.Units.gridUnit * 4.5
            
            cellWidth: Kirigami.Units.gridUnit * 2 
            cellHeight: Kirigami.Units.gridUnit * 2
            model: pyController.currentPaletteData.colors
            interactive: false
            clip: true

            delegate: Item {
                width: paletteGrid.cellWidth
                height: paletteGrid.cellHeight

                Rectangle {
                    // 1.5 x 1.5 visual size inside the 2.0 cell
                    width: Kirigami.Units.gridUnit * 1.5
                    height: Kirigami.Units.gridUnit * 1.5
                    anchors.centerIn: parent
                    color: modelData
                    border.width: root.selectedColor == modelData ? 2 : 0
                    border.color: Kirigami.Theme.highlightColor
                    radius: 3

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.selectedColor = parent.color
                    }
                    
                    ToolTip.visible: hovered
                    ToolTip.text: modelData
                }
            }
        }

        // 5. Accent Colors 
        Label { 
            text: qsTr("Accent Colors")
            font.bold: true 
            Layout.topMargin: Kirigami.Units.smallSpacing
        }
        
        // Using GridView for accents to match styling exactly
        GridView {
            id: accentGrid
            Layout.fillWidth: true
            Layout.preferredHeight: Kirigami.Units.gridUnit * 2.5
            cellWidth: Kirigami.Units.gridUnit * 2
            cellHeight: Kirigami.Units.gridUnit * 2
            model: pyController.currentPaletteData.accents
            interactive: false
            flow: GridView.FlowLeftToRight

            delegate: Item {
                width: accentGrid.cellWidth
                height: accentGrid.cellHeight

                Rectangle {
                    // Same 1.5 x 1.5 size
                    width: Kirigami.Units.gridUnit * 1.5
                    height: Kirigami.Units.gridUnit * 1.5
                    anchors.centerIn: parent
                    color: modelData
                    border.width: root.selectedColor == modelData ? 2 : 0
                    border.color: Kirigami.Theme.highlightColor
                    radius: 3
                    
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.selectedColor = parent.color
                    }
                    
                    ToolTip.visible: hovered
                    ToolTip.text: modelData
                }
            }
        }
        
        Item { Layout.fillHeight: true } // Spacer
    }
}
