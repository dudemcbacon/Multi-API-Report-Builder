# Multi API Report Builder

A powerful PyQt6-based desktop application for integrating and analyzing data from multiple business APIs including Salesforce, WooCommerce, Avalara, and QuickBase.

## Features

### Multi-API Integration
- **Salesforce**: Access reports and data with JWT Bearer Flow authentication
- **WooCommerce**: Retrieve products, orders, customers, and more via REST API
- **Avalara**: Fetch tax transactions and compliance data
- **QuickBase**: Query tables and reports with field metadata support

### Data Management
- Unified tree view for browsing all connected data sources
- Real-time data loading with progress indicators
- Polars DataFrame backend for efficient data processing
- Export capabilities to CSV and Excel formats
- Date range filtering for time-based queries

### Performance Optimizations
- Asynchronous data loading with worker threads
- Connection pooling and session reuse
- Intelligent caching for metadata
- Batch processing for large datasets
- Optimized tree population to prevent redundant updates

### User Interface
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
# Salesforce JWT Configuration
SF_CLIENT_ID=your_client_id
SF_JWT_SUBJECT=your_username@company.com
SF_JWT_KEY_PATH=./salesforce_private.key
SF_JWT_KEY_ID=optional_key_id

# WooCommerce Configuration
WOO_STORE_URL=https://your-store.com
WOO_CONSUMER_KEY=your_consumer_key
WOO_CONSUMER_SECRET=your_consumer_secret

# Avalara Configuration
AVALARA_ACCOUNT_ID=your_account_id
AVALARA_LICENSE_KEY=your_license_key
AVALARA_COMPANY_CODE=your_company_code
AVALARA_ENVIRONMENT=sandbox  # or production

# QuickBase Configuration
QB_REALM_HOSTNAME=your-realm.quickbase.com
QB_USER_TOKEN=your_user_token
QB_APP_ID=your_app_id
```

### Salesforce JWT Setup

JWT Bearer Flow requires additional setup in Salesforce:

1. **Generate RSA Key Pair**:
```bash
# Generate private key
openssl genrsa -out salesforce_private.key 2048

# Extract public key (for Salesforce)
openssl rsa -in salesforce_private.key -pubout -out salesforce_public.key
```

2. **Create Salesforce Connected App**:
   - Go to Setup → App Manager → New Connected App
   - Fill in basic information
   - Enable API (Enable OAuth Settings)
   - Enable "Use Digital Signatures" and upload the public key
   - Select OAuth Scopes: "Full access (full)"
   - Save and note the Consumer Key (Client ID)

3. **Configure Connected App Policies**:
   - Go to Setup → Connected Apps → Manage Connected Apps
   - Edit your Connected App → Edit Policies
   - Permitted Users: "Admin approved users are pre-authorized"
   - IP Relaxation: "Relax IP restrictions"
   - Assign to user profiles/permission sets

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
│   │   ├── async_jwt_salesforce_api.py
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
│   ├── models/
│   │   └── config.py       # Pydantic configuration models
│   └── utils/              # Utility functions
│       └── jwt_utils.py    # JWT token generation
├── tests/                  # Test suite
├── docs/                   # Documentation
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create this)
└── launch.py              # Application entry point
```

### Key Technologies

- **PyQt6**: Desktop GUI framework
- **Polars**: High-performance DataFrame library
- **aiohttp**: Async HTTP client for API requests
- **PyJWT**: JWT token generation for Salesforce authentication
- **Pydantic**: Configuration management with validation
- **keyring**: Secure credential storage
- **python-dotenv**: Environment variable management
- **QDarkStyle**: Dark theme styling

## API-Specific Features

### Salesforce
- JWT Bearer Flow authentication (server-to-server)
- Report and dashboard access
- SOQL query support
- Metadata caching for performance
- RSA certificate-based security

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
- **BREAKING CHANGE**: Migrated Salesforce authentication from OAuth 2.0 to JWT Bearer Flow
- Complete removal of browser-based authentication dependency
- Added comprehensive JWT token generation and validation
- Added QuickBase API integration with field metadata support
- Fixed field headers to show descriptive names instead of numeric IDs
- Optimized tree population to prevent race conditions and redundant updates
- Enhanced connection management with automatic session restoration
- Improved error handling, logging, and user feedback
- Updated all environment variables for consistency
- Complete codebase cleanup and documentation updates

## Author

Quinn Quigley

---

Built with Python and PyQt6 for efficient multi-API data integration and analysis.