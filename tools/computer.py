"""ComputerUseToolset – desktop automation client toolset.

Mirrors Anthropic's ``computer_toolset_20260801`` client toolset but works
with **any LLM**.  Provides screenshot, mouse-click, keyboard, and scroll
actions via ``pyautogui`` (or ``pynput``) locally, with the same interface
as Anthropic's computer-use API.

When using Claude, you can emit the native ``computer_toolset_20260801``
declaration by calling ``to_anthropic_toolset()``.

Usage::

    from buddy.tools.computer import ComputerUseToolset

    agent = Agent(model=..., tools=[ComputerUseToolset()])
"""

from __future__ import annotations

import base64
import json
import logging
from io import BytesIO
from typing import Any, Dict, List, Literal, Optional

from buddy.tools.toolkit import Toolkit

logger = logging.getLogger(__name__)

ANTHROPIC_TOOLSET_TYPE = "computer_toolset_20260801"


class ComputerUseToolset(Toolkit):
    """Control the desktop via screenshot, mouse, and keyboard actions.

    Equivalent to Anthropic's ``computer_toolset_20260801`` client toolset.
    Uses ``pyautogui`` for cross-platform desktop automation.

    The model receives screenshots as base64-encoded PNG images and can
    issue click, type, scroll, key, and screenshot actions.

    Parameters
    ----------
    screenshot_quality:
        JPEG quality (1-95) for screenshot compression. Lower = smaller tokens.
    scale_factor:
        Scale screenshots by this factor before sending (reduces token cost).
    enable_clipboard:
        If ``True``, expose clipboard read/write tools.
    allowed_actions:
        Optional allowlist of action names.
    """

    ANTHROPIC_TOOLSET_TYPE = ANTHROPIC_TOOLSET_TYPE

    def __init__(
        self,
        screenshot_quality: int = 75,
        scale_factor: float = 1.0,
        enable_clipboard: bool = False,
        allowed_actions: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        self._quality = screenshot_quality
        self._scale = scale_factor
        self._enable_clipboard = enable_clipboard
        self._allowed_actions = set(allowed_actions) if allowed_actions else None

        tools = [
            self.screenshot,
            self.left_click,
            self.right_click,
            self.double_click,
            self.middle_click,
            self.type_text,
            self.key,
            self.scroll,
            self.move_mouse,
            self.drag,
            self.get_cursor_position,
        ]
        if enable_clipboard:
            tools += [self.read_clipboard, self.write_clipboard]

        super().__init__(
            name="computer_use",
            tools=tools,
            instructions=(
                "Use computer_use tools to control the desktop. "
                "Always take a screenshot first to see the current screen state. "
                "Identify element positions visually before clicking. "
                "Use keyboard shortcuts where possible for efficiency."
            ),
            **kwargs,
        )

    def _check_allowed(self, action: str) -> Optional[str]:
        if self._allowed_actions and action not in self._allowed_actions:
            return json.dumps({"error": f"Action '{action}' is not in the allowed list."})
        return None

    def _take_screenshot(self) -> str:
        """Return a base64-encoded PNG screenshot."""
        try:
            import pyautogui
            from PIL import Image
            screenshot = pyautogui.screenshot()
            if self._scale != 1.0:
                w = int(screenshot.width * self._scale)
                h = int(screenshot.height * self._scale)
                screenshot = screenshot.resize((w, h), Image.LANCZOS)
            buf = BytesIO()
            screenshot.save(buf, format="PNG", optimize=True)
            return base64.b64encode(buf.getvalue()).decode()
        except ImportError:
            return self._fallback_screenshot()

    def _fallback_screenshot(self) -> str:
        """Attempt screenshot with mss if pyautogui is unavailable."""
        try:
            import mss
            import mss.tools
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                img = sct.grab(monitor)
                buf = BytesIO(mss.tools.to_png(img.rgb, img.size))
                return base64.b64encode(buf.getvalue()).decode()
        except ImportError:
            return json.dumps({"error": "No screenshot library available. Install pyautogui or mss."})

    # ── tool methods ─────────────────────────────────────────────────────────

    def screenshot(self) -> str:
        """Capture the current screen and return it as a base64-encoded PNG.

        Use this to see the current state of the desktop before deciding
        what action to take next. Always call this after any action that
        changes the screen to verify the result.

        Returns:
            str: JSON with a base64-encoded PNG image of the current screen.
        """
        err = self._check_allowed("screenshot")
        if err:
            return err
        data = self._take_screenshot()
        if data.startswith("{"):
            return data
        return json.dumps({"type": "image", "format": "png", "data": data})

    def left_click(self, x: int, y: int) -> str:
        """Click the left mouse button at the specified screen coordinates.

        Args:
            x: Horizontal pixel coordinate (from left edge).
            y: Vertical pixel coordinate (from top edge).

        Returns:
            str: Confirmation message.
        """
        err = self._check_allowed("left_click")
        if err:
            return err
        try:
            import pyautogui
            pyautogui.click(x, y)
            return f"Left-clicked at ({x}, {y})."
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def right_click(self, x: int, y: int) -> str:
        """Right-click at the specified screen coordinates.

        Args:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.

        Returns:
            str: Confirmation message.
        """
        err = self._check_allowed("right_click")
        if err:
            return err
        try:
            import pyautogui
            pyautogui.rightClick(x, y)
            return f"Right-clicked at ({x}, {y})."
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def double_click(self, x: int, y: int) -> str:
        """Double-click at the specified screen coordinates.

        Args:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.

        Returns:
            str: Confirmation message.
        """
        err = self._check_allowed("double_click")
        if err:
            return err
        try:
            import pyautogui
            pyautogui.doubleClick(x, y)
            return f"Double-clicked at ({x}, {y})."
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def middle_click(self, x: int, y: int) -> str:
        """Middle-click at the specified screen coordinates.

        Args:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.

        Returns:
            str: Confirmation message.
        """
        err = self._check_allowed("middle_click")
        if err:
            return err
        try:
            import pyautogui
            pyautogui.middleClick(x, y)
            return f"Middle-clicked at ({x}, {y})."
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def type_text(self, text: str, interval: float = 0.02) -> str:
        """Type text at the current cursor position.

        Types the given string character by character at the cursor's current
        location. Use this after clicking a text input field.

        Args:
            text: The text to type.
            interval: Delay in seconds between keystrokes.

        Returns:
            str: Confirmation message.
        """
        err = self._check_allowed("type_text")
        if err:
            return err
        try:
            import pyautogui
            pyautogui.write(text, interval=interval)
            return f"Typed {len(text)} characters."
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def key(self, keys: str) -> str:
        """Press one or more keyboard keys or a hotkey combination.

        Use key names separated by '+' for combinations (e.g. 'ctrl+c',
        'alt+F4', 'enter', 'escape', 'tab').

        Args:
            keys: Key name or '+'-separated combination (e.g. "ctrl+c").

        Returns:
            str: Confirmation message.
        """
        err = self._check_allowed("key")
        if err:
            return err
        try:
            import pyautogui
            if "+" in keys:
                parts = [k.strip() for k in keys.split("+")]
                pyautogui.hotkey(*parts)
            else:
                pyautogui.press(keys)
            return f"Pressed key: '{keys}'."
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def scroll(self, x: int, y: int, direction: Literal["up", "down", "left", "right"] = "down", amount: int = 3) -> str:
        """Scroll the mouse wheel at the specified position.

        Args:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.
            direction: Scroll direction – "up", "down", "left", or "right".
            amount: Number of scroll clicks (each ~120 units).

        Returns:
            str: Confirmation message.
        """
        err = self._check_allowed("scroll")
        if err:
            return err
        try:
            import pyautogui
            pyautogui.moveTo(x, y)
            clicks = amount if direction in ("up", "right") else -amount
            if direction in ("left", "right"):
                pyautogui.hscroll(clicks)
            else:
                pyautogui.scroll(clicks)
            return f"Scrolled {direction} {amount} click(s) at ({x}, {y})."
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def move_mouse(self, x: int, y: int) -> str:
        """Move the mouse to the specified coordinates without clicking.

        Args:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.

        Returns:
            str: Confirmation message.
        """
        err = self._check_allowed("move_mouse")
        if err:
            return err
        try:
            import pyautogui
            pyautogui.moveTo(x, y)
            return f"Mouse moved to ({x}, {y})."
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, button: str = "left") -> str:
        """Drag the mouse from one position to another.

        Args:
            start_x: Starting horizontal coordinate.
            start_y: Starting vertical coordinate.
            end_x: Ending horizontal coordinate.
            end_y: Ending vertical coordinate.
            button: Mouse button to hold during drag ("left", "right", or "middle").

        Returns:
            str: Confirmation message.
        """
        err = self._check_allowed("drag")
        if err:
            return err
        try:
            import pyautogui
            pyautogui.moveTo(start_x, start_y)
            pyautogui.dragTo(end_x, end_y, button=button, duration=0.5)
            return f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})."
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def get_cursor_position(self) -> str:
        """Get the current mouse cursor position.

        Returns:
            str: JSON with x and y pixel coordinates.
        """
        err = self._check_allowed("get_cursor_position")
        if err:
            return err
        try:
            import pyautogui
            pos = pyautogui.position()
            return json.dumps({"x": pos.x, "y": pos.y})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def read_clipboard(self) -> str:
        """Read the current contents of the system clipboard.

        Returns:
            str: The clipboard text content.
        """
        try:
            import pyperclip  # type: ignore
            return pyperclip.paste() or "(empty clipboard)"
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def write_clipboard(self, text: str) -> str:
        """Write text to the system clipboard.

        Args:
            text: The text to write to the clipboard.

        Returns:
            str: Confirmation message.
        """
        try:
            import pyperclip  # type: ignore
            pyperclip.copy(text)
            return f"Copied {len(text)} characters to clipboard."
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def to_anthropic_toolset(self, configs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return the native Anthropic computer-use toolset declaration."""
        entry: Dict[str, Any] = {"type": self.ANTHROPIC_TOOLSET_TYPE}
        if configs:
            entry["configs"] = configs
        return entry
