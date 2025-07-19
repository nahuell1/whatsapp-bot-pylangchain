"""
News function to get latest news from Reddit Argentina RSS feed.
"""

import httpx
import logging
from typing import Dict, Any
import xml.etree.ElementTree as ET
from datetime import datetime
import re

from functions.base import FunctionBase, bot_function

logger = logging.getLogger(__name__)


@bot_function("news")
class NewsFunction(FunctionBase):
    """Get latest news from Reddit Argentina RSS feed."""
    
    def __init__(self):
        """Initialize the News function."""
        super().__init__(
            name="news",
            description="Get the latest news from Reddit Argentina",
            parameters={},  # No parameters needed
            command_info={
                "usage": "!news",
                "examples": [
                    "!news"
                ],
                "parameter_mapping": {}  # No parameters needed
            },
            intent_examples=[
                {
                    "message": "show me the latest news",
                    "parameters": {}
                },
                {
                    "message": "what's happening in Argentina",
                    "parameters": {}
                }
            ]
        )
        self.rss_url = "https://www.reddit.com/r/argentina/.rss"
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the news function.
        
        Args:
            **kwargs: Function parameters (none needed)
            
        Returns:
            Latest news from Reddit Argentina
        """
        try:
            logger.info("Fetching latest news from Reddit Argentina")
            
            # Fetch RSS feed
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(self.rss_url, timeout=10.0)
                response.raise_for_status()
                
                # Parse XML
                root = ET.fromstring(response.content)
                
                # Extract entries
                entries = []
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                
                for entry in root.findall('.//atom:entry', ns)[:10]:  # Get top 10
                    try:
                        title = entry.find('atom:title', ns).text if entry.find('atom:title', ns) is not None else "Sin título"
                        link = entry.find('atom:link', ns).get('href') if entry.find('atom:link', ns) is not None else ""
                        published = entry.find('atom:published', ns).text if entry.find('atom:published', ns) is not None else ""
                        author_elem = entry.find('atom:author/atom:name', ns)
                        author = author_elem.text if author_elem is not None else "Anónimo"
                        content_elem = entry.find('atom:content', ns)
                        content = content_elem.text if content_elem is not None else ""
                        
                        # Clean up author name
                        if author.startswith('/u/'):
                            author = author[3:]
                        
                        # Extract summary from content (remove HTML)
                        summary = self._extract_summary(content)
                        
                        # Format date
                        formatted_date = self._format_date(published)
                        
                        entries.append({
                            'title': title,
                            'author': author,
                            'summary': summary,
                            'link': link,
                            'date': formatted_date
                        })
                        
                    except Exception as e:
                        logger.warning(f"Error parsing entry: {e}")
                        continue
                
                if not entries:
                    return self.format_error_response("No se pudieron obtener noticias")
                
                # Format response
                response_text = self._format_news_response(entries)
                
                return self.format_success_response(
                    {"news_count": len(entries), "entries": entries},
                    response_text
                )
                
        except httpx.TimeoutException:
            logger.error("Timeout fetching news")
            return self.format_error_response("Timeout al obtener noticias. Intenta nuevamente.")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching news: {e}")
            return self.format_error_response(f"Error HTTP al obtener noticias: {e.response.status_code}")
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            return self.format_error_response("Error al procesar el feed de noticias")
        except Exception as e:
            logger.error(f"Error in news function: {str(e)}")
            return self.format_error_response(f"Error al obtener noticias: {str(e)}")
    
    def _extract_summary(self, content: str) -> str:
        """Extract a clean summary from HTML content."""
        if not content:
            return "Sin resumen disponible"
        
        # Remove HTML tags
        clean_content = re.sub(r'<[^>]+>', '', content)
        
        # Remove extra whitespace and newlines
        clean_content = re.sub(r'\s+', ' ', clean_content).strip()
        
        # Remove Reddit-specific text patterns
        clean_content = re.sub(r'submitted by.*?\[link\].*?\[comments\]', '', clean_content)
        clean_content = re.sub(r'&#32;', ' ', clean_content)
        
        # Truncate to reasonable length
        if len(clean_content) > 200:
            clean_content = clean_content[:200] + "..."
        
        return clean_content or "Sin resumen disponible"
    
    def _format_date(self, date_str: str) -> str:
        """Format date string to a readable format."""
        try:
            # Parse ISO format
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            # Format to Argentine locale style
            return dt.strftime('%d/%m/%Y %H:%M')
        except Exception:
            return date_str
    
    def _format_news_response(self, entries: list) -> str:
        """Format the news entries into a readable message."""
        response = "📰 *Últimas noticias de Reddit Argentina*\n\n"
        
        for i, entry in enumerate(entries, 1):
            response += f"*{i}. {entry['title']}*\n"
            
            response += f"🔗 {entry['link']}\n\n"
            
            # Add separator except for last item
            if i < len(entries):
                response += "─" * 3 + "\n\n"
        
        response += "🇦🇷 *Fuente: Reddit Argentina*"
        return response
