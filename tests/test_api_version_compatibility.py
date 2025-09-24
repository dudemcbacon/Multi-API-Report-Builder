"""
API Version Compatibility Tests for Salesforce REST API
Tests compatibility between v58.0 (current) and v63.0 (Spring '25)
"""
import asyncio
import pytest
import logging
from typing import Dict, Any, List
import json
from datetime import datetime

from src.services.async_salesforce_api import AsyncSalesforceAPI
from src.services.auth_manager import SalesforceAuthManager

logger = logging.getLogger(__name__)

class TestAPIVersionCompatibility:
    """Test suite for API version compatibility between v58.0 and v63.0"""
    
    @pytest.fixture(scope="class")
    def auth_manager(self):
        """Create auth manager for testing"""
        return SalesforceAuthManager()
    
    @pytest.fixture(scope="class")
    def api_v58(self, auth_manager):
        """Create API instance with v58.0"""
        api = AsyncSalesforceAPI(auth_manager=auth_manager)
        # Override the API version for testing
        api._api_version = "v58.0"
        return api
    
    @pytest.fixture(scope="class")
    def api_v63(self, auth_manager):
        """Create API instance with v63.0"""
        api = AsyncSalesforceAPI(auth_manager=auth_manager)
        # Override the API version for testing
        api._api_version = "v63.0"
        return api
    
    @pytest.mark.asyncio
    async def test_api_version_info(self, api_v58, api_v63):
        """Test basic API version information endpoint"""
        logger.info("Testing API version info endpoints")
        
        # Test if both APIs can authenticate and get basic info
        async with api_v58:
            result_v58 = await api_v58.test_connection()
            assert result_v58.get('success'), f"v58.0 connection failed: {result_v58.get('error')}"
            
        async with api_v63:
            result_v63 = await api_v63.test_connection()
            assert result_v63.get('success'), f"v63.0 connection failed: {result_v63.get('error')}"
        
        logger.info("✓ Both API versions connect successfully")
    
    @pytest.mark.asyncio
    async def test_sobjects_endpoint_compatibility(self, api_v58, api_v63):
        """Test /services/data/vXX.X/sobjects endpoint compatibility"""
        logger.info("Testing sobjects endpoint compatibility")
        
        async with api_v58:
            objects_v58 = await api_v58.get_all_objects()
            
        async with api_v63:
            objects_v63 = await api_v63.get_all_objects()
        
        # Both should return data
        assert objects_v58 is not None, "v58.0 returned no objects"
        assert objects_v63 is not None, "v63.0 returned no objects"
        assert len(objects_v58) > 0, "v58.0 returned empty objects list"
        assert len(objects_v63) > 0, "v63.0 returned empty objects list"
        
        # Check response structure consistency
        self._validate_sobjects_response_structure(objects_v58, "v58.0")
        self._validate_sobjects_response_structure(objects_v63, "v63.0")
        
        # Compare common objects between versions
        self._compare_sobjects_responses(objects_v58, objects_v63)
        
        logger.info(f"✓ sobjects endpoint compatible: v58.0({len(objects_v58)}) vs v63.0({len(objects_v63)}) objects")
    
    @pytest.mark.asyncio
    async def test_describe_endpoint_compatibility(self, api_v58, api_v63):
        """Test object describe endpoint compatibility"""
        logger.info("Testing describe endpoint compatibility")
        
        # Test with common standard objects
        test_objects = ['Account', 'Contact', 'Opportunity']
        
        for obj_name in test_objects:
            logger.info(f"Testing describe for {obj_name}")
            
            async with api_v58:
                desc_v58 = await api_v58.describe_object(obj_name)
                
            async with api_v63:
                desc_v63 = await api_v63.describe_object(obj_name)
            
            # Both should return descriptions
            assert desc_v58 is not None, f"v58.0 describe failed for {obj_name}"
            assert desc_v63 is not None, f"v63.0 describe failed for {obj_name}"
            
            # Validate structure
            self._validate_describe_response_structure(desc_v58, obj_name, "v58.0")
            self._validate_describe_response_structure(desc_v63, obj_name, "v63.0")
            
            # Compare field counts (should be similar, allowing for minor differences)
            fields_v58 = len(desc_v58.get('fields', []))
            fields_v63 = len(desc_v63.get('fields', []))
            
            # Allow up to 10% difference in field count (for new fields)
            diff_ratio = abs(fields_v58 - fields_v63) / max(fields_v58, fields_v63)
            assert diff_ratio < 0.1, f"{obj_name} field count difference too large: v58({fields_v58}) vs v63({fields_v63})"
            
            logger.info(f"✓ {obj_name} describe compatible: v58({fields_v58}) vs v63({fields_v63}) fields")
    
    @pytest.mark.asyncio
    async def test_query_endpoint_compatibility(self, api_v58, api_v63):
        """Test SOQL query endpoint compatibility"""
        logger.info("Testing query endpoint compatibility")
        
        # Simple test query
        test_query = "SELECT Id, Name FROM Account LIMIT 5"
        
        async with api_v58:
            result_v58 = await api_v58.execute_soql(test_query)
            
        async with api_v63:
            result_v63 = await api_v63.execute_soql(test_query)
        
        # Both should execute successfully
        assert result_v58 is not None, "v58.0 query execution failed"
        assert result_v63 is not None, "v63.0 query execution failed"
        
        # Check that we get data in both cases
        if not result_v58.is_empty() and not result_v63.is_empty():
            # Compare column structure
            cols_v58 = set(result_v58.columns)
            cols_v63 = set(result_v63.columns)
            assert cols_v58 == cols_v63, f"Query result columns differ: v58{cols_v58} vs v63{cols_v63}"
        
        logger.info(f"✓ Query endpoint compatible: v58({len(result_v58)} rows) vs v63({len(result_v63)} rows)")
    
    @pytest.mark.asyncio
    async def test_global_describe_compatibility(self, api_v58, api_v63):
        """Test global describe endpoint compatibility"""
        logger.info("Testing global describe compatibility")
        
        async with api_v58:
            global_v58 = await api_v58.get_global_describe()
            
        async with api_v63:
            global_v63 = await api_v63.get_global_describe()
        
        # Both should return data
        assert global_v58 is not None, "v58.0 global describe failed"
        assert global_v63 is not None, "v63.0 global describe failed"
        
        # Check basic structure
        assert 'sobjects' in global_v58, "v58.0 missing sobjects in global describe"
        assert 'sobjects' in global_v63, "v63.0 missing sobjects in global describe"
        
        sobjects_v58 = len(global_v58['sobjects'])
        sobjects_v63 = len(global_v63['sobjects'])
        
        # Should have similar number of objects
        diff_ratio = abs(sobjects_v58 - sobjects_v63) / max(sobjects_v58, sobjects_v63)
        assert diff_ratio < 0.05, f"Global describe object count difference too large: v58({sobjects_v58}) vs v63({sobjects_v63})"
        
        logger.info(f"✓ Global describe compatible: v58({sobjects_v58}) vs v63({sobjects_v63}) objects")
    
    def _validate_sobjects_response_structure(self, objects: List[Dict[str, Any]], version: str):
        """Validate the structure of sobjects response"""
        assert isinstance(objects, list), f"{version}: sobjects should be a list"
        
        if len(objects) > 0:
            sample_obj = objects[0]
            required_fields = ['name', 'label', 'custom', 'queryable']
            
            for field in required_fields:
                assert field in sample_obj, f"{version}: Missing required field '{field}' in sobject"
            
            # Validate data types
            assert isinstance(sample_obj['name'], str), f"{version}: 'name' should be string"
            assert isinstance(sample_obj['label'], str), f"{version}: 'label' should be string" 
            assert isinstance(sample_obj['custom'], bool), f"{version}: 'custom' should be boolean"
            assert isinstance(sample_obj['queryable'], bool), f"{version}: 'queryable' should be boolean"
    
    def _validate_describe_response_structure(self, description: Dict[str, Any], obj_name: str, version: str):
        """Validate the structure of describe response"""
        required_fields = ['name', 'label', 'custom', 'fields']
        
        for field in required_fields:
            assert field in description, f"{version}: Missing required field '{field}' in {obj_name} describe"
        
        # Validate fields array
        fields = description['fields']
        assert isinstance(fields, list), f"{version}: 'fields' should be a list in {obj_name}"
        
        if len(fields) > 0:
            sample_field = fields[0]
            field_required = ['name', 'label', 'type', 'custom']
            
            for field in field_required:
                assert field in sample_field, f"{version}: Missing field '{field}' in {obj_name} field describe"
    
    def _compare_sobjects_responses(self, objects_v58: List[Dict], objects_v63: List[Dict]):
        """Compare sobjects responses between versions"""
        # Create lookup maps by object name
        v58_map = {obj['name']: obj for obj in objects_v58}
        v63_map = {obj['name']: obj for obj in objects_v63}
        
        # Find common objects
        common_objects = set(v58_map.keys()) & set(v63_map.keys())
        assert len(common_objects) > 50, f"Too few common objects found: {len(common_objects)}"
        
        # Check some standard objects exist in both
        standard_objects = ['Account', 'Contact', 'Opportunity', 'User', 'Profile']
        for std_obj in standard_objects:
            assert std_obj in v58_map, f"Standard object {std_obj} missing in v58.0"
            assert std_obj in v63_map, f"Standard object {std_obj} missing in v63.0"
        
        # Compare properties of common objects
        compatibility_issues = []
        for obj_name in list(common_objects)[:10]:  # Test first 10 for performance
            obj_v58 = v58_map[obj_name]
            obj_v63 = v63_map[obj_name]
            
            # Compare key properties
            key_props = ['custom', 'queryable', 'searchable', 'createable', 'updateable', 'deleteable']
            for prop in key_props:
                if prop in obj_v58 and prop in obj_v63:
                    if obj_v58[prop] != obj_v63[prop]:
                        compatibility_issues.append(f"{obj_name}.{prop}: v58({obj_v58[prop]}) != v63({obj_v63[prop]})")
        
        # Allow minor differences but flag major incompatibilities
        if len(compatibility_issues) > 5:
            logger.warning(f"Found {len(compatibility_issues)} compatibility issues: {compatibility_issues[:5]}")
        
        logger.info(f"Compared {len(common_objects)} common objects with {len(compatibility_issues)} minor differences")

@pytest.mark.asyncio
async def test_session_management_compatibility():
    """Test that session management works correctly with different API versions"""
    logger.info("Testing session management across API versions")
    
    auth_manager = SalesforceAuthManager()
    
    # Test that we can create multiple API instances with different versions
    api_v58 = AsyncSalesforceAPI(auth_manager=auth_manager)
    api_v58._api_version = "v58.0"
    
    api_v63 = AsyncSalesforceAPI(auth_manager=auth_manager)  
    api_v63._api_version = "v63.0"
    
    # Test sequential usage
    async with api_v58:
        result_v58 = await api_v58.test_connection()
        assert result_v58.get('success'), "v58.0 session test failed"
    
    async with api_v63:
        result_v63 = await api_v63.test_connection()
        assert result_v63.get('success'), "v63.0 session test failed"
    
    logger.info("✓ Session management compatible across API versions")

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "integration: mark test as integration test")

if __name__ == "__main__":
    # Run tests directly
    import sys
    import os
    
    # Add project root to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the tests
    pytest.main([__file__, "-v", "-s"])