pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import org.kde.kirigami as Kirigami

Kirigami.Page {
    id: wallpaperPage
    title: qsTr("Wallpapers")
    
    // State for sidebar
    property bool sidePaneOpen: false

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
            //color: Kirigami.Theme.backgroundColor
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

                        Layout.fillWidth: true
                        // Visually indicate selection by comparing the folder path with controller.selectedFolder
                        property bool isSelected: path === controller.selectedFolder
                        property bool isHovered: mouseArea.containsMouse

                        // Selection border
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
                                onClicked: controller.selectFolder(index)
                                cursorShape: Qt.PointingHandCursor
                            }
                            
                            GridLayout {
                                id: delegateLayout
                                anchors.fill: parent
                                columns: 2
                                columnSpacing: Kirigami.Units.smallSpacing
                                rowSpacing: Kirigami.Units.smallSpacing
                                ColumnLayout {
                                    Kirigami.Heading {
                                        level: 2
                                        text: name.includes("/") ? name.split('/').filter(Boolean).pop() : name
                                    }
                                    Kirigami.Separator {Layout.fillWidth: true; color: Kirigami.Theme.alternateBackgroundColor}
                                    Label {
                                        Layout.fillWidth: true
                                        // wrapMode: Text.WordWrap
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
                                    icon.name: "edit-clear"
                                    icon.width: Kirigami.Units.gridUnit
                                    icon.height: Kirigami.Units.gridUnit
                                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                                    // Disable removal for the built-in Local folder
                                    enabled: name !== "Local"
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

            Connections {
                target: controller
                function onSelectedWallpaperChanged() {
                    rightPaneWallpapers.selectedScoreColorIndex = 0
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
                        onToggled: wallpaperPage.sidePaneOpen = checked
                        ToolTip.text: qsTr("Toggle Folders Panel")
                        ToolTip.visible: hovered
                        display: AbstractButton.IconOnly
                    }

                    Item { Layout.fillWidth: true }
                    
                    ColumnLayout {
                        id: headerTitle
                        spacing: 0
                        //visible: controller.selectedWallpaper !== ""
                        Layout.fillWidth: true          // ← acota el ancho
                        Layout.maximumWidth: 600        // ← opcional: límite razonable
                    
                        Label {
                            Layout.fillWidth: true      // ← necesario para que elide funcione
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
                        onToggled: rightPaneWallpapers.searchOpen = checked
                        ToolTip.text: qsTr("Toggle Search Panel")
                        ToolTip.visible: hovered
                        display: AbstractButton.IconOnly
                    }

                    ToolButton {
                        icon.name: "preferences-system-symbolic"
                        checkable: true
                        checked: rightPaneWallpapers.drawerOpen
                        onToggled: rightPaneWallpapers.drawerOpen = checked
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

                    // "All" / Reset Button
                    ToolButton {
                        icon.name: "view-filter"
                        text: qsTr("All")
                        display: AbstractButton.TextBesideIcon
                        checkable: true
                        checked: imageModel.colorFilter === ""
                        onClicked: imageModel.colorFilter = ""
                    }

                    Item { Layout.fillWidth: true }               

                    Repeater {
                        model: wallpaperPage.categoryColorModel
                        delegate: Rectangle {
                            required property var modelData
                            width: Kirigami.Units.gridUnit * 1.5
                            height: width
                            radius: Kirigami.Units.smallSpacing
                            //radius: width / 2
                            color: modelData.hex
                            border.color: imageModel.colorFilter === modelData.name ? Kirigami.Theme.highlightColor : Qt.alpha(Kirigami.Theme.textColor, 0.3)
                            border.width: imageModel.colorFilter === modelData.name ? 3 : 1
                            
                            HoverHandler { id: filterHover }
                            TapHandler {
                                onTapped: {
                                    if (imageModel.colorFilter === modelData.name) {
                                        imageModel.colorFilter = "" // toggle off
                                    } else {
                                        imageModel.colorFilter = modelData.name
                                    }
                                }
                            }
                            
                            ToolTip.text: modelData.label
                            ToolTip.visible: filterHover.hovered
                        }
                    }
                    Item { Layout.fillWidth: true }
                    Item { Layout.fillWidth: true }
                    ToolButton {
                        icon.name: "tag-symbolic"
                        checkable: true
                        checked: categoryEditorPopup.visible
                        onToggled: {
                            if (checked) categoryEditorPopup.open()
                            else categoryEditorPopup.close()
                        }
                        ToolTip.text: qsTr("Edit Color Categories")
                        ToolTip.visible: hovered
                        display: AbstractButton.IconOnly
                    }
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
                        
                            // Use strict integer division to avoid sub-pixel jitter
                            cellWidth: Math.floor(width / Math.max(2, Math.floor(width / 250)))
                            cellHeight: Math.floor(cellWidth * 0.5625)
                        
                            model: imageModel

                            delegate: Item {
                                width: thumbnailGrid.cellWidth
                                height: thumbnailGrid.cellHeight
                            
                                required property string filePath
                                required property string fileName
                                required property string thumbPath
                                property bool isVideo: {
                                    var ext = fileName.substring(fileName.lastIndexOf(".")).toLowerCase()
                                    return [".mp4", ".webm", ".mkv", ".avi", ".mov", ".flv", ".m4v", ".wmv", ".3gp"].includes(ext)
                                }

                                property bool isSelected: filePath === controller.selectedWallpaper
                                property bool isHovered: hoverHandler.hovered

                                Rectangle {
                                    anchors.fill: parent
                                    anchors.margins: Kirigami.Units.smallSpacing
                                    color: Qt.alpha(Kirigami.Theme.textColor, 0.05)
                                    border.color: isHovered ? Kirigami.Theme.focusColor : (isSelected ? Kirigami.Theme.highlightColor : "transparent")
                                    border.width: isSelected ? 3 : 1
                                    radius: Kirigami.Units.smallSpacing

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        //onClicked: controller.selectWallpaper(filePath)
                                        onClicked: {
                                            controller.selectWallpaper(filePath)
                                            gridContainer.selWallpaper = controller.selectedWallpaper
                                            gridContainer.selWallpaperThumb = controller.thumbPath
                                            gridContainer.isVideo = isVideo
                                        }
                                        onDoubleClicked: {
                                            controller.selectWallpaper(filePath)
                                            gridContainer.selWallpaper = controller.selectedWallpaper
                                            gridContainer.selWallpaperThumb = controller.thumbPath
                                            gridContainer.isVideo = isVideo
                                            lightboxPopup.open()
                                        }
                                    }

                                    Item {
                                        anchors.fill: parent
                                        anchors.margins: Kirigami.Units.smallSpacing
                                        clip: true
                                    
                                        Image {
                                            id: thumbImg
                                            anchors.fill: parent
                                            source: thumbPath ? thumbPath : "file://" + filePath
                                            sourceSize.width: 320
                                            fillMode: Image.PreserveAspectCrop
                                            asynchronous: true
                                            smooth: true
                                        
                                            scale: isHovered ? 1.05 : 1.0
                                            Behavior on scale { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic } }
                                        
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
                                            active: isVideo && isSelected
                                            asynchronous: true

                                            sourceComponent: Item {
                                                anchors.fill: parent

                                                MediaPlayer {
                                                    id: inlineVideoPlayer
                                                    source: "file://" + filePath
                                                    videoOutput: inlineVideoOutput
                                                    audioOutput: AudioOutput {
                                                        // Preview autoplay muted like a live-wallpaper preview.
                                                        // Set muted: false if you'd rather hear audio.
                                                        muted: true
                                                    }
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

                                        // Play indicator for video files (hidden once it's actually playing)
                                        // Rectangle {
                                        //     anchors.centerIn: parent
                                        //     width: Kirigami.Units.gridUnit * 2.5
                                        //     height: width
                                        //     radius: width / 2
                                        //     color: Qt.rgba(0, 0, 0, 0.6)
                                        //     visible: isVideo && thumbImg.status === Image.Ready && !isSelected
                                            
                                        //     Kirigami.Icon {
                                        //         anchors.centerIn: parent
                                        //         source: "media-playback-start"
                                        //         width: Kirigami.Units.gridUnit * 1.5
                                        //         height: width
                                        //         color: "white"
                                        //     }
                                        // }
                                    }

                                    Rectangle {
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        anchors.margins: Kirigami.Units.smallSpacing * 2
                                        radius: Kirigami.Units.cornerRadius
                                        visible: controller.showExtensionBadge
                                        color: Qt.alpha(Kirigami.Theme.backgroundColor, 0.80)
                                        width: extLabel.implicitWidth + Kirigami.Units.smallSpacing * 2
                                        height: extLabel.implicitHeight + Kirigami.Units.smallSpacing
                                        border.color: Kirigami.Theme.highlightColor //isVideo === true ? Kirigami.Theme.neutralTextColor : Kirigami.Theme.highlightColor
                                        border.width: 0.5

                                        Label {
                                            id: extLabel
                                            anchors.centerIn: parent
                                            text: fileName.split(".").pop().toUpperCase()
                                            color: Kirigami.Theme.textColor //isVideo === true ? Kirigami.Theme.neutralTextColor : Kirigami.Theme.textColor
                                            font.pointSize: Kirigami.Theme.smallFont.pointSize * 0.8
                                            font.bold: true
                                        }
                                    }

                                    Rectangle {
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

                                        // Minimalist Color Palette Dots
                                        RowLayout {
                                            id: colorDots
                                            anchors.centerIn: parent
                                            spacing: 2 //Kirigami.Units.smallSpacing
                                            visible: isSelected

                                            Repeater {
                                                model: controller.wallpaperColors
                                                delegate: Rectangle {
                                                    required property string modelData
                                                    required property int index
                                                    width: Kirigami.Units.gridUnit * 0.8
                                                    height: width
                                                    //radius: width / 2
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
                                        anchors.top: parent.top
                                        anchors.right: parent.right
                                        anchors.margins: Kirigami.Units.smallSpacing
                                        icon.name: "dialog-ok-apply"
                                        icon.color: Kirigami.Theme.positiveTextColor
                                        display: AbstractButton.IconOnly
                                        visible: isSelected
                                        onClicked: {
                                            // Determine which path to use for %image% placeholder
                                            var image = isVideo ? controller.thumbPath : controller.selectedWallpaper
                                            if (isVideo) {
                                                root.notifyOther("Under construction!!")
                                                controller.setAsWallpaper(controller.thumbPath)
                                            } 
                                            else {
                                                controller.setAsWallpaper(controller.selectedWallpaper)
                                            }

                                            // Build command array with all replacements applied
                                            var commandsArray = []
                                            for (var i = 0; i < controller.customCommands.length; i++) {
                                                var cmdObj = controller.customCommands[i]
                                                if (!cmdObj || !cmdObj.enabled) continue
                                                var cmd = cmdObj.command
                                                if (!cmd || cmd.trim() === "") continue
                                                
                                                cmd = cmd.replace(/%sc%/g, rightPaneWallpapers.selectedScoreColorIndex.toString())
                                                        .replace(/%path%/g, '"' + controller.selectedWallpaper + '"')
                                                        .replace(/%image%/g, '"' + image + '"')
                                                
                                                commandsArray.push(cmd.trim())
                                            }

                                            if (commandsArray.length > 0) {
                                                controller.runCMD(commandsArray.join(" && "))
                                            }
                                        }
                                        ToolTip.text: qsTr("Set as Wallpaper")
                                        ToolTip.visible: hovered
                                    }
                                
                                    HoverHandler { id: hoverHandler }
                                
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

            // Bottom Drawer
            Rectangle {
                id: bottomDrawer
                // Use y position for sliding animation instead of anchors.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                
                width: parent.width - Kirigami.Units.largeSpacing //* 4
                height: drawerContent.implicitHeight + Kirigami.Units.largeSpacing * 2
                
                property bool isOpen: rightPaneWallpapers.drawerOpen

                // Slide up from bottom
                y: isOpen ? parent.height - height - Kirigami.Units.largeSpacing * 2 : parent.height
                opacity: isOpen ? 1.0 : 0.0
                visible: y < parent.height

                Behavior on y { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic } }
                Behavior on height { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic } }
                Behavior on opacity { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic } }

                radius: Kirigami.Units.largeSpacing
                //color: root.overlayBackgroundColor
                color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g, Kirigami.Theme.backgroundColor.b, 0.95)
                border.color: Kirigami.Theme.highlightColor
                border.width: 1

                // Block mouse events from passing through to items behind the drawer
                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.AllButtons
                    onWheel: wheel => wheel.accepted = true
                }

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
                        Label {
                            Layout.fillWidth: true
                            text: qsTr("Placeholders: \n%sc% for selected color, %path% for path, %image% for image/video thumb path")
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                            color: Kirigami.Theme.disabledTextColor
                            elide: Text.ElideRight
                        }
                        ToolButton {
                            icon.name: "list-add-symbolic"
                            text: qsTr("Add")
                            ToolTip.visible: hovered
                            ToolTip.text: qsTr("Add new command")
                            onClicked: {
                                controller.addCustomCommand("")
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing

                        Repeater {
                            model: controller.customCommands

                            delegate: RowLayout {
                                id: commandRow
                                required property int index
                                required property var modelData
                                Layout.fillWidth: true

                                Switch {
                                    checked: commandRow.modelData.enabled
                                    ToolTip.text: checked ? qsTr("Enabled") : qsTr("Disabled")
                                    ToolTip.visible: hovered
                                    onToggled: controller.setCustomCommandEnabled(commandRow.index, checked)
                                }

                                TextField {
                                    id: cmdInput
                                    text: commandRow.modelData.command
                                    placeholderText: qsTr("Ex: pywal -i %1")
                                    Layout.fillWidth: true
                                    opacity: commandRow.modelData.enabled ? 1.0 : 0.5
                                    
                                    onEditingFinished: {
                                        controller.updateCustomCommand(commandRow.index, cmdInput.text)
                                    }
                                }
                                ToolButton {
                                    icon.name: "edit-clear"
                                    ToolTip.text: qsTr("Remove command")
                                    ToolTip.visible: hovered
                                    onClicked: {
                                        controller.removeCustomCommand(commandRow.index)
                                    }
                                }
                                ToolButton {
                                    id: runCmdButton
                                    icon.name: "media-playback-start"
                                    ToolTip.visible: hovered
                                    ToolTip.text: qsTr("Execute individual command")
                                    onClicked: {
                                        var image = gridContainer.isVideo ? controller.thumbPath : controller.selectedWallpaper
                                        let cmd = cmdInput.text

                                        cmd = cmd.replace(/%sc%/g, rightPaneWallpapers.selectedScoreColorIndex.toString())
                                        .replace(/%path%/g, '"' + controller.selectedWallpaper + '"')
                                        .replace(/%image%/g, '"' + image + '"')
                                        controller.runCMD(cmd.trim());

                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Lightbox Popup
            Popup {
                id: lightboxPopup
                parent: Overlay.overlay
                x: Math.round((parent.width - width) / 2)
                y: Math.round((parent.height - height) / 2)
                width: parent.width * 0.96
                height: parent.height * 0.86
                modal: true
                focus: true
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                property string selWallpaper: gridContainer.selWallpaper
                property string selWallpaperThumb: gridContainer.selWallpaperThumb
                property bool isVideo: gridContainer.isVideo

                // --- Palette panel state (ported from DialogPalette.qml) ---
                property bool paletteExpanded: false
                property string paletteCurrentBackend: "material-you" // "pywal16", "material-you-kwal", "material-you", "imagemagick"
                property bool paletteGenerationActive: false
                property int paletteSelectedIndex: -1
                property string paletteSelectedSet: ""
                property color paletteSelectedColor: "transparent"
                property bool paletteDarkMode: true
                property string paletteSelectedScheme: "TonalSpot"
                property real paletteColorfulnessValue: 1.0
                property real paletteBrightnessValue: 0.8
                property real paletteContrastValue: 0.0
                property string paletteSeedColor: ""
                property string paletteActualSeed: (controller.currentPaletteData && controller.currentPaletteData.seed) ? controller.currentPaletteData.seed : ""

                // --- Color categories for the currently shown wallpaper ---
                property var categories: []

                function loadCategories() {
                    var path = lightboxPopup.selWallpaper
                    lightboxPopup.categories = path ? (controller.getWallpaperCategories(path) || []) : []
                }

                function toggleCategory(catName) {
                    var path = lightboxPopup.selWallpaper
                    if (!path) return

                    var cats = (lightboxPopup.categories || []).slice()
                    var idx = cats.indexOf(catName)
                    if (idx !== -1) cats.splice(idx, 1)
                    else cats.push(catName)

                    var ok = controller.updateWallpaperCategories(path, cats)
                    if (ok) {
                        lightboxPopup.categories = cats
                        // Keep the big category-editor popup in sync too, if it has
                        // already loaded an entry for this same path.
                        for (var i = 0; i < categoryEditorPopup.allEntries.length; i++) {
                            if (categoryEditorPopup.allEntries[i].path === path) {
                                categoryEditorPopup.allEntries[i].categories = cats
                                categoryEditorPopup.allEntries = categoryEditorPopup.allEntries.slice()
                                break
                            }
                        }
                    } else {
                        applicationWindow().showPassiveNotification(qsTr("Failed to update categories"))
                    }
                }

                // Source image used for palette extraction: for videos we always use the thumbnail
                function paletteSourcePath() {
                    return lightboxPopup.isVideo ? lightboxPopup.selWallpaperThumb : lightboxPopup.selWallpaper
                }

                function refreshPalette(path) {
                    if (!path) return

                    var params = {}
                    if (paletteCurrentBackend === "material-you-kwal") {
                        params = {
                            "dark_mode": lightboxPopup.paletteDarkMode,
                            "scheme": lightboxPopup.paletteSelectedScheme,
                            "colorfulness": lightboxPopup.paletteColorfulnessValue,
                            "brightness": lightboxPopup.paletteBrightnessValue,
                            "contrast": lightboxPopup.paletteContrastValue,
                            "seed_color": lightboxPopup.paletteSeedColor
                        }
                    } else if (paletteCurrentBackend === "material-you") {
                        params = {
                            "dark_mode": lightboxPopup.paletteDarkMode,
                            "scheme": lightboxPopup.paletteSelectedScheme
                        }
                    } else if (paletteCurrentBackend === "pywal16") {
                        params = {
                            "dark_mode": lightboxPopup.paletteDarkMode
                        }
                    }
                    controller.generatePalette(path, paletteCurrentBackend, params)
                }

                function resetPaletteParameters() {
                    lightboxPopup.paletteSelectedScheme = "TonalSpot"
                    lightboxPopup.paletteColorfulnessValue = 1.0
                    lightboxPopup.paletteBrightnessValue = 0.8
                    lightboxPopup.paletteContrastValue = 0.0
                    lightboxPopup.paletteSeedColor = ""
                    lightboxPopup.paletteDarkMode = true
                }

                function triggerPaletteRefresh() {
                    if (!lightboxPopup.paletteGenerationActive) return
                    var path = lightboxPopup.paletteSourcePath()
                    if (path) lightboxPopup.refreshPalette(path)
                }

                onOpened: {
                    // Fresh wallpaper: drop any palette generated for a previous image
                    lightboxPopup.paletteGenerationActive = false
                    lightboxPopup.paletteSelectedIndex = -1
                    lightboxPopup.paletteSelectedSet = ""
                    lightboxPopup.paletteSelectedColor = "transparent"
                    if (controller && controller.clearPalette) controller.clearPalette()
                    lightboxPopup.loadCategories()
                }

                Timer {
                    id: paletteDebouncer
                    interval: 300
                    repeat: false
                    onTriggered: lightboxPopup.triggerPaletteRefresh()
                }

                function debouncePaletteRefresh() {
                    paletteDebouncer.restart()
                }

                Connections {
                    target: controller
                    function onPaletteGenerationError(msg) {
                        applicationWindow().showPassiveNotification(qsTr("Error: ") + msg)
                    }
                }

                Connections {
                    target: controller
                    function onCurrentPaletteDataChanged() {
                        var colors = (controller.currentPaletteData && controller.currentPaletteData.colors) ? controller.currentPaletteData.colors : []
                        var accents = (controller.currentPaletteData && controller.currentPaletteData.accents) ? controller.currentPaletteData.accents : []
                        if (lightboxPopup.paletteSelectedSet === "palette" && lightboxPopup.paletteSelectedIndex >= colors.length) {
                            lightboxPopup.paletteSelectedIndex = -1
                            lightboxPopup.paletteSelectedSet = ""
                            lightboxPopup.paletteSelectedColor = "transparent"
                        }
                        if (lightboxPopup.paletteSelectedSet === "accent" && lightboxPopup.paletteSelectedIndex >= accents.length) {
                            lightboxPopup.paletteSelectedIndex = -1
                            lightboxPopup.paletteSelectedSet = ""
                            lightboxPopup.paletteSelectedColor = "transparent"
                        }
                    }
                }

                background: Rectangle {
                    Kirigami.Theme.colorSet: Kirigami.Theme.View
                    color: Kirigami.Theme.backgroundColor
                    border.color: Kirigami.Theme.highlightColor
                    border.width: 1
                    radius: Kirigami.Units.largeSpacing
                }
                
                contentItem: Item {
                    readonly property bool selectedIsVideo: lightboxPopup.isVideo
                    
                    Image {
                        id: lightboxImage
                        anchors.fill: parent
                        anchors.margins: Kirigami.Units.largeSpacing * 4
                        source: lightboxPopup.selWallpaper ? (parent.selectedIsVideo ? "image://video_thumbnail/" + lightboxPopup.selWallpaper : "file://" + lightboxPopup.selWallpaper) : ""
                        fillMode: Image.PreserveAspectFit
                        asynchronous: true
                        smooth: true
                        visible: !parent.selectedIsVideo || lightboxVideoLoader.status !== Loader.Ready
                    }

                    Loader {
                        id: lightboxVideoLoader
                        anchors.fill: parent
                        anchors.margins: Kirigami.Units.largeSpacing * 4
                        active: lightboxPopup.opened && parent.selectedIsVideo
                        asynchronous: true

                        sourceComponent: Item {
                            anchors.fill: parent

                            MediaPlayer {
                                id: lightboxVideoPlayer
                                source: "file://" + lightboxPopup.selWallpaper
                                videoOutput: lightboxVideoOutput
                                audioOutput: AudioOutput { muted: true }//{ volume: 1.0 }
                                loops: MediaPlayer.Infinite

                                Component.onCompleted: play()
                            }

                            VideoOutput {
                                id: lightboxVideoOutput
                                anchors.fill: parent
                                fillMode: VideoOutput.PreserveAspectFit
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (lightboxVideoPlayer.playbackState === MediaPlayer.PlayingState)
                                        lightboxVideoPlayer.pause()
                                    else
                                        lightboxVideoPlayer.play()
                                }
                            }
                        }
                    }
                    
                    // Rectangle {
                    //     anchors.centerIn: parent
                    //     width: Kirigami.Units.gridUnit * 4
                    //     height: width
                    //     radius: width / 2
                    //     color: Qt.rgba(0, 0, 0, 0.7)
                    //     visible: parent.selectedIsVideo && lightboxVideoLoader.status !== Loader.Ready
                        
                    //     Column {
                    //         anchors.centerIn: parent
                    //         spacing: Kirigami.Units.smallSpacing
                            
                    //         Kirigami.Icon {
                    //             anchors.horizontalCenter: parent.horizontalCenter
                    //             source: "media-playback-start"
                    //             width: Kirigami.Units.gridUnit * 2
                    //             height: width
                    //             color: "white"
                    //         }
                            
                    //         Label {
                    //             anchors.horizontalCenter: parent.horizontalCenter
                    //             text: qsTr("Video")
                    //             color: "white"
                    //             font.bold: true
                    //         }
                    //     }
                    // }
                    
                    ToolButton {
                        id: paletteToggleButton
                        anchors.top: parent.top
                        anchors.topMargin: Kirigami.Units.smallSpacing
                        anchors.right: closeLightboxButton.left
                        icon.name: "palette-symbolic"
                        icon.width: Kirigami.Units.gridUnit * 1.5
                        icon.height: Kirigami.Units.gridUnit * 1.5
                        display: AbstractButton.IconOnly
                        checkable: true
                        checked: lightboxPopup.paletteExpanded
                        ToolTip.text: qsTr("Color Palette")
                        ToolTip.visible: hovered
                        onToggled: lightboxPopup.paletteExpanded = checked
                    }

                    ToolButton {
                        id: closeLightboxButton
                        anchors.top: parent.top
                        anchors.topMargin: Kirigami.Units.smallSpacing
                        anchors.right: parent.right
                        icon.name: "dialog-close"
                        icon.width: Kirigami.Units.gridUnit * 1.5
                        icon.height: Kirigami.Units.gridUnit * 1.5
                        display: AbstractButton.IconOnly
                        onClicked: lightboxPopup.close()
                    }

                    // --- Palette Panel (ported from DialogPalette.qml) ---
                    // Fixed-size container that clips its content; only the inner
                    // Rectangle's "x" is animated, so contained controls never see
                    // a width/height of 0 (which caused QPainter paint-device warnings).
                    Item {
                        id: palettePanelContainer
                        anchors.top: closeLightboxButton.bottom
                        anchors.bottom: parent.bottom
                        anchors.right: parent.right
                        anchors.topMargin: Kirigami.Units.largeSpacing
                        anchors.bottomMargin: Kirigami.Units.largeSpacing * 4
                        anchors.rightMargin: Kirigami.Units.largeSpacing
                        width: Math.min(Kirigami.Units.gridUnit * 18, parent.width * 0.42)
                        clip: true

                        // Handle/tab attached to the container's left edge, always visible
                        Rectangle {
                            id: paletteHandle
                            anchors.right: palettePanelContainer.left
                            anchors.verticalCenter: palettePanelContainer.verticalCenter
                            width: Kirigami.Units.gridUnit * 1.6
                            height: Kirigami.Units.gridUnit * 4
                            radius: Kirigami.Units.smallSpacing
                            color: Qt.alpha(Kirigami.Theme.backgroundColor, 0.92)
                            border.color: Kirigami.Theme.highlightColor
                            border.width: 1
                            visible: !lightboxPopup.paletteExpanded

                            Kirigami.Icon {
                                anchors.centerIn: parent
                                source: "palette-symbolic"
                                width: Kirigami.Units.gridUnit
                                height: width
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: lightboxPopup.paletteExpanded = true
                            }
                        }

                        Rectangle {
                            id: palettePanel
                            width: palettePanelContainer.width
                            height: palettePanelContainer.height
                            x: lightboxPopup.paletteExpanded ? 0 : width
                            color: Qt.alpha(Kirigami.Theme.backgroundColor, 0.92)
                            border.color: Kirigami.Theme.highlightColor
                            border.width: 1
                            radius: Kirigami.Units.smallSpacing

                            Behavior on x {
                                NumberAnimation { duration: 200; easing.type: Easing.InOutQuad }
                            }

                        ScrollView {
                            id: palettePanelScroll
                            anchors.fill: parent
                            anchors.margins: Kirigami.Units.largeSpacing
                            clip: true
                            visible: lightboxPopup.paletteExpanded
                            opacity: lightboxPopup.paletteExpanded ? 1.0 : 0.0

                            Behavior on opacity {
                                NumberAnimation { duration: 150 }
                            }

                            ColumnLayout {
                                id: palettePanelLayout
                                width: palettePanelScroll.availableWidth
                                spacing: Kirigami.Units.largeSpacing

                                RowLayout {
                                    Layout.fillWidth: true
                                    Label {
                                        text: qsTr("Color Palette")
                                        font.bold: true
                                        Layout.fillWidth: true
                                    }
                                    ToolButton {
                                        icon.name: "collapse-all"
                                        flat: true
                                        display: AbstractButton.IconOnly
                                        ToolTip.text: qsTr("Collapse")
                                        ToolTip.visible: hovered
                                        onClicked: lightboxPopup.paletteExpanded = false
                                    }
                                }

                                Kirigami.Separator { Layout.fillWidth: true }

                                // Categories
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: Kirigami.Units.smallSpacing

                                    Label {
                                        text: qsTr("Categories")
                                        font.bold: true
                                    }

                                    Flow {
                                        Layout.fillWidth: true
                                        spacing: Kirigami.Units.smallSpacing

                                        Repeater {
                                            model: lightboxPopup.categories
                                            delegate: Rectangle {
                                                id: lbActiveChip
                                                required property string modelData
                                                readonly property var catInfo: wallpaperPage.categoryInfo(lbActiveChip.modelData)
                                                implicitWidth: lbChipRow.implicitWidth + Kirigami.Units.largeSpacing
                                                implicitHeight: Kirigami.Units.gridUnit * 1.6
                                                radius: Kirigami.Units.smallSpacing
                                                color: Qt.alpha(lbActiveChip.catInfo.hex, 0.22)
                                                //border.color: lbActiveChip.catInfo.hex
                                                border.color: lbActiveChip.catInfo.label === "Black/Dark" ? Kirigami.Theme.textColor : lbActiveChip.catInfo.hex
                                                border.width: 1

                                                RowLayout {
                                                    id: lbChipRow
                                                    anchors.centerIn: parent
                                                    spacing: Kirigami.Units.smallSpacing / 2

                                                    Rectangle {
                                                        Layout.preferredWidth: Kirigami.Units.gridUnit * 0.55
                                                        Layout.preferredHeight: width
                                                        radius: 2 //width / 2
                                                        color: lbActiveChip.catInfo.hex
                                                        border.color: Qt.alpha("#000000", 0.25)
                                                        border.width: 1
                                                    }

                                                    Label {
                                                        text: lbActiveChip.catInfo.label
                                                        //color: Kirigami.Theme.textColor
                                                        color: lbActiveChip.catInfo.label === "Black/Dark" ? Kirigami.Theme.textColor : lbActiveChip.catInfo.hex
                                                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                                                    }

                                                    Label {
                                                        text: "\u2715"
                                                        //color: Kirigami.Theme.disabledTextColor
                                                        color: lbActiveChip.catInfo.label === "Black/Dark" ? Kirigami.Theme.textColor : lbActiveChip.catInfo.hex
                                                        font.pointSize: Kirigami.Theme.smallFont.pointSize

                                                        TapHandler {
                                                            onTapped: lightboxPopup.toggleCategory(lbActiveChip.modelData)
                                                        }
                                                    }
                                                }
                                            }
                                        }

                                        Rectangle {
                                            id: lbAddChip
                                            implicitWidth: lbAddChipRow.implicitWidth + Kirigami.Units.largeSpacing
                                            implicitHeight: Kirigami.Units.gridUnit * 1.6
                                            radius: Kirigami.Units.smallSpacing
                                            color: lbAddChipHover.hovered ? Qt.alpha(Kirigami.Theme.highlightColor, 0.18) : "transparent"
                                            border.color: Qt.alpha(Kirigami.Theme.textColor, 0.35)
                                            border.width: 1

                                            RowLayout {
                                                id: lbAddChipRow
                                                anchors.centerIn: parent
                                                spacing: Kirigami.Units.smallSpacing / 2

                                                Label {
                                                    text: "+"
                                                    color: Kirigami.Theme.disabledTextColor
                                                    font.bold: true
                                                }
                                                Label {
                                                    text: qsTr("Add")
                                                    color: Kirigami.Theme.disabledTextColor
                                                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                                                }
                                            }

                                            HoverHandler { id: lbAddChipHover }
                                            TapHandler {
                                                onTapped: lbAddCategoryMenu.popup()
                                            }

                                            Menu {
                                                id: lbAddCategoryMenu
                                                Repeater {
                                                    model: wallpaperPage.categoryColorModel.filter(function (c) {
                                                        return (lightboxPopup.categories || []).indexOf(c.name) === -1
                                                    })
                                                    delegate: MenuItem {
                                                        required property var modelData
                                                        text: modelData.label
                                                        icon.color: modelData.hex
                                                        onTriggered: lightboxPopup.toggleCategory(modelData.name)
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                Kirigami.Separator { Layout.fillWidth: true }

                                // Extraction Controls
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Kirigami.Units.smallSpacing

                                    ComboBox {
                                        id: extractMethodCombo
                                        model: ["pywal16", "material-you-kwal", "material-you", "imagemagick"]
                                        currentIndex: model.indexOf(lightboxPopup.paletteCurrentBackend)
                                        Layout.fillWidth: true
                                        onActivated: {
                                            lightboxPopup.paletteCurrentBackend = currentText
                                            lightboxPopup.paletteGenerationActive = false
                                            lightboxPopup.paletteSelectedColor = "transparent"
                                            lightboxPopup.paletteSelectedIndex = -1
                                            lightboxPopup.paletteSelectedSet = ""
                                            lightboxPopup.resetPaletteParameters()
                                            if (controller && controller.clearPalette) controller.clearPalette()
                                        }
                                    }

                                    ToolButton {
                                        id: extractButton
                                        icon.name: "palette-symbolic"
                                        ToolTip.text: qsTr("Extract Color Palette")
                                        ToolTip.visible: hovered
                                        onClicked: {
                                            var path = lightboxPopup.paletteSourcePath()
                                            if (!path) {
                                                applicationWindow().showPassiveNotification(qsTr("No image available to extract from"))
                                                return
                                            }
                                            lightboxPopup.paletteGenerationActive = true
                                            lightboxPopup.refreshPalette(path)
                                        }
                                    }
                                }

                                Kirigami.Separator {
                                    Layout.fillWidth: true
                                    visible: lightboxPopup.paletteGenerationActive
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    visible: lightboxPopup.paletteGenerationActive
                                    spacing: Kirigami.Units.smallSpacing

                                    Label {
                                        text: qsTr("Palette Colors")
                                        font.bold: true
                                    }

                                    Grid {
                                        id: paletteGrid
                                        Layout.fillWidth: true
                                        columns: 8
                                        spacing: Kirigami.Units.smallSpacing / 6
                                        clip: true

                                        Repeater {
                                            model: (controller.currentPaletteData && controller.currentPaletteData.colors) ? controller.currentPaletteData.colors : []
                                            delegate: Item {
                                                required property string modelData
                                                required property int index
                                                width: Kirigami.Units.gridUnit * 1.5
                                                height: Kirigami.Units.gridUnit * 1.5

                                                Rectangle {
                                                    anchors.fill: parent
                                                    anchors.margins: Kirigami.Units.smallSpacing / 2
                                                    color: parent.modelData
                                                    border.width: (lightboxPopup.paletteSelectedSet === "palette" && lightboxPopup.paletteSelectedIndex === parent.index) ? 2 : 1
                                                    border.color: (lightboxPopup.paletteSelectedSet === "palette" && lightboxPopup.paletteSelectedIndex === parent.index) ? Kirigami.Theme.highlightColor : Kirigami.Theme.disabledTextColor
                                                    radius: 3

                                                    MouseArea {
                                                        id: maPalette
                                                        anchors.fill: parent
                                                        hoverEnabled: true
                                                        cursorShape: Qt.PointingHandCursor
                                                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                                                        onClicked: (mouse) => {
                                                            if (mouse.button === Qt.RightButton) {
                                                                clipboardHelper.copyToClipboard(parent.parent.modelData)
                                                                return
                                                            }
                                                            lightboxPopup.paletteSelectedIndex = parent.parent.index
                                                            lightboxPopup.paletteSelectedSet = "palette"
                                                            lightboxPopup.paletteSelectedColor = parent.parent.modelData
                                                        }
                                                    }

                                                    ToolTip.visible: maPalette.containsMouse
                                                    ToolTip.text: parent.modelData
                                                }
                                            }
                                        }
                                    }

                                    RowLayout {
                                        Layout.topMargin: Kirigami.Units.smallSpacing
                                        spacing: Kirigami.Units.smallSpacing
                                        Label {
                                            text: qsTr("Accent Colors")
                                            font.bold: true
                                        }
                                        Label {
                                            text: lightboxPopup.paletteCurrentBackend === "material-you-kwal" ? qsTr("(Right click: new variation)") : ""
                                            font.pixelSize: parent.children[0].font.pixelSize * 0.8
                                            font.italic: true
                                            color: Kirigami.Theme.disabledTextColor
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }
                                    }

                                    Grid {
                                        id: accentGrid
                                        Layout.fillWidth: true
                                        columns: 8
                                        spacing: Kirigami.Units.smallSpacing / 6
                                        clip: true

                                        Repeater {
                                            model: (controller.currentPaletteData && controller.currentPaletteData.accents) ? controller.currentPaletteData.accents : []
                                            delegate: Item {
                                                required property string modelData
                                                required property int index
                                                width: Kirigami.Units.gridUnit * 1.5
                                                height: Kirigami.Units.gridUnit * 1.5

                                                Rectangle {
                                                    id: accentRect
                                                    anchors.fill: parent
                                                    anchors.margins: Kirigami.Units.smallSpacing / 2
                                                    color: parent.modelData
                                                    border.width: (lightboxPopup.paletteSelectedSet === "accent" && lightboxPopup.paletteSelectedIndex === parent.index) ? 2 : 1
                                                    border.color: (lightboxPopup.paletteSelectedSet === "accent" && lightboxPopup.paletteSelectedIndex === parent.index) ? Kirigami.Theme.highlightColor : Kirigami.Theme.disabledTextColor
                                                    radius: 3

                                                    MouseArea {
                                                        id: maAccent
                                                        anchors.fill: parent
                                                        hoverEnabled: true
                                                        cursorShape: Qt.PointingHandCursor
                                                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                                                        onClicked: (mouse) => {
                                                            if (mouse.button === Qt.LeftButton) {
                                                                lightboxPopup.paletteSelectedIndex = parent.parent.index
                                                                lightboxPopup.paletteSelectedSet = "accent"
                                                                lightboxPopup.paletteSelectedColor = parent.parent.modelData
                                                            } else if (mouse.button === Qt.RightButton) {
                                                                if (lightboxPopup.paletteCurrentBackend === "material-you-kwal") {
                                                                    lightboxPopup.paletteSeedColor = parent.parent.modelData
                                                                    lightboxPopup.triggerPaletteRefresh()
                                                                } else {
                                                                    clipboardHelper.copyToClipboard(parent.parent.modelData)
                                                                }
                                                            }
                                                        }
                                                    }

                                                    ToolTip.visible: maAccent.containsMouse
                                                    ToolTip.text: parent.modelData

                                                    Item {
                                                        anchors.top: parent.top
                                                        anchors.right: parent.right
                                                        anchors.margins: Kirigami.Units.smallSpacing / 4
                                                        width: Kirigami.Units.gridUnit * 0.6
                                                        height: width
                                                        visible: lightboxPopup.paletteCurrentBackend === "material-you-kwal" &&
                                                                 (lightboxPopup.paletteSeedColor === parent.parent.modelData)

                                                        Label {
                                                            anchors.centerIn: parent
                                                            text: "\u2605"
                                                            color: Kirigami.Theme.positiveTextColor
                                                            font.pixelSize: Math.max(10, parent.width * 0.6)
                                                            style: Text.Outline
                                                            styleColor: Kirigami.Theme.backgroundColor
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                Kirigami.Separator {
                                    Layout.fillWidth: true
                                    visible: lightboxPopup.paletteGenerationActive && (lightboxPopup.paletteCurrentBackend === "material-you-kwal" || lightboxPopup.paletteCurrentBackend === "material-you" || lightboxPopup.paletteCurrentBackend === "pywal16")
                                }

                                // Aux Controls (for Material You and pywal16)
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    visible: lightboxPopup.paletteGenerationActive && (lightboxPopup.paletteCurrentBackend === "material-you-kwal" || lightboxPopup.paletteCurrentBackend === "material-you" || lightboxPopup.paletteCurrentBackend === "pywal16")
                                    spacing: Kirigami.Units.smallSpacing

                                    Label {
                                        text: qsTr("Parameters")
                                        font.bold: true
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: Kirigami.Units.smallSpacing

                                        RadioButton {
                                            text: qsTr("Dark")
                                            checked: lightboxPopup.paletteDarkMode
                                            onToggled: {
                                                if (checked) {
                                                    lightboxPopup.paletteDarkMode = true
                                                    lightboxPopup.triggerPaletteRefresh()
                                                }
                                            }
                                        }
                                        RadioButton {
                                            text: qsTr("Light")
                                            checked: !lightboxPopup.paletteDarkMode
                                            onToggled: {
                                                if (checked) {
                                                    lightboxPopup.paletteDarkMode = false
                                                    lightboxPopup.triggerPaletteRefresh()
                                                }
                                            }
                                        }
                                    }

                                    RowLayout {
                                        visible: lightboxPopup.paletteCurrentBackend === "material-you-kwal"
                                        spacing: Kirigami.Units.smallSpacing

                                        Label { text: qsTr("Seed:") }
                                        Rectangle {
                                            id: seedRect
                                            width: Kirigami.Units.gridUnit
                                            height: width
                                            radius: 3
                                            color: (lightboxPopup.paletteSeedColor !== "") ? lightboxPopup.paletteSeedColor : lightboxPopup.paletteActualSeed
                                            border.color: Kirigami.Theme.disabledTextColor
                                            border.width: 1

                                            ToolTip.text: (lightboxPopup.paletteSeedColor !== "") ? (lightboxPopup.paletteSeedColor + " (Manual)") : (lightboxPopup.paletteActualSeed + " (Auto)")
                                            ToolTip.visible: seedMouse.containsMouse

                                            MouseArea {
                                                id: seedMouse
                                                anchors.fill: parent
                                                hoverEnabled: true
                                            }
                                        }
                                        Label {
                                            text: (lightboxPopup.paletteSeedColor !== "") ? qsTr("Manual") : qsTr("Auto")
                                            opacity: 0.7
                                        }
                                        ToolButton {
                                            visible: lightboxPopup.paletteSeedColor !== ""
                                            icon.name: "edit-clear"
                                            flat: true
                                            ToolTip.text: qsTr("Reset to Auto")
                                            onClicked: {
                                                lightboxPopup.paletteSeedColor = ""
                                                lightboxPopup.triggerPaletteRefresh()
                                            }
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        visible: lightboxPopup.paletteCurrentBackend !== "pywal16"
                                        spacing: Kirigami.Units.smallSpacing

                                        Label { text: qsTr("Tone:") }
                                        ComboBox {
                                            Layout.fillWidth: true
                                            model: ["TonalSpot", "Vibrant", "Expressive", "Content", "FruitSalad", "Rainbow", "Monochrome", "Neutral", "Fidelity"]
                                            currentIndex: model.indexOf(lightboxPopup.paletteSelectedScheme)
                                            onActivated: {
                                                lightboxPopup.paletteSelectedScheme = currentText
                                                if (!lightboxPopup.paletteGenerationActive && lightboxPopup.paletteSourcePath()) {
                                                    lightboxPopup.paletteGenerationActive = true
                                                }
                                                lightboxPopup.triggerPaletteRefresh()
                                            }
                                        }
                                        ToolButton {
                                            icon.name: "edit-clear"
                                            flat: true
                                            opacity: (lightboxPopup.paletteSelectedScheme !== "TonalSpot") ? 1.0 : 0.0
                                            enabled: (lightboxPopup.paletteSelectedScheme !== "TonalSpot")
                                            ToolTip.text: qsTr("Reset to TonalSpot")
                                            onClicked: {
                                                lightboxPopup.paletteSelectedScheme = "TonalSpot"
                                                lightboxPopup.triggerPaletteRefresh()
                                            }
                                        }
                                    }

                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: 3
                                        rowSpacing: Kirigami.Units.smallSpacing
                                        columnSpacing: Kirigami.Units.smallSpacing
                                        visible: lightboxPopup.paletteCurrentBackend === "material-you-kwal"

                                        Label { text: qsTr("Colorfulness:") }
                                        Slider {
                                            Layout.fillWidth: true
                                            from: 0.0
                                            to: 2.0
                                            value: lightboxPopup.paletteColorfulnessValue
                                            stepSize: 0.1
                                            onMoved: {
                                                lightboxPopup.paletteColorfulnessValue = Math.round(value * 10) / 10
                                                lightboxPopup.debouncePaletteRefresh()
                                            }
                                        }
                                        Label { text: lightboxPopup.paletteColorfulnessValue.toFixed(1) }

                                        Label { text: qsTr("Brightness:") }
                                        Slider {
                                            Layout.fillWidth: true
                                            from: 0.1
                                            to: 2.0
                                            value: lightboxPopup.paletteBrightnessValue
                                            stepSize: 0.1
                                            onMoved: {
                                                lightboxPopup.paletteBrightnessValue = Math.round(value * 10) / 10
                                                lightboxPopup.debouncePaletteRefresh()
                                            }
                                        }
                                        Label { text: lightboxPopup.paletteBrightnessValue.toFixed(1) }
                                    }
                                }

                                Item { Layout.preferredHeight: Kirigami.Units.largeSpacing }
                            }
                        }
                        }
                    }
                    
                    RowLayout {
                        anchors.top: parent.top
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.margins: Kirigami.Units.largeSpacing
                        spacing: Kirigami.Units.smallSpacing

                        Repeater {
                            model: controller.wallpaperColors
                            delegate: Rectangle {
                                required property string modelData
                                required property int index
                                width: Kirigami.Units.gridUnit * 1.2
                                height: width
                                radius: Kirigami.Units.smallSpacing
                                color: modelData
                                border.color: rightPaneWallpapers.selectedScoreColorIndex === index ? Kirigami.Theme.positiveTextColor : Qt.alpha(Kirigami.Theme.textColor, 0.5)
                                border.width: rightPaneWallpapers.selectedScoreColorIndex === index ? 3 : 1

                                HoverHandler { id: lightboxColorHover }
                                TapHandler {
                                    acceptedButtons: Qt.LeftButton
                                    onTapped: rightPaneWallpapers.selectedScoreColorIndex = index
                                }
                                TapHandler {
                                    acceptedButtons: Qt.RightButton
                                    onTapped: clipboardHelper.copyToClipboard(modelData)
                                }
                                ToolTip.text: modelData.toUpperCase()
                                ToolTip.visible: lightboxColorHover.hovered
                            }
                        }
                    }

                    Button {
                        anchors.bottom: parent.bottom
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.margins: Kirigami.Units.largeSpacing
                        text: qsTr("Apply Wallpaper")
                        icon.name: "dialog-ok-apply"
                        
                        onClicked: {
                            var image = lightboxPopup.isVideo ? lightboxPopup.selWallpaperThumb : lightboxPopup.selWallpaper
                            
                            if (lightboxPopup.isVideo) {
                                root.notifyOther("Under construction!!")
                                controller.setAsWallpaper(lightboxPopup.selWallpaperThumb)
                            } else {
                                controller.setAsWallpaper(lightboxPopup.selWallpaper)
                            }

                            var commandsArray = []
                            for (var i = 0; i < controller.customCommands.length; i++) {
                                var cmdObj = controller.customCommands[i]
                                if (!cmdObj || !cmdObj.enabled) continue
                                var cmd = cmdObj.command
                                if (!cmd || cmd.trim() === "") continue
                                
                                cmd = cmd.replace(/%sc%/g, rightPaneWallpapers.selectedScoreColorIndex.toString())
                                        .replace(/%path%/g, '"' + lightboxPopup.selWallpaper + '"')
                                        .replace(/%image%/g, '"' + image + '"')
                                
                                commandsArray.push(cmd.trim())
                            }

                            if (commandsArray.length > 0) {
                                controller.runCMD(commandsArray.join(" && "))
                            }
                            
                            lightboxPopup.close()
                        }
                    }
                }
            }

            // Color Category Editor Popup
            Popup {
                id: categoryEditorPopup
                parent: Overlay.overlay
                x: Math.round((parent.width - width) / 2)
                y: Math.round((parent.height - height) / 2)
                width: parent.width * 0.96
                height: parent.height * 0.86                
                modal: true
                focus: true
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                property var allEntries: []
                property string searchText: ""

                function reload() {
                    categoryEditorPopup.allEntries = controller.getCachedColorEntries()
                }

                function toggleCategory(path, catName) {
                    var target = null
                    for (var i = 0; i < categoryEditorPopup.allEntries.length; i++) {
                        if (categoryEditorPopup.allEntries[i].path === path) {
                            target = categoryEditorPopup.allEntries[i]
                            break
                        }
                    }
                    if (!target) return

                    var cats = (target.categories || []).slice()
                    var idx = cats.indexOf(catName)
                    if (idx !== -1) cats.splice(idx, 1)
                    else cats.push(catName)

                    var ok = controller.updateWallpaperCategories(path, cats)
                    if (ok) {
                        target.categories = cats
                        // Reassign so the ListView model binding re-evaluates
                        // and every chip in this row reflects the new state.
                        categoryEditorPopup.allEntries = categoryEditorPopup.allEntries.slice()
                        // Keep the lightbox's own category editor (if open on
                        // this same wallpaper) in sync too.
                        if (lightboxPopup.selWallpaper === path) {
                            lightboxPopup.categories = cats
                        }
                    } else {
                        applicationWindow().showPassiveNotification(qsTr("Failed to update categories"))
                    }
                }

                onOpened: categoryEditorPopup.reload()

                background: Rectangle {
                    Kirigami.Theme.colorSet: Kirigami.Theme.View
                    color: Kirigami.Theme.backgroundColor
                    border.color: Kirigami.Theme.highlightColor
                    border.width: 1
                    radius: Kirigami.Units.largeSpacing
                }

                contentItem: ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Kirigami.Units.largeSpacing * 4
                    spacing: Kirigami.Units.largeSpacing

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing

                        Kirigami.Heading {
                            text: qsTr("Color Category Editor")
                            level: 2
                            Layout.fillWidth: true
                        }
                        Label {
                            text: qsTr("%1 wallpapers").arg(categoryEditorPopup.allEntries.length)
                            color: Kirigami.Theme.disabledTextColor
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                        }
                        ToolButton {
                            icon.name: "view-refresh"
                            flat: true
                            ToolTip.text: qsTr("Reload from cache")
                            ToolTip.visible: hovered
                            onClicked: categoryEditorPopup.reload()
                        }
                        ToolButton {
                            icon.name: "dialog-close"
                            flat: true
                            ToolTip.text: qsTr("Close")
                            ToolTip.visible: hovered
                            onClicked: categoryEditorPopup.close()
                        }
                    }

                    Kirigami.SearchField {
                        Layout.fillWidth: true
                        placeholderText: qsTr("Filter by filename...")
                        onTextChanged: categoryEditorPopup.searchText = text
                    }

                    Kirigami.Separator { Layout.fillWidth: true }

                    Label {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        visible: categoryEditorPopup.allEntries.length === 0
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        color: Kirigami.Theme.disabledTextColor
                        text: qsTr("No cached wallpapers found yet. Browse a folder first so colors get extracted.")
                        wrapMode: Text.WordWrap
                    }

                    ListView {
                        id: categoryListView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        visible: categoryEditorPopup.allEntries.length > 0
                        clip: true
                        spacing: Kirigami.Units.smallSpacing
                        ScrollBar.vertical: ScrollBar {}

                        model: {
                            var term = categoryEditorPopup.searchText.toLowerCase()
                            if (!term) return categoryEditorPopup.allEntries
                            return categoryEditorPopup.allEntries.filter(function (e) {
                                return e.path.toLowerCase().indexOf(term) !== -1
                            })
                        }

                        delegate: Rectangle {
                            id: entryDelegate
                            required property var modelData
                            width: categoryListView.width
                            height: entryRowLayout.implicitHeight + Kirigami.Units.largeSpacing
                            color: Qt.alpha(Kirigami.Theme.backgroundColor, 0.5)
                            radius: Kirigami.Units.smallSpacing
                            border.color: Qt.alpha(Kirigami.Theme.textColor, 0.15)
                            border.width: 1

                            RowLayout {
                                id: entryRowLayout
                                anchors.fill: parent
                                anchors.margins: Kirigami.Units.smallSpacing
                                spacing: Kirigami.Units.largeSpacing

                                Item { Layout.fillWidth: true }
                                Image {
                                    Layout.preferredWidth: Kirigami.Units.gridUnit * 4.5
                                    Layout.preferredHeight: Kirigami.Units.gridUnit * 2.8
                                    fillMode: Image.PreserveAspectCrop
                                    asynchronous: true
                                    cache: true
                                    source: entryDelegate.modelData.isVideo
                                            ? ("image://video_thumbnail/" + entryDelegate.modelData.path)
                                            : ("image://fdo_thumbnail/" + entryDelegate.modelData.path)

                                    Rectangle {
                                        anchors.fill: parent
                                        color: "transparent"
                                        border.color: Qt.alpha(Kirigami.Theme.textColor, 0.2)
                                        border.width: 1
                                        radius: 2
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: Kirigami.Units.smallSpacing / 2

                                    Label {
                                        Layout.fillWidth: true
                                        text: entryDelegate.modelData.path.split("/").pop()
                                        elide: Text.ElideMiddle
                                        font.bold: true
                                    }

                                    Flow {
                                        Layout.fillWidth: true
                                        spacing: Kirigami.Units.smallSpacing

                                        Repeater {
                                            model: entryDelegate.modelData.categories || []
                                            delegate: Rectangle {
                                                id: activeChip
                                                required property string modelData
                                                readonly property var catInfo: wallpaperPage.categoryInfo(activeChip.modelData)
                                                implicitWidth: chipRow.implicitWidth + Kirigami.Units.largeSpacing
                                                implicitHeight: Kirigami.Units.gridUnit * 1.6
                                                radius: Kirigami.Units.smallSpacing
                                                color: Qt.alpha(activeChip.catInfo.hex, 0.22)
                                                //border.color: activeChip.catInfo.hex
                                                border.color: activeChip.catInfo.label === "Black/Dark" ? Kirigami.Theme.textColor : activeChip.catInfo.hex
                                                border.width: 1

                                                RowLayout {
                                                    id: chipRow
                                                    anchors.centerIn: parent
                                                    spacing: Kirigami.Units.smallSpacing / 2

                                                    Rectangle {
                                                        Layout.preferredWidth: Kirigami.Units.gridUnit * 0.55
                                                        Layout.preferredHeight: width
                                                        radius: 2 //width / 2
                                                        color: activeChip.catInfo.hex
                                                        border.color: Qt.alpha("#000000", 0.25)
                                                        border.width: 1
                                                    }

                                                    Label {
                                                        text: activeChip.catInfo.label
                                                        //Si activeChip.catInfo.label es "Black/Dark", cambiar el color a Kirigami.Theme.textColor para ser legible
                                                        color: activeChip.catInfo.label === "Black/Dark" ? Kirigami.Theme.textColor : activeChip.catInfo.hex
                                                        //color: Kirigami.Theme.textColor
                                                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                                                    }

                                                    Label {
                                                        text: "\u2715"
                                                        color: activeChip.catInfo.label === "Black/Dark" ? Kirigami.Theme.textColor : activeChip.catInfo.hex 
                                                        //color: Kirigami.Theme.disabledTextColor
                                                        font.pointSize: Kirigami.Theme.smallFont.pointSize

                                                        TapHandler {
                                                            onTapped: categoryEditorPopup.toggleCategory(entryDelegate.modelData.path, activeChip.modelData)
                                                        }
                                                    }
                                                }

                                                HoverHandler {
                                                    id: activeChipHover
                                                }
                                                Behavior on color { ColorAnimation { duration: 100 } }
                                            }
                                        }

                                        Rectangle {
                                            id: addChip
                                            implicitWidth: addChipRow.implicitWidth + Kirigami.Units.largeSpacing
                                            implicitHeight: Kirigami.Units.gridUnit * 1.6
                                            radius: Kirigami.Units.smallSpacing
                                            color: addChipHover.hovered ? Qt.alpha(Kirigami.Theme.highlightColor, 0.18) : "transparent"
                                            border.color: Qt.alpha(Kirigami.Theme.textColor, 0.35)
                                            border.width: 1

                                            RowLayout {
                                                id: addChipRow
                                                anchors.centerIn: parent
                                                spacing: Kirigami.Units.smallSpacing / 2

                                                Label {
                                                    text: "+"
                                                    color: Kirigami.Theme.disabledTextColor
                                                    font.bold: true
                                                }
                                                Label {
                                                    text: qsTr("Add")
                                                    color: Kirigami.Theme.disabledTextColor
                                                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                                                }
                                            }

                                            HoverHandler { id: addChipHover }
                                            TapHandler {
                                                onTapped: addCategoryMenu.popup()
                                            }

                                            Menu {
                                                id: addCategoryMenu
                                                Repeater {
                                                    model: wallpaperPage.categoryColorModel.filter(function (c) {
                                                        return (entryDelegate.modelData.categories || []).indexOf(c.name) === -1
                                                    })
                                                    delegate: MenuItem {
                                                        required property var modelData
                                                        text: modelData.label
                                                        icon.color: modelData.hex
                                                        onTriggered: categoryEditorPopup.toggleCategory(entryDelegate.modelData.path, modelData.name)
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}