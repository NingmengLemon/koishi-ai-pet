"""浏览器操作核心逻辑。"""

import logging
import webbrowser

logger = logging.getLogger(__name__)


class BrowserTool:
    def open_url(self, url: str) -> dict:
        """打开指定网址。"""
        webbrowser.open(url)
        return {"status": "opened", "url": url}

    def search(self, query: str) -> dict:
        """用默认浏览器搜索。"""
        url = f"https://www.bing.com/search?q={query}"
        webbrowser.open(url)
        return {"status": "searching", "query": query, "url": url}