import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.ui.expanded_view import ExpandedView


class _StyleContext:
    def add_class(self, name):
        pass

    def remove_class(self, name):
        pass


class _Button:
    def __init__(self):
        self.style_context = _StyleContext()

    def get_style_context(self):
        return self.style_context


class ExpandedViewClipboardTests(unittest.TestCase):
    def _make_view(self):
        view = SimpleNamespace(
            current_tab="media",
            stack=SimpleNamespace(set_visible_child_name=Mock()),
            notif_mgr=None,
            tab_buttons={"media": _Button(), "clipboard": _Button()},
            update_tab_labels=Mock(),
            media_tab=SimpleNamespace(update=Mock()),
            vitals_tab=SimpleNamespace(update=Mock()),
            controls_tab=SimpleNamespace(update=Mock()),
            timer_tab=SimpleNamespace(update=Mock()),
            notifs_tab=SimpleNamespace(update=Mock()),
            clipboard_tab=SimpleNamespace(update=Mock()),
        )
        view.update = lambda: ExpandedView.update(view)
        return view

    def test_switching_to_clipboard_refreshes_once(self):
        view = self._make_view()

        with patch("src.ui.expanded_view.GLib.idle_add") as idle_add:
            idle_add.side_effect = lambda callback: callback()
            ExpandedView.switch_to_tab(view, "clipboard")

        view.stack.set_visible_child_name.assert_called_once_with("clipboard")
        idle_add.assert_called_once_with(view.clipboard_tab.update)
        view.clipboard_tab.update.assert_called_once_with()

    def test_periodic_updates_do_not_rebuild_clipboard(self):
        view = self._make_view()
        view.current_tab = "clipboard"

        with patch("src.ui.expanded_view.GLib.idle_add") as idle_add:
            for _ in range(120):
                ExpandedView.update(view)

        idle_add.assert_not_called()
        view.clipboard_tab.update.assert_not_called()


if __name__ == "__main__":
    unittest.main()
