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
                        model: [
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
                                                var cmd = controller.customCommands[i]
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
                            text: qsTr("Placeholders: \n%sc% for selected color, %path% for path, %image% for image/video thumb path, %video% for video path")
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
                                required property string modelData
                                Layout.fillWidth: true

                                TextField {
                                    id: cmdInput
                                    text: commandRow.modelData
                                    placeholderText: qsTr("Ex: pywal -i %1")
                                    Layout.fillWidth: true
                                    
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
                                    icon.name: "media-playback-start"
                                    ToolTip.visible: hovered
                                    ToolTip.text: qsTr("Execute command")
                                    onClicked: {
                                        let finalCmd = cmdInput.text
                                        finalCmd = finalCmd.replace(/%sc%/g, rightPaneWallpapers.selectedScoreColorIndex.toString())
                                        finalCmd = finalCmd.replace(/%path%/g, `"${controller.selectedWallpaper}"`).trim()
                                        finalCmd = finalCmd.replace(/%vidimg%/g, `"${controller.thumbPath}"`).trim()
                                        controller.runCMD(finalCmd);
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
                        anchors.top: parent.top
                        anchors.right: parent.right
                        icon.name: "dialog-close"
                        icon.width: Kirigami.Units.gridUnit * 1.5
                        icon.height: Kirigami.Units.gridUnit * 1.5
                        display: AbstractButton.IconOnly
                        onClicked: lightboxPopup.close()
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
                                var cmd = controller.customCommands[i]
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
        }
    }
}