"""
Dollar price function to get current USD exchange rates from DolarAPI.
"""

import httpx
import logging
from typing import Dict, Any
from datetime import datetime

from functions.base import FunctionBase

logger = logging.getLogger(__name__)


class DollarFunction(FunctionBase):
    """Get current USD exchange rates from DolarAPI."""
    
    def __init__(self):
        """Initialize the Dollar function."""
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
            }
        )
        self.api_url = "https://dolarapi.com/v1/dolares"
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the dollar function.
        
        Args:
            **kwargs: Function parameters (none needed)
            
        Returns:
            Current USD exchange rates
        """
        try:
            logger.info("Fetching current USD exchange rates from DolarAPI")
            
            # Fetch dollar prices
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(self.api_url, timeout=10.0)
                response.raise_for_status()
                
                # Parse JSON response
                dollar_data = response.json()
                
                if not dollar_data:
                    return self.format_error_response("No se pudieron obtener los precios del dólar")
                
                # Format response
                response_text = self._format_dollar_response(dollar_data)
                
                return self.format_success_response(
                    {"rates": dollar_data, "count": len(dollar_data)},
                    response_text
                )
                
        except httpx.TimeoutException:
            logger.error("Timeout fetching dollar prices")
            return self.format_error_response("Timeout al obtener precios del dólar. Intenta nuevamente.")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching dollar prices: {e}")
            return self.format_error_response(f"Error HTTP al obtener precios del dólar: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error in dollar function: {str(e)}")
            return self.format_error_response(f"Error al obtener precios del dólar: {str(e)}")
    
    def _format_date(self, date_str: str) -> str:
        """Format date string to a readable format."""
        try:
            # Parse ISO format
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            # Format to Argentine locale style
            return dt.strftime('%d/%m/%Y %H:%M')
        except Exception:
            return date_str
    
    def _format_dollar_response(self, dollar_data: list) -> str:
        """Format the dollar rates into a readable message."""
        response = "💵 *Precios del Dólar en Argentina 🇦🇷*\n\n"
        
        # Find oficial rate for comparison
        oficial_rate = None
        for rate in dollar_data:
            if rate.get('casa') == 'oficial':
                oficial_rate = rate
                break
        
        # Sort by importance (put most common ones first)
        priority_order = ['oficial', 'blue', 'cripto', 'tarjeta']
        
        # Sort dollar_data based on priority_order
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
            
            # Format numbers with thousands separator
            compra_formatted = f"${compra:,.2f}".replace(',', '.')
            venta_formatted = f"${venta:,.2f}".replace(',', '.')
            
            # Add emoji based on type
            emoji = self._get_emoji_for_casa(casa)
            
            # Calculate difference with oficial rate
            diff_text = ""
            if oficial_rate and casa != 'oficial':
                diff_text = self._calculate_difference(venta, oficial_rate.get('venta', 0))
            
            response += f"{emoji} *{nombre}*{diff_text}\n"
            response += f"  💰 Compra: {compra_formatted}\n"
            response += f"  💸 Venta: {venta_formatted}\n"
            
            if fecha:
                formatted_date = self._format_date(fecha)
                response += f"  🕐 Actualizado: {formatted_date}\n"
            
            # Add separator except for last item
            if i < len(sorted_data) - 1:
                response += "\n"
        return response
    
    def _calculate_difference(self, current_price: float, oficial_price: float) -> str:
        """Calculate difference with oficial rate."""
        if oficial_price == 0:
            return ""
        
        # Calculate absolute difference
        diff_amount = current_price - oficial_price
        
        # Calculate percentage difference
        diff_percentage = (diff_amount / oficial_price) * 100
        
        # Format the difference
        if diff_amount > 0:
            sign = "+"
            diff_formatted = f"${diff_amount:,.2f}".replace(',', '.')
        else:
            sign = ""
            diff_formatted = f"${diff_amount:,.2f}".replace(',', '.')
        
        return f" ({sign}{diff_formatted} / {diff_percentage:+.1f}%)"
    
    def _get_emoji_for_casa(self, casa: str) -> str:
        """Get appropriate emoji for each casa."""
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
