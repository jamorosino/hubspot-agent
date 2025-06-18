
"""
Playwright helpers + JSON schemas that allow the OpenAI agent to drive a
*single*, visible Chromium tab.  Viewport adapts to the window size so the
content rescales when the user resizes.
"""
from playwright.sync_api import sync_playwright
import json

# ---------- launch ----------
_pw = sync_playwright().start()
_browser = _pw.chromium.launch(headless=False)      # visible window
# viewport=None disables fixed size and lets content follow window resize
_context = _browser.new_context(viewport=None)
_page = _context.new_page()

def _ensure():
    if _page.is_closed():
        raise RuntimeError("Browser window was closed.")

# ---------- tool implementations ----------
def browser_goto(url: str):
    "Navigate the shared browser to the given absolute URL."
    _ensure()
    _page.goto(url)
    return f"Navigated to {url}"

def browser_click(selector: str, timeout: int = 8000):
    "Click the first element matching *selector* (CSS or text)."
    _ensure()
    _page.click(selector, timeout=timeout)
    return f"Clicked '{selector}'"

def browser_type(selector: str, text: str, press_enter: bool = False):
    """
    Focus the element matching *selector*, replace its value with *text*,
    then optionally press Enter.
    """
    _ensure()
    _page.fill(selector, "")
    _page.type(selector, text)
    if press_enter:
        _page.press(selector, "Enter")
    return f"Typed '{text}' into '{selector}'"

def browser_snapshot_dom() -> str:
    "Return current document HTML so the model can reason on it."
    _ensure()
    return _page.content()

# ---------- JSON schemas for the Agents SDK ----------
def _schema(name, description, props, required=None):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required or list(props.keys())
            }
        }
    }

TOOL_SCHEMAS = [
    _schema(
        "browser_goto",
        browser_goto.__doc__,
        {"url": {"type": "string", "description": "Absolute URL"}}
    ),
    _schema(
        "browser_click",
        browser_click.__doc__,
        {
            "selector": {"type": "string", "description": "CSS/text selector"},
            "timeout":  {"type": "integer", "description": "Timeout ms", "default": 8000}
        },
        required=["selector"]
    ),
    _schema(
        "browser_type",
        browser_type.__doc__,
        {
            "selector":    {"type": "string", "description": "Input field selector"},
            "text":        {"type": "string", "description": "Text to type"},
            "press_enter": {"type": "boolean", "description": "Press Enter?", "default": False}
        },
        required=["selector", "text"]
    ),
    _schema(
        "browser_snapshot_dom",
        browser_snapshot_dom.__doc__,
        {}
    )
]

TOOL_MAP = {
    "browser_goto": browser_goto,
    "browser_click": browser_click,
    "browser_type": browser_type,
    "browser_snapshot_dom": browser_snapshot_dom
}
