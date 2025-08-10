"""
Fetch trending X (Twitter) topics via public trends24.in HTML parsing.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
import httpx
from bs4 import BeautifulSoup

from functions.base import FunctionBase, bot_function

logger = logging.getLogger(__name__)


@bot_function("trends")
class TrendsFunction(FunctionBase):
    """Get current X (Twitter) trending topics for a region (best-effort, no auth)."""

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
        super().__init__(
            name="trends",
            description="Get current X (Twitter) trending topics (no API key needed)",
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
        try:
            params = self.validate_parameters(**kwargs)
            region = params.get("region") or "worldwide"
            count = params.get("count", 10)
            if count < 1:
                count = 1
            if count > 20:
                count = 20

            norm_region = self._normalize_region(region)
            logger.info(f"Fetching trends for region '{region}' -> slug '{norm_region}' (count={count})")

            trends = await self._fetch_trends(norm_region)
            if not trends:
                return self.format_error_response(f"No trends found for {region}")

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
            logger.error(f"Error in trends function: {e}")
            return self.format_error_response(str(e))

    def _normalize_region(self, region: str) -> str:
        key = (region or "").strip().lower()
        return self.REGION_SYNONYMS.get(key, key if key else "worldwide")

    async def _fetch_trends(self, region_slug: str) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}/" if region_slug in ("world", "worldwide", "") else f"{self.BASE_URL}/{region_slug}/"
        timeout = httpx.Timeout(10.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (WhatsAppBot TrendsFetcher)"}) as client:
            r = await client.get(url)
            r.raise_for_status()
            html = r.text
        soup = BeautifulSoup(html, "html.parser")

        trends: List[Dict[str, Any]] = []

        # Primary strategy: first trend-card list
        try:
            card = soup.find("div", class_="trend-card")
            if card:
                trend_list = card.find("ol", class_="trend-card__list") or card.find("ol")
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
                            link = f"https://twitter.com{link}" if "/search?q=" in link else f"{self.BASE_URL}{link}"
                        trends.append({"name": name, "url": link})
        except Exception as e:  # pragma: no cover
            logger.debug(f"Primary trends parse failed: {e}")

        # Fallback: any ol.trend-card__list on page (pick first with >=5 items)
        if len(trends) < 3:
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
                        link = f"https://twitter.com{link}" if "/search?q=" in link else f"{self.BASE_URL}{link}"
                    cand.append({"name": name, "url": link})
                if len(cand) >= 3:
                    trends = cand
                    break

        # Last resort: collect any anchors with hashtag or leading # text
        if len(trends) < 3:
            seen = set()
            for a in soup.find_all('a'):
                txt = a.get_text(strip=True)
                if not txt or len(txt) > 80:
                    continue
                if txt.startswith('#') and txt.lower() not in seen:
                    link = a.get('href')
                    if link and link.startswith('/'):
                        link = f"https://twitter.com{link}" if "/search?q=" in link else f"{self.BASE_URL}{link}"
                    trends.append({"name": txt, "url": link})
                    seen.add(txt.lower())
                if len(trends) >= 10:
                    break

        logger.debug(f"Parsed {len(trends)} trends from {url}")
        return trends

    def _format_response(self, result: Dict[str, Any]) -> str:
        lines = [f"📈 X Trends: {result['region']} ({result['count']})"]
        for idx, t in enumerate(result['trends'], 1):
            lines.append(f"{idx}. {t['name']}")
        lines.append("\nFuente: trends24.in (no oficial)")
        return "\n".join(lines)
