"""
搜索服务
网络搜索功能
"""
import json
from typing import List, Dict, Optional
import httpx
from abc import ABC, abstractmethod
from config import settings


class BaseSearchProvider(ABC):
    """搜索提供商基类"""
    
    @abstractmethod
    async def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """执行搜索"""
        pass
    
    @abstractmethod
    async def get_content(self, url: str) -> str:
        """获取页面内容"""
        pass


class DuckDuckGoSearch(BaseSearchProvider):
    """DuckDuckGo搜索（使用 HTML 搜索接口）"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """执行 DuckDuckGo HTML 搜索"""
        try:
            url = "https://html.duckduckgo.com/html/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            data = {"q": query}
            response = await self.client.post(url, data=data, headers=headers)
            response.raise_for_status()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            for i, result in enumerate(soup.select(".result"), 1):
                if i > num_results:
                    break

                title_el = result.select_one(".result__title a")
                snippet_el = result.select_one(".result__snippet")
                url_el = result.select_one(".result__url")

                title = title_el.get_text(strip=True) if title_el else ""
                href = title_el.get("href", "") if title_el else ""
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                display_url = url_el.get_text(strip=True) if url_el else ""

                # DuckDuckGo 使用重定向链接，需要提取真实 URL
                import re
                real_url = href
                if "uddg=" in str(href):
                    m = re.search(r'uddg=([^&]+)', str(href))
                    if m:
                        from urllib.parse import unquote
                        real_url = unquote(m.group(1))

                if title:
                    results.append({
                        "title": title,
                        "url": real_url,
                        "snippet": snippet,
                        "source": "DuckDuckGo"
                    })

            return results[:num_results]
        except Exception as e:
            return [{"error": str(e)}]
    
    async def get_content(self, url: str) -> str:
        """获取页面内容"""
        try:
            response = await self.client.get(url, timeout=30.0)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            return "\n".join(lines[:100])
        except Exception as e:
            return f"Error fetching content: {str(e)}"
    
    async def close(self):
        await self.client.aclose()


class TavilySearch(BaseSearchProvider):
    """Tavily AI搜索"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.search.tavily_api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """执行Tavily搜索"""
        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": num_results
            }
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for result in data.get("results", [])[:num_results]:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("content", ""),
                    "source": "Tavily"
                })
            
            return results
        except Exception as e:
            return [{"error": str(e)}]
    
    async def get_content(self, url: str) -> str:
        """获取页面内容"""
        try:
            url_endpoint = "https://api.tavily.com/extract"
            payload = {"api_key": self.api_key, "urls": [url]}
            response = await self.client.post(url_endpoint, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if data.get("results"):
                return data["results"][0].get("raw_content", "")
            return ""
        except Exception as e:
            return f"Error extracting content: {str(e)}"
    
    async def close(self):
        await self.client.aclose()


class BraveSearch(BaseSearchProvider):
    """Brave搜索"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.search.brave_api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key
        }
    
    async def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """执行Brave搜索"""
        try:
            url = "https://api.search.brave.com/res/v1/web/search"
            params = {
                "q": query,
                "count": num_results
            }
            response = await self.client.get(
                url,
                params=params,
                headers=self._get_headers()
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("web", {}).get("results", [])[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("description", ""),
                    "source": "Brave"
                })
            
            return results
        except Exception as e:
            return [{"error": str(e)}]
    
    async def get_content(self, url: str) -> str:
        """获取页面内容"""
        try:
            response = await self.client.get(url, timeout=30.0)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            return "\n".join(lines[:100])
        except Exception as e:
            return f"Error fetching content: {str(e)}"
    
    async def close(self):
        await self.client.aclose()


class SearXNGSearch(BaseSearchProvider):
    """SearXNG自托管搜索"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.search.searxng_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """执行SearXNG搜索"""
        try:
            url = f"{self.base_url}/search"
            params = {
                "q": query,
                "format": "json",
                "engines": "google,duckduckgo",
                "limit": num_results
            }
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", [])[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", ""),
                    "source": "SearXNG"
                })
            
            return results
        except Exception as e:
            return [{"error": str(e)}]
    
    async def get_content(self, url: str) -> str:
        """获取页面内容"""
        try:
            response = await self.client.get(url, timeout=30.0)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            return "\n".join(lines[:100])
        except Exception as e:
            return f"Error fetching content: {str(e)}"
    
    async def close(self):
        await self.client.aclose()


class BingSearch(BaseSearchProvider):
    """Bing 搜索（HTML 抓取，国内可用）"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """执行 Bing HTML 搜索"""
        try:
            url = "https://www.bing.com/search"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            params = {
                "q": query,
                "count": num_results,
                "setlang": "zh-cn",
            }
            response = await self.client.get(url, params=params, headers=headers)
            response.raise_for_status()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            # Bing 有两种结果布局: li.b_algo (新版) 和 .b_caption (旧版)
            for i, result in enumerate(soup.select("li.b_algo"), 1):
                if i > num_results:
                    break

                title_el = result.select_one("h2 a")
                snippet_el = result.select_one(".b_caption p")
                url_el = result.select_one(".b_attribution cite")

                title = title_el.get_text(strip=True) if title_el else ""
                href = title_el.get("href", "") if title_el else ""
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                if title:
                    results.append({
                        "title": title,
                        "url": href,
                        "snippet": snippet,
                        "source": "Bing"
                    })

            return results[:num_results]
        except Exception as e:
            return [{"error": str(e)}]

    async def get_content(self, url: str) -> str:
        """获取页面内容"""
        try:
            response = await self.client.get(url, timeout=30.0)
            response.raise_for_status()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")

            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()

            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            return "\n".join(lines[:100])
        except Exception as e:
            return f"Error fetching content: {str(e)}"

    async def close(self):
        await self.client.aclose()


class SearchService:
    """搜索服务"""
    
    def __init__(self):
        self.providers: Dict[str, BaseSearchProvider] = {}
    
    def get_provider(self, provider_type: str = None) -> BaseSearchProvider:
        """获取搜索提供商"""
        if provider_type is None:
            provider_type = settings.search.search_provider
        
        if provider_type not in self.providers:
            if provider_type == "duckduckgo":
                self.providers[provider_type] = DuckDuckGoSearch()
            elif provider_type == "tavily":
                self.providers[provider_type] = TavilySearch()
            elif provider_type == "brave":
                self.providers[provider_type] = BraveSearch()
            elif provider_type == "searxng":
                self.providers[provider_type] = SearXNGSearch()
            elif provider_type == "bing":
                self.providers[provider_type] = BingSearch()
            else:
                self.providers[provider_type] = BingSearch()
        
        return self.providers[provider_type]
    
    async def search(
        self,
        query: str,
        provider: str = None,
        num_results: int = None
    ) -> List[Dict]:
        """执行搜索"""
        if num_results is None:
            num_results = settings.search.search_result_count
        
        provider_obj = self.get_provider(provider)
        return await provider_obj.search(query, num_results)
    
    async def search_with_context(
        self,
        query: str,
        provider: str = None,
        num_results: int = None
    ) -> str:
        """搜索并返回带上下文的文本"""
        results = await self.search(query, provider, num_results)
        
        context = f"以下是与'{query}'相关的搜索结果:\n\n"
        for i, result in enumerate(results, 1):
            if "error" in result:
                continue
            context += f"{i}. {result['title']}\n"
            context += f"   来源: {result['url']}\n"
            context += f"   摘要: {result['snippet']}\n\n"
        
        return context
    
    async def close(self):
        """关闭所有连接"""
        for provider in self.providers.values():
            await provider.close()
