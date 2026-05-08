import asyncio
import random
from playwright.async_api import async_playwright, Browser, Page


class ScraperCore:
    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None

    async def __aenter__(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        return self

    async def __aexit__(self, *_):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def new_page(self) -> Page:
        context = await self._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )
        return await context.new_page()

    async def random_delay(self, min_s: float = 1.0, max_s: float = 2.0):
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def slow_scroll(self, page: Page, max_scrolls: int = 3):
        for _ in range(max_scrolls):
            await page.evaluate('window.scrollBy(0, window.innerHeight)')
            await self.random_delay(0.5, 1.0)
