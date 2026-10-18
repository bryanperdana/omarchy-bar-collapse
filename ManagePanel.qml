import QtQuick
import Quickshell.Io
import qs.Commons
import qs.Ui

// Right-click list: one row per widget in the arrow's bar section, with a
// switch that marks it hidden. Rows come from `layout.py list`, names from
// `omarchy plugin list --json`.
Panel {
  id: root
  moduleName: "io.github.bryanperdana.bar-collapse"
  manageIpc: false

  property var anchorItem: null
  property var hostWidget: null
  readonly property var barIdentity: hostWidget || root

  property var rows: []
  property var names: ({})
  property bool loading: false

  function open() {
    root.controller.show()
    reload()
  }

  function reload() {
    loading = true
    if (!listProc.running) listProc.running = true
    if (!namesProc.running) namesProc.running = true
  }

  function displayName(id) {
    return names[id] || id
  }

  function setHidden(id, hidden) {
    if (hostWidget) hostWidget.runLayout([hidden ? "hide" : "show", id])
  }

  Process {
    id: listProc
    command: ["python3", hostWidget ? hostWidget.helper : "", "list"]
    stdout: StdioCollector {
      onStreamFinished: {
        try { root.rows = JSON.parse(text) } catch (e) { root.rows = [] }
        root.loading = false
      }
    }
  }

  Process {
    id: namesProc
    command: ["omarchy", "plugin", "list", "--json"]
    stdout: StdioCollector {
      onStreamFinished: {
        var map = {}
        try {
          var list = JSON.parse(text)
          for (var i = 0; i < list.length; i++) if (list[i] && list[i].id) map[list[i].id] = list[i].name || list[i].id
        } catch (e) {}
        root.names = map
      }
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    owner: root.barIdentity
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(300))
    contentHeight: panel.fittedContentHeight(column.implicitHeight)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()

      Flickable {
        id: scroll
        anchors.fill: parent
        contentWidth: width
        contentHeight: column.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        interactive: contentHeight > height

        Column {
          id: column
          width: scroll.width
          spacing: Style.spacing.md

          Text {
            text: "Hidden widgets"
            color: Color.popups.text
            font.family: Style.font.family
            font.pixelSize: Style.font.title
            font.bold: true
          }

          Text {
            visible: !root.loading && root.rows.length === 0
            text: "No widgets to manage"
            color: Color.muted
            font.family: Style.font.family
            font.pixelSize: Style.font.body
          }

          Repeater {
            model: root.rows

            delegate: Item {
              required property var modelData
              width: column.width
              height: Style.spacing.popupRowHeight

              Text {
                anchors.left: parent.left
                anchors.right: toggle.left
                anchors.rightMargin: Style.spacing.lg
                anchors.verticalCenter: parent.verticalCenter
                text: root.displayName(modelData.id)
                elide: Text.ElideRight
                color: Color.popups.text
                font.family: Style.font.family
                font.pixelSize: Style.font.body
              }

              ToggleSwitch {
                id: toggle
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                checked: modelData.hidden === true
                onToggled: root.setHidden(modelData.id, !checked)
              }
            }
          }
        }
      }
    }
  }
}
