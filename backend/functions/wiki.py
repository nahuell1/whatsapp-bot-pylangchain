"""Wikipedia lookup function."""

import logging
import httpx
import urllib.parse
from typing import Dict, Any, List, Tuple
from datetime import datetime

from functions.base import FunctionBase, bot_function

logger = logging.getLogger(__name__)


@bot_function("wiki")
class WikiFunction(FunctionBase):
    """Search Wikipedia (pref English, fallback Spanish) and return first paragraph + link."""

    SEARCH_ENDPOINT = "https://{lang}.wikipedia.org/w/api.php"
    SUMMARY_ENDPOINT = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
    LANGS = ["en", "es"]  # preference order

    def __init__(self):
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
        try:
            params = self.validate_parameters(**kwargs)
            query = (params.get("query") or "").strip()
            if not query:
                return self.format_error_response("Query vacía")
            logger.info(f"Wikipedia lookup query='{query}'")

            # Perform searches in preferred languages
            candidates: List[Tuple[float, str, str]] = []  # (score, lang, title)
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0), headers={"User-Agent": "WhatsAppBotWiki/1.0"}) as client:
                for lang in self.LANGS:
                    try:
                        titles = await self._search(client, lang, query)
                        scored = [(self._score(query, t), lang, t) for t in titles]
                        for sc in scored:
                            candidates.append(sc)
                        logger.debug(f"Lang {lang} returned {len(titles)} titles")
                    except Exception as e:  # pragma: no cover
                        logger.debug(f"Search failed for {lang}: {e}")

                if not candidates:
                    return self.format_error_response("No se encontraron resultados en Wikipedia")

                # Sort by: score desc, language preference (index in LANGS), original order preserved by stable sort
                candidates.sort(key=lambda x: (-x[0], self.LANGS.index(x[1]) if x[1] in self.LANGS else 99))
                best_score, best_lang, best_title = candidates[0]

                # If best is Spanish but there exists a close English (>0.9) we keep English; logic already in sort.
                summary = await self._fetch_summary(client, best_lang, best_title)
                if not summary:
                    return self.format_error_response("No se pudo obtener el resumen del artículo")

                # If disambiguation, try next candidate non-disambiguation
                if summary.get('type') == 'disambiguation':
                    for sc, lang, title in candidates[1:5]:
                        alt = await self._fetch_summary(client, lang, title)
                        if alt and alt.get('type') != 'disambiguation':
                            summary = alt
                            best_lang = lang
                            best_title = title
                            best_score = sc
                            break

            extract = (summary.get('extract') or '').strip()
            # Take only first paragraph
            first_para = extract.split('\n')[0].strip()
            url = summary.get('content_urls', {}).get('desktop', {}).get('page') or summary.get('canonicalurl') or summary.get('title')
            display_title = summary.get('displaytitle') or best_title
            lang_label = 'English' if best_lang == 'en' else 'Español'

            response = self._format_response(display_title, first_para, url, lang_label, best_score)
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
            logger.error(f"Error in wiki function: {e}")
            return self.format_error_response(str(e))

    async def _search(self, client: httpx.AsyncClient, lang: str, query: str) -> List[str]:
        params = {
            'action': 'opensearch',
            'search': query,
            'limit': 5,
            'namespace': 0,
            'format': 'json'
        }
        r = await client.get(self.SEARCH_ENDPOINT.format(lang=lang), params=params)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) >= 2:
            return data[1]
        return []

    async def _fetch_summary(self, client: httpx.AsyncClient, lang: str, title: str) -> Dict[str, Any]:
        encoded = urllib.parse.quote(title.replace(' ', '_'))
        url = self.SUMMARY_ENDPOINT.format(lang=lang, title=encoded)
        r = await client.get(url)
        if r.status_code >= 400:
            return {}
        return r.json()

    def _score(self, query: str, title: str) -> float:
        q = query.lower().strip()
        t = title.lower().strip()
        if q == t:
            return 1.0
        # Simple token overlap score
        qt = set(q.split())
        tt = set(t.split())
        if not qt or not tt:
            return 0.0
        overlap = len(qt & tt) / len(qt)
        # boost if title starts with query
        if t.startswith(q):
            overlap += 0.2
        return min(overlap, 1.0)

    def _format_response(self, title: str, paragraph: str, url: str, lang_label: str, score: float) -> str:
        resp = f"📚 Wikipedia ({lang_label})\n\n" + f"**{title}**\n\n"
        if paragraph:
            # Truncate if very long
            if len(paragraph) > 900:
                paragraph = paragraph[:900].rsplit(' ', 1)[0] + '...'
            resp += paragraph + '\n\n'
        resp += f"🔗 {url}\n"
        return resp
