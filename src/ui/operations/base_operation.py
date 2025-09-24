"""
Base class for operations
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable

class BaseOperation(ABC):
    """Base class for all operations"""
    
    def __init__(self, sf_api=None, woo_api=None):
        self.sf_api = sf_api
        self.woo_api = woo_api
        self.progress_callback: Optional[Callable[[int, str], None]] = None
        
    def report_progress(self, percentage: int, message: str):
        """Report progress to UI"""
        if self.progress_callback:
            self.progress_callback(percentage, message)
            
    @abstractmethod
    def execute(self, start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        """
        Execute the operation
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dictionary with results or None
        """
        pass