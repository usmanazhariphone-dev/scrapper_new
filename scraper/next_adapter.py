from typing import List
from playwright.async_api import Page
from .base import BaseAdapter, Product
from loguru import logger


class NextAdapter(BaseAdapter):
    SITE_NAME = 'next'

    async def search_product(self, page: Page, product_name: str) -> List[Product]:
        products = []
        try:
            search_url = f'https://www.next.co.uk/search?q={product_name.replace(" ", "+")}'
            await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            await self.accept_cookies(page)
            await page.wait_for_timeout(2000)
            items = []
            for selector in ['.ProductItem', '[class*="product"]', 'article']:
                found = await page.query_selector_all(selector)
                if found:
                    items = found
                    break
            for item in items:
                try:
                    p_name = ''
                    for sel in ['.product-name', '.product-title', 'h3', 'h2', 'a']:
                        el = await item.query_selector(sel)
                        if el:
                            p_name = await el.inner_text()
                            if p_name.strip():
                                break
                    if product_name.lower() in p_name.lower():
                        img = await item.query_selector('img')
                        image_url = await img.get_attribute('src') if img else ''
                        if image_url and image_url.startswith('//'):
                            image_url = 'https:' + image_url
                        price_el = await item.query_selector('.price')
                        price = await price_el.inner_text() if price_el else ''
                        link = await item.query_selector('a')
                        product_url = await link.get_attribute('href') if link else ''
                        if product_url and not product_url.startswith('http'):
                            product_url = 'https://www.next.co.uk' + product_url
                        products.append(Product(name=p_name, image_url=image_url, price=price, product_url=product_url))
                        break
                except Exception:
                    continue
        except Exception as e:
            logger.error(f'{self.SITE_NAME} error: {e}')
        return products

    async def scrape(self, page: Page) -> List[Product]:
        return []
