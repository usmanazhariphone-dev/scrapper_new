from typing import List
from playwright.async_api import Page
from .base import BaseAdapter, Product
from loguru import logger


class BrakeburnAdapter(BaseAdapter):
    SITE_NAME = 'brakeburn'

    async def search_product(self, page: Page, product_name: str) -> List[Product]:
        products = []
        try:
            search_url = f'https://www.brakeburn.com/search?q={product_name.replace(" ", "+")}'
            await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            await self.accept_cookies(page)
            await page.wait_for_timeout(2000)
            items = []
            for selector in ['.product-item', '[class*="product"]', 'article', 'li']:
                found = await page.query_selector_all(selector)
                if found:
                    items = found
                    break
            for item in items:
                try:
                    p_name = ''
                    for sel in ['.product-item__title', '.product-name', '.product-title', 'h3', 'h2', 'a']:
                        el = await item.query_selector(sel)
                        if el:
                            p_name = (await el.inner_text()).strip()
                            if p_name:
                                break
                    if product_name.lower() in p_name.lower():
                        # Get product URL first, then scrape product page for full details
                        link = await item.query_selector('a')
                        product_url = await link.get_attribute('href') if link else ''
                        if product_url and not product_url.startswith('http'):
                            product_url = 'https://www.brakeburn.com' + product_url

                        # Try to get image from listing
                        img = await item.query_selector('img')
                        image_url = ''
                        if img:
                            image_url = await img.get_attribute('src') or await img.get_attribute('data-src') or ''
                            if image_url.startswith('//'):
                                image_url = 'https:' + image_url

                        # Try to get price from listing
                        price = ''
                        for price_sel in ['.price', '.product-price', '[class*="price"]']:
                            price_el = await item.query_selector(price_sel)
                            if price_el:
                                price = (await price_el.inner_text()).strip()
                                if price:
                                    break

                        # If missing image/price, scrape product page
                        if product_url and (not image_url or not price):
                            try:
                                prod_page = await page.context.new_page()
                                await prod_page.goto(product_url, wait_until='domcontentloaded', timeout=30000)
                                await prod_page.wait_for_timeout(1500)
                                if not image_url:
                                    for img_sel in ['.product__media img', '.product-single__photo img', 'img.product__photo', 'img']:
                                        img_el = await prod_page.query_selector(img_sel)
                                        if img_el:
                                            image_url = await img_el.get_attribute('src') or await img_el.get_attribute('data-src') or ''
                                            if image_url:
                                                if image_url.startswith('//'):
                                                    image_url = 'https:' + image_url
                                                break
                                if not price:
                                    for price_sel in ['.price__regular', '.price', '[class*="price"]']:
                                        price_el = await prod_page.query_selector(price_sel)
                                        if price_el:
                                            price = (await price_el.inner_text()).strip()
                                            if price:
                                                break
                                await prod_page.close()
                            except Exception as pe:
                                logger.warning(f'brakeburn product page scrape failed: {pe}')

                        products.append(Product(name=p_name, image_url=image_url, price=price, product_url=product_url))
                        break
                except Exception:
                    continue
        except Exception as e:
            logger.error(f'{self.SITE_NAME} error: {e}')
        return products

    async def scrape(self, page: Page) -> List[Product]:
        return []
