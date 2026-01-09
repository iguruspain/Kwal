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
    property bool generationActive: false
    // Single selection across both grids: index + set name ("palette" or "accent")
    property int selectedIndex: -1
    property string selectedSet: ""
    
    // Dimensions
    width: Kirigami.Units.gridUnit * 32
    // Allow dialog to size to its content so footer buttons stay near content
    implicitHeight: contentItem.implicitHeight + Kirigami.Units.gridUnit * 6

    onOpened: {
        // Logic to determine initial image variable state on open
        var sys = ""
        
        if (sourceMode === 0) {
            // App Wallpaper Mode is default
             if (appSelectedWallpaper === "") {
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
            Layout.fillWidth: true
            Layout.preferredHeight: Kirigami.Units.gridUnit * 12
            //Layout.preferredWidth: Kirigami.Units.gridUnit * 12
            
            Image {
                anchors.fill: parent
                // Show what we *would* extract from
                source: {
                    var finalPath = (root.sourceMode === 0) ? root.appSelectedWallpaper : root.sourceImage
                    if (finalPath) return "file://" + finalPath
                    return ""
                }
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                cache: false 
                
                Rectangle {
                    // Match the visible image area (respect `fillMode`)
                    width: parent.paintedWidth
                    height: parent.paintedHeight
                    anchors.centerIn: parent
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
                id: extractMethodCombo
                model: ["pywal16", "material-you", "imagemagick"]
                currentIndex: 0
                Layout.preferredWidth: Kirigami.Units.gridUnit * 8
                onActivated: {
                    // Switch backend and reset any generated data
                    root.currentBackend = currentText
                    root.generationActive = false
                    root.contrastValue = 0.0
                    root.selectedColor = "transparent"
                    root.selectedIndex = -1
                    root.selectedSet = ""
                    if (pyController && pyController.clearPalette) pyController.clearPalette()
                }
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
                id: extractButton
                //text: qsTr("Extract")
                icon.name: "palette-symbolic"
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
                        // mark that generation was triggered from this dialog
                        root.generationActive = true
                        root.refreshPalette(path)
                    }
                }
            }
            Item { Layout.fillWidth: true } // Spacer
        }

        ColumnLayout {
            id: generationGroup
            Layout.fillWidth: true
            visible: root.generationActive
     
            // 3b. Aux Controls (Contrast only for Material You)
            RowLayout {
                id: auxControls
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
                id: paletteLabel 
                text: qsTr("Palette Colors")
                font.bold: true 
            }

            Grid {
                id: paletteGrid
                columns: 8
                // Keep grid compact rather than stretching to fill the dialog
                spacing: Kirigami.Units.smallSpacing / 6
                clip: true

                Repeater {
                    model: pyController.currentPaletteData.colors
                    delegate: Item {
                        width: Kirigami.Units.gridUnit * 1.5
                        height: Kirigami.Units.gridUnit * 1.5

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: Kirigami.Units.smallSpacing / 2
                            color: modelData
                            border.width: (root.selectedSet === "palette" && root.selectedIndex === index) ? 2 : 0
                            border.color: Kirigami.Theme.highlightColor
                            radius: 3

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    root.selectedIndex = index
                                    root.selectedSet = "palette"
                                    root.selectedColor = modelData
                                }
                            }

                            ToolTip.visible: hovered
                            ToolTip.text: modelData
                        }
                    }
                }
            }

            // 5. Accent Colors 
            Label {
                id: accentLabel 
                text: qsTr("Accent Colors")
                font.bold: true 
                Layout.topMargin: Kirigami.Units.smallSpacing
            }
            
            // Using GridView for accents to match styling exactly
            Grid {
                id: accentGrid
                columns: 8
                spacing: Kirigami.Units.smallSpacing / 6
                clip: true

                Repeater {
                    model: pyController.currentPaletteData.accents
                    delegate: Item {
                        width: Kirigami.Units.gridUnit * 1.5
                        height: Kirigami.Units.gridUnit * 1.5

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: Kirigami.Units.smallSpacing / 2
                            color: modelData
                            border.width: (root.selectedSet === "accent" && root.selectedIndex === index) ? 2 : 0
                            border.color: Kirigami.Theme.highlightColor
                            radius: 3
                            
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    root.selectedIndex = index
                                    root.selectedSet = "accent"
                                    root.selectedColor = modelData
                                }
                            }
                            
                            ToolTip.visible: hovered
                            ToolTip.text: modelData
                        }
                    }
                }
            }
        }
        
        Item { Layout.fillHeight: true } // Spacer
    }
}
