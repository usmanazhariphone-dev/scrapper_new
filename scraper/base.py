from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel
from playwright.async_api import Page
from loguru import logger


class Product(BaseModel):
    name: str = ''
    price: str = ''
    image_url: str = ''
    product_url: str = ''
    local_image_path: str = ''
    ai_description: str = ''


class BaseAdapter(ABC):
    SITE_NAME: str = ''
    core = None

    @abstractmethod
    async def scrape(self, page: Page) -> List[Product]:
        pass

    async def accept_cookies(self, page: Page):
        try:
            cookie_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Accept All")',
                'button:has-text("I Accept")',
                '.cookie-accept',
                '#cookie-accept',
                '[data-testid="cookie-accept"]',
            ]
            for selector in cookie_selectors:
                try:
                    btn = await page.query_selector(selector)
                    if btn:
                        await btn.click()
                        await page.wait_for_timeout(500)
                        break
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f'Cookie acceptance error: {e}')

    async def infinite_scroll(self, page: Page, max_scrolls: int = 10):
        for _ in range(max_scrolls):
            await page.evaluate('window.scrollBy(0, window.innerHeight)')
            await page.wait_for_timeout(1000)

    async def handle_pagination(self, page: Page, next_selector: str, max_pages: int = 5):
        for _ in range(max_pages):
            await page.wait_for_timeout(2000)
            next_btn = await page.query_selector(next_selector)
            if not next_btn:
                break
            await next_btn.click()
            await page.wait_for_load_state('networkidle')
