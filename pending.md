# Pending Features from Previous SDK

Based on the previous Namecheap Python SDK implementation, here's what's still pending in our new clean architecture:

## 🚧 Not Yet Implemented

### 1. **SSL API** (`namecheap.ssl.*`)
- `create()` - Purchase SSL certificates
- `activate()` - Activate SSL certificates
- `getInfo()` - Get SSL certificate details
- `parseCSR()` - Parse Certificate Signing Request
- `getApproverEmailList()` - Get domain control validation emails
- `resendApproverEmail()` - Resend DCV email
- `reissue()` - Reissue SSL certificate
- `renew()` - Renew SSL certificate
- `revoke()` - Revoke SSL certificate
- `getList()` - List SSL certificates

### 2. **Users API** (`namecheap.users.*`)
- `getBalances()` - Get account balance
- `changePassword()` - Change account password
- `update()` - Update user information
- `createAddFundsRequest()` - Create add funds request
- `getAddFundsStatus()` - Check add funds status
- `create()` - Create sub-account (resellers)
- `login()` - Login to get session
- `resetPassword()` - Reset password

### 3. **Domains Transfer API** (`namecheap.domains.transfer.*`)
- `create()` - Initiate domain transfer
- `getStatus()` - Check transfer status
- `updateStatus()` - Approve/reject transfer
- `getList()` - List pending transfers

### 4. **Domains NS API** (`namecheap.domains.ns.*`)
- `create()` - Create nameserver
- `delete()` - Delete nameserver
- `getInfo()` - Get nameserver details
- `update()` - Update nameserver IP

### 5. **Whois API** (`namecheap.whois.*`)
- `getWhoisInfo()` - Get WHOIS information

### 6. **Domains Forwarding API**
- `setEmailForwarding()` - Configure email forwarding
- `getEmailForwarding()` - Get email forwarding settings

## ✅ Already Implemented (Core Features)

### Domains API
- ✅ `check()` - Check domain availability
- ✅ `list()` - List domains in account
- ✅ `register()` - Register new domain
- ✅ `renew()` - Renew domain
- ✅ `setContacts()` - Update contact information
- ✅ `lock()`/`unlock()` - Domain locking

### DNS API
- ✅ `get()` - Get DNS records
- ✅ `set()` - Set DNS records (with builder pattern!)
- ✅ `add()` - Add single record
- ✅ `delete()` - Delete records
- ✅ `set_custom_nameservers()` - Switch to custom nameservers (e.g., Route 53)
- ✅ `set_default_nameservers()` - Reset to Namecheap BasicDNS
- ✅ `get_nameserver_info()` - Get current nameserver configuration

### Enhanced Features
- ✅ Smart IP detection and validation
- ✅ Helpful error messages with IP troubleshooting
- ✅ Pydantic models with proper type safety
- ✅ Rich logging with colors
- ✅ Context manager support
- ✅ DNS builder pattern

## 🔧 Pricing Implementation Status

### Current Issues
- The `getPricing` API call is implemented but needs debugging
- Price fields are properly modeled but not being populated correctly
- Need to verify the API path and response structure for pricing

### Enhanced Domain Check (from old SDK)
The old SDK had an enhanced domain check that fetched pricing automatically. We've implemented this with the `include_pricing=True` parameter, but it needs fixing.

## 📝 Notes

The core domain and DNS functionality is complete and working well. The additional APIs (SSL, transfers, user management) are less commonly used but would make the SDK feature-complete with the Namecheap API.

Priority for implementation:
1. Fix pricing retrieval (high - already partially implemented)
2. SSL API (medium - common use case)
3. Transfer API (medium - needed for domain transfers)
4. Users API pricing methods (medium - already have getPricing)
5. Other APIs (low - rarely used)