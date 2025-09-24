#!/usr/bin/env python3
"""
Salesforce Report Pull Application Launcher
Multi-API Data Integration Tool
"""
import sys
import logging
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv('.env')
    print("Loaded environment variables from .env file")
except ImportError:
    print("python-dotenv not available, using system environment variables only")

# Add src to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
import qtawesome as qta  # type: ignore[import]

def setup_logging():
    """Setup application logging"""
    log_dir = Path.home() / '.config' / 'SalesforceReportPull' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / 'app.log'
    
    logging.basicConfig(
        level=logging.DEBUG,  # Changed to DEBUG for verbose logging
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=== Salesforce Report Pull Application Starting ===")
    return logger

def check_dependencies():
    """Check if all required dependencies are available"""
    import importlib
    
    dependencies = [
        # Core framework dependencies
        'PyQt6',
        'polars',
        'pydantic',
        
        # API integration dependencies
        'simple_salesforce',
        'requests',
        'httpx',
        
        # Security dependencies
        'keyring',
        'cryptography',
        'jwt',
        
        # Data processing dependencies
        'openpyxl',
        
        # UI enhancement dependencies
        'qtawesome',
        'qdarkstyle',
    ]
    
    for dep in dependencies:
        try:
            importlib.import_module(dep)
        except ImportError:
            return False, f"Missing dependency: {dep}"
    
    return True, None

def main():
    """Main application entry point"""
    logger = setup_logging()
    
    try:
        # Check dependencies
        deps_ok, error = check_dependencies()
        if not deps_ok:
            print(f"Missing dependency: {error}")
            print("Please install dependencies with: pip install -r requirements.txt")
            return 1
        
        # Enable high DPI scaling before creating QApplication
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        
        # Set WebEngine attributes before creating QApplication
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        
        # Create QApplication
        app = QApplication(sys.argv)
        app.setApplicationName("Salesforce Report Pull")
        app.setApplicationVersion("1.0")
        app.setOrganizationName("Multi-API Data Integration")
        
        # Set application icon
        try:
            app.setWindowIcon(qta.icon('fa5b.salesforce'))  # type: ignore[arg-type]
        except Exception:
            pass  # Icon not critical
        
        # Import and create main window
        from src.ui.main_window import MainWindow
        
        # Create main window
        main_window = MainWindow()
        main_window.show()
        
        logger.info("Application window created and shown")
        
        # Run application
        return app.exec()
        
    except ImportError as e:
        error_msg = f"""
Failed to import required modules: {e}

This usually means the dependencies are not installed properly.

To fix this:
1. Make sure you're in the correct directory
2. Create a virtual environment: python -m venv .venv
3. Activate it: .venv\\Scripts\\activate (Windows) or source .venv/bin/activate (Unix)
4. Install dependencies: pip install -r requirements.txt
5. Run the application: python launch.py

If you're still having issues, check that Python 3.8+ is installed.
        """
        print(error_msg)
        
        # Try to show a GUI error if PyQt6 is available
        try:
            app = QApplication(sys.argv)
            QMessageBox.critical(None, "Import Error", error_msg)
        except:
            pass
        
        return 1
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        
        # Try to show a GUI error if possible
        try:
            if 'app' in locals():
                QMessageBox.critical(None, "Application Error", f"An unexpected error occurred:\n{e}")
        except:
            pass
        
        return 1

if __name__ == "__main__":
    sys.exit(main())