"""
Metadata Cache Manager for Salesforce object and field information
"""
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import polars as pl

logger = logging.getLogger(__name__)

class MetadataCacheManager:
    """
    Manages caching of Salesforce metadata (objects, fields, relationships)
    to minimize API calls and improve performance
    """
    
    def __init__(self, cache_dir: Optional[Path] = None, cache_duration_hours: int = 24):
        """
        Initialize the metadata cache manager
        
        Args:
            cache_dir: Directory to store cache files (default: ~/.config/SalesforceReportPull/cache/)
            cache_duration_hours: How long to keep cached data (default: 24 hours)
        """
        if cache_dir is None:
            # Use default cache directory
            home = Path.home()
            cache_dir = home / '.config' / 'Multi API Report Builder' / 'cache'
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_duration = timedelta(hours=cache_duration_hours)
        
        # In-memory cache for current session
        self._memory_cache = {}
        
        logger.info(f"[METADATA-CACHE] Initialized with cache dir: {self.cache_dir}")
    
    def _get_cache_path(self, cache_type: str, key: str = "") -> Path:
        """Get the file path for a cache entry"""
        if key:
            filename = f"{cache_type}_{key.replace('/', '_')}.json"
        else:
            filename = f"{cache_type}.json"
        return self.cache_dir / filename
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if a cache file is still valid"""
        if not cache_path.exists():
            return False
        
        # Check file modification time
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - mtime
        
        return age < self.cache_duration
    
    def get_all_objects(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached list of all Salesforce objects
        
        Returns:
            List of object metadata or None if not cached
        """
        cache_key = "all_objects"
        
        # Check memory cache first
        if cache_key in self._memory_cache:
            logger.debug("[METADATA-CACHE] Returning all objects from memory cache")
            return self._memory_cache[cache_key]
        
        # Check file cache
        cache_path = self._get_cache_path("objects", "all")
        
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                    self._memory_cache[cache_key] = data
                    logger.info(f"[METADATA-CACHE] Loaded {len(data)} objects from cache")
                    return data
            except Exception as e:
                logger.error(f"[METADATA-CACHE] Error reading cache: {e}")
        
        return None
    
    def save_all_objects(self, objects: List[Dict[str, Any]]):
        """Save list of all objects to cache"""
        cache_key = "all_objects"
        cache_path = self._get_cache_path("objects", "all")
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(objects, f, indent=2)
            
            # Also save to memory cache
            self._memory_cache[cache_key] = objects
            
            logger.info(f"[METADATA-CACHE] Saved {len(objects)} objects to cache")
        except Exception as e:
            logger.error(f"[METADATA-CACHE] Error saving cache: {e}")
    
    def get_object_description(self, object_name: str) -> Optional[Dict[str, Any]]:
        """
        Get cached description for a specific object
        
        Args:
            object_name: API name of the object
            
        Returns:
            Object description or None if not cached
        """
        cache_key = f"object_desc_{object_name}"
        
        # Check memory cache first
        if cache_key in self._memory_cache:
            logger.debug(f"[METADATA-CACHE] Returning {object_name} description from memory cache")
            return self._memory_cache[cache_key]
        
        # Check file cache
        cache_path = self._get_cache_path("object_desc", object_name)
        
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                    self._memory_cache[cache_key] = data
                    logger.info(f"[METADATA-CACHE] Loaded {object_name} description from cache")
                    return data
            except Exception as e:
                logger.error(f"[METADATA-CACHE] Error reading cache: {e}")
        
        return None
    
    def save_object_description(self, object_name: str, description: Dict[str, Any]):
        """Save object description to cache"""
        cache_key = f"object_desc_{object_name}"
        cache_path = self._get_cache_path("object_desc", object_name)
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(description, f, indent=2)
            
            # Also save to memory cache
            self._memory_cache[cache_key] = description
            
            field_count = len(description.get('fields', []))
            logger.info(f"[METADATA-CACHE] Saved {object_name} description with {field_count} fields to cache")
        except Exception as e:
            logger.error(f"[METADATA-CACHE] Error saving cache: {e}")
    
    def get_global_describe(self) -> Optional[Dict[str, Any]]:
        """Get cached global describe data"""
        cache_key = "global_describe"
        
        # Check memory cache first
        if cache_key in self._memory_cache:
            logger.debug("[METADATA-CACHE] Returning global describe from memory cache")
            return self._memory_cache[cache_key]
        
        # Check file cache
        cache_path = self._get_cache_path("global_describe")
        
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                    self._memory_cache[cache_key] = data
                    logger.info("[METADATA-CACHE] Loaded global describe from cache")
                    return data
            except Exception as e:
                logger.error(f"[METADATA-CACHE] Error reading cache: {e}")
        
        return None
    
    def save_global_describe(self, data: Dict[str, Any]):
        """Save global describe data to cache"""
        cache_key = "global_describe"
        cache_path = self._get_cache_path("global_describe")
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Also save to memory cache
            self._memory_cache[cache_key] = data
            
            object_count = len(data.get('sobjects', []))
            logger.info(f"[METADATA-CACHE] Saved global describe with {object_count} objects to cache")
        except Exception as e:
            logger.error(f"[METADATA-CACHE] Error saving cache: {e}")
    
    def clear_cache(self, cache_type: Optional[str] = None):
        """
        Clear cache files
        
        Args:
            cache_type: Specific cache type to clear, or None to clear all
        """
        if cache_type:
            # Clear specific cache type
            pattern = f"{cache_type}*.json"
            for cache_file in self.cache_dir.glob(pattern):
                try:
                    cache_file.unlink()
                    logger.info(f"[METADATA-CACHE] Deleted cache file: {cache_file.name}")
                except Exception as e:
                    logger.error(f"[METADATA-CACHE] Error deleting cache file: {e}")
        else:
            # Clear all cache files
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                    logger.info(f"[METADATA-CACHE] Deleted cache file: {cache_file.name}")
                except Exception as e:
                    logger.error(f"[METADATA-CACHE] Error deleting cache file: {e}")
        
        # Clear memory cache
        self._memory_cache.clear()
        logger.info("[METADATA-CACHE] Cleared memory cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache"""
        stats = {
            'cache_dir': str(self.cache_dir),
            'memory_cache_size': len(self._memory_cache),
            'file_cache_count': len(list(self.cache_dir.glob("*.json"))),
            'total_cache_size_mb': 0,
            'oldest_cache_file': None,
            'newest_cache_file': None
        }
        
        cache_files = list(self.cache_dir.glob("*.json"))
        if cache_files:
            # Calculate total size
            total_size = sum(f.stat().st_size for f in cache_files)
            stats['total_cache_size_mb'] = round(total_size / (1024 * 1024), 2)
            
            # Find oldest and newest
            cache_files.sort(key=lambda f: f.stat().st_mtime)
            stats['oldest_cache_file'] = {
                'name': cache_files[0].name,
                'age_hours': round((datetime.now() - datetime.fromtimestamp(cache_files[0].stat().st_mtime)).total_seconds() / 3600, 1)
            }
            stats['newest_cache_file'] = {
                'name': cache_files[-1].name,
                'age_hours': round((datetime.now() - datetime.fromtimestamp(cache_files[-1].stat().st_mtime)).total_seconds() / 3600, 1)
            }
        
        return stats
    
    def create_objects_dataframe(self, objects: List[Dict[str, Any]]) -> pl.DataFrame:
        """
        Convert objects list to a Polars DataFrame for efficient filtering/sorting
        
        Args:
            objects: List of object metadata dictionaries
            
        Returns:
            Polars DataFrame with object information
        """
        if not objects:
            return pl.DataFrame()
        
        # Create DataFrame with useful columns
        df = pl.DataFrame(objects).select([
            pl.col('name').alias('api_name'),
            pl.col('label'),
            pl.col('labelPlural').alias('label_plural'),
            pl.col('custom'),
            pl.col('queryable'),
            pl.col('searchable'),
            pl.col('createable'),
            pl.col('updateable'),
            pl.col('deleteable'),
            pl.col('keyPrefix').alias('key_prefix')
        ])
        
        # Add computed columns
        df = df.with_columns([
            pl.when(pl.col('custom')).then(pl.lit('Custom')).otherwise(pl.lit('Standard')).alias('type'),
            pl.col('api_name').str.ends_with('__c').alias('is_custom_object')
        ])
        
        return df
    
    def create_fields_dataframe(self, fields: List[Dict[str, Any]]) -> pl.DataFrame:
        """
        Convert fields list to a Polars DataFrame for efficient filtering/sorting
        
        Args:
            fields: List of field metadata dictionaries
            
        Returns:
            Polars DataFrame with field information
        """
        if not fields:
            return pl.DataFrame()
        
        # Create DataFrame with useful columns
        df = pl.DataFrame(fields).select([
            pl.col('name').alias('api_name'),
            pl.col('label'),
            pl.col('type').alias('data_type'),
            pl.col('length'),
            pl.col('custom'),
            pl.col('nillable'),
            pl.col('createable'),
            pl.col('updateable'),
            pl.col('filterable'),
            pl.col('sortable'),
            pl.col('groupable'),
            pl.col('unique'),
            pl.col('relationshipName').alias('relationship_name'),
            pl.col('referenceTo').alias('reference_to')
        ])
        
        # Add computed columns
        df = df.with_columns([
            pl.when(pl.col('custom')).then(pl.lit('Custom')).otherwise(pl.lit('Standard')).alias('field_type'),
            pl.col('api_name').str.ends_with('__c').alias('is_custom_field'),
            pl.col('reference_to').list.len().gt(0).alias('is_relationship')
        ])
        
        return df