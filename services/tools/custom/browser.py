import asyncio
import os

async def browser_use(action: str, url: str = None, selector: str = None) -> str:
    """
    Controls a headless browser to navigate the web.
    Actions:
    - navigate: Go to a URL and return the visible text content.
    - screenshot: Take a screenshot of the current page (saved to frontend/public).
    - get_html: Get the full HTML of the current page.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return "Playwright not installed. Please run 'pip install playwright' and 'playwright install' via execute_shell."

    async with async_playwright() as p:
        # Launch browser (headless by default)
        try:
            browser = await p.chromium.launch()
        except Exception:
            return "Browser launch failed. Did you run 'playwright install'?"
            
        page = await browser.new_page()
        
        if action == "navigate":
            if not url:
                return "Error: URL required for navigate action."
            try:
                await page.goto(url, timeout=30000)
                # Extract text
                text = await page.evaluate("document.body.innerText")
                title = await page.title()
                await browser.close()
                return f"Title: {title}\n\nContent Snippet:\n{text[:2000]}..."
            except Exception as e:
                await browser.close()
                return f"Navigation error: {str(e)}"
                
        elif action == "screenshot":
            if not url:
                return "Error: URL required for screenshot (navigates first)."
            try:
                await page.goto(url)
                filename = f"screenshot_{os.urandom(4).hex()}.png"
                path = os.path.join("c:/Dev/Skynet/frontend/public", filename)
                await page.screenshot(path=path)
                await browser.close()
                return f"Screenshot saved to {path}. Access at http://localhost:4321/{filename}"
            except Exception as e:
                await browser.close()
                return f"Screenshot error: {str(e)}"
        
        await browser.close()
        return "Invalid action."
