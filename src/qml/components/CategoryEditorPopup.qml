pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

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

    required property var pageRef
    required property var lightbox

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
            if (lightbox.selWallpaper === path) {
                lightbox.categories = cats
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
                                    readonly property var catInfo: pageRef.categoryInfo(activeChip.modelData)
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
                                            border.color: Qt.alpha("#000000",  0.25)
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
                                MouseArea {
                                    anchors.fill: parent
                                    acceptedButtons: Qt.LeftButton
                                    hoverEnabled: true
                                    propagateComposedEvents: false
                                    preventStealing: true
                                    onPressed: (mouse) => {
                                        mouse.accepted = true
                                    }
                                    onClicked: (mouse) => {
                                        mouse.accepted = true
                                        addCategoryMenu.popup()
                                    }
                                }

                                Menu {
                                    id: addCategoryMenu
                                    modal: true
                                    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                                    Repeater {
                                        model: pageRef.categoryColorModel.filter(function (c) {
                                            return (entryDelegate.modelData.categories || []).indexOf(c.name) === -1
                                        })
                                        delegate: MenuItem {
                                            required property var modelData
                                            text: modelData.label
                                            onTriggered: categoryEditorPopup.toggleCategory(entryDelegate.modelData.path, modelData.name)

                                            contentItem: RowLayout {
                                                spacing: Kirigami.Units.smallSpacing
                                                Rectangle {
                                                    width: Kirigami.Units.gridUnit * 0.6
                                                    height: Kirigami.Units.gridUnit * 0.6
                                                    color: modelData.hex
                                                    border.color: Qt.alpha("#000000",  0.25)
                                                    border.width: 1
                                                    radius: 2
                                                    Layout.preferredWidth: width
                                                    Layout.preferredHeight: height
                                                }
                                                Label {
                                                    text: modelData.label
                                                    Layout.fillWidth: true
                                                    Layout.alignment: Qt.AlignVCenter
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
