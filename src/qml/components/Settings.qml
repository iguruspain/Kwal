pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami



Kirigami.PageRow{
    id: mainRow
    //width: parent.width
    //height: parent.height
    anchors.fill: parent

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
                    section: "Apps",
                    qmlpage: "apps/" + apps[i] + ".qml"
                    });
            }
        }
    }

    globalToolBar.style: Kirigami.ApplicationHeaderStyle.Auto
    initialPage: [settingsPage,settingsContentPage]

    Kirigami.Page {
        id: settingsContentPage
        title: qsTr("Welcome to settings")
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
    
    Kirigami.Page {
        id: settingsPage
        title: qsTr("Settings")
        background: Rectangle {
            color: Kirigami.Theme.backgroundColor
            opacity: 0.8 
        }
            
        ColumnLayout {
            anchors.fill: parent

            ScrollView {
                id: scrollListView
                Layout.fillWidth: true
                Layout.fillHeight: true

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
                            width: ListView.view.width - ListView.view.leftMargin - ListView.view.rightMargin
                        }
                    }
                }
            }
        }
    }
Component {
        id: delegateComponent
        Kirigami.SwipeListItem {
            id: listItem
            required property int index
            required property string title
            required property string qmlpage

            contentItem: RowLayout {
                Kirigami.ListItemDragHandle {
                    listItem: listItem
                    listView: mainList
                    onMoveRequested: (old, curr) => listModel.move(old, curr, 1)
                }

                Label {
                    id: itemLabel
                    text: listItem.title
                    Layout.fillWidth: true
                    
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            let pageURL = Qt.resolvedUrl(listItem.qmlpage);
                            mainRow.push(pageURL);
                        }
                    }
                }
            }
        }
    }
    // Open second page on load for testing
    //Component.onCompleted: {mainRow.push(secondPage);}
}