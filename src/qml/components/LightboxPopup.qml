pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import org.kde.kirigami as Kirigami
import "." as Components

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

    required property var gridContainer
    required property var rightPane
    required property var pageRef
    required property var categoryEditor
    required property var clipboard

    property string selWallpaper: gridContainer.selWallpaper
    property string selWallpaperThumb: gridContainer.selWallpaperThumb
    property bool isVideo: gridContainer.isVideo

    // Palette panel state
    property bool paletteExpanded: false
    property string paletteCurrentBackend: "material-you" // "pywal16", "material-you", "imagemagick"
    property bool paletteGenerationActive: false
    property int paletteSelectedIndex: -1
    property string paletteSelectedSet: ""
    property color paletteSelectedColor: "transparent"
    property bool paletteDarkMode: true
    property string paletteSelectedScheme: "TonalSpot"
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
            for (var i = 0; i < categoryEditor.allEntries.length; i++) {
                if (categoryEditor.allEntries[i].path === path) {
                    categoryEditor.allEntries[i].categories = cats
                    categoryEditor.allEntries = categoryEditor.allEntries.slice()
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
        if (paletteCurrentBackend === "material-you") {
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
        id: lightboxBackground
        Kirigami.Theme.colorSet: Kirigami.Theme.View
        color: Kirigami.Theme.backgroundColor
        border.color: Kirigami.Theme.highlightColor
        border.width: 1
        radius: Kirigami.Units.largeSpacing
    }

    contentItem: Item {
        readonly property bool selectedIsVideo: lightboxPopup.isVideo

        // Media container - fills all available space as background area
        Rectangle {
            id: mediaContainer
            anchors.top: topBar.bottom
            anchors.topMargin: Kirigami.Units.largeSpacing
            anchors.bottom: lightboxApplyWallpaper.top
            anchors.bottomMargin: Kirigami.Units.largeSpacing
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: Kirigami.Units.largeSpacing * 2
            anchors.rightMargin: Kirigami.Units.largeSpacing
            color: lightboxBackground.color
            clip: true

            // Image fills the container with PreserveAspectCrop so the rounded
            // overlay frame always aligns with the container edges (no black bars).
            Image {
                id: lightboxImage
                anchors.fill: parent
                source: lightboxPopup.selWallpaper ? (parent.parent.selectedIsVideo ? "image://video_thumbnail/" + lightboxPopup.selWallpaper : "file://" + lightboxPopup.selWallpaper) : ""
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                smooth: true
                visible: !parent.parent.selectedIsVideo || lightboxVideoLoader.status !== Loader.Ready
            }

            // Video loader fills the container
            Loader {
                id: lightboxVideoLoader
                anchors.fill: parent
                active: lightboxPopup.opened && parent.parent.selectedIsVideo && lightboxPopup.pageRef.visible
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
                        fillMode: VideoOutput.PreserveAspectCrop
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

            // Overlay frame: draws the background color with a rounded
            // hole (where lightboxOverlayFrame3 was) so the image/video
            // is visible, plus a highlight border around the cutout.
            Canvas {
                id: lightboxOverlayCanvas
                anchors.fill: parent
                visible: lightboxImage.source !== ""
                layer.enabled: true
                layer.smooth: false

                onPaint: {
                    var ctx = getContext("2d")
                    ctx.clearRect(0, 0, width + 2, height + 2)

                    // 1) Fill with background color (replaces frame1)
                    ctx.fillStyle = lightboxBackground.color
                    ctx.fillRect(0, 0, width + 2, height + 2)

                    // Hole dimensions (matches former frame2 / frame3 area)
                    var margin = 2 //Kirigami.Units.smallSpacing
                    var holeX = margin
                    var holeY = margin
                    var holeW = width - margin * 2
                    var holeH = height - margin * 2
                    var radius = lightboxBackground.radius

                    // 2) Cut out the rounded hole (replaces frame3 green area)
                    ctx.globalCompositeOperation = 'destination-out'
                    lightboxOverlayCanvas._drawRoundedRect(ctx, holeX, holeY, holeW, holeH, radius)
                    ctx.fill()

                    // 3) Restore and draw the highlight border (replaces frame2)
                    ctx.globalCompositeOperation = 'source-over'
                    ctx.lineWidth = lightboxBackground.border.width
                    ctx.strokeStyle = lightboxBackground.border.color
                    lightboxOverlayCanvas._drawRoundedRect(ctx, holeX, holeY, holeW, holeH, radius)
                    ctx.stroke()
                }

                // Shared helper for rounded-rect paths
                function _drawRoundedRect(ctx, x, y, w, h, r) {
                    ctx.beginPath()
                    ctx.moveTo(x + r, y)
                    ctx.lineTo(x + w - r, y)
                    ctx.quadraticCurveTo(x + w, y, x + w, y + r)
                    ctx.lineTo(x + w, y + h - r)
                    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h)
                    ctx.lineTo(x + r, y + h)
                    ctx.quadraticCurveTo(x, y + h, x, y + h - r)
                    ctx.lineTo(x, y + r)
                    ctx.quadraticCurveTo(x, y, x + r, y)
                    ctx.closePath()
                }
            }
        }

        // Top bar: score colors + close/settings buttons in one row
        RowLayout {
            id: topBar
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: Kirigami.Units.largeSpacing
            spacing: Kirigami.Units.smallSpacing

            Item { Layout.fillWidth: true }

            // Score colors
            Repeater {
                model: controller.wallpaperColors
                delegate: Rectangle {
                    required property string modelData
                    required property int index
                    width: Kirigami.Units.gridUnit * 1.2
                    height: width
                    radius: Kirigami.Units.smallSpacing
                    color: modelData
                    border.color: rightPane.selectedScoreColorIndex === index ? Kirigami.Theme.positiveTextColor : Qt.alpha(Kirigami.Theme.textColor, 0.5)
                    border.width: rightPane.selectedScoreColorIndex === index ? 3 : 1

                    HoverHandler { id: lightboxColorHover }
                    TapHandler {
                        acceptedButtons: Qt.LeftButton
                        onTapped: rightPane.selectedScoreColorIndex = index
                    }
                    TapHandler {
                        acceptedButtons: Qt.RightButton
                        onTapped: clipboard.copyToClipboard(modelData)
                    }
                    ToolTip.text: modelData.toUpperCase()
                    ToolTip.visible: lightboxColorHover.hovered
                }
            }

            Item { Layout.fillWidth: true }

            // Settings toggle button
            ToolButton {
                id: paletteToggleButton
                icon.name: lightboxPopup.paletteExpanded ? "expand" : "preferences-system-symbolic"
                icon.width: Kirigami.Units.gridUnit * 1.5
                icon.height: Kirigami.Units.gridUnit * 1.5
                display: AbstractButton.IconOnly
                checkable: true
                checked: lightboxPopup.paletteExpanded
                ToolTip.text: lightboxPopup.paletteExpanded ? qsTr("Hide Settings") : qsTr("Show Settings")
                ToolTip.visible: hovered
                onToggled: lightboxPopup.paletteExpanded = checked
            }

            // Close button
            ToolButton {
                id: closeLightboxButton
                icon.name: "dialog-close"
                icon.width: Kirigami.Units.gridUnit * 1.5
                icon.height: Kirigami.Units.gridUnit * 1.5
                display: AbstractButton.IconOnly
                onClicked: lightboxPopup.close()
            }
        }

        Components.PalettePanel {
            lightbox: lightboxPopup
            pageRef: lightboxPopup.pageRef
            topBar: topBar
        }
        Button {
            id: lightboxApplyWallpaper
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.margins: Kirigami.Units.largeSpacing
            text: qsTr("Apply Wallpaper")
            icon.name: "dialog-ok-apply"

            onClicked: {
                var image = lightboxPopup.isVideo ? lightboxPopup.selWallpaperThumb : lightboxPopup.selWallpaper

                controller.setAsWallpaper(lightboxPopup.selWallpaper, image)

                var commandsArray = []
                for (var i = 0; i < controller.customCommands.length; i++) {
                    var cmdObj = controller.customCommands[i]
                    if (!cmdObj || !cmdObj.enabled) continue
                    var cmd = cmdObj.command
                    if (!cmd || cmd.trim() === "") continue

                    cmd = cmd.replace(/%sc%/g, rightPane.selectedScoreColorIndex.toString())
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
