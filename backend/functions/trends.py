"""Fetch trending X (Twitter) topics via public trends24.in HTML parsing.

Scrapes trends24.in to provide trending topics by region without requiring
Twitter API authentication.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

import httpx
from bs4 import BeautifulSoup

from functions.base import FunctionBase, bot_function

logger = logging.getLogger(__name__)

HTTP_TIMEOUT_SECONDS = 10.0
HTTP_CONNECT_TIMEOUT = 5.0
MIN_TRENDS_COUNT = 3
MAX_TREND_NAME_LENGTH = 80
FALLBACK_HASHTAG_LIMIT = 10
MIN_COUNT = 1
MAX_COUNT = 20
DEFAULT_COUNT = 10


@bot_function("trends")
class TrendsFunction(FunctionBase):
    """Get current X (Twitter) trending topics by region.
    
    Scrapes trends24.in to fetch trending topics without requiring
    Twitter API credentials. Supports multiple regions with synonym mapping.
    """

    BASE_URL = "https://trends24.in"

    REGION_SYNONYMS = {
        "world": "worldwide",
        "worldwide": "worldwide",
        "global": "worldwide",
        "arg": "argentina",
        "ar": "argentina",
        "argentina": "argentina",
        "spain": "spain",
        "es": "spain",
        "usa": "united-states",
        "us": "united-states",
        "united-states": "united-states",
        "mex": "mexico",
        "mx": "mexico",
        "mexico": "mexico",
    }

    def __init__(self):
        """Initialize trends function with region synonyms and parameters."""
        super().__init__(
            name="trends",
            description=(
                "Get current X (Twitter) trending topics (no API key needed)"
            ),
            parameters={
                "region": {
                    "type": "string",
                    "description": "Region / country (e.g. argentina, worldwide)",
                    "default": "worldwide"
                },
                "count": {
                    "type": "integer",
                    "description": "Max number of trends to return (1-20)",
                    "default": 10
                }
            },
            command_info={
                "usage": "!trends [region]",
                "examples": [
                    "!trends",
                    "!trends argentina",
                    "!tt ar",
                    "!tendencias world"
                ],
                "aliases": ["tt", "tendencias"],
                "parameter_mapping": {
                    "region": "first_arg"
                }
            },
            intent_examples=[
                {"message": "what's trending now", "parameters": {}},
                {"message": "twitter trends argentina", "parameters": {"region": "argentina"}}
            ]
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the trends function.
        
        Args:
            **kwargs: Function parameters (region, count)
            
        Returns:
            Dict with trending topics and metadata
        """
        try:
            params = self.validate_parameters(**kwargs)
            region = params.get("region") or "worldwide"
            count = params.get("count", DEFAULT_COUNT)
            count = max(MIN_COUNT, min(count, MAX_COUNT))

            norm_region = self._normalize_region(region)
            logger.info(
                "Fetching trends for region '%s' -> slug '%s' (count=%d)",
                region, norm_region, count
            )

            trends = await self._fetch_trends(norm_region)
            if not trends:
                return self.format_error_response(
                    f"No trends found for {region}"
                )

            top = trends[:count]
            result = {
                "region": region,
                "normalized_region": norm_region,
                "count": len(top),
                "trends": top,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            response = self._format_response(result)
            return self.format_success_response(result, response)
        except Exception as e:
            logger.error("Error in trends function: %s", e)
            return self.format_error_response(str(e))

    def _normalize_region(self, region: str) -> str:
        """Normalize region name using synonym mapping.
        
        Args:
            region: User-provided region name
            
        Returns:
            Normalized region slug for trends24.in
        """
        key = (region or "").strip().lower()
        return self.REGION_SYNONYMS.get(key, key if key else "worldwide")

    async def _fetch_trends(self, region_slug: str) -> List[Dict[str, Any]]:
        """Fetch and parse trends from trends24.in.
        
        Uses multiple parsing strategies for robustness.
        
        Args:
            region_slug: Normalized region slug
            
        Returns:
            List of trend dicts with name and url
        """
        url = (
            f"{self.BASE_URL}/" if region_slug in ("world", "worldwide", "")
            else f"{self.BASE_URL}/{region_slug}/"
        )
        timeout = httpx.Timeout(HTTP_TIMEOUT_SECONDS, connect=HTTP_CONNECT_TIMEOUT)
        async with httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (WhatsAppBot TrendsFetcher)"}
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            html = r.text
        soup = BeautifulSoup(html, "html.parser")

        trends: List[Dict[str, Any]] = []

        try:
            card = soup.find("div", class_="trend-card")
            if card:
                trend_list = (
                    card.find("ol", class_="trend-card__list") or card.find("ol")
                )
                if trend_list:
                    for li in trend_list.find_all("li"):
                        a = li.find("a")
                        if not a:
                            continue
                        name = a.get_text(strip=True)
                        if not name:
                            continue
                        link = a.get("href")
                        if link and link.startswith("/"):
                            link = (
                                f"https://twitter.com{link}"
                                if "/search?q=" in link
                                else f"{self.BASE_URL}{link}"
                            )
                        trends.append({"name": name, "url": link})
        except Exception as e:
            logger.debug("Primary trends parse failed: %s", e)

        if len(trends) < MIN_TRENDS_COUNT:
            for ol in soup.find_all("ol", class_="trend-card__list"):
                cand = []
                for li in ol.find_all("li"):
                    a = li.find("a")
                    if not a:
                        continue
                    name = a.get_text(strip=True)
                    if not name:
                        continue
                    link = a.get("href")
                    if link and link.startswith("/"):
                        link = (
                            f"https://twitter.com{link}"
                            if "/search?q=" in link
                            else f"{self.BASE_URL}{link}"
                        )
                    cand.append({"name": name, "url": link})
                if len(cand) >= MIN_TRENDS_COUNT:
                    trends = cand
                    break

        if len(trends) < MIN_TRENDS_COUNT:
            seen = set()
            for a in soup.find_all('a'):
                txt = a.get_text(strip=True)
                if not txt or len(txt) > MAX_TREND_NAME_LENGTH:
                    continue
                if txt.startswith('#') and txt.lower() not in seen:
                    link = a.get('href')
                    if link and link.startswith('/'):
                        link = (
                            f"https://twitter.com{link}"
                            if "/search?q=" in link
                            else f"{self.BASE_URL}{link}"
                        )
                    trends.append({"name": txt, "url": link})
                    seen.add(txt.lower())
                if len(trends) >= FALLBACK_HASHTAG_LIMIT:
                    break

        logger.debug("Parsed %d trends from %s", len(trends), url)
        return trends

    @staticmethod
    def _format_response(result: Dict[str, Any]) -> str:
        """Format trends result into readable message.
        
        Args:
            result: Dict with region, count, and trends list
            
        Returns:
            Formatted message with numbered trends
        """
        lines = [f"📈 X Trends: {result['region']} ({result['count']})"]
        for idx, t in enumerate(result['trends'], 1):
            lines.append(f"{idx}. {t['name']}")
        lines.append("\nSource: trends24.in (unofficial)")
        return "\n".join(lines)
