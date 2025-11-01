"""Wikipedia lookup function.

Searches Wikipedia with language preference (English first, Spanish fallback)
and returns article summaries with smart disambiguation handling.
"""

import logging
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Tuple

import httpx

from functions.base import FunctionBase, bot_function

logger = logging.getLogger(__name__)

HTTP_TIMEOUT_SECONDS = 10.0
HTTP_CONNECT_TIMEOUT = 5.0
MAX_SEARCH_RESULTS = 5
MAX_PARAGRAPH_LENGTH = 900
DISAMBIGUATION_CHECK_LIMIT = 5
TITLE_BOOST_SCORE = 0.2


@bot_function("wiki")
class WikiFunction(FunctionBase):
    """Search Wikipedia with English preference and Spanish fallback.
    
    Provides article summaries with smart scoring and disambiguation
    handling. Returns the first paragraph and article link.
    """

    SEARCH_ENDPOINT = "https://{lang}.wikipedia.org/w/api.php"
    SUMMARY_ENDPOINT = (
        "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
    )
    LANGS = ["en", "es"]

    def __init__(self):
        """Initialize Wikipedia function with search parameters."""
        super().__init__(
            name="wiki",
            description="Lookup a topic on Wikipedia (prefers English, falls back to Spanish)",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query/topic",
                    "required": True
                }
            },
            command_info={
                "usage": "!wiki <término>",
                "examples": [
                    "!wiki pez espada",
                    "!wiki draven",
                    "!wikipedia milanesa"
                ],
                "aliases": ["wikipedia"],
                "parameter_mapping": {"query": "join_args"}
            },
            intent_examples=[
                {"message": "search wikipedia for draven", "parameters": {"query": "draven"}},
                {"message": "wikipedia pez espada", "parameters": {"query": "pez espada"}}
            ]
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute Wikipedia search.
        
        Args:
            **kwargs: Function parameters (query)
            
        Returns:
            Dict with article summary and metadata
        """
        try:
            params = self.validate_parameters(**kwargs)
            query = (params.get("query") or "").strip()
            if not query:
                return self.format_error_response("Empty query")
            logger.info("Wikipedia lookup query='%s'", query)

            candidates: List[Tuple[float, str, str]] = []
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(
                    HTTP_TIMEOUT_SECONDS,
                    connect=HTTP_CONNECT_TIMEOUT
                ),
                headers={"User-Agent": "WhatsAppBotWiki/1.0"}
            ) as client:
                for lang in self.LANGS:
                    try:
                        titles = await self._search(client, lang, query)
                        scored = [
                            (self._score(query, t), lang, t) for t in titles
                        ]
                        candidates.extend(scored)
                        logger.debug(
                            "Lang %s returned %d titles", lang, len(titles)
                        )
                    except Exception as e:
                        logger.debug("Search failed for %s: %s", lang, e)

                if not candidates:
                    return self.format_error_response(
                        "No results found in Wikipedia"
                    )

                candidates.sort(
                    key=lambda x: (
                        -x[0],
                        self.LANGS.index(x[1]) if x[1] in self.LANGS else 99
                    )
                )
                best_score, best_lang, best_title = candidates[0]

                summary = await self._fetch_summary(
                    client, best_lang, best_title
                )
                if not summary:
                    return self.format_error_response(
                        "Could not fetch article summary"
                    )

                if summary.get('type') == 'disambiguation':
                    for sc, lang, title in candidates[
                        1:DISAMBIGUATION_CHECK_LIMIT
                    ]:
                        alt = await self._fetch_summary(client, lang, title)
                        if alt and alt.get('type') != 'disambiguation':
                            summary = alt
                            best_lang = lang
                            best_title = title
                            best_score = sc
                            break

            extract = (summary.get('extract') or '').strip()
            first_para = extract.split('\n')[0].strip()
            url = (
                summary.get('content_urls', {}).get('desktop', {}).get('page')
                or summary.get('canonicalurl')
                or summary.get('title')
            )
            display_title = summary.get('displaytitle') or best_title
            lang_label = 'English' if best_lang == 'en' else 'Spanish'

            response = self._format_response(
                display_title, first_para, url, lang_label, best_score
            )
            result = {
                "query": query,
                "title": display_title,
                "language": best_lang,
                "score": best_score,
                "url": url,
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }
            return self.format_success_response(result, response)
        except Exception as e:
            logger.error("Error in wiki function: %s", e)
            return self.format_error_response(str(e))

    async def _search(
        self,
        client: httpx.AsyncClient,
        lang: str,
        query: str
    ) -> List[str]:
        """Search Wikipedia for articles matching query.
        
        Args:
            client: HTTP client
            lang: Language code (en, es, etc.)
            query: Search query
            
        Returns:
            List of article titles
        """
        params = {
            'action': 'opensearch',
            'search': query,
            'limit': MAX_SEARCH_RESULTS,
            'namespace': 0,
            'format': 'json'
        }
        r = await client.get(
            self.SEARCH_ENDPOINT.format(lang=lang),
            params=params
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) >= 2:
            return data[1]
        return []

    async def _fetch_summary(
        self,
        client: httpx.AsyncClient,
        lang: str,
        title: str
    ) -> Dict[str, Any]:
        """Fetch article summary from Wikipedia REST API.
        
        Args:
            client: HTTP client
            lang: Language code
            title: Article title
            
        Returns:
            Dict with article summary or empty dict on error
        """
        encoded = urllib.parse.quote(title.replace(' ', '_'))
        url = self.SUMMARY_ENDPOINT.format(lang=lang, title=encoded)
        r = await client.get(url)
        if r.status_code >= 400:
            return {}
        return r.json()

    @staticmethod
    def _score(query: str, title: str) -> float:
        """Calculate relevance score between query and title.
        
        Uses token overlap and prefix matching for scoring.
        
        Args:
            query: Search query
            title: Article title
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        q = query.lower().strip()
        t = title.lower().strip()
        if q == t:
            return 1.0
        
        qt = set(q.split())
        tt = set(t.split())
        if not qt or not tt:
            return 0.0
        
        overlap = len(qt & tt) / len(qt)
        
        if t.startswith(q):
            overlap += TITLE_BOOST_SCORE
        
        return min(overlap, 1.0)

    @staticmethod
    def _format_response(
        title: str,
        paragraph: str,
        url: str,
        lang_label: str,
        score: float
    ) -> str:
        """Format Wikipedia result into readable message.
        
        Args:
            title: Article title
            paragraph: First paragraph text
            url: Article URL
            lang_label: Language label
            score: Relevance score (unused but kept for signature)
            
        Returns:
            Formatted message with title, paragraph, and link
        """
        resp = f"📚 Wikipedia ({lang_label})\n\n**{title}**\n\n"
        if paragraph:
            if len(paragraph) > MAX_PARAGRAPH_LENGTH:
                paragraph = (
                    paragraph[:MAX_PARAGRAPH_LENGTH].rsplit(' ', 1)[0] + '...'
                )
            resp += paragraph + '\n\n'
        resp += f"🔗 {url}\n"
        return resp
