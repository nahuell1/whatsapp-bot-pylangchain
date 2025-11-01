"""Dollar price function to get current USD exchange rates from DolarAPI.

Fetches real-time USD exchange rates for Argentina including official,
blue, and other market rates.
"""

import logging
from datetime import datetime
from typing import Any, Dict

import httpx

from functions.base import FunctionBase, bot_function

logger = logging.getLogger(__name__)

API_TIMEOUT_SECONDS = 10.0


@bot_function("dollar")
class DollarFunction(FunctionBase):
    """Get current USD exchange rates from DolarAPI.
    
    Provides official, blue, crypto, and card exchange rates for
    Argentina with real-time updates.
    """
    
    def __init__(self):
        """Initialize the dollar function with DolarAPI endpoint."""
        super().__init__(
            name="dollar",
            description="Get current USD exchange rates in Argentina",
            parameters={},  # No parameters needed
            command_info={
                "usage": "!dollar",
                "examples": [
                    "!dollar",
                    "!dolar"
                ],
                "parameter_mapping": {},  # No parameters needed
                "aliases": ["dolar"]
            },
            intent_examples=[
                {
                    "message": "what's the dollar price today",
                    "parameters": {}
                },
                {
                    "message": "current USD exchange rate",
                    "parameters": {}
                }
            ]
        )
        self.api_url = "https://dolarapi.com/v1/dolares"
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the dollar function.
        
        Args:
            **kwargs: Function parameters (none required)
            
        Returns:
            Dict with exchange rates and formatted message
        """
        try:
            logger.info("Fetching current USD exchange rates from DolarAPI")
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    self.api_url,
                    timeout=API_TIMEOUT_SECONDS
                )
                response.raise_for_status()
                
                dollar_data = response.json()
                
                if not dollar_data:
                    return self.format_error_response(
                        "Could not fetch dollar prices"
                    )
                
                response_text = self._format_dollar_response(dollar_data)
                
                return self.format_success_response(
                    {"rates": dollar_data, "count": len(dollar_data)},
                    response_text
                )
                
        except httpx.TimeoutException:
            logger.error("Timeout fetching dollar prices")
            return self.format_error_response(
                "Timeout fetching dollar prices. Try again."
            )
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error fetching dollar prices: %s", e)
            return self.format_error_response(
                f"HTTP error fetching dollar prices: {e.response.status_code}"
            )
        except Exception as e:
            logger.error("Error in dollar function: %s", str(e))
            return self.format_error_response(
                f"Error fetching dollar prices: {str(e)}"
            )
    
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
    
    def _format_dollar_response(self, dollar_data: list) -> str:
        """Format dollar rates into a readable message.
        
        Args:
            dollar_data: List of exchange rate dicts
            
        Returns:
            Formatted message with rates and comparisons
        """
        response = "💵 *Dollar Prices in Argentina 🇦🇷*\n\n"
        
        oficial_rate = None
        for rate in dollar_data:
            if rate.get('casa') == 'oficial':
                oficial_rate = rate
                break
        
        priority_order = ['oficial', 'blue', 'cripto', 'tarjeta']
        
        sorted_data = []
        for priority in priority_order:
            for rate in dollar_data:
                if rate.get('casa') == priority:
                    sorted_data.append(rate)
                    break
        
        for i, rate in enumerate(sorted_data):
            casa = rate.get('casa', '')
            nombre = rate.get('nombre', casa.title())
            compra = rate.get('compra', 0)
            venta = rate.get('venta', 0)
            fecha = rate.get('fechaActualizacion', '')
            
            compra_formatted = f"${compra:,.2f}".replace(',', '.')
            venta_formatted = f"${venta:,.2f}".replace(',', '.')
            
            emoji = self._get_emoji_for_casa(casa)
            
            diff_text = ""
            if oficial_rate and casa != 'oficial':
                diff_text = self._calculate_difference(
                    venta,
                    oficial_rate.get('venta', 0)
                )
            
            response += f"{emoji} *{nombre}*{diff_text}\n"
            response += f"  💰 Buy: {compra_formatted}\n"
            response += f"  💸 Sell: {venta_formatted}\n"
            
            if fecha:
                formatted_date = self._format_date(fecha)
                response += f"  🕐 Updated: {formatted_date}\n"
            
            if i < len(sorted_data) - 1:
                response += "\n"
        return response
    
    @staticmethod
    def _calculate_difference(
        current_price: float,
        oficial_price: float
    ) -> str:
        """Calculate difference with official rate.
        
        Args:
            current_price: Current rate price
            oficial_price: Official rate price
            
        Returns:
            Formatted difference string with absolute and percentage
        """
        if oficial_price == 0:
            return ""
        
        diff_amount = current_price - oficial_price
        diff_percentage = (diff_amount / oficial_price) * 100
        
        sign = "+" if diff_amount > 0 else ""
        diff_formatted = f"${diff_amount:,.2f}".replace(',', '.')
        
        return f" ({sign}{diff_formatted} / {diff_percentage:+.1f}%)"
    
    @staticmethod
    def _get_emoji_for_casa(casa: str) -> str:
        """Get emoji for exchange house type.
        
        Args:
            casa: Exchange house type identifier
            
        Returns:
            Emoji representing the exchange house
        """
        emoji_map = {
            'oficial': '🏛️',
            'blue': '🔵',
            'bolsa': '📈',
            'contadoconliqui': '💹',
            'mayorista': '🏪',
            'cripto': '₿',
            'tarjeta': '💳'
        }
        return emoji_map.get(casa, '💵')
