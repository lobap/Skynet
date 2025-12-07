"""Browser automation tool using Playwright."""

import os
import asyncio
from typing import Literal
from backend.logger import logger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

ActionType = Literal["navigate", "screenshot"]


async def browser_use(action: ActionType = "navigate", url: str | None = None, selector: str | None = None) -> str:
    """Browser automation: navigate to URL or take screenshot.
    
    Args:
        action: 'navigate' or 'screenshot'
        url: Target URL
        selector: Optional CSS selector
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return "Playwright not installed. Run: pip install playwright && playwright install"

    if not url:
        return f"Error: URL required for {action}"

    async with async_playwright() as p:
        browser = await _launch_browser(p)
        if isinstance(browser, str):  # Error message
            return browser
        
        page = await browser.new_page()
        
        try:
            if action == "navigate":
                return await _navigate(page, browser, url)
            elif action == "screenshot":
                return await _screenshot(page, browser, url)
            return "Invalid action"
        except Exception as e:
            await browser.close()
            return f"Browser error: {e}"


async def _launch_browser(playwright):
    """Launch browser, auto-install if needed."""
    try:
        return await playwright.chromium.launch()
    except Exception:
        logger.warning("Browser launch failed, attempting chromium install...")
        try:
            proc = await asyncio.create_subprocess_shell(
                "playwright install chromium",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            return await playwright.chromium.launch()
        except Exception as e:
            return f"Browser launch failed: {e}"


async def _navigate(page, browser, url: str) -> str:
    """Navigate to URL and extract content."""
    await page.goto(url, timeout=30000)
    text = await page.evaluate("document.body.innerText")
    title = await page.title()
    await browser.close()
    return f"Title: {title}\n\nContent:\n{text[:2000]}..."


async def _screenshot(page, browser, url: str) -> str:
    """Take screenshot of URL."""
    await page.goto(url)
    filename = f"screenshot_{os.urandom(4).hex()}.png"
    
    public_dir = os.path.join(BASE_DIR, "frontend", "public")
    os.makedirs(public_dir, exist_ok=True)
    
    path = os.path.join(public_dir, filename)
    await page.screenshot(path=path)
    await browser.close()
    return f"Screenshot: {path}"
