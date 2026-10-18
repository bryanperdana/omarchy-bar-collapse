import QtQuick
import Quickshell.Io
import qs.Commons
import qs.Ui

// Bartender-style arrow. Left click hides or reveals the widgets listed in
// this entry's `hidden` setting; right click opens the list to choose them.
// Every change goes through layout.py, which rewrites shell.json (only bar
// plugins may mutate the layout from inside the shell), so the bar reloads.
BarWidget {
  id: root
  moduleName: "io.github.bryanperdana.bar-collapse"

  readonly property bool expanded: setting("expanded", true) !== false
  readonly property string helper: String(Qt.resolvedUrl("layout.py")).replace(/^file:\/\//, "")

  function runLayout(args) {
    if (layoutProc.running) return false
    layoutProc.command = ["python3", root.helper].concat(args)
    layoutProc.running = true
    return true
  }

  function injectPanel() {
    var target = panelLoader.item
    if (!target) return
    target.bar = root.bar
    target.anchorItem = button
    target.hostWidget = root
  }

  readonly property bool opened: panelLoader.item ? panelLoader.item.opened === true : false
  function open() { if (panelLoader.item) panelLoader.item.open() }
  function close() { if (panelLoader.item) panelLoader.item.close() }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  onBarChanged: injectPanel()

  Process {
    id: layoutProc
    stderr: StdioCollector {
      waitForEnd: true
      onStreamFinished: if (text.trim()) console.warn("bar-collapse:", text.trim())
    }
    onExited: if (panelLoader.item && panelLoader.item.opened) panelLoader.item.reload()
  }

  Loader {
    id: panelLoader
    active: true
    source: Qt.resolvedUrl("ManagePanel.qml")
    visible: false
    onLoaded: {
      root.injectPanel()
      Qt.callLater(root.injectPanel)
    }
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.expanded ? "" : ""
    tooltipText: root.expanded ? "Hide extra widgets" : "Show hidden widgets"

    onPressed: function(b) {
      if (b === Qt.RightButton) {
        if (panelLoader.item) panelLoader.item.toggle()
      } else if (b === Qt.LeftButton) {
        root.runLayout(["toggle"])
      }
    }
  }
}
