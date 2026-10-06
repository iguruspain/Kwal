pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import org.kde.kirigami as Kirigami
import ".." as Components

Kirigami.Page {
    id: wallpaperPage
    title: qsTr("Wallpapers")
    
    // State for sidebar
    property bool sidePaneOpen: false
    // Theme mode: "light" or "dark", used by the custom commands panel.
    property string themeMode: "dark"
    // Custom color picked
    property string customColor: ""

    // Shared category list (name/hex/label) used both by the color-filter
    // chips and the manual category editor panel.
    property var categoryColorModel: [
        { name: "red", hex: "#E53935", label: "Red" },
        { name: "orange", hex: "#FB8C00", label: "Orange" },
        { name: "yellow", hex: "#FDD835", label: "Yellow" },
        { name: "yellow-green", hex: "#7CB342", label: "Yellow-Green" },
        { name: "green", hex: "#43A047", label: "Green" },
        { name: "cyan-green", hex: "#00897B", label: "Cyan-Green" },
        { name: "cyan", hex: "#00ACC1", label: "Cyan" },
        { name: "blue-cyan", hex: "#1E88E5", label: "Blue-Cyan" },
        { name: "blue", hex: "#3949AB", label: "Blue" },
        { name: "violet", hex: "#8E24AA", label: "Violet" },
        { name: "magenta", hex: "#D81B60", label: "Magenta" },
        { name: "rose", hex: "#F06292", label: "Rose" },
        { name: "black", hex: "#212121", label: "Black/Dark" },
        { name: "gray", hex: "#757575", label: "Gray" },
        { name: "white", hex: "#F5F5F5", label: "White/Light" }
    ]

    function categoryInfo(name) {
        for (var i = 0; i < wallpaperPage.categoryColorModel.length; i++) {
            if (wallpaperPage.categoryColorModel[i].name === name) return wallpaperPage.categoryColorModel[i]
        }
        return { name: name, hex: "#888888", label: name }
    }

    background: Rectangle {
        color: "transparent"
    }

    // --- Main Layout ---

    RowLayout {
        anchors.fill: parent
        spacing: Kirigami.Units.smallSpacing

        // Left Pane
        Rectangle {
            id: leftPaneWallpapers
            color: Qt.alpha(Kirigami.Theme.backgroundColor, 0.80)
            
            // Collapsible logic
            Layout.preferredWidth: wallpaperPage.sidePaneOpen ? 300 : 0
            Layout.fillHeight: true
            radius: Kirigami.Units.largeSpacing
            border.color: Kirigami.Theme.highlightColor
            border.width: 1
            
            visible: Layout.preferredWidth > 0
            opacity: wallpaperPage.sidePaneOpen ? 1 : 0
            clip: true

            Behavior on Layout.preferredWidth { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.InOutQuad } }
            Behavior on opacity { OpacityAnimator { duration: Kirigami.Units.shortDuration } }
       
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.largeSpacing

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing
                    Label {
                        id: foldersLabel
                        text: qsTr("Folders")
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                        font.bold: true                        
                    }

                    ToolButton {
                        icon.name: "folder-new"
                        Layout.preferredWidth: Kirigami.Units.gridUnit * 2
                        ToolTip.text: qsTr("Add a wallpapers folder")
                        ToolTip.visible: hovered
                        onClicked: {controller.openFolderDialog()}               
                    }            
                }
                    
                MenuSeparator { Layout.fillWidth: true }

                Kirigami.CardsListView {
                    id: wallpaperCards
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: Kirigami.Units.smallSpacing
                    leftMargin: Kirigami.Units.smallSpacing
                    rightMargin: Kirigami.Units.smallSpacing
                    model: wallpaperFolderModel
                    delegate: Kirigami.AbstractCard {
                        id: card
                        required property string name
                        required property string path
                        required property int index

                        // ── Rename state ──────────────────────────────────────
                        property bool editing: false
                        property string pendingName: name

                        function startEditing() {
                            if (name === "Local") return
                            pendingName = name
                            editing = true
                            Qt.callLater(function() { nameField.forceActiveFocus(); nameField.selectAll() })
                        }
                        function confirmRename() {
                            editing = false
                            if (nameField.text.trim() !== "" && nameField.text.trim() !== name) {
                                controller.renameFolder(index, nameField.text.trim())
                            }
                        }
                        function cancelRename() {
                            editing = false
                        }

                        Layout.fillWidth: true
                        property bool isSelected: path === controller.selectedFolder

                        HoverHandler { id: cardHover }
                        property bool isHovered: cardHover.hovered

                        Rectangle {
                            anchors.fill: parent
                            color: "transparent"
                            border.color: isHovered ? Kirigami.Theme.focusColor : (isSelected ? Kirigami.Theme.highlightColor : Kirigami.Theme.alternateBackgroundColor)
                            border.width: isSelected ? 3 : 1
                            radius: Kirigami.Units.smallSpacing
                            visible: card.isSelected || card.isHovered
                        }

                        contentItem: Item {
                            implicitHeight: delegateLayout.implicitHeight

                            MouseArea {
                                id: mouseArea
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: if (!card.editing) controller.selectFolder(index)
                                onDoubleClicked: card.startEditing()
                                cursorShape: card.editing ? Qt.ArrowCursor : Qt.PointingHandCursor
                            }

                            GridLayout {
                                id: delegateLayout
                                anchors.fill: parent
                                columns: 2
                                columnSpacing: Kirigami.Units.smallSpacing
                                rowSpacing: Kirigami.Units.smallSpacing

                                ColumnLayout {
                                    Layout.fillWidth: true

                                    // ── View mode: static heading + pencil ────
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: Kirigami.Units.smallSpacing
                                        visible: !card.editing

                                        Kirigami.Heading {
                                            level: 2
                                            Layout.fillWidth: true
                                            text: name.includes("/") ? name.split('/').filter(Boolean).pop() : name
                                            elide: Text.ElideRight
                                        }

                                        ToolButton {
                                            icon.name: "edit-rename"
                                            icon.width: Kirigami.Units.iconSizes.small
                                            icon.height: Kirigami.Units.iconSizes.small
                                            padding: Kirigami.Units.smallSpacing / 2
                                            opacity: card.isHovered && name !== "Local" ? 1.0 : 0.0
                                            Behavior on opacity { OpacityAnimator { duration: Kirigami.Units.shortDuration } }
                                            ToolTip.text: qsTr("Rename folder")
                                            ToolTip.visible: hovered
                                            ToolTip.delay: Kirigami.Units.toolTipDelay
                                            onClicked: card.startEditing()
                                            // Prevent click from propagating to mouseArea (would also trigger selectFolder)
                                            MouseArea {
                                                anchors.fill: parent
                                                onClicked: (mouse) => { mouse.accepted = true; card.startEditing() }
                                                cursorShape: Qt.PointingHandCursor
                                            }
                                        }
                                    }

                                    // ── Edit mode: TextField ──────────────────
                                    TextField {
                                        id: nameField
                                        Layout.fillWidth: true
                                        visible: card.editing
                                        text: card.pendingName
                                        placeholderText: qsTr("Folder name...")
                                        selectByMouse: true
                                        onAccepted: card.confirmRename()
                                        Keys.onEscapePressed: card.cancelRename()
                                        onActiveFocusChanged: if (!activeFocus && card.editing) card.confirmRename()
                                    }

                                    Kirigami.Separator { Layout.fillWidth: true; color: Kirigami.Theme.alternateBackgroundColor }
                                    Label {
                                        Layout.fillWidth: true
                                        text: {
                                            if (name !== "Local") {
                                                return path.replace(controller.homePath, "~\/")
                                            } else {
                                                return path
                                            }
                                        }
                                        color: Kirigami.Theme.disabledTextColor
                                        font.pixelSize: Kirigami.Units.smallSpacing * 3
                                        elide: Text.ElideLeft
                                    }
                                }

                                ToolButton {
                                    id: removeFolderButton
                                    icon.name: "edit-delete"
                                    icon.width: Kirigami.Units.gridUnit
                                    icon.height: Kirigami.Units.gridUnit
                                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                                    enabled: !card.editing && name !== "Local"
                                    visible: !card.editing
                                    onClicked: {
                                        if (!enabled) return
                                        controller.removeFolder(index)
                                    }
                                    hoverEnabled: true
                                    ToolTip.text: qsTr("Remove this folder")
                                    ToolTip.visible: hovered
                                    ToolTip.delay: Kirigami.Units.toolTipDelay
                                }
                            }
                        }
                    }
                }
            }
        }
        // Right Pane
        Rectangle {
            id: rightPaneWallpapers
            color: "transparent"
            Layout.fillWidth: true
            Layout.fillHeight: true

            // --- Drawer State ---
            property bool drawerOpen: false
            property int selectedScoreColorIndex: 0
            property bool searchOpen: false

            // Applies the selected wallpaper and runs the custom commands.
            // Shared by the thumbnail button and the drawer button.
            function applySelectedWallpaper(isVideo) {
                var image = isVideo ? controller.thumbPath : controller.selectedWallpaper
                controller.setAsWallpaper(controller.selectedWallpaper, image)

                var commandsArray = []
                for (var i = 0; i < controller.customCommands.length; i++) {
                    var cmdObj = controller.customCommands[i]
                    if (!cmdObj || !cmdObj.enabled) continue
                    var cmd = cmdObj.command
                    if (!cmd || cmd.trim() === "") continue

                    cmd = expandPlaceholders(cmd, controller.selectedWallpaper, image)

                    commandsArray.push(cmd.trim())
                }

                if (commandsArray.length > 0) {
                    controller.runCMD(commandsArray.join(" && "))
                }
            }


            // Expands all placeholders in a command: %scolor%, %mode%, %ccolor%, %sc%, %path%, %image%.
            function expandPlaceholders(cmd, path, image) {
                var colors = controller.wallpaperColors
                var scolor = (colors && colors.length > rightPaneWallpapers.selectedScoreColorIndex)
                    ? colors[rightPaneWallpapers.selectedScoreColorIndex]
                    : ""
                cmd = cmd.replace(/%scolor%/g, scolor)
                         .replace(/%mode%/g, wallpaperPage.themeMode)
                         .replace(/%ccolor%/g, wallpaperPage.customColor)
                         .replace(/%sc%/g, rightPaneWallpapers.selectedScoreColorIndex.toString())
                         .replace(/%path%/g, '"' + path + '"')
                         .replace(/%image%/g, '"' + image + '"')
                return cmd
            }
            Connections {
                target: controller
                function onSelectedWallpaperChanged() {
                    rightPaneWallpapers.selectedScoreColorIndex = 0
                }
            }

            // Accessibility: Shortcut for Ctrl+F to toggle search
            Shortcut {
                sequence: "Ctrl+F"
                context: Qt.ApplicationShortcut
                onActivated: {
                    rightPaneWallpapers.searchOpen = !rightPaneWallpapers.searchOpen
                }
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing
                spacing: Kirigami.Units.smallSpacing

                // Header Info
                RowLayout {
                    Layout.fillWidth: true
                    //Layout.preferredHeight: Kirigami.Units.gridUnit * 2
                    
                    ToolButton {
                        icon.name: "view-list-details" 
                        checkable: true
                        checked: wallpaperPage.sidePaneOpen
                        onClicked: wallpaperPage.sidePaneOpen = checked
                        ToolTip.text: qsTr("Toggle Folders Panel")
                        ToolTip.visible: hovered
                        display: AbstractButton.IconOnly
                    }

                    Item { Layout.fillWidth: true }
                    
                    ColumnLayout {
                        id: headerTitle
                        spacing: 0
                        Layout.fillWidth: true
                        Layout.maximumWidth: 600
                    
                        Label {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            text: controller.selectedWallpaper ? controller.selectedWallpaper.split("/").pop() : ""
                            font.bold: true
                            elide: Text.ElideMiddle
                            visible: !rightPaneWallpapers.searchOpen
                        }
                        Label {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            text: controller.selectedWallpaperResolution
                            color: Kirigami.Theme.disabledTextColor
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                            visible: !rightPaneWallpapers.searchOpen
                        }

                        Kirigami.SearchField {
                            id: searchField
                            Layout.fillWidth: true
                            Layout.preferredWidth: 200
                            placeholderText: qsTr("Filter wallpapers...")
                            onTextChanged: imageModel.filterText = text
                            visible: rightPaneWallpapers.searchOpen

                            onVisibleChanged: {
                                    if (visible) {
                                        searchField.forceActiveFocus()
                                    }
                            }
                        }                        
                    }

                    Item { Layout.fillWidth: true }
                    
                    ToolButton {
                        icon.name: "search-symbolic"
                        checkable: true
                        checked: rightPaneWallpapers.searchOpen
                        onClicked: rightPaneWallpapers.searchOpen = checked
                        ToolTip.text: qsTr("Toggle Search Panel")
                        ToolTip.visible: hovered
                        display: AbstractButton.IconOnly
                    }

                    ToolButton {
                        icon.name: "preferences-system-symbolic"
                        checkable: true
                        checked: rightPaneWallpapers.drawerOpen
                        onClicked: rightPaneWallpapers.drawerOpen = checked
                        ToolTip.text: qsTr("Toggle Custom Scripts")
                        ToolTip.visible: hovered
                        display: AbstractButton.IconOnly
                    }
                }

                RowLayout {
                    id: colorFilterLayout
                    Layout.fillWidth: true
                    //width: searchField.width
                    Layout.alignment: Qt.AlignHCenter
                    visible: rightPaneWallpapers.searchOpen
                    spacing: Kirigami.Units.smallSpacing

                    Item { Layout.fillWidth: true }
                    Item { Layout.fillWidth: true }

                    Repeater {
                        model: wallpaperPage.categoryColorModel
                        delegate: Rectangle {
                            required property var modelData
                            width: Kirigami.Units.gridUnit * 1.5
                            height: width
                            radius: Kirigami.Units.smallSpacing
                            color: modelData.hex
                            border.color: imageModel.colorFilters.indexOf(modelData.name) !== -1 ? Kirigami.Theme.highlightColor : Qt.alpha(Kirigami.Theme.textColor, 0.3)
                            border.width: imageModel.colorFilters.indexOf(modelData.name) !== -1 ? 3 : 1

                            HoverHandler { id: filterHover }
                            TapHandler {
                                onTapped: {
                                    var currentFilters = imageModel.colorFilters.slice()
                                    var idx = currentFilters.indexOf(modelData.name)
                                    if (idx !== -1) {
                                        currentFilters.splice(idx, 1)
                                    } else {
                                        currentFilters.push(modelData.name)
                                    }
                                    imageModel.colorFilters = currentFilters
                                }
                            }

                            ToolTip.text: modelData.label
                            ToolTip.visible: filterHover.hovered
                        }
                    }
                    // "All" / Reset Button
                    ToolButton {
                        icon.name: "view-filter"
                        display: AbstractButton.TextBesideIcon
                        checkable: true
                        checked: imageModel.colorFilters.length === 0
                        onClicked: imageModel.colorFilters = []
                        ToolTip.text: qsTr("Reset Color Filter")
                        ToolTip.visible: hovered
                    }

                    Item { Layout.fillWidth: true }
                    Item { Layout.fillWidth: true }
                }
                
                MenuSeparator { Layout.fillWidth: true }
                // Grid View
                Item {
                    id: gridContainer
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    property string selWallpaper: ""
                    property string selWallpaperThumb: ""
                    property bool isVideo: false

                    Connections {
                        target: controller
                        function onInitialWallpaperIndexChanged() {
                            var idx = controller.initialWallpaperIndex
                            if (idx >= 0) {
                                Qt.callLater(function() {
                                    thumbnailGrid.positionViewAtIndex(idx, GridView.PositionViewCenter)
                                })
                            }
                        }
                        // BUG-1: keep selWallpaper/selWallpaperThumb/isVideo in sync via
                        // the controller signal instead of reading them synchronously right
                        // after selectWallpaper() (the Python side updates them asynchronously).
                        function onSelectedWallpaperChanged() {
                            gridContainer.selWallpaper = controller.selectedWallpaper
                            gridContainer.selWallpaperThumb = controller.thumbPath
                        }
                    }

                    ScrollView {
                        id: scrollView
                        anchors.fill: parent
                        clip: true

                        GridView {
                            id: thumbnailGrid
                            // Use anchors to bind to the viewport width securely
                            anchors.left: parent.left
                            anchors.right: parent.right
                            // Reserve space for the scrollbar to prevent visual overlap
                            anchors.rightMargin: Kirigami.Units.smallSpacing + Kirigami.Units.largeSpacing

                        
                            // Column count: at least 2, ~250px per column
                            property int columnCount: Math.max(2, Math.floor(width / 250))
                            cellWidth: Math.floor(width / thumbnailGrid.columnCount)
                            cellHeight: Math.floor(cellWidth * 0.5625)
                        
                            model: imageModel

                            // ── Grid transitions (matching the custom-commands feel) ──
                            // Note: GridView only supports "move" and "displaced"
                            // transitions (unlike ListView, which also has enter/exit).
                            // Animate an item sliding to its new cell when the model reorders.
                            move: Transition {
                                PropertyAnimation { property: "x"; duration: 300; easing.type: Easing.OutCubic }
                                PropertyAnimation { property: "y"; duration: 300; easing.type: Easing.OutCubic }
                                PropertyAnimation { property: "scale"; from: 0.94; to: 1.0; duration: 260; easing.type: Easing.OutCubic }
                            }

                            // Animate neighbours sliding out of the way while another item moves.
                            displaced: Transition {
                                PropertyAnimation { property: "x"; duration: 260; easing.type: Easing.OutCubic }
                                PropertyAnimation { property: "y"; duration: 260; easing.type: Easing.OutCubic }
                                PropertyAnimation { property: "scale"; from: 0.97; to: 1.0; duration: 220; easing.type: Easing.OutCubic }
                            }

                            delegate: Item {
                                id: thumbDelegate
                                width: thumbnailGrid.cellWidth
                                height: thumbnailGrid.cellHeight
                                // Center the scale origin so the move/displaced
                                // scale animations grow from the middle of the cell.
                                transformOrigin: Item.Center

                                required property string filePath
                                required property string fileName
                                required property string thumbPath
                                property bool isVideo: {
                                    var ext = fileName.substring(fileName.lastIndexOf(".")).toLowerCase()
                                    return [".mp4", ".webm", ".mkv", ".avi", ".mov", ".flv", ".m4v", ".wmv", ".3gp"].includes(ext)
                                }

                                property bool isSelected: filePath === controller.selectedWallpaper
                                property bool isHovered: hoverHandler.hovered

                                // Border flash, mirroring the custom-commands
                                // "flashHighlight": a short bright pulse fired on
                                // hover-enter and on selection.
                                property bool flashHighlight: false

                                function triggerFlash() {
                                    flashHighlight = true
                                    flashTimer.restart()
                                }

                                Timer {
                                    id: flashTimer
                                    interval: 420
                                    repeat: false
                                    onTriggered: thumbDelegate.flashHighlight = false
                                }

                                // Fire the flash when the pointer enters the cell.
                                HoverHandler {
                                    id: hoverHandler
                                    onHoveredChanged: {
                                        if (hovered) thumbDelegate.triggerFlash()
                                    }
                                }

                                // Fire the flash when this cell becomes selected.
                                onIsSelectedChanged: {
                                    if (isSelected) thumbDelegate.triggerFlash()
                                }

                                // Border drawn outside the clipped area so it's always visible
                                Rectangle {
                                    id: borderRect
                                    anchors.fill: parent
                                    anchors.margins: 2
                                    color: "transparent"
                                    // Selected cells keep the subtle neutral border so
                                    // the shimmer comet stays the clear focus; the
                                    // highlight color is reserved for hover only.
                                    border.color: thumbDelegate.flashHighlight
                                        ? Qt.lighter(Kirigami.Theme.highlightColor, 1.35)
                                        : (isSelected ? Qt.alpha(Kirigami.Theme.textColor, 0.80)
                                                      : (isHovered ? Kirigami.Theme.highlightColor : Qt.alpha(Kirigami.Theme.textColor, 0.30)))
                                    border.width: thumbDelegate.flashHighlight ? 4 : (isSelected ? 3 : 2)
                                    radius: Kirigami.Units.smallSpacing
                                    z: 10

                                    // Smooth border transitions on hover/selection,
                                    // matching the custom-commands flash feel.
                                    Behavior on border.color {
                                        ColorAnimation {
                                            duration: 220
                                            easing.type: Easing.OutCubic
                                        }
                                    }
                                    Behavior on border.width {
                                        NumberAnimation {
                                            duration: 220
                                            easing.type: Easing.OutCubic
                                        }
                                    }
                                }

                                // Shimmer border: a comet of light that travels around
                                // the full perimeter of the cell while it is selected,
                                // signalling the active state. The fixed border stays
                                // in the subtle neutral color.
                                //
                                // Rendered on the GPU with a fragment shader: the
                                // rounded-rect border, the perimeter position and the
                                // gaussian glow band are computed analytically per
                                // pixel, so the CPU only updates the u_head uniform
                                // per tick (no QPainter repaints, no shadowBlur).
                                ShaderEffect {
                                    id: shimmerCanvas
                                    anchors.fill: parent
                                    anchors.margins: 2
                                    visible: isSelected
                                    z: 11

                                    // ── Sweep parameters ─────────────────────────────────
                                    // A soft, symmetric "searchlight" band that circles the
                                    // perimeter endlessly. No pause, no fade-out-then-back-in:
                                    // on a closed loop that stop/restart always reads as a
                                    // seam, so instead the band just keeps travelling forever
                                    // and the loop itself (going around and around) is what
                                    // reads as continuous.

                                    // Speed: seconds for one full revolution around
                                    // the perimeter.
                                    property real revolutionDuration: 3.0

                                    // How many glowing bands travel the perimeter at
                                    // once, evenly spaced around the loop (1 = the
                                    // original single comet, 2 = two opposite lights,
                                    // etc).
                                    property int lightCount: 2

                                    // Band: width as a fraction of the perimeter
                                    // (measured off the reference clip: ~90px of a
                                    // ~670px edge, i.e. ~0.13-0.15).
                                    property real bandFraction: 0.14
                                    // Band: how peaked the glow is across its width.
                                    // Higher = narrower, snappier band.
                                    property real bandSharpness: 2.2
                                    // Band: core line width in px.
                                    property real coreWidth: 2.4
                                    // Band: peak opacity of the core stroke.
                                    property real coreOpacity: 0.9
                                    // Band: soft blur radius (px) that gives the glow
                                    // its diffuse, out-of-focus look.
                                    property real glowBlur: 5.0
                                    // Band: color.
                                    property color glowColor: Qt.lighter(Kirigami.Theme.positiveTextColor, 1.4) //Qt.lighter(Kirigami.Theme.highlightColor, 1.4)

                                    // Head position along the perimeter, 0..1 (loops).
                                    property real head: 0.0

                                    // Precompiled shader package (baked from
                                    // ../shaders/shimmer_border.frag with the qsb tool,
                                    // see scripts/build_shaders.sh).
                                    fragmentShader: "../shaders/shimmer_border.qsb"

                                    // Uniforms: property names must match the shader's
                                    // uniform block members. QML types map to GLSL
                                    // (real -> float, var QSize -> vec2, color -> vec4).
                                    property real u_head: head
                                    property real u_radius: Math.min(Kirigami.Units.smallSpacing, width / 2, height / 2)
                                    property real u_bandFraction: bandFraction
                                    property real u_bandSharpness: bandSharpness
                                    property real u_coreWidth: coreWidth
                                    property real u_coreOpacity: coreOpacity
                                    property real u_glowBlur: glowBlur
                                    property real u_lightCount: lightCount
                                    property real u_inset: 1.5
                                    property var u_size: Qt.size(width, height)
                                    property color u_color: glowColor

                                    // Advance the head with a timer so the loop is
                                    // perfectly continuous (no restart seam). The step
                                    // per tick is derived from revolutionDuration.
                                    Timer {
                                        interval: 16
                                        running: shimmerCanvas.visible && wallpaperPage.visible
                                        repeat: true
                                        onTriggered: {
                                            const step = interval / (shimmerCanvas.revolutionDuration * 1000.0)
                                            shimmerCanvas.head = (shimmerCanvas.head + step) % 1.0
                                        }
                                    }
                                }

                                Rectangle {
                                    id: thumbContainer
                                    anchors.fill: parent
                                    anchors.margins: Kirigami.Units.smallSpacing
                                    color: "transparent"
                                    radius: Kirigami.Units.smallSpacing
                                    clip: true

                                    TapHandler {
                                        onTapped: {
                                            controller.selectWallpaper(filePath)
                                            gridContainer.isVideo = isVideo
                                        }
                                        onDoubleTapped: {
                                            controller.selectWallpaper(filePath)
                                            gridContainer.isVideo = isVideo
                                            lightboxPopup.open()
                                        }
                                    }

                                    Image {
                                        id: thumbImg
                                        anchors.fill: parent
                                        source: thumbPath ? thumbPath : "file://" + filePath
                                        fillMode: Image.PreserveAspectCrop
                                        asynchronous: true
                                        smooth: true
                                    
                                        // More dramatic zoom: a clear lift on hover plus a
                                        // subtle resting scale for the selected cell.
                                        scale: isHovered ? 1.14 : (isSelected ? 1.06 : 1.0)
                                        Behavior on scale {
                                            SpringAnimation {
                                                spring: 8.0
                                                damping: 0.55
                                                mass: 1.0
                                            }
                                        }

                                        opacity: status === Image.Ready ? 1.0 : 0.0
                                        Behavior on opacity { NumberAnimation { duration: Kirigami.Units.longDuration; easing.type: Easing.InOutQuad } }
                                    }

                                    BusyIndicator {
                                        anchors.centerIn: parent
                                        running: thumbImg.status === Image.Loading
                                        visible: running
                                    }

                                    // Inline video playback: loads only for the selected video cell
                                    Loader {
                                        id: inlineVideoLoader
                                        anchors.fill: parent
                                        active: isVideo && isSelected && wallpaperPage.visible
                                        asynchronous: true

                                        sourceComponent: Item {
                                            anchors.fill: parent

                                            MediaPlayer {
                                                id: inlineVideoPlayer
                                                source: "file://" + filePath
                                                videoOutput: inlineVideoOutput
                                                audioOutput: AudioOutput { muted: true }
                                                loops: MediaPlayer.Infinite
                                                Component.onCompleted: play()
                                            }

                                            VideoOutput {
                                                id: inlineVideoOutput
                                                anchors.fill: parent
                                                fillMode: VideoOutput.PreserveAspectCrop
                                            }
                                        }
                                    }

                                    Rectangle {
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        anchors.margins: Kirigami.Units.smallSpacing * 2
                                        radius: Kirigami.Units.cornerRadius
                                        visible: controller.showExtensionBadge && fileName.includes(".")
                                        color: Qt.alpha(Kirigami.Theme.backgroundColor, 0.80)
                                        width: extLabel.implicitWidth + Kirigami.Units.smallSpacing * 2
                                        height: extLabel.implicitHeight + Kirigami.Units.smallSpacing
                                        border.color: Kirigami.Theme.highlightColor
                                        border.width: 0.5

                                        Label {
                                            id: extLabel
                                            anchors.centerIn: parent
                                            text: {
                                                var dot = fileName.lastIndexOf(".")
                                                return dot !== -1 ? fileName.substring(dot + 1).toUpperCase() : ""
                                            }
                                            color: Kirigami.Theme.textColor
                                            font.pointSize: Kirigami.Theme.smallFont.pointSize * 0.8
                                            font.bold: true
                                        }
                                    }

                                    Rectangle {
                                        id: colorDotsContainer
                                        anchors.left: parent.left
                                        anchors.bottom: parent.bottom
                                        anchors.margins: Kirigami.Units.smallSpacing * 2
                                        radius: Kirigami.Units.cornerRadius
                                        visible: isSelected
                                        color: Qt.alpha(Kirigami.Theme.backgroundColor, 0.80)
                                        width: colorDots.implicitWidth + Kirigami.Units.smallSpacing * 2
                                        height: colorDots.implicitHeight + Kirigami.Units.smallSpacing
                                        border.color: Kirigami.Theme.highlightColor
                                        border.width: 0.5

                                        RowLayout {
                                            id: colorDots
                                            anchors.centerIn: parent
                                            spacing: 2
                                            visible: isSelected

                                            Repeater {
                                                model: controller.wallpaperColors
                                                delegate: Rectangle {
                                                    required property string modelData
                                                    required property int index
                                                    width: Kirigami.Units.gridUnit * 0.8
                                                    height: width
                                                    radius: Kirigami.Units.smallSpacing 
                                                    color: modelData
                                                    border.color: rightPaneWallpapers.selectedScoreColorIndex === index ? Kirigami.Theme.positiveTextColor : Qt.alpha(Kirigami.Theme.textColor, 0.5)
                                                    border.width: rightPaneWallpapers.selectedScoreColorIndex === index ? 2 : 1

                                                    HoverHandler { id: colorHover }
                                                    TapHandler {
                                                        acceptedButtons: Qt.LeftButton
                                                        onTapped: rightPaneWallpapers.selectedScoreColorIndex = index
                                                    }
                                                    TapHandler {
                                                        acceptedButtons: Qt.RightButton
                                                        onTapped: clipboardHelper.copyToClipboard(modelData)
                                                    }
                                                    ToolTip.text: modelData.toUpperCase()
                                                    ToolTip.visible: colorHover.hovered
                                                    ToolTip.delay: Kirigami.Units.toolTipDelay
                                                }
                                            }
                                        }
                                    }

                                    ToolButton {
                                        id: setWallpaperButton
                                        anchors.top: parent.top
                                        anchors.right: parent.right
                                        anchors.margins: Kirigami.Units.smallSpacing
                                        icon.name: "dialog-ok-apply"
                                        icon.color: Kirigami.Theme.positiveTextColor
                                        display: AbstractButton.IconOnly
                                        visible: isSelected
                                        onClicked: rightPaneWallpapers.applySelectedWallpaper(isVideo)
                                        ToolTip.text: qsTr("Set as Wallpaper")
                                        ToolTip.visible: hovered
                                    }

                                    ToolTip.text: fileName
                                    ToolTip.visible: hoverHandler.hovered
                                    ToolTip.delay: Kirigami.Units.toolTipDelay
                                }
                            }
                        }
                    }

                    Kirigami.PlaceholderMessage {
                        anchors.centerIn: parent
                        width: parent.width - Kirigami.Units.largeSpacing * 4
                        icon.name: "edit-none"
                        text: rightPaneWallpapers.searchOpen
                              ? qsTr("No wallpapers match your search")
                              : qsTr("No wallpapers found")
                        visible: !imageModel.loading && thumbnailGrid.count === 0
                    }
                }
            }
            
            BusyIndicator {
                anchors.centerIn: parent
                running: imageModel.loading
                visible: running
            }

            Components.ClipboardHelper {
                id: clipboardHelper
            }

            // Transparent blocker above the grid (z:50) that intercepts events while the
            // drawer is open, preventing TapHandler passthrough to grid delegates.
            Rectangle {
                id: drawerBlocker
                anchors.horizontalCenter: parent.horizontalCenter
                z: 50

                width: bottomDrawer.width
                height: bottomDrawer.height
                y: bottomDrawer.y

                visible: bottomDrawer.visible
                enabled: bottomDrawer.visible

                color: "transparent"

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.AllButtons
                    propagateComposedEvents: false
                    preventStealing: true
                    onWheel: (wheel) => wheel.accepted = true
                    onPressed: (mouse) => mouse.accepted = true
                    onClicked: (mouse) => mouse.accepted = true
                    onReleased: (mouse) => mouse.accepted = true
                    onDoubleClicked: (mouse) => mouse.accepted = true
                }
            }

            // Bottom Drawer
            Rectangle {
                id: bottomDrawer
                // Use y position for sliding animation instead of anchors.bottom
                anchors.horizontalCenter: parent.horizontalCenter

                z: 100 // Stays above the grid in hit-testing, not just visually

                width: parent.width - Kirigami.Units.largeSpacing //* 4
                height: (drawerContent.implicitHeight + Kirigami.Units.largeSpacing * 2 ) 

                property bool isOpen: rightPaneWallpapers.drawerOpen
                property int showNumCustCommands: 4

                // Slide up from bottom
                y: isOpen ? parent.height - height - Kirigami.Units.largeSpacing * 2 : parent.height
                opacity: isOpen ? 1.0 : 0.0
                visible: opacity > 0.001
                enabled: visible // Stays interactive while visually reachable (incl. close animation)

                Behavior on y { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic } }
                Behavior on height { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic } }
                Behavior on opacity { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic } }

                radius: Kirigami.Units.largeSpacing
                color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g, Kirigami.Theme.backgroundColor.b, 0.95)
                border.color: Kirigami.Theme.highlightColor
                border.width: 1

                ColumnLayout {
                    id: drawerContent
                    anchors.fill: parent
                    anchors.margins: Kirigami.Units.largeSpacing
                    spacing: Kirigami.Units.smallSpacing

                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            text: qsTr("Custom Commands")
                            font.bold: true
                            Layout.fillWidth: true
                        }
                        Item { Layout.fillWidth: true } // Spacer
                        
                        // Theme Mode Toggle
                        RowLayout {
                            Layout.fillWidth: true

                            Kirigami.Icon {
                                source: "lighttable-symbolic"
                                fallback: "dark-mode-symbolic"
                                Layout.preferredWidth: Kirigami.Units.gridUnit
                                Layout.preferredHeight: Kirigami.Units.gridUnit
                                color: Kirigami.Theme.highlightColor
                            }

                            Switch {
                                id: themeModeToggle //mode dark/light save in property themeMode
                                checked: themeMode === "dark"

                                ToolTip.text:
                                    checked
                                    ? qsTr("Dark")
                                    : qsTr("Light")

                                ToolTip.visible: hovered

                                onToggled: {
                                    themeMode = checked ? "dark" : "light"
                                }
                            }
                        }

                        Item { Layout.fillWidth: true } // Spacer
                        
                        ToolButton {
                            icon.name: "dialog-ok-apply"
                            icon.color: Kirigami.Theme.positiveTextColor
                            display: AbstractButton.IconOnly
                            enabled: controller.selectedWallpaper !== ""
                            onClicked: rightPaneWallpapers.applySelectedWallpaper(gridContainer.isVideo)
                            ToolTip.text: qsTr("Set as Wallpaper")
                            ToolTip.visible: hovered
                        }

                        ToolButton {
                            icon.name: "dialog-close"
                            icon.color: Kirigami.Theme.negativeTextColor
                            display: AbstractButton.IconOnly
                            onClicked: rightPaneWallpapers.drawerOpen = false
                            ToolTip.text: qsTr("Close Preferences")
                            ToolTip.visible: hovered
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        id: drawerPlaceholderOptions
                        spacing: Kirigami.Units.smallSpacing
                        
                        RowLayout {
                            //Layout.fillWidth: true
                            // Matugen source color index label
                            Label {
                                //Layout.fillWidth: true
                                text: qsTr("Matugen source color index: %1").arg(rightPaneWallpapers.selectedScoreColorIndex)
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                color: Kirigami.Theme.disabledTextColor
                                //elide: Text.ElideRight
                            }

                            // Color Dots for Matugen source color index
                            RowLayout {
                                id: colorDotsCC
                                spacing: 2
                                Layout.alignment: Qt.AlignVCenter

                                Repeater {
                                    model: controller.wallpaperColors
                                    delegate: Rectangle {
                                        required property string modelData
                                        required property int index
                                        width: Kirigami.Units.gridUnit * 0.8
                                        height: width
                                        radius: Kirigami.Units.smallSpacing 

                                        color: modelData
                                        border.color: rightPaneWallpapers.selectedScoreColorIndex === index ? Kirigami.Theme.positiveTextColor : Qt.alpha(Kirigami.Theme.textColor, 0.5)
                                        border.width: rightPaneWallpapers.selectedScoreColorIndex === index ? 2 : 1

                                        HoverHandler { id: colorHoverCC }
                                        MouseArea {
                                            anchors.fill: parent
                                            hoverEnabled: false // El hover ya lo gestiona HoverHandler arriba
                                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                                            propagateComposedEvents: false
                                            preventStealing: true
                                            onPressed: (mouse) => mouse.accepted = true
                                            onClicked: (mouse) => {
                                                if (mouse.button === Qt.LeftButton) {
                                                    rightPaneWallpapers.selectedScoreColorIndex = index
                                                } else if (mouse.button === Qt.RightButton) {
                                                    clipboardHelper.copyToClipboard(modelData)
                                                }
                                                mouse.accepted = true
                                            }
                                        }
                                        ToolTip.text: modelData.toUpperCase()
                                        ToolTip.visible: colorHoverCC.hovered
                                        ToolTip.delay: Kirigami.Units.toolTipDelay
                                    }
                                }
                            }
                        }

                        Item { Layout.fillWidth: true } // Spacer
                    }
                    
                    RowLayout {
                        //Layout.fillWidth: true
                        // Custom color picker
                        Label {
                            //Layout.fillWidth: true
                            text: qsTr("Custom color:")
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                            color: Kirigami.Theme.disabledTextColor
                            //elide: Text.ElideRight
                        }
                        // Color Picker for custom color picked stored in customColor
                        Rectangle {
                            id: colorPreview
                            Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                            width: Kirigami.Units.gridUnit * 0.8
                            height: Kirigami.Units.gridUnit * 0.8

                            //transparent if no color is selected
                            color: customColor === "" ? "transparent" : customColor

                            border.color: Kirigami.Theme.disabledTextColor
                            border.width: 1
                            radius: Kirigami.Units.smallSpacing

                            ToolTip.text: {
                                if (!controller) return qsTr("Pick color")
                                var t = controller.formatColorWithAlpha(customColor)
                                return t && t !== "" ? t : qsTr("Pick color")
                            }
                            ToolTip.delay: Kirigami.Units.toolTipDelay
                            ToolTip.visible: colorPreviewMouse.containsMouse

                            MouseArea {
                                id: colorPreviewMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                acceptedButtons: Qt.LeftButton | Qt.RightButton
                                onClicked: (mouse) => {
                                    if (mouse.button === Qt.RightButton) {
                                        clipboardHelper.copyToClipboard(customColor !== "" ? customColor : colorPreview.color.toString())
                                        return
                                    }
                                    if (!controller) return;
                                    var currentColor = customColor;
                                    var color = controller.openColorDialog(currentColor === "" ? "transparent" : currentColor);
                                    if (color) {
                                        customColor = color;
                                    }
                                }
                            }
                        }
                    }
                    
                    RowLayout {
                        Layout.fillWidth: true

                        Label {
                            id: placeholdersLabel
                            Layout.fillWidth: true
                            textFormat: Text.RichText
                            text: qsTr("Placeholders: <br><b>%path%</b> path, <b>%image%</b> image/video thumb path.<br><b>%ccolor%</b> custom color, <b>%mode%</b> theme mode (dark/light).<br><b>%sc%</b> selected color index, <b>%scolor%</b> selected color hex.<br>")
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                            color: Kirigami.Theme.disabledTextColor
                        }

                        ToolButton {
                            icon.name: "list-add"
                            text: qsTr("Add")
                            ToolTip.visible: hovered
                            ToolTip.text: qsTr("Add new command")
                            onClicked: {
                                controller.addCustomCommand("")
                            }
                        }
                    }

                    Timer {
                        id: reorderPersistTimer
                        interval: 260
                        repeat: false
                        onTriggered: {
                            commandsProxy.dragging = false
                            commandsProxy.persistToController()
                        }
                    }

                    // ── Local proxy model for drag-and-drop ──
                    ListModel {
                        id: commandsProxy

                        // true while a drag gesture is in progress;
                        // blocks sync from Python so the proxy stays stable.
                        property bool dragging: false

                        function syncFromController() {
                            if (dragging) return
                            clear()
                            var cmds = controller.customCommands
                            for (var i = 0; i < cmds.length; i++) {
                                append({
                                    command: cmds[i].command,
                                    cmdEnabled: cmds[i].enabled
                                })
                            }
                        }

                        // Push the current proxy order back to the
                        // Python controller as a single bulk update.
                        function persistToController() {
                            var result = []
                            for (var i = 0; i < count; i++) {
                                var item = get(i)
                                result.push({
                                    command: item.command,
                                    enabled: item.cmdEnabled
                                })
                            }
                            controller.customCommands = result
                        }

                        Component.onCompleted: syncFromController()
                    }

                    Connections {
                        target: controller
                        function onCustomCommandsChanged() {
                            commandsProxy.syncFromController()
                        }
                    }

                    ListView {
                        id: customCommandsList

                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(
                            contentHeight,
                            bottomDrawer.showNumCustCommands * rowHeight
                                + Math.max(0, bottomDrawer.showNumCustCommands - 1) * spacing
                        )

                        // Shared row height: the cap above and the delegate below derive from it.
                        property real rowHeight: Kirigami.Units.gridUnit * 3

                        clip: true
                        spacing: Kirigami.Units.smallSpacing

                        model: commandsProxy

                        // Estado del arrastre para el Overlay
                        property int draggedIndex: -1
                        property string draggedCommand: ""

                        // Animate item movement naturally when the list is reordered
                        // through the buttons or drag interactions.
                        move: Transition {
                            ParallelAnimation {
                                NumberAnimation {
                                    properties: "x,y"
                                    duration: 320
                                    easing.type: Easing.OutCubic
                                }
                                NumberAnimation {
                                    property: "scale"
                                    from: 0.94
                                    to: 1.0
                                    duration: 260
                                    easing.type: Easing.OutCubic
                                }
                            }
                        }

                        // Animate neighbours sliding out of the way
                        // while a delegate is being dragged past them.
                        displaced: Transition {
                            ParallelAnimation {
                                NumberAnimation {
                                    properties: "x,y"
                                    duration: 260
                                    easing.type: Easing.OutCubic
                                }
                                NumberAnimation {
                                    property: "scale"
                                    from: 0.97
                                    to: 1.0
                                    duration: 220
                                    easing.type: Easing.OutCubic
                                }
                            }
                        }

                        // ── Floating element for the drag (outside the ListView layout) ──
                        Rectangle {
                            id: dragOverlay
                            parent: customCommandsList
                            width: customCommandsList.width
                            height: customCommandsList.rowHeight
                            z: 999
                            visible: customCommandsList.draggedIndex !== -1

                            color: Qt.alpha(Kirigami.Theme.highlightColor, 0.25)
                            border.color: Kirigami.Theme.highlightColor
                            border.width: 2
                            radius: Kirigami.Units.smallSpacing

                            Drag.active: visible
                            Drag.source: dragOverlay
                            Drag.hotSpot.x: width / 2
                            Drag.hotSpot.y: height / 2

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: Kirigami.Units.smallSpacing
                                spacing: Kirigami.Units.smallSpacing

                                Label {
                                    Layout.preferredWidth: Kirigami.Units.gridUnit * 1.5
                                    text: (customCommandsList.draggedIndex + 1).toString()
                                    horizontalAlignment: Text.AlignHCenter
                                    font.bold: true
                                    color: Kirigami.Theme.highlightColor
                                }

                                Kirigami.Icon {
                                    source: "view-sort"
                                    width: Kirigami.Units.gridUnit
                                    height: width
                                    color: Kirigami.Theme.highlightColor
                                }

                                Label {
                                    Layout.fillWidth: true
                                    text: customCommandsList.draggedCommand
                                    elide: Text.ElideRight
                                    color: Kirigami.Theme.textColor
                                    font.bold: true
                                }
                            }
                        }

                        // ── Auto-scroll while dragging near edges ──
                        property Item draggedItem: null
                        property real autoScrollMargin: Kirigami.Units.gridUnit * 2
                        property real autoScrollStep: Kirigami.Units.gridUnit * 0.6

                        Timer {
                            id: autoScrollTimer
                            interval: 30
                            repeat: true
                            running: customCommandsList.draggedItem !== null

                            onTriggered: {
                                var item = customCommandsList.draggedItem
                                if (!item) return

                                var yInView = item.y + item.height / 2
                                var margin = customCommandsList.autoScrollMargin
                                var step   = customCommandsList.autoScrollStep

                                if (yInView < margin) {
                                    customCommandsList.contentY = Math.max(
                                        customCommandsList.originY,
                                        customCommandsList.contentY - step
                                    )
                                } else if (yInView > customCommandsList.height - margin) {
                                    var maxY = customCommandsList.contentHeight
                                            - customCommandsList.height
                                            + customCommandsList.originY
                                    customCommandsList.contentY = Math.min(
                                        maxY,
                                        customCommandsList.contentY + step
                                    )
                                }
                            }
                        }

                        delegate: Item {
                            id: commandDelegate

                            required property int index
                            required property string command
                            required property bool cmdEnabled

                            width: customCommandsList.width
                            height: customCommandsList.rowHeight

                            property bool flashHighlight: false

                            // Active element behaves like a transparent hole in the list, allowing the drag overlay to show through.
                            opacity: commandDelegate.index === customCommandsList.draggedIndex ? 0.3 : 1.0

                            function triggerHighlight() {
                                flashHighlight = true
                                cmdFlashTimer.restart()
                            }

                            Timer {
                                id: cmdFlashTimer
                                interval: 420
                                repeat: false
                                onTriggered: commandDelegate.flashHighlight = false
                            }

                            // Background
                            Rectangle {
                                anchors.fill: parent
                                radius: Kirigami.Units.smallSpacing
                                color: Qt.alpha(Kirigami.Theme.backgroundColor, 0.80)
                                border.color: commandDelegate.flashHighlight ? Qt.lighter(Kirigami.Theme.highlightColor, 1.35) : Kirigami.Theme.alternateBackgroundColor
                                border.width: commandDelegate.flashHighlight ? 3 : 1
                                Behavior on border.color {
                                    ColorAnimation {
                                        duration: 220
                                        easing.type: Easing.OutCubic
                                    }
                                }
                                Behavior on border.width {
                                    NumberAnimation {
                                        duration: 220
                                        easing.type: Easing.OutCubic
                                    }
                                }
                            }

                            // Reordering target
                            DropArea {
                                anchors.fill: parent
                                onEntered: function(drag) {
                                    var from = customCommandsList.draggedIndex
                                    var to   = commandDelegate.index
                                    if (from !== -1 && from !== to) {
                                        commandsProxy.move(from, to, 1)
                                        customCommandsList.draggedIndex = to
                                        commandDelegate.triggerHighlight()
                                    }
                                }
                            }

                            // Main content
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: Kirigami.Units.smallSpacing
                                spacing: Kirigami.Units.smallSpacing

                                // Priority number
                                Label {
                                    Layout.preferredWidth: Kirigami.Units.gridUnit * 1.5
                                    Layout.fillHeight: true
                                    text: (commandDelegate.index + 1).toString()

                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    font.bold: true
                                    color: commandDelegate.cmdEnabled ? Kirigami.Theme.highlightColor : Kirigami.Theme.disabledTextColor
                                }

                                // Drag handle
                                Item {
                                    Layout.preferredWidth: Kirigami.Units.gridUnit
                                    Layout.fillHeight: true

                                    Kirigami.Icon {
                                        anchors.centerIn: parent
                                        source: "view-sort"
                                        width: Kirigami.Units.gridUnit
                                        height: width
                                        color: commandDelegate.index === customCommandsList.draggedIndex ? Kirigami.Theme.highlightColor : Kirigami.Theme.disabledTextColor
                                    }

                                    MouseArea {
                                        id: dragArea
                                        anchors.fill: parent
                                        hoverEnabled: true

                                        cursorShape:
                                            pressed
                                            ? Qt.ClosedHandCursor
                                            : Qt.OpenHandCursor

                                        drag.target: dragOverlay
                                        drag.axis: Drag.YAxis

                                        onPressed: {
                                            commandsProxy.dragging = true
                                            var mapped = commandDelegate.mapToItem(customCommandsList, 0, 0)
                                            dragOverlay.y = mapped.y
                                            customCommandsList.draggedIndex = commandDelegate.index
                                            customCommandsList.draggedCommand = commandDelegate.command
                                            customCommandsList.draggedItem = dragOverlay
                                        }

                                        onReleased: {
                                            customCommandsList.draggedItem = null
                                            customCommandsList.draggedIndex = -1
                                            commandDelegate.triggerHighlight()
                                            reorderPersistTimer.restart()
                                        }
                                    }
                                }

                                // Enable / disable
                                Switch {
                                    checked: commandDelegate.cmdEnabled

                                    ToolTip.text:
                                        checked
                                        ? qsTr("Enabled")
                                        : qsTr("Disabled")

                                    ToolTip.visible: hovered

                                    onToggled: {
                                        controller.setCustomCommandEnabled(
                                            commandDelegate.index,
                                            checked
                                        )
                                    }
                                }

                                // Command text
                                TextField {
                                    id: cmdInput

                                    Layout.fillWidth: true

                                    text: commandDelegate.command

                                    placeholderText:
                                        qsTr(
                                            "e.g: notify-send 'Wallpaper changed to %path%'"
                                        )

                                    placeholderTextColor:
                                        Kirigami.Theme.disabledTextColor

                                    opacity:
                                        commandDelegate.cmdEnabled
                                        ? 1.0
                                        : 0.5

                                    onEditingFinished: {
                                        controller.updateCustomCommand(
                                            commandDelegate.index,
                                            cmdInput.text
                                        )
                                    }
                                }

                                // Remove command
                                ToolButton {
                                    icon.name: "edit-clear"

                                    ToolTip.text:
                                        qsTr("Remove command")

                                    ToolTip.visible: hovered

                                    onClicked: {
                                        controller.removeCustomCommand(
                                            commandDelegate.index
                                        )
                                    }
                                }

                                // Execute individual command
                                ToolButton {
                                    icon.name: "media-playback-start"

                                    ToolTip.text:
                                        qsTr("Execute individual command")

                                    ToolTip.visible: hovered

                                    onClicked: {
                                        var image =
                                            gridContainer.isVideo
                                            ? controller.thumbPath
                                            : controller.selectedWallpaper

                                        var cmd = cmdInput.text

                                        controller.runCMD(expandPlaceholders(cmd, controller.selectedWallpaper, image).trim())
                                    }
                                }

                                // Move up
                                ToolButton {
                                    icon.name: "go-up"

                                    enabled:
                                        commandDelegate.index > 0

                                    ToolTip.text:
                                        qsTr("Move command up")

                                    ToolTip.visible: hovered

                                    onClicked: {
                                        var from = commandDelegate.index
                                        var to = from - 1
                                        if (from > 0) {
                                            commandsProxy.dragging = true
                                            commandsProxy.move(from, to, 1)
                                            commandDelegate.triggerHighlight()
                                            reorderPersistTimer.restart()
                                        }
                                    }
                                }

                                // Move down
                                ToolButton {
                                    icon.name: "go-down"

                                    enabled:
                                        commandDelegate.index <
                                        customCommandsList.count - 1

                                    ToolTip.text:
                                        qsTr("Move command down")

                                    ToolTip.visible: hovered

                                    onClicked: {
                                        var from = commandDelegate.index
                                        var to = from + 1
                                        if (from < customCommandsList.count - 1) {
                                            commandsProxy.dragging = true
                                            commandsProxy.move(from, to, 1)
                                            commandDelegate.triggerHighlight()
                                            reorderPersistTimer.restart()
                                        }
                                    }
                                }
                            }
                        }
                    }                
                }
            }

            // Lightbox Popup
            Components.LightboxPopup {
                id: lightboxPopup
                gridContainer: gridContainer
                rightPane: rightPaneWallpapers
                pageRef: wallpaperPage
                categoryEditor: categoryEditorPopup
                clipboard: clipboardHelper
            }

            // Color Category Editor Popup
            Components.CategoryEditorPopup {
                id: categoryEditorPopup
                pageRef: wallpaperPage
                lightbox: lightboxPopup
            }
        }
    }
}
