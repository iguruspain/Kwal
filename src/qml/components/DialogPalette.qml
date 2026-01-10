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
    property string currentBackend: "material-you" // "pywal16", "material-you", "imagemagick"
    property int sourceMode: 0 // 0: App (Wallpapers Tab), 1: Custom/System
    property bool generationActive: false
    // Single selection across both grids: index + set name ("palette" or "accent")
    property int selectedIndex: -1
    property string selectedSet: ""
    //["TonalSpot", "Vibrant", "Expressive", "Content", "FruitSalad", "Rainbow", "Monochrome", "Neutral", "Fidelity"]
    property bool darkMode: true
    property  int toneValue: 1
    property real colorfulnessValue: 1.0
    property real brightnessValue: 0.8
    property real contrastValue: 0.0
    property string seed_color: ""
    
    // Dimensions
    width: Kirigami.Units.gridUnit * 32
    
    // Remove manual implicitHeight here, let contentItem drive it, but use constraints
    // implicitHeight: Math.min(...)

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
        if (path !== "" && currentBackend === "material-you") {
             var params = {
                "dark_mode": root.darkMode,
                "tone": root.toneValue,
                "colorfulness": root.colorfulnessValue,
                "brightness": root.brightnessValue,
                "contrast": root.contrastValue,
                "seed_color": root.seed_color
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

    contentItem: ScrollView {
        id: contentScroll
        clip: true
        
        // This is the maximum visible height. 
        // We use Math.min to allow the dialog to be smaller if content is small,
        // but cap it at 30 units if it's large.
        implicitHeight: Math.min(contentContainer.implicitHeight, Kirigami.Units.gridUnit * 30)

        Item {
            id: contentContainer
            // The constraint for the width is the scrollview's width (which matches dialog width)
            width: contentScroll.availableWidth 
            
            // The height is determined by the content + margins
            implicitHeight: mainLayout.implicitHeight + (Kirigami.Units.largeSpacing * 2)

            ColumnLayout {
                id: mainLayout
                // We manually anchor to create margins within the Item container
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Kirigami.Units.largeSpacing
                
                spacing: Kirigami.Units.largeSpacing

                // Wallpaper Selection Row
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.largeSpacing
                    
                    Label { text: qsTr("From:") }
                    
                    ComboBox {
                        id: sourceCombo
                        model: [qsTr("Selected wallpaper in Kwal"), qsTr("Current wallpaper")]
                        currentIndex: root.sourceMode
                        Layout.fillWidth: false
                        onActivated: {
                            root.sourceMode = currentIndex
                            if (currentIndex === 1) {
                                // Fetch system wallpaper immediately when switching to this mode
                                var sys = pyController.getCurrentSystemWallpaper()
                                if (sys !== "") root.sourceImage = sys
                            }
                        }
                    }
                    Item { Layout.fillWidth: true } // Spacer
                }

                // Wallpaper Preview
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
                            text: qsTr("No Image selected")
                            visible: parent.status !== Image.Ready
                        }
                    }
                }

                // Extraction Controls
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.largeSpacing
                    
                    // Backend
                    ComboBox {
                        id: extractMethodCombo
                        model: ["pywal16", "material-you", "imagemagick"]
                        currentIndex: 1
                        Layout.preferredWidth: Kirigami.Units.gridUnit * 8
                        onActivated: {
                            // Switch backend and reset any generated data
                            root.currentBackend = currentText
                            root.generationActive = false
                            root.selectedColor = "transparent"
                            root.selectedIndex = -1
                            root.selectedSet = ""
                            root.contrastValue = 0.0
                            root.brightnessValue = 0.8
                            root.colorfulnessValue = 1.0
                            root.toneValue = 1
                            root.darkMode = true
                            if (pyController && pyController.clearPalette) pyController.clearPalette()
                        }
                    }

                    // Extract Button
                    Button {
                        id: extractButton
                        //text: qsTr("Extract")
                        icon.name: "palette-symbolic"
                        Layout.fillWidth: false
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

                RowLayout {
                    id: generationGroup
                    Layout.fillWidth: true
                    visible: root.generationActive
                    spacing: Kirigami.Units.largeSpacing
            
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter | Qt.AlignRight

                        // Palette Colors
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

                        // Accent Colors 
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
                                            onClicked: (mouse) => {
                                                if (mouse.button === Qt.LeftButton) {
                                                root.selectedIndex = index
                                                root.selectedSet = "accent"
                                                root.selectedColor = modelData
                                                }
                                                // else if (mouse.button === Qt.RightButton) {
                                                //     // Right-click to copy color to clipboard
                                                //     root.seed_color = modelData
                                                //     pyController.RefreshPalette(root.sourceImage)
                                                // }
                                            }
                                        }
                                        ToolTip.visible: hovered
                                        ToolTip.text: modelData
                                    }
                                }
                            }
                        }
                    }
                    // Aux Controls (for Material You)
                    ColumnLayout {
                        id: auxControls
                        Layout.fillWidth: true
                        visible: root.currentBackend === "material-you"
                        spacing: Kirigami.Units.largeSpacing

                        // Parameters Label
                        Label {
                            id: auxParamsLabel 
                            text: qsTr("Parameters")
                            font.bold: true 
                        }                        

                        // Mode (Dark/Light)
                        RowLayout {
                            id: modeRow
                            spacing: Kirigami.Units.smallSpacing
                            RadioButton {
                                text: qsTr("Dark")
                                checked: root.darkMode
                                onToggled: if (checked) root.darkMode = true
                                onCheckedChanged: {
                                    // To be defined, will update palette with new mode
                                }
                            }
                            RadioButton {
                                text: qsTr("Light")
                                checked: !root.darkMode
                                onToggled: if (checked) root.darkMode = false
                                onCheckedChanged: {
                                    // To be defined, will update palette with new mode
                                }
                            }
                        }
                        
                        // Parameters laid out in a GridLayout: Label | Slider | Value
                        GridLayout {
                            id: auxGrid
                            Layout.fillWidth: true
                            columns: 3
                            rowSpacing: Kirigami.Units.smallSpacing
                            columnSpacing: Kirigami.Units.smallSpacing

                            Label { text: qsTr("Tone:") }
                            Slider {
                                Layout.fillWidth: true
                                Layout.preferredWidth: Kirigami.Units.gridUnit * 16
                                from: 1
                                to: 9
                                value: root.toneValue
                                stepSize: 1
                                onMoved: root.toneValue = value
                                onValueChanged: {
                                    //To be defined, will update palette with new tone
                                }
                            }
                            Label { text: root.toneValue.toFixed(0) }

                            Label { text: qsTr("Colorfulness:") }
                            Slider {
                                Layout.fillWidth: true
                                Layout.preferredWidth: Kirigami.Units.gridUnit * 16
                                from: -1.0
                                to: 1.0
                                value: root.colorfulnessValue
                                stepSize: 0.1
                                onMoved: root.colorfulnessValue = value
                                onValueChanged: {
                                    //To be defined, will update palette with new colorfulness
                                }
                            }
                            Label { text: root.colorfulnessValue.toFixed(1) }

                            Label { text: qsTr("Brightness:") }
                            Slider {
                                Layout.fillWidth: true
                                Layout.preferredWidth: Kirigami.Units.gridUnit * 16
                                from: -1.0
                                to: 1.0
                                value: root.brightnessValue
                                stepSize: 0.1
                                onMoved: root.brightnessValue = value
                                onValueChanged: {
                                    //To be defined, will update palette with new brightness
                                }
                            }
                            Label { text: root.brightnessValue.toFixed(1) }

                            Label { text: qsTr("Contrast:") }
                            Slider {
                                Layout.fillWidth: true
                                Layout.preferredWidth: Kirigami.Units.gridUnit * 16
                                from: -1.0
                                to: 1.0
                                value: root.contrastValue
                                stepSize: 0.1
                                onMoved: root.contrastValue = value
                                onValueChanged: {
                                    //To be defined, will update palette with new contrast
                                }
                            }
                            Label { text: root.contrastValue.toFixed(1) }
                        }
                    }
                }
            }
        }
    }
}