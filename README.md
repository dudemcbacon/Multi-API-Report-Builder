# Multi API Report Builder

A powerful PyQt6-based desktop application for integrating and analyzing data from multiple business APIs including Salesforce, WooCommerce, Avalara, and QuickBase.

## Features

### 🔌 Multi-API Integration
- **Salesforce**: Access reports and data with OAuth2 authentication
- **WooCommerce**: Retrieve products, orders, customers, and more via REST API
- **Avalara**: Fetch tax transactions and compliance data
- **QuickBase**: Query tables and reports with field metadata support

### 📊 Data Management
- Unified tree view for browsing all connected data sources
- Real-time data loading with progress indicators
- Polars DataFrame backend for efficient data processing
- Export capabilities to CSV and Excel formats
- Date range filtering for time-based queries

### 🚀 Performance Optimizations
- Asynchronous data loading with worker threads
- Connection pooling and session reuse
- Intelligent caching for metadata
- Batch processing for large datasets
- Optimized tree population to prevent redundant updates

### 🎨 User Interface
- Dark theme support via QDarkStyle
- Tabbed interface for different operations
- Status bar with connection indicators
- Token management and connection status display
- Responsive design with progress feedback

## Installation

### Prerequisites
- Python 3.8 or higher
- Windows, macOS, or Linux

### Setup

1. Clone the repository:
```bash
git clone https://github.com/QuiQuig/Multi-API-Report-Builder.git
cd Multi-API-Report-Builder
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# or
source venv/bin/activate  # On macOS/Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
Create a `.env` file in the project root with your API credentials:

```env
# Salesforce Configuration
SALESFORCE_CLIENT_ID=your_client_id
SALESFORCE_CLIENT_SECRET=your_client_secret
SALESFORCE_REDIRECT_URI=http://localhost:8080/callback

# WooCommerce Configuration
WOOCOMMERCE_URL=https://your-store.com
WOOCOMMERCE_CONSUMER_KEY=your_consumer_key
WOOCOMMERCE_CONSUMER_SECRET=your_consumer_secret

# Avalara Configuration
AVALARA_ACCOUNT_ID=your_account_id
AVALARA_LICENSE_KEY=your_license_key
AVALARA_COMPANY_CODE=your_company_code
AVALARA_ENVIRONMENT=sandbox  # or production

# QuickBase Configuration
QUICKBASE_REALM_HOSTNAME=your-realm.quickbase.com
QUICKBASE_USER_TOKEN=your_user_token
QUICKBASE_APP_ID=your_app_id
```

## Usage

### Starting the Application

```bash
python launch.py
```

### Connecting to APIs

1. The application will attempt to auto-connect to configured APIs on startup
2. Manual connection available through the UI for each API
3. Connection status displayed in the toolbar

### Loading Data

1. **Browse Data Sources**: Navigate the unified tree view in the Source Data tab
2. **Select Report/Table**: Double-click any report or data source to load
3. **Apply Filters**: Use date range selector for time-based filtering
4. **View Results**: Data appears in the table view with sortable columns

### Exporting Data

1. Load desired data into the table view
2. Click "Export to CSV" or "Export to Excel"
3. Choose save location
4. Data exported with all current filters applied

## Architecture

### Project Structure

```
Multi-API-Report-Builder/
├── src/
│   ├── services/          # API service implementations
│   │   ├── async_salesforce_api.py
│   │   ├── async_woocommerce_api.py
│   │   ├── async_avalara_api.py
│   │   └── async_quickbase_api.py
│   ├── ui/
│   │   ├── main_window.py # Main application window
│   │   ├── workers.py      # Async worker threads
│   │   ├── managers/       # UI state managers
│   │   │   ├── connection_manager.py
│   │   │   ├── data_source_manager.py
│   │   │   ├── status_manager.py
│   │   │   └── tree_population_manager.py
│   │   ├── tabs/           # Tab implementations
│   │   └── operations/     # Business operations
│   ├── config/
│   │   └── app_config.py   # Application configuration
│   └── utils/              # Utility functions
├── tests/                  # Test suite
├── docs/                   # Documentation
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create this)
└── launch.py              # Application entry point
```

### Key Technologies

- **PyQt6**: Desktop GUI framework
- **Polars**: High-performance DataFrame library
- **aiohttp**: Async HTTP client
- **quickbase-client**: QuickBase API integration
- **simple-salesforce**: Salesforce API wrapper
- **python-dotenv**: Environment variable management
- **QDarkStyle**: Dark theme styling

## API-Specific Features

### Salesforce
- OAuth2 authentication flow
- Report and dashboard access
- SOQL query support
- Metadata caching for performance

### WooCommerce
- REST API v3 support
- Product, order, and customer data
- Pagination handling
- Date-based filtering

### Avalara
- AvaTax API integration
- Transaction retrieval
- Company and jurisdiction data
- Tax code lookups

### QuickBase
- Table and report browsing
- Field metadata extraction
- Descriptive column headers
- Query builder support

## Development

### Running Tests

```bash
pytest tests/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

### Building for Distribution

```bash
# Create standalone executable (Windows)
pyinstaller --onefile --windowed launch.py
```

## Troubleshooting

### Common Issues

1. **Connection Errors**: Verify API credentials in `.env` file
2. **Tree Not Displaying**: Check API connection status in toolbar
3. **Data Not Loading**: Ensure proper permissions for API tokens
4. **Export Failures**: Verify write permissions for output directory

### Debug Mode

Set logging level in `launch.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

## License

This project is proprietary software. All rights reserved.

## Support

For issues and questions, please open an issue on [GitHub](https://github.com/QuiQuig/Multi-API-Report-Builder/issues).

## Changelog

### Latest Updates
- Added QuickBase API integration
- Fixed field headers to show descriptive names
- Optimized tree population to prevent race conditions
- Improved connection management for all APIs
- Enhanced error handling and logging

## Author

Quinn Quigley

---

Built with Python and PyQt6 for efficient multi-API data integration and analysis.