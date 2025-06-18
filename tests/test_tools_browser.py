import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


def load_tools_browser(monkeypatch):
    """Import tools_browser with Playwright mocked so no browser is launched."""
    # Remove module if previously loaded
    sys.modules.pop("tools_browser", None)

    # Ensure repository root is on sys.path so we can import tools_browser
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Dummy classes to satisfy Playwright API used at import time
    class DummyPage:
        def is_closed(self):
            return False

        def goto(self, url):
            pass

        def click(self, selector, timeout=8000):
            pass

        def fill(self, selector, text):
            pass

        def type(self, selector, text):
            pass

        def press(self, selector, keys):
            pass

        def content(self):
            return ""

    class DummyContext:
        def new_page(self):
            return DummyPage()

    class DummyBrowser:
        def new_context(self, viewport=None):
            return DummyContext()

    class DummyPlaywright:
        def start(self):
            return self

        @property
        def chromium(self):
            return SimpleNamespace(launch=lambda headless=False: DummyBrowser())

    def dummy_sync_playwright():
        return DummyPlaywright()

    # Create stub modules for playwright and playwright.sync_api
    stub_sync_api = ModuleType("playwright.sync_api")
    stub_sync_api.sync_playwright = dummy_sync_playwright

    stub_playwright = ModuleType("playwright")
    stub_playwright.sync_api = stub_sync_api
    stub_playwright.__path__ = []

    monkeypatch.setitem(sys.modules, "playwright", stub_playwright)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", stub_sync_api)

    return importlib.import_module("tools_browser")


def test_schema_all_required(monkeypatch):
    tb = load_tools_browser(monkeypatch)
    props = {"foo": {"type": "string"}, "bar": {"type": "integer"}}
    schema = tb._schema("test", "desc", props, required=None)
    assert schema["function"]["parameters"]["required"] == ["foo", "bar"]
