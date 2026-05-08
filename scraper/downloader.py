import aiohttp
import tempfile
import os
from loguru import logger
from typing import Optional


class ImageDownloader:
    def __init__(self, site_name: str):
        self.site_name = site_name

    async def download(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.read()
                    suffix = ".jpg"
                    if "png" in url:
                        suffix = ".png"
                    elif "webp" in url:
                        suffix = ".webp"
                    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
                    tmp.write(data)
                    tmp.close()
                    return tmp.name
        except Exception as e:
            logger.warning(f"ImageDownloader failed for {url}: {e}")
            return None
