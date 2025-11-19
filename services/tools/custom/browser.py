import asyncio
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def browser_use(action: str, url: str = None, selector: str = None) -> str:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return "Playwright not installed. Please run 'pip install playwright' and 'playwright install' via execute_shell."

    async with async_playwright() as p:
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
                
                public_dir = os.path.join(BASE_DIR, "frontend", "public")
                os.makedirs(public_dir, exist_ok=True)
                
                path = os.path.join(public_dir, filename)
                await page.screenshot(path=path)
                await browser.close()
                return f"Screenshot saved to {path}. Access at http://localhost:4321/{filename}"
            except Exception as e:
                await browser.close()
                return f"Screenshot error: {str(e)}"
        
        await browser.close()
        return "Invalid action."
