pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami



Kirigami.PageRow{
    id: mainRow
    width: parent.width
    height: parent.height

    ListModel {
        id: listModel

        // apps for testing
        Component.onCompleted: {
            const apps = [
                "ulauncher",
                "starship",
                "fastfetch"
            ]
            for (let i = 0; i < apps.length; i++) {
                listModel.append({
                    title: apps[i],
                    section: "Apps"
                    });
            }
        }
    }

    globalToolBar.style: Kirigami.ApplicationHeaderStyle.Auto
    initialPage: settingsPage
    
    Kirigami.Page {
        id: settingsPage
        title: qsTr("Settings")
        //Kirigami.Theme.colorSet: Kirigami.Theme.View
        background: Rectangle {
            color: Kirigami.Theme.backgroundColor
            opacity: 0.8 
        }
            
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.smallSpacing
            spacing: Kirigami.Units.smallSpacing

            ScrollView {
                id: scrollListView
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: Kirigami.Units.smallSpacing
                clip: true

                background: Rectangle {
                    color: Kirigami.Theme.backgroundColor
                    opacity: 0.8
                }

                ListView {
                    id: mainList
                    Timer {
                        id: refreshRequestTimer
                        interval: 3000
                        onTriggered: {
                            scrollListView.refreshing = false;
                        }
                    }
                    model: listModel
                    moveDisplaced: Transition {
                        YAnimator {
                            duration: Kirigami.Units.longDuration
                            easing.type: Easing.InOutQuad
                        }
                    }
                    delegate: delegateComponent
                    section {
                        property: "section"
                        delegate: Kirigami.ListSectionHeader {
                            required property string section
                            text: qsTr(section)
                            //text: qsTr("Section %1").arg(parseInt(section) + 1)
                            width: ListView.view.width - ListView.view.leftMargin - ListView.view.rightMargin
                        }
                    }
                }
            }
        }
    }
    Component {
        id: delegateComponent
        Item {
            id: listItemRoot

            required property int index
            required property string title

            width: mainList.width - mainList.leftMargin - mainList.rightMargin
            height: listItem.implicitHeight

            Kirigami.SwipeListItem {
                id: listItem
                width: listItemRoot.width
                contentItem: RowLayout {
                    Kirigami.ListItemDragHandle {
                        listItem: listItem
                        listView: mainList
                        onMoveRequested: (oldIndex, newIndex) => {
                            console.log('!!!', oldIndex, newIndex)
                            listModel.move(oldIndex, newIndex, 1);
                        }
                        onDropped: (oldIndex, newIndex) => {
                            console.log(">>>", oldIndex, newIndex)
                        }
                    }

                    Label {
                        id: itemLabel
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.max(implicitHeight, Kirigami.Units.iconSizes.smallMedium)
                        text: listItemRoot.title
                        color: listItem.checked || (listItem.pressed && !listItem.checked && !listItem.sectionDelegate) ? listItem.activeTextColor : listItem.textColor
                    }

                    MouseArea {
                        id: mouseArea
                        anchors.fill: itemLabel
                        hoverEnabled: true
                        onClicked: { mainRow.push(secondPage) }
                        cursorShape: Qt.PointingHandCursor
                    }                    
                }
                actions: [
                    Kirigami.Action {
                        icon.name: "document-decrypt"
                        text: qsTr("Action 1")
                        onTriggered: {
                            console.log("Action 1 triggered on item:", listItemRoot.title)
                        }
                    },
                    Kirigami.Action {
                        icon.name: "mail-reply-sender"
                        text: qsTr("Action 2")
                        onTriggered: {
                            console.log("Action 2 triggered on item:", listItemRoot.title)
                        }
                    }
                ]
            }
        }
    }
    Component {
        id: secondPage
        Kirigami.Page {
            id: secondSettingsPage
            title: qsTr("Second Page")
            //Kirigami.Theme.colorSet: Kirigami.Theme.View
            background: Rectangle {
                color: Kirigami.Theme.backgroundColor
                opacity: 0.8 
            }
            actions: [
                Kirigami.Action {
                    icon.name: "go-previous"
                    text: qsTr("Back")
                    onTriggered: {
                        mainRow.pop()
                    }
                }
            ]
        }
    }
}