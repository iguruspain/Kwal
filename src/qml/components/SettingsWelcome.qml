import QtQuick
import QtQuick.Controls
import org.kde.kirigami as Kirigami

Kirigami.Page {
    id: settingsContentPage
    title: qsTr("Welcome to settings")

    signal requestGoBack()

    background: Rectangle {
        color: Kirigami.Theme.backgroundColor
        opacity: 0.8 
    }
    actions: [
        Kirigami.Action {
            icon.name: "go-previous"
            text: qsTr("Back")
            onTriggered: {
                settingsContentPage.requestGoBack()
            }
        }
    ]
}
