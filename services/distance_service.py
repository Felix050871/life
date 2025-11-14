import os
import logging
import time
import copy
from typing import Dict, List, Optional, Tuple, Any, Callable
import googlemaps
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
        self._cache: Dict[str, Tuple[float, float, List[Dict]]] = {}  # key -> (timestamp, total_km, segments)
        self._cache_ttl = 86400  # 24 hours in seconds
        self._cache_max_size = 1000  # Maximum number of cache entries
        
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
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """
        Get result from cache if it exists and is not expired.
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Cached result dictionary or None if not found/expired
        """
        if cache_key in self._cache:
            cached_timestamp, total_km, segments = self._cache[cache_key]
            current_time = time.time()
            
            # Check if cache entry is still valid (within TTL)
            if current_time - cached_timestamp < self._cache_ttl:
                logger.info(f"Cache hit for route {cache_key[:8]}... (age: {int(current_time - cached_timestamp)}s)")
                return {
                    'success': True,
                    'total_km': total_km,
                    'segments': copy.deepcopy(segments),  # Deep copy to prevent mutation
                    'cached': True
                }
            else:
                # Cache expired, remove it
                logger.info(f"Cache expired for route {cache_key[:8]}... (age: {int(current_time - cached_timestamp)}s)")
                del self._cache[cache_key]
        
        return None
    
    def _save_to_cache(self, cache_key: str, total_km: float, segments: List[Dict]) -> None:
        """
        Save result to cache with size-based eviction.
        
        Args:
            cache_key: Cache key
            total_km: Total distance in km
            segments: List of route segments
        """
        # Evict oldest entries if cache is full
        if len(self._cache) >= self._cache_max_size:
            # Sort entries by timestamp (oldest first) and remove the oldest 10%
            sorted_entries = sorted(self._cache.items(), key=lambda x: x[1][0])
            evict_count = max(1, self._cache_max_size // 10)
            
            for i in range(evict_count):
                key_to_remove = sorted_entries[i][0]
                del self._cache[key_to_remove]
            
            logger.info(f"Cache eviction: removed {evict_count} oldest entries (cache size was {len(self._cache) + evict_count})")
        
        # Store deep copy to prevent shared state mutations
        self._cache[cache_key] = (time.time(), total_km, copy.deepcopy(segments))
        logger.info(f"Cached result for route {cache_key[:8]}... ({len(segments)} segments, {total_km} km, cache size: {len(self._cache)})")
    
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
        
        # Check cache first
        cache_key = self._normalize_route_signature(addresses)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
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
            
            # Save result to cache before returning
            self._save_to_cache(cache_key, total_km, segments)
            
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
