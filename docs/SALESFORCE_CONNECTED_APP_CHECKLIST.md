# Salesforce Connected App Configuration Checklist

## Required Connected App Settings

Based on the official Salesforce documentation, your Connected App must be configured with these **exact** settings:

### 1. Basic Information
- **Connected App Name**: SalesForce Report Pull (or your preferred name)
- **API Name**: Auto-generated from the name
- **Contact Email**: Your email address

### 2. OAuth Settings (CRITICAL)
- **Enable OAuth Settings**: ✅ **MUST BE CHECKED**
- **Callback URL**: `http://localhost:8080/callback`
- **Use Digital Certificates**: ❌ (Leave unchecked for standard OAuth)

### 3. Selected OAuth Scopes
Add these **EXACT** scopes to "Selected OAuth Scopes":
- **Access and manage your data (api)**
- **Perform requests on your behalf at any time (refresh_token)** *(This enables refresh tokens but is not requested in the initial flow)*

**IMPORTANT**: The application only requests the `api` scope initially. The refresh token will be automatically provided if the Connected App has the refresh_token scope configured. If you're getting "The requested scope is not allowed" error:
1. Make sure "Access and manage your data (api)" is in the "Selected OAuth Scopes" list
2. The refresh_token scope should be available but is not explicitly requested during auth
3. Check that no additional scopes are required by your organization

### 4. Web Server Flow Settings (IMPORTANT)
- **Require Secret for Web Server Flow**: ✅ **MUST BE CHECKED**
  - This is critical! Without this, token exchange will fail
  - Even with PKCE, Salesforce requires the consumer secret

### 5. Refresh Token Policy
- **Refresh Token Policy**: "Refresh token is valid until revoked"
- **Require Proof Key for Code Exchange (PKCE)**: ✅ **SHOULD BE CHECKED**

### 6. IP Restrictions
- **IP Restrictions**: "Relax IP restrictions" (for development)
- **Permitted Users**: "All users may self-authorize" (for development)

## Verification Steps

1. **Go to Setup → App Manager**
2. **Find your Connected App**
3. **Click the dropdown → Edit**
4. **Verify OAuth Settings section matches above**
5. **Save changes**

## Common Issues and Solutions

### Issue: "invalid_client" Error
**Solution**: 
- Verify "Require Secret for Web Server Flow" is ENABLED
- Check Consumer Key and Secret are correct
- Ensure callback URL exactly matches: `http://localhost:8080/callback`

### Issue: "redirect_uri_mismatch" Error
**Solution**:
- Callback URL in Connected App must exactly match the one in the code
- Case sensitive!
- No trailing slashes

### Issue: "invalid_grant" Error
**Solution**:
- Check OAuth scopes are properly configured
- Verify the authorization code hasn't expired
- Ensure PKCE is properly implemented

## Environment Variables Required

Your `.env` file must contain:
```
SF_CONSUMER_KEY=3MVG9zlTNB8o8BA1YxGd... (from Connected App)
SF_CONSUMER_SECRET=03473E7351275CB32E5C... (from Connected App)
SF_INSTANCE_URL=https://company.my.salesforce.com
```

## Testing Your Configuration

Run the OAuth test to verify everything works:
```bash
python test_oauth_fix.py
```

## Additional Resources

- [Salesforce OAuth 2.0 Web Server Flow](https://help.salesforce.com/s/articleView?id=sf.remoteaccess_oauth_web_server_flow.htm)
- [Connected App Basics](https://help.salesforce.com/s/articleView?id=sf.connected_app_create_basics.htm)
- [OAuth Authorization Flows](https://help.salesforce.com/s/articleView?id=sf.remoteaccess_oauth_flows.htm)