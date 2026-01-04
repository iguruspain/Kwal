pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami


Kirigami.PageRow {
    id: mainRow
    anchors.fill: parent

    globalToolBar.style: Kirigami.ApplicationHeaderStyle.Auto

    Kirigami.Page {
        id: settingsListPage
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
                    
                    model: pyController.settingsAppModel
                    
                    moveDisplaced: Transition {
                        YAnimator {
                            duration: Kirigami.Units.longDuration
                            easing.type: Easing.InOutQuad
                        }
                    }
                    
                    delegate: SettingsDelegate {
                        targetListView: mainList
                        onRequestPage: (pageUrl) => {
                            mainRow.push(pageUrl);
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

    Component {
        id: welcomeComponent
        SettingsWelcome {
            onRequestGoBack: {
                mainRow.pop()
            }
        }
    }
    
    initialPage: [settingsListPage, welcomeComponent]
}

