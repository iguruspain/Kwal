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
            id: leftPane

            // preferredWidth computed from the longest title measured by `titleMeasure`
            SplitView.preferredWidth: Math.min(Math.max(titleMeasure.implicitWidth + Kirigami.Units.smallSpacing, 200), 500)
            SplitView.minimumWidth: 200
            SplitView.maximumWidth: 500

            // longest title provided by controller; measurement remains in QML
            property string longestTitle: ""

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
                        onCountChanged: leftPane.longestTitle = pyController.longestSettingsTitle()
                        onModelChanged: leftPane.longestTitle = pyController.longestSettingsTitle()
                        Timer {
                            id: refreshRequestTimer
                            interval: 3000
                            onTriggered: {
                                scrollListView.refreshing = false;
                            }
                        }
                        
                        model: pyController.settingsAppModel

                        // Auto-select first item logic + compute title measurement
                        Component.onCompleted: {
                            leftPane.longestTitle = pyController.longestSettingsTitle()
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

            // Invisible text used to measure the width of the longest title.
            // Keep visible so implicitWidth is calculated; use transparent color.
            Text {
                id: titleMeasure
                text: leftPane.longestTitle
                wrapMode: Text.NoWrap
                color: "transparent"
                anchors.left: parent.left
                anchors.top: parent.top
                horizontalAlignment: Text.AlignLeft
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

