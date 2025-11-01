"""News function to get latest news from Reddit Argentina RSS feed.

Fetches and parses RSS feed from Reddit Argentina, extracting
titles, authors, and links with clean formatting.
"""

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict

import httpx

from functions.base import FunctionBase, bot_function

logger = logging.getLogger(__name__)

RSS_TIMEOUT_SECONDS = 10.0
MAX_NEWS_ITEMS = 10
MAX_SUMMARY_LENGTH = 200
ATOM_NAMESPACE = {'atom': 'http://www.w3.org/2005/Atom'}


@bot_function("news")
class NewsFunction(FunctionBase):
    """Get latest news from Reddit Argentina RSS feed.
    
    Provides top posts from r/argentina with titles, authors, and links.
    """
    
    def __init__(self):
        """Initialize the news function with Reddit RSS endpoint."""
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
        """Execute the news function.
        
        Args:
            **kwargs: Function parameters (none required)
            
        Returns:
            Dict with news entries and formatted message
        """
        try:
            logger.info("Fetching latest news from Reddit Argentina")
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    self.rss_url,
                    timeout=RSS_TIMEOUT_SECONDS
                )
                response.raise_for_status()
                
                root = ET.fromstring(response.content)
                
                entries = []
                
                for entry in root.findall(
                    './/atom:entry', ATOM_NAMESPACE
                )[:MAX_NEWS_ITEMS]:
                    try:
                        title_elem = entry.find('atom:title', ATOM_NAMESPACE)
                        title = (
                            title_elem.text if title_elem is not None
                            else "No title"
                        )
                        
                        link_elem = entry.find('atom:link', ATOM_NAMESPACE)
                        link = (
                            link_elem.get('href') if link_elem is not None
                            else ""
                        )
                        
                        pub_elem = entry.find('atom:published', ATOM_NAMESPACE)
                        published = (
                            pub_elem.text if pub_elem is not None else ""
                        )
                        
                        author_elem = entry.find(
                            'atom:author/atom:name', ATOM_NAMESPACE
                        )
                        author = (
                            author_elem.text if author_elem is not None
                            else "Anonymous"
                        )
                        
                        content_elem = entry.find('atom:content', ATOM_NAMESPACE)
                        content = (
                            content_elem.text if content_elem is not None else ""
                        )
                        
                        if author.startswith('/u/'):
                            author = author[3:]
                        
                        summary = self._extract_summary(content)
                        formatted_date = self._format_date(published)
                        
                        entries.append({
                            'title': title,
                            'author': author,
                            'summary': summary,
                            'link': link,
                            'date': formatted_date
                        })
                        
                    except Exception as e:
                        logger.warning("Error parsing entry: %s", e)
                        continue
                
                if not entries:
                    return self.format_error_response("Could not fetch news")
                
                response_text = self._format_news_response(entries)
                
                return self.format_success_response(
                    {"news_count": len(entries), "entries": entries},
                    response_text
                )
                
        except httpx.TimeoutException:
            logger.error("Timeout fetching news")
            return self.format_error_response(
                "Timeout fetching news. Try again."
            )
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error fetching news: %s", e)
            return self.format_error_response(
                f"HTTP error fetching news: {e.response.status_code}"
            )
        except ET.ParseError as e:
            logger.error("XML parse error: %s", e)
            return self.format_error_response("Error processing news feed")
        except Exception as e:
            logger.error("Error in news function: %s", str(e))
            return self.format_error_response(f"Error fetching news: {str(e)}")
    
    @staticmethod
    def _extract_summary(content: str) -> str:
        """Extract clean summary from HTML content.
        
        Args:
            content: HTML content string
            
        Returns:
            Cleaned and truncated summary text
        """
        if not content:
            return "No summary available"
        
        clean_content = re.sub(r'<[^>]+>', '', content)
        clean_content = re.sub(r'\s+', ' ', clean_content).strip()
        clean_content = re.sub(
            r'submitted by.*?\[link\].*?\[comments\]', '', clean_content
        )
        clean_content = re.sub(r'&#32;', ' ', clean_content)
        
        if len(clean_content) > MAX_SUMMARY_LENGTH:
            clean_content = clean_content[:MAX_SUMMARY_LENGTH] + "..."
        
        return clean_content or "No summary available"
    
    @staticmethod
    def _format_date(date_str: str) -> str:
        """Format ISO date string to readable format.
        
        Args:
            date_str: ISO 8601 date string
            
        Returns:
            Formatted date string (DD/MM/YYYY HH:MM)
        """
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%d/%m/%Y %H:%M')
        except Exception:
            return date_str
    
    @staticmethod
    def _format_news_response(entries: list) -> str:
        """Format news entries into readable message.
        
        Args:
            entries: List of news entry dicts
            
        Returns:
            Formatted message with news items
        """
        response = "📰 *Latest News from Reddit Argentina*\n\n"
        
        for i, entry in enumerate(entries, 1):
            response += f"*{i}. {entry['title']}*\n"
            response += f"🔗 {entry['link']}\n\n"
            
            if i < len(entries):
                response += "─" * 3 + "\n\n"
        
        response += "🇦🇷 *Source: Reddit Argentina*"
        return response
