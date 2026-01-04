pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami


Kirigami.Page {
    id: settingsRoot
    title: qsTr("Settings")

    background: Rectangle {
        color: Kirigami.Theme.backgroundColor
        opacity: 0.8 
    }

    SplitView {
        anchors.fill: parent
        
        // Left Pane: Settings List
        Item {
            SplitView.preferredWidth: 300
            SplitView.minimumWidth: 200
            SplitView.maximumWidth: 500
            
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
                        
                        model: pyController.settingsAppModel

                        // Auto-select first item logic
                        Component.onCompleted: {
                            if (count > 0) {
                                currentIndex = 0
                                var itemData = model.get(0)
                                if (itemData && itemData.qmlpage) {
                                    mainRow.replace(Qt.resolvedUrl(itemData.qmlpage))
                                }
                            }
                        }
                        
                        moveDisplaced: Transition {
                            YAnimator {
                                duration: Kirigami.Units.longDuration
                                easing.type: Easing.InOutQuad
                            }
                        }
                        
                        delegate: SettingsDelegate {
                            targetListView: mainList
                            onRequestPage: (pageUrl) => {
                                mainRow.replace(pageUrl);
                            }
                        }
                        
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

        // Right Pane: Content Stack
        StackView {
            id: mainRow
            SplitView.fillWidth: true
                        
            background: Rectangle {
                color: "transparent" //Kirigami.Theme.backgroundColor
                //opacity: 0.8
            }
            
            // Custom transition for pushing pages
            pushEnter: Transition {
                PropertyAnimation {
                    property: "opacity"
                    from: 0
                    to: 1
                    duration: 200
                }
            }
            pushExit: Transition {
                PropertyAnimation {
                    property: "opacity"
                    from: 1
                    to: 0
                    duration: 200
                }
            }
            popEnter: Transition {
                PropertyAnimation {
                    property: "opacity"
                    from: 0
                    to: 1
                    duration: 200
                }
            }
            popExit: Transition {
                PropertyAnimation {
                    property: "opacity"
                    from: 1
                    to: 0
                    duration: 200
                }
            }
        }
    }
}

