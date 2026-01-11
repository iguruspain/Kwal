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
    property string selectedScheme: "TonalSpot"
    property real colorfulnessValue: 1.0
    property real brightnessValue: 0.8
    property real contrastValue: 0.0
    property string seed_color: ""
    
    // Watch for backend updates to seed
    property string actualSeed: (pyController.currentPaletteData && pyController.currentPaletteData.seed) ? pyController.currentPaletteData.seed : ""
    onActualSeedChanged: {
        // If we have an actual seed returned, and no manual override is active (or it matches),
        // we can update our local state or just use this for visualization
        console.log("Actual seed returned:", actualSeed)
        if (seed_color === "" && actualSeed !== "") {
            // Implicitly we are using this seed. 
            // DO NOT set seed_color = actualSeed here, 
            // because that locks it as a manual override for the NEXT image.
        }
    }
    
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
        if (path === "") return

        var params = {}
        if (currentBackend === "material-you") {
             params = {
                "dark_mode": root.darkMode,
                "scheme": root.selectedScheme,
                "colorfulness": root.colorfulnessValue,
                "brightness": root.brightnessValue,
                "contrast": root.contrastValue,
                "seed_color": root.seed_color
             }
        }
        pyController.generatePalette(path, currentBackend, params)
    }

    function resetParameters() {
        // Reset all parameters to defaults
        root.selectedScheme = "TonalSpot"
        root.colorfulnessValue = 1.0
        root.brightnessValue = 0.8
        root.contrastValue = 0.0
        root.seed_color = ""
        root.darkMode = true
    }

    Timer {
        id: debouncer
        interval: 300 // 300ms delay
        repeat: false
        onTriggered: {
            console.log("Debouncer triggered refresh")
            triggerRefresh()
        }
    }

    function debounceRefresh() {
        debouncer.restart()
    }

    function triggerRefresh() {
        if (!root.generationActive) {
            console.log("triggerRefresh skipped: generationActive is false")
            return
        }
        var path = (root.sourceMode === 0) ? root.appSelectedWallpaper : root.sourceImage
        if (path) {
            console.log("Triggering refresh for path:", path)
            root.refreshPalette(path)
        } else {
            console.log("triggerRefresh skipped: no path")
        }
    }

    Connections {
        target: pyController
        function onPaletteGenerationError(msg) {
            applicationWindow().showPassiveNotification("Error: " + msg)
        }
    }

    Connections {
        target: pyController
        function onCurrentPaletteDataChanged() {
            var colors = (pyController.currentPaletteData && pyController.currentPaletteData.colors) ? pyController.currentPaletteData.colors : []
            var accents = (pyController.currentPaletteData && pyController.currentPaletteData.accents) ? pyController.currentPaletteData.accents : []
            var len = colors.length
            var a_len = accents.length
            // If current selection refers to a palette index that no longer exists, clear selection
            if (root.selectedSet === "palette" && root.selectedIndex >= len) {
                root.selectedIndex = -1
                root.selectedSet = ""
                root.selectedColor = "transparent"
            }
            // If selection was an accent and index out of range, clear selection
            if (root.selectedSet === "accent" && root.selectedIndex >= a_len) {
                root.selectedIndex = -1
                root.selectedSet = ""
                root.selectedColor = "transparent"
            }
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
                            // Reset everything when changing source
                            if (currentIndex !== root.sourceMode) { 
                                // logic if needed for partial reset, but full reset usually safer 
                                // when switching context completely
                            }
                            root.resetParameters()
                            
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
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.largeSpacing
                    
                    Item {
                        id: wallpaperPreviewContainer
                        Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                        Layout.fillWidth: true
                        Layout.preferredHeight: Kirigami.Units.gridUnit * 8
                        
                        Image {
                            id: wallpaperPreview
                            // 1. Ocupamos todo el contenedor para tener el área de dibujo
                            anchors.fill: parent
                            
                            // 2. Alineamos el dibujo internamente a la izquierda
                            horizontalAlignment: Image.AlignLeft
                            verticalAlignment: Image.AlignTop
                            
                            // 3. Mantenemos proporción sin estirar
                            fillMode: Image.PreserveAspectFit
                            
                            source: {
                                var finalPath = (root.sourceMode === 0) ? root.appSelectedWallpaper : root.sourceImage
                                return finalPath ? "file://" + finalPath : ""
                            }
                            
                            asynchronous: true
                            cache: false

                            // El Borde
                            Rectangle {
                                id: imageBorder
                                // 4. Usamos las propiedades 'painted' para que el borde
                                // se ajuste automáticamente a los píxeles visibles.
                                width: parent.paintedWidth
                                height: parent.paintedHeight
                                x: 0 // Como alineamos a la izquierda, x siempre es 0
                                
                                color: "transparent"
                                border.color: Kirigami.Theme.highlightColor
                                border.width: 1
                                visible: parent.status === Image.Ready
                            }

                            Label {
                                anchors.centerIn: parent // Mejor centrado en el contenedor
                                text: qsTr("No Image selected")
                                visible: parent.status !== Image.Ready
                            }
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
                            root.resetParameters()
                            if (pyController && pyController.clearPalette) pyController.clearPalette()
                        }
                    }

                    // Extract Button
                    Button {
                        id: extractButton
                        //text: qsTr("Extract")
                        icon.name: "palette-symbolic"
                        Layout.fillWidth: false
                        ToolTip.text: qsTr("Extract Color Palette")
                        ToolTip.visible: hovered
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
                                model: (pyController.currentPaletteData && pyController.currentPaletteData.colors) ? pyController.currentPaletteData.colors : []
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
                                            id: maPalette
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                root.selectedIndex = index
                                                root.selectedSet = "palette"
                                                root.selectedColor = modelData
                                            }
                                        }

                                        ToolTip.visible: maPalette.containsMouse
                                        ToolTip.text: modelData
                                    }
                                }
                            }
                        }

                        // Accent Colors 
                        Label {
                            id: accentLabel 
                            text: root.currentBackend === "material-you" ? qsTr("Accent Colors (right click to set seed)") : qsTr("Accent Colors")
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
                                model: (pyController.currentPaletteData && pyController.currentPaletteData.accents) ? pyController.currentPaletteData.accents : []
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
                                            id: maAccent
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                                            onClicked: (mouse) => {
                                                if (mouse.button === Qt.LeftButton) {
                                                    root.selectedIndex = index
                                                    root.selectedSet = "accent"
                                                    root.selectedColor = modelData
                                                }
                                                else if (mouse.button === Qt.RightButton) {
                                                    // Right-click sets this color as seed and refreshes
                                                    root.seed_color = modelData
                                                    triggerRefresh()
                                                }
                                            }
                                        }

                                        ToolTip.visible: maAccent.containsMouse
                                        ToolTip.text: modelData
                                        // Star icon for the accent currently set as manual seed
                                        Item {
                                            anchors.top: parent.top
                                            anchors.right: parent.right
                                            anchors.margins: Kirigami.Units.smallSpacing / 4
                                            width: Kirigami.Units.gridUnit * 0.6
                                            height: width
                                            visible: root.currentBackend === "material-you" && root.seed_color === modelData

                                            Rectangle {
                                                anchors.fill: parent
                                                color: "transparent"
                                            }
                                            Label {
                                                anchors.centerIn: parent
                                                text: "\u2605"
                                                color: Kirigami.Theme.positiveTextColor
                                                font.pixelSize: Math.max(10, parent.width * 0.6)
                                                //opacity: 0.95
                                                style: Text.Outline
                                                styleColor: Kirigami.Theme.backgroundColor
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        Item { Layout.fillHeight: true }
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
                                onToggled: {
                                    if (checked) {
                                        root.darkMode = true
                                        triggerRefresh()
                                    }
                                }
                            }
                            RadioButton {
                                text: qsTr("Light")
                                checked: !root.darkMode
                                onToggled: {
                                    if (checked) {
                                        root.darkMode = false
                                        triggerRefresh()
                                    }
                                }
                            }
                            Item { Layout.fillWidth: true }
                            // Seed visualization
                            Label {
                                textFormat: Text.StyledText
                                text: qsTr("Seed") + 
                                    "<font color='" + Kirigami.Theme.positiveTextColor + "'>\u2605</font>:"
                                
                                // If you need to adjust the star size specifically,
                                // you can use <font> tags or inline CSS:
                                // text: qsTr("Seed") + " <span style='color:" + Kirigami.Theme.positiveTextColor + "; font-size:12px;'>\u2605</span>:"
                            }
                            RowLayout {
                                Layout.columnSpan: 3
                                spacing: Kirigami.Units.smallSpacing
                                Rectangle {
                                    width: Kirigami.Units.gridUnit
                                    height: width
                                    radius: 3
                                    color: (root.seed_color !== "") ? root.seed_color : root.actualSeed
                                    border.color: Kirigami.Theme.highlightColor
                                    border.width: 1
                                    
                                    ToolTip.visible: seedMouse.containsMouse
                                    ToolTip.text: (root.seed_color !== "") ? (root.seed_color + " (Manual)") : (root.actualSeed + " (Auto)")
                                    
                                    MouseArea {
                                        id: seedMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                    }
                                }
                                Label {
                                    text: (root.seed_color !== "") ? qsTr("Manual") : qsTr("Auto")
                                    opacity: 0.7
                                }
                                Button {
                                    icon.name: "edit-clear"
                                    visible: root.seed_color !== ""
                                    flat: true
                                    ToolTip.text: qsTr("Reset to Auto")
                                    onClicked: {
                                        root.seed_color = ""
                                        triggerRefresh()
                                    }
                                }
                                Item { Layout.fillWidth: true }
                            }                            
                        }
                        
                        // Parameters laid out in a GridLayout: Label | Slider | Value | Reset
                        GridLayout {
                            id: auxGrid
                            Layout.fillWidth: true
                            columns: 4
                            rowSpacing: Kirigami.Units.smallSpacing
                            columnSpacing: Kirigami.Units.smallSpacing

                            Label { text: qsTr("Tone:") }
                            ComboBox {
                                Layout.fillWidth: true
                                Layout.columnSpan: 2
                                model: ["TonalSpot", "Vibrant", "Expressive", "Content", "FruitSalad", "Rainbow", "Monochrome", "Neutral", "Fidelity"]
                                currentIndex: model.indexOf(root.selectedScheme)
                                onActivated: {
                                    root.selectedScheme = currentText
                                    console.log("Tone changed to:", currentText)
                                    // If generation wasn't active but we have an image, force activation to show preview
                                    if (!root.generationActive && ((root.sourceMode === 0 && root.appSelectedWallpaper) || (root.sourceMode === 1 && root.sourceImage))) {
                                        root.generationActive = true
                                    }
                                    triggerRefresh()
                                }
                            }
                            Button {
                                icon.name: "edit-clear"
                                flat: true
                                opacity: (root.selectedScheme !== "TonalSpot") ? 1.0 : 0.0
                                enabled: (root.selectedScheme !== "TonalSpot")
                                ToolTip.text: qsTr("Reset to TonalSpot")
                                onClicked: {
                                    root.selectedScheme = "TonalSpot"
                                    triggerRefresh()
                                }
                            }

                            Label { text: qsTr("Colorfulness:") }
                            Slider {
                                Layout.fillWidth: true
                                Layout.preferredWidth: Kirigami.Units.gridUnit * 16
                                from: 0.0
                                to: 2.0
                                value: root.colorfulnessValue
                                stepSize: 0.1
                                onMoved: {
                                    root.colorfulnessValue = Math.round(value * 10) / 10
                                    debounceRefresh()
                                }
                            }
                            Label { text: root.colorfulnessValue.toFixed(1) }
                            Button {
                                icon.name: "edit-clear"
                                flat: true
                                opacity: (Math.abs(root.colorfulnessValue - 1.0) > 0.01) ? 1.0 : 0.0
                                enabled: (Math.abs(root.colorfulnessValue - 1.0) > 0.01)
                                ToolTip.text: qsTr("Reset to 1.0")
                                onClicked: {
                                    root.colorfulnessValue = 1.0
                                    triggerRefresh()
                                }
                            }

                            Label { text: qsTr("Brightness:") }
                            Slider {
                                Layout.fillWidth: true
                                Layout.preferredWidth: Kirigami.Units.gridUnit * 16
                                from: 0.1
                                to: 2.0
                                value: root.brightnessValue
                                stepSize: 0.1
                                onMoved: {
                                    root.brightnessValue = Math.round(value * 10) / 10
                                    debounceRefresh()
                                }
                            }
                            Label { text: root.brightnessValue.toFixed(1) }
                            Button {
                                icon.name: "edit-clear"
                                flat: true
                                opacity: (Math.abs(root.brightnessValue - 0.8) > 0.01) ? 1.0 : 0.0
                                enabled: (Math.abs(root.brightnessValue - 0.8) > 0.01)
                                ToolTip.text: qsTr("Reset to 0.8")
                                onClicked: {
                                    root.brightnessValue = 0.8
                                    triggerRefresh()
                                }
                            }

                            Label { text: qsTr("Contrast:") }
                            Slider {
                                Layout.fillWidth: true
                                Layout.preferredWidth: Kirigami.Units.gridUnit * 16
                                from: -1.0
                                to: 1.0
                                value: root.contrastValue
                                stepSize: 0.1
                                onMoved: {
                                    root.contrastValue = Math.round(value * 10) / 10
                                    debounceRefresh()
                                }
                            }
                            Label { text: root.contrastValue.toFixed(1) }
                            Button {
                                icon.name: "edit-clear"
                                flat: true
                                opacity: (Math.abs(root.contrastValue - 0.0) > 0.01) ? 1.0 : 0.0
                                enabled: (Math.abs(root.contrastValue - 0.0) > 0.01)
                                ToolTip.text: qsTr("Reset to 0.0")
                                onClicked: {
                                    root.contrastValue = 0.0
                                    triggerRefresh()
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
