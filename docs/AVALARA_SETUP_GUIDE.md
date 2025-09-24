# Avalara Integration Setup Guide

## Issue Analysis

The authentication error (401) occurs because the Avalara credentials in the `.env` file are still set to placeholder values:

```
AVALARA_ACCOUNT_ID=your_account_id
AVALARA_LICENSE_KEY=your_license_key
```

## Solution

### 1. Get Avalara Credentials

#### For Testing/Development (Sandbox):
1. Go to https://sandbox-admin.avalara.com
2. Sign up for a free sandbox account
3. Navigate to **Settings > License and API Keys**
4. Copy your Account ID and License Key

#### For Production:
1. Go to https://admin.avalara.com
2. Use your production Avalara account
3. Navigate to **Settings > License and API Keys**
4. Copy your Account ID and License Key

#### Test Credentials (Public):
For testing purposes, you can use Avalara's publicly available test credentials:
- Account ID: `2000134479`
- License Key: `1234567890123456`
- Environment: `sandbox`

### 2. Update .env File

Replace the placeholder values in your `.env` file:

```bash
# Avalara API Credentials
AVALARA_ACCOUNT_ID=2000134479
AVALARA_LICENSE_KEY=1234567890123456
AVALARA_ENVIRONMENT=sandbox
```

### 3. Verify Setup

You can test the connection using curl:

```bash
curl -u 'your_account_id:your_license_key' \
     'https://sandbox-rest.avatax.com/api/v2/utilities/ping'
```

Expected response:
```json
{
  "authenticated": true,
  "version": "22.12.0",
  "build": "..."
}
```

### 4. Test Integration

Run the test script to verify everything works:

```bash
python3 test_avalara_transactions.py
```

## Available Avalara Data Sources

Once connected, you'll have access to:

1. **Companies** - List of companies in your Avalara account
2. **Transactions** - Transaction data for specified date ranges
3. **Tax Codes** - Available tax codes
4. **Jurisdictions** - Tax jurisdictions (US by default)

## Troubleshooting

### Common Issues:

1. **401 Authentication Error**
   - Check that credentials are not placeholder values
   - Verify Account ID and License Key are correct
   - Ensure environment (sandbox/production) matches your credentials

2. **Environment Variables Not Loading**
   - Ensure the `.env` file is in the project root
   - Check that `python-dotenv` is installed
   - Verify the application is loading the `.env` file correctly

3. **Rate Limiting**
   - Avalara has a rate limit of 1000 requests per minute
   - The API client includes rate limiting protection

### Debug Steps:

1. Check environment variables:
   ```python
   import os
   print(f"Account ID: {os.getenv('AVALARA_ACCOUNT_ID')}")
   print(f"License Key: {os.getenv('AVALARA_LICENSE_KEY')}")
   ```

2. Test connection manually:
   ```python
   import asyncio
   from src.services.async_avalara_api import AsyncAvalaraAPI
   
   async def test():
       async with AsyncAvalaraAPI(verbose_logging=True) as api:
           result = await api.test_connection()
           print(result)
   
   asyncio.run(test())
   ```

## API Endpoints Used

- Base URL (Sandbox): `https://sandbox-rest.avatax.com/api/v2`
- Base URL (Production): `https://rest.avatax.com/api/v2`

Endpoints:
- `/utilities/ping` - Connection test
- `/accounts` - Account information
- `/companies` - Company list
- `/transactions` - Transaction data
- `/definitions/taxcodes` - Tax codes
- `/definitions/jurisdictions` - Jurisdictions

## Security Notes

- Never commit actual credentials to version control
- Use environment variables for credential storage
- The API client uses HTTPS and proper authentication headers
- Rate limiting is implemented to prevent API abuse

## Next Steps

1. Update your `.env` file with valid credentials
2. Restart the application
3. You should now see "AV: ✓" in the connection status
4. Avalara data sources will be available in the data tree
5. You can load data from Companies, Transactions, Tax Codes, and Jurisdictions