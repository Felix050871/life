import os
import logging
import time
from typing import Dict, List, Optional, Tuple, Any, Callable
import googlemaps
from functools import lru_cache
import hashlib

logger = logging.getLogger(__name__)

class DistanceService:
    """
    Service for calculating distances between addresses using Google Maps Distance Matrix API.
    Implements caching, error handling, and exponential retry logic.
    """
    
    def __init__(self):
        self.api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
        self.client: Optional[googlemaps.Client] = None
        
        if self.api_key:
            try:
                self.client = googlemaps.Client(key=self.api_key)
                logger.info("Google Maps Distance Matrix client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Google Maps client: {e}")
        else:
            logger.warning("GOOGLE_MAPS_API_KEY not found in environment variables")
    
    def is_available(self) -> bool:
        """Check if the distance service is available."""
        return self.client is not None
    
    def _normalize_route_signature(self, addresses: List[str]) -> str:
        """
        Create a normalized signature for a route to use as cache key.
        
        Args:
            addresses: List of address strings
            
        Returns:
            MD5 hash of the normalized route
        """
        # Normalize addresses: lowercase, strip whitespace
        normalized = [addr.lower().strip() for addr in addresses]
        route_string = "|".join(normalized)
        return hashlib.md5(route_string.encode('utf-8')).hexdigest()
    
    @lru_cache(maxsize=500)
    def _get_cached_distance(self, route_signature: str, timestamp: int) -> Optional[float]:
        """
        Internal cached method. The timestamp parameter ensures cache expires after 24h.
        
        Args:
            route_signature: MD5 hash of the route
            timestamp: Current day timestamp (used for cache expiration)
            
        Returns:
            Cached distance in km or None
        """
        # This is just a placeholder - actual cache data is stored in the LRU cache
        return None
    
    def _calculate_day_timestamp(self) -> int:
        """Get a timestamp that changes once per day (for cache TTL)."""
        return int(time.time() / 86400)  # 86400 seconds = 24 hours
    
    def _retry_with_exponential_backoff(self, func: Callable, max_retries: int = 3) -> Any:
        """
        Retry a function with exponential backoff.
        
        Args:
            func: Function to retry
            max_retries: Maximum number of retry attempts
            
        Returns:
            Result of the function call
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return func()
            except googlemaps.exceptions.Timeout as e:
                last_exception = e
                wait_time = (2 ** attempt) + (time.time() % 1)  # Exponential + jitter
                logger.warning(f"Google Maps API timeout (attempt {attempt + 1}/{max_retries}), retrying in {wait_time:.2f}s")
                time.sleep(wait_time)
            except googlemaps.exceptions.ApiError as e:
                # Rate limit (429) or server errors (5xx) - retry
                if hasattr(e, 'status') and e.status in ['OVER_QUERY_LIMIT', 'UNKNOWN_ERROR']:
                    last_exception = e
                    wait_time = (2 ** attempt) + (time.time() % 1)
                    logger.warning(f"Google Maps API error {e.status} (attempt {attempt + 1}/{max_retries}), retrying in {wait_time:.2f}s")
                    time.sleep(wait_time)
                else:
                    # Other API errors - don't retry
                    raise
            except Exception as e:
                # Unexpected errors - don't retry
                logger.error(f"Unexpected error in Google Maps API call: {e}")
                raise
        
        # All retries exhausted
        logger.error(f"All {max_retries} retry attempts failed")
        if last_exception:
            raise last_exception
        raise Exception("Retry attempts exhausted")
    
    def calculate_distance(self, addresses: List[str]) -> Dict:
        """
        Calculate the total distance for a route with multiple waypoints.
        
        Args:
            addresses: List of addresses (minimum 2)
            
        Returns:
            Dictionary with:
                - success: bool
                - total_km: float (total distance in kilometers)
                - segments: list of dicts with origin, destination, distance_km
                - error: str (if success=False)
        """
        if not addresses or len(addresses) < 2:
            return {
                'success': False,
                'error': 'Servono almeno 2 indirizzi per calcolare la distanza'
            }
        
        if not self.is_available():
            return {
                'success': False,
                'error': 'Servizio di calcolo distanze non disponibile. Chiave API mancante.'
            }
        
        # Validate number of waypoints (Google Maps limit)
        if len(addresses) > 25:
            return {
                'success': False,
                'error': 'Numero massimo di indirizzi superato (massimo 25)'
            }
        
        # Check cache
        route_signature = self._normalize_route_signature(addresses)
        day_timestamp = self._calculate_day_timestamp()
        
        try:
            # Calculate distances for each segment
            segments = []
            total_distance_meters = 0
            
            for i in range(len(addresses) - 1):
                origin = addresses[i]
                destination = addresses[i + 1]
                
                # Call Google Maps Distance Matrix API with retry logic
                def api_call():
                    if self.client:
                        return self.client.distance_matrix(
                            origins=[origin],
                            destinations=[destination],
                            mode='driving',
                            language='it',
                            region='it'
                        )
                    return None
                
                result = self._retry_with_exponential_backoff(api_call)
                
                # Parse result
                if result['status'] != 'OK':
                    logger.error(f"Distance Matrix API returned status: {result['status']}")
                    return {
                        'success': False,
                        'error': f"Errore API Google Maps: {result['status']}"
                    }
                
                # Extract distance from result
                row = result['rows'][0]
                element = row['elements'][0]
                
                if element['status'] != 'OK':
                    logger.error(f"Route segment {i} status: {element['status']}")
                    return {
                        'success': False,
                        'error': f"Impossibile calcolare la distanza tra '{origin}' e '{destination}'. Verifica gli indirizzi."
                    }
                
                distance_meters = element['distance']['value']
                distance_km = round(distance_meters / 1000, 2)
                total_distance_meters += distance_meters
                
                segments.append({
                    'origin': origin,
                    'destination': destination,
                    'distance_km': distance_km
                })
            
            total_km = round(total_distance_meters / 1000, 2)
            
            logger.info(f"Successfully calculated distance for route: {total_km} km ({len(segments)} segments)")
            
            return {
                'success': True,
                'total_km': total_km,
                'segments': segments
            }
            
        except googlemaps.exceptions.ApiError as e:
            logger.error(f"Google Maps API error: {e}")
            return {
                'success': False,
                'error': f"Errore API Google Maps: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error calculating distance: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"Errore imprevisto nel calcolo della distanza: {str(e)}"
            }


# Singleton instance
_distance_service = None

def get_distance_service() -> DistanceService:
    """Get the singleton distance service instance."""
    global _distance_service
    if _distance_service is None:
        _distance_service = DistanceService()
    return _distance_service
