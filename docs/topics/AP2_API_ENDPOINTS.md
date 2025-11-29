# SOHO API Endpoints - AP2 Payment Flow

## Overview
This document details all API endpoints that SOHO (as Credentials Provider and Merchant Payment Processor) must implement to support the Agent Payments Protocol (AP2) flow.

**SOHO's Dual Role:**
1. **Credentials Provider**: Manages user credit accounts, payment methods, and credentials
2. **Payment Processor**: Executes payments on-chain and settles with merchants

---

## Quick Reference: All Endpoints by Category

### Authentication & OAuth (4 endpoints)
- `#1` GET `/authorize` - Initiate OAuth authorization
- `#2` POST `/token` - Exchange code for token / Refresh token
- `#3` POST `/token` - Refresh access token
- `#4` GET `/v1/validate-token` - Validate token and get user context

### User Profile & Shipping (5 endpoints)
- `#6` GET `/v1/user/shipping-addresses` - Get shipping addresses
- `#6` GET `/v1/user/credit-status` - Get credit status
- `#7` POST `/v1/user/shipping-addresses` - Add shipping address
- `#8` PUT `/v1/user/shipping-addresses/{id}` - Update shipping address
- `#9` DELETE `/v1/user/shipping-addresses/{id}` - Delete shipping address
- `#10` POST `/v1/user/set-agent-limit` - Set agent spend limit
- `#9` GET `/v1/user/profile` - Get complete user profile

### Payment Methods & Credentials (3 endpoints) **[NEW]**
- `#10` POST `/v1/credentials/search-payment-methods` - **NEW**: Search compatible payment methods
- `#11` POST `/v1/credentials/create-token` - **NEW**: Create payment credential token
- `#15` POST `/v1/credentials/verify-token` - **NEW**: Verify payment credential token

### BNPL & Credit Management (1 endpoint)
- `#12` POST `/v1/credit/quote` - Request BNPL quote

### Payment Processing (4 endpoints)
- `#13` POST `/v1/pay` - **Complete payment flow (auto-approve or send push, then execute on-chain)**
- `#14` GET `/v1/pay/status` - Poll approval status and get final payment result
- `#22` GET `/v1/pay/qr` - Generate QR code for approval (alternative to push)
- `#15` POST `/v1/credentials/verify-token` - Verify payment credential token

### Payment Plans & History (3 endpoints)
- `#16` GET `/v1/user/payment-plans` - Get user payment plans
- `#17` POST `/v1/payment-plans/{id}/pay` - Make manual payment
- `#18` GET `/v1/user/purchases` - Get purchase history

### Webhooks (3 endpoints)
- `#19` POST `/v1/webhooks/register` - Register webhook
- `#20` Webhook Event: `payment.approved`
- `#21` Webhook Event: `payment.completed`

### Merchant Integration (2 endpoints)
- `#23` GET `/v1/merchants/verify-payment` - Merchant verify payment
- `#24` GET `/v1/merchants/settlements` - Get settlement info

### User Registration (1 endpoint)
- `#5` POST `/v1/user/register` - Register new user

---

## Key Changes & Additions

### ✅ **NEW Endpoints Added** (Based on Python Implementation)

1. **`POST /v1/credentials/search-payment-methods`** (#10)
   - Searches for user payment methods compatible with merchant requirements
   - Called by `handle_search_payment_methods` in credentials provider
   - Returns matching payment method aliases

2. **`POST /v1/credentials/create-token`** (#11)
   - Creates payment credential token for selected payment method
   - Called by `handle_create_payment_credential_token`
   - Token included in PaymentMandate sent to Payment Processor

3. **`POST /v1/credentials/verify-token`** (#16)
   - Payment Processor verifies token from PaymentMandate
   - Associates token with payment_mandate_id
   - Called before executing payment on-chain

### 🔄 **Biometric Approval Flow Simplified**

**REMOVED**: `POST /v1/credentials/request-biometric-approval`

**Why**: The `/v1/pay` endpoint handles approval internally:
- Payment Processor receives PaymentMandate
- Checks if `amount > agent_spend_limit`
- If yes: **Automatically sends push notification** to user's mobile app
- Returns `approval_id` for polling
- User approves via biometric on mobile app (Face ID/Touch ID)
- Alternative: QR code scan if push notification fails

**Shopping Agent doesn't need to request approval separately** - the Payment Processor handles it!

### 🔄 **Single Payment Endpoint - Simplified Architecture**

**MERGED**: `/v1/pay` now handles the complete payment lifecycle:

1. **Verify token** (internal)
2. **Check agent_spend_limit**
3. **IF amount ≤ limit**: Execute on-chain immediately, return result
4. **IF amount > limit**: Send push notification, wait for approval, then execute on-chain
5. **Return final result** with transaction_hash

**No separate `/v1/process-payment` needed** - everything happens in one endpoint!

**Benefits:**
- Simpler API - one endpoint for all payment flows
- Automatic execution after approval
- Consistent with industry standards (Stripe, PayPal, etc.)
- Merchant just polls `/v1/pay/status` and gets final result

### 🔄 **Clarified Endpoint Flow**

**Credentials Provider Flow (Shopping Agent → SOHO):**
```
1. GET credit-status → Get agent_spend_limit and user limits
2. search-payment-methods → Find compatible methods
3. create-token → Generate credential token
→ Shopping Agent creates PaymentMandate with token
→ Sends PaymentMandate to Merchant → Payment Processor
```

**Payment Processor Flow (Merchant → SOHO):**
```
1. verify-token → Validate token from PaymentMandate
2. /pay → Process payment
   - If amount ≤ agent_spend_limit: Auto-approve, return payment_hash
   - If amount > agent_spend_limit: Send push notification, return approval_id
3. /pay/status → Poll for approval (if approval_id returned)
4. /process-payment → Execute on-chain
```

---

## Authentication & OAuth 2.0

### 1. Initiate OAuth Authorization
**Endpoint:** `GET https://auth.soho.finance/authorize`

**Purpose:** User grants Shopping Agent access to their SOHO credit

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `client_id` | string | Yes | Shopping Agent's registered client ID |
| `redirect_uri` | string | Yes | OAuth callback URL for agent |
| `response_type` | string | Yes | Must be "code" for authorization code flow |
| `scope` | string | Yes | Requested permissions (e.g., "credit:read payment:authorize") |
| `state` | string | Yes | Random string for CSRF protection |

**Example:**
```
GET https://auth.soho.finance/authorize?
  client_id=shopping_agent_123&
  redirect_uri=https://agent.example.com/callback&
  response_type=code&
  scope=credit:read%20payment:authorize&
  state=random_state_xyz789
```

**User Experience:**
- User redirected to SOHO authorization page
- User logs in (if not already)
- User sees permission screen with spending limits
- User approves or denies

**Success Response:**
```
Redirect to: https://agent.example.com/callback?
  code=auth_code_abc123&
  state=random_state_xyz789
```

---

### 2. Exchange Authorization Code for Token
**Endpoint:** `POST https://auth.soho.finance/token`

**Purpose:** Shopping Agent exchanges authorization code for access token

**Request Headers:**
```
Content-Type: application/x-www-form-urlencoded
```

**Request Body:**
```
grant_type=authorization_code&
code=auth_code_abc123&
redirect_uri=https://agent.example.com/callback&
client_id=shopping_agent_123&
client_secret=agent_secret_xyz789
```

**Response (200 OK):**
```json
{
  "access_token": "soho_agent_token_abc123def456",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "soho_refresh_token_xyz789",
  "scope": "credit:read payment:authorize",
  "user_id": "user_abc123"
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `access_token` | string | Bearer token for authenticated requests |
| `token_type` | string | Always "Bearer" |
| `expires_in` | integer | Token lifetime in seconds (3600 = 1 hour) |
| `refresh_token` | string | Token to obtain new access token |
| `scope` | string | Granted permissions |
| `user_id` | string | SOHO user identifier |

---

### 3. Refresh Access Token
**Endpoint:** `POST https://auth.soho.finance/token`

**Purpose:** Get new access token using refresh token

**Request Body:**
```
grant_type=refresh_token&
refresh_token=soho_refresh_token_xyz789&
client_id=shopping_agent_123&
client_secret=agent_secret_xyz789
```

**Response (200 OK):**
```json
{
  "access_token": "soho_agent_token_new_abc456",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "soho_refresh_token_new_xyz123",
  "scope": "credit:read payment:authorize"
}
```

---

### 4. Validate Token
**Endpoint:** `GET https://api.soho.finance/v1/validate-token`

**Purpose:** Verify token is valid and get user context

**Request Headers:**
```
Authorization: Bearer soho_agent_token_abc123def456
```

**Response (200 OK):**
```json
{
  "valid": true,
  "user_id": "user_abc123",
  "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "agent_id": "shopping_agent_123",
  "scope": ["credit:read", "payment:authorize"],
  "spending_limits": {
    "per_transaction": 500.00,
    "daily": 1000.00,
    "monthly": 5000.00
  },
  "expires_at": "2025-11-15T16:30:00Z"
}
```

---

## User Registration & Profile Management

### 5. Register User
**Endpoint:** `POST https://api.soho.finance/v1/user/register`

**Purpose:** Create a new user account in SOHO system

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "john.doe@example.com",
  "phone": "+1-555-123-4567",
  "first_name": "John",
  "last_name": "Doe",
  "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "wallet_type": "connected"
}
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | User's email address |
| `phone` | string | Yes | User's phone number |
| `first_name` | string | Yes | User's first name |
| `last_name` | string | Yes | User's last name |
| `borrower_address` | string | Yes | Ethereum address (0x...) |
| `wallet_type` | string | Yes | "connected" (user's wallet) or "generated" (backend-generated) |

**Response (201 Created):**
```json
{
  "status": "success",
  "user_id": "user_abc123",
  "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "wallet_type": "connected",
  "registered_on_chain": true,
  "registration_tx": "0xabc123...",
  "credit_limit": 100.00,
  "credit_score": 500,
  "created_at": "2025-11-15T10:00:00Z"
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `user_id` | string | SOHO user identifier |
| `registered_on_chain` | boolean | Whether `Creditor.registerBorrower()` was called |
| `registration_tx` | string | Blockchain transaction hash of registration |
| `credit_limit` | number | Initial credit limit assigned |
| `credit_score` | number | Initial credit score (typically 500) |

**Error Response (409 Conflict):**
```json
{
  "status": "error",
  "error_code": "USER_ALREADY_EXISTS",
  "message": "User with this email or address already exists",
  "existing_user_id": "user_xyz456"
}
```

---

## User Profile & Credentials (Credentials Provider)

### 6. Get User Shipping Addresses
**Endpoint:** `GET https://api.soho.finance/v1/user/shipping-addresses`

**Purpose:** Shopping Agent retrieves user's saved shipping addresses

**Request Headers:**
```
Authorization: Bearer soho_agent_token_abc123def456
```

**Response (200 OK):**
```json
{
  "shipping_addresses": [
    {
      "address_id": "addr_primary_001",
      "is_default": true,
      "recipient_name": "John Doe",
      "street": "123 Main St",
      "apartment": "Apt 4B",
      "city": "San Francisco",
      "state": "CA",
      "zip": "94105",
      "country": "US",
      "phone": "+1-555-123-4567"
    },
    {
      "address_id": "addr_002",
      "is_default": false,
      "recipient_name": "John Doe",
      "street": "456 Work Plaza",
      "city": "San Francisco",
      "state": "CA",
      "zip": "94107",
      "country": "US",
      "phone": "+1-555-123-4567"
    }
  ]
}
```

---

### 7. Add Shipping Address
**Endpoint:** `POST https://api.soho.finance/v1/user/shipping-addresses`

**Purpose:** User adds a new shipping address to their profile

**Request Headers:**
```
Authorization: Bearer soho_agent_token_abc123def456
Content-Type: application/json
```

**Request Body:**
```json
{
  "recipient_name": "John Doe",
  "street": "789 New Address St",
  "apartment": "Suite 5",
  "city": "Los Angeles",
  "state": "CA",
  "zip": "90001",
  "country": "US",
  "phone": "+1-555-987-6543",
  "is_default": false
}
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `recipient_name` | string | Yes | Name of recipient |
| `street` | string | Yes | Street address |
| `apartment` | string | No | Apartment/Suite number |
| `city` | string | Yes | City name |
| `state` | string | Yes | State/Province code |
| `zip` | string | Yes | Postal code |
| `country` | string | Yes | Country code (ISO 3166-1) |
| `phone` | string | Yes | Contact phone number |
| `is_default` | boolean | No | Set as default address (default: false) |

**Response (201 Created):**
```json
{
  "status": "success",
  "address_id": "addr_003",
  "is_default": false,
  "created_at": "2025-11-15T11:00:00Z",
  "address": {
    "address_id": "addr_003",
    "recipient_name": "John Doe",
    "street": "789 New Address St",
    "apartment": "Suite 5",
    "city": "Los Angeles",
    "state": "CA",
    "zip": "90001",
    "country": "US",
    "phone": "+1-555-987-6543",
    "is_default": false
  }
}
```

**Business Logic:**
- User can have multiple shipping addresses
- Only one address can be marked as default
- If `is_default: true`, previous default is updated to false
- Agent retrieves all addresses and decides which to use

---

### 8. Update Shipping Address
**Endpoint:** `PUT https://api.soho.finance/v1/user/shipping-addresses/{address_id}`

**Purpose:** Update an existing shipping address

**Request Headers:**
```
Authorization: Bearer soho_agent_token_abc123def456
Content-Type: application/json
```

**Request Body:**
```json
{
  "recipient_name": "John Doe",
  "street": "789 Updated Address St",
  "apartment": "Suite 5A",
  "city": "Los Angeles",
  "state": "CA",
  "zip": "90002",
  "country": "US",
  "phone": "+1-555-987-6543",
  "is_default": true
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "address_id": "addr_003",
  "updated_at": "2025-11-15T12:00:00Z",
  "address": {
    "address_id": "addr_003",
    "recipient_name": "John Doe",
    "street": "789 Updated Address St",
    "apartment": "Suite 5A",
    "city": "Los Angeles",
    "state": "CA",
    "zip": "90002",
    "country": "US",
    "phone": "+1-555-987-6543",
    "is_default": true
  }
}
```

---

### 9. Delete Shipping Address
**Endpoint:** `DELETE https://api.soho.finance/v1/user/shipping-addresses/{address_id}`

**Purpose:** Delete a shipping address

**Request Headers:**
```
Authorization: Bearer soho_agent_token_abc123def456
```

**Response (200 OK):**
```json
{
  "status": "success",
  "address_id": "addr_003",
  "deleted_at": "2025-11-15T13:00:00Z"
}
```

**Error Response (400 Bad Request - Cannot Delete Default):**
```json
{
  "status": "error",
  "error_code": "CANNOT_DELETE_DEFAULT",
  "message": "Cannot delete default address. Set another address as default first."
}
```

---

### 6. Get User Credit Status
**Endpoint:** `GET https://api.soho.finance/v1/user/credit-status`

**Purpose:** Shopping Agent checks user's available credit before purchase

**Request Headers:**
```
Authorization: Bearer soho_agent_token_abc123def456
```

**Response (200 OK):**
```json
{
  "user_id": "user_abc123",
  "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "credit_limit": 5000.00,
  "outstanding_balance": 860.58,
  "available_credit": 4139.42,
  "credit_used": 860.58,
  "payment_history": {
    "on_time_payments": 12,
    "missed_payments": 0,
    "total_payments": 12
  },
  "spending_limits": {
    "agent_spend_limit": 500.00,
    "per_transaction": 1000.00,
    "per_day": 2000.00,
    "per_month": 5000.00
  },
  "status": "active"
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `credit_limit` | number | Total credit line from `BorrowerProfile.creditLimit` |
| `outstanding_balance` | number | Current debt from `BorrowerProfile.outstandingDebt` |
| `available_credit` | number | Remaining credit (`creditLimit - outstandingDebt`) |
| `credit_used` | number | Same as outstanding_balance |
| `spending_limits` | object | **Agent and user spending limits** |
| `agent_spend_limit` | number | **Max amount agent can spend without biometric approval** |
| `per_transaction` | number | Max amount per transaction |
| `per_day` | number | Max daily spending limit |
| `per_month` | number | Max monthly spending limit |
| `status` | string | Account status: "active", "suspended", "closed" |

**Business Logic:**
- **Shopping Agent uses `agent_spend_limit` to determine if biometric approval is needed**
- If `transaction_amount > agent_spend_limit`: Call `request-biometric-approval` (#13)
- If `transaction_amount <= agent_spend_limit`: Proceed without additional approval

---

### 10. Set Agent Spend Limit
**Endpoint:** `POST https://api.soho.finance/v1/user/set-agent-limit`

**Purpose:** Set or update the maximum amount an agent (admin) can spend on behalf of user per transaction

**Request Headers:**
```
Authorization: Bearer soho_agent_token_abc123def456
Content-Type: application/json
```

**Request Body:**
```json
{
  "user_id": "user_abc123",
  "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "agent_spend_limit": 500.00
}
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | string | Yes | SOHO user identifier |
| `borrower_address` | string | Yes | User's blockchain address |
| `agent_spend_limit` | number | Yes | Max amount per transaction (0 = disable agent spending) |

**Response (200 OK):**
```json
{
  "status": "success",
  "user_id": "user_abc123",
  "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "agent_spend_limit": 500.00,
  "previous_limit": 0.00,
  "transaction_hash": "0xdef456...",
  "updated_at": "2025-11-15T10:30:00Z"
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `agent_spend_limit` | number | New agent spend limit |
| `previous_limit` | number | Previous limit value |
| `transaction_hash` | string | Blockchain transaction hash of `setAgentSpendLimit()` call |

**Error Response (400 Bad Request - Exceeds Credit Limit):**
```json
{
  "status": "error",
  "error_code": "LIMIT_EXCEEDS_CREDIT",
  "message": "Agent spend limit cannot exceed user's credit limit",
  "agent_spend_limit": 500.00,
  "credit_limit": 100.00
}
```

**Business Logic:**
- Agent spend limit cannot exceed user's total credit limit
- Setting limit to 0 disables agent spending (user must spend directly)
- Calls `Creditor.setAgentSpendLimit(borrower, limit)` on-chain
- Both user and admin (SOHO backend) can set this limit

---

### 9. Get User Profile
**Endpoint:** `GET https://api.soho.finance/v1/user/profile`

**Purpose:** Get complete user profile including contact info

**Request Headers:**
```
Authorization: Bearer soho_agent_token_abc123def456
```

**Response (200 OK):**
```json
{
  "user_id": "user_abc123",
  "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "email": "john.doe@example.com",
  "phone": "+1-555-123-4567",
  "name": {
    "first": "John",
    "last": "Doe"
  },
  "kyc_status": "verified",
  "account_created": "2025-01-15T10:00:00Z",
  "credit_status": {
    "credit_limit": 5000.00,
    "available_credit": 4139.42,
    "status": "active"
  }
}
```

---

## Payment Method Management (Credentials Provider)

### 10. Search Payment Methods
**Endpoint:** `POST https://api.soho.finance/v1/credentials/search-payment-methods`

**Purpose:** Credentials Provider searches for user's payment methods that match merchant's accepted payment types. This is called by the Shopping Agent to find compatible payment methods.

**Request Headers:**
```
Authorization: Bearer soho_agent_token_abc123def456
Content-Type: application/json
```

**Request Body:**
```json
{
  "user_email": "user@example.com",
  "merchant_accepted_methods": [
    {
      "supported_methods": ["SOHO_CREDIT", "VISA", "MASTERCARD"],
      "provider_url": "https://api.soho.finance"
    }
  ]
}
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_email` | string | Yes | User's email address |
| `merchant_accepted_methods` | array | Yes | Array of PaymentMethodData from merchant |

**Response (200 OK):**
```json
{
  "payment_method_aliases": [
    "soho_credit",
    "SOHO Credit - Pay in Full",
    "SOHO Credit - Pay in 4",
    "SOHO Credit - 12 Month Plan"
  ]
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `payment_method_aliases` | array | List of payment method aliases that match merchant's requirements |

**Business Logic:**
- Checks if merchant accepts `SOHO_CREDIT` payment type
- Returns all SOHO Credit payment method aliases if accepted
- Returns empty array if merchant doesn't accept SOHO Credit
- Used by Shopping Agent during payment credential selection

---

### 11. Create Payment Credential Token
**Endpoint:** `POST https://api.soho.finance/v1/credentials/create-token`

**Purpose:** Creates a payment credential token for the selected payment method. This token is used in the PaymentMandate and sent to the Merchant Payment Processor.

**Request Headers:**
```
Authorization: Bearer soho_agent_token_abc123def456
Content-Type: application/json
```

**Request Body:**
```json
{
  "user_email": "user@example.com",
  "payment_method_alias": "SOHO Credit - Pay in 4"
}
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_email` | string | Yes | User's email address |
| `payment_method_alias` | string | Yes | The alias of the selected payment method |

**Response (200 OK):**
```json
{
  "payment_credential_token": {
    "type": "soho_credit",
    "value": "soho_token_0_user@example.com",
    "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "plan_id": "pay_in_4",
    "provider_url": "https://api.soho.finance"
  }
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Token type (e.g., "soho_credit") |
| `value` | string | The actual token value for payment processing |
| `borrower_address` | string | User's blockchain address |
| `plan_id` | string | Selected payment plan ID |
| `provider_url` | string | Credentials provider's API URL |

**Business Logic:**
- Validates that the payment method exists for the user
- Creates a unique token linking user email and payment method
- Token is included in PaymentMandate sent to Payment Processor
- Token is later verified during payment processing
- Used for tracking payment credentials across the AP2 flow

**Error Response (404 Not Found):**
```json
{
  "status": "error",
  "error_code": "PAYMENT_METHOD_NOT_FOUND",
  "message": "Payment method not found for user",
  "payment_method_alias": "invalid_alias"
}
```

---

## BNPL Credit Management

### 12. Request BNPL Quote
**Endpoint:** `POST https://api.soho.finance/v1/credit/quote`

**Purpose:** Get available BNPL payment plans for a purchase amount

**Request Headers:**
```
Authorization: Bearer soho_agent_token_abc123def456
Content-Type: application/json
```

**Request Body:**
```json
{
  "amount": 139.42,
  "merchant_id": "merchant_shoes_store",
  "cart_id": "cart_nike_001_xyz",
  "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
}
```

**Response (200 OK):**
```json
{
  "validation_status": "approved",
  "amount": 139.42,
  "currency": "USD",
  "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "credit_check": {
    "credit_limit": 5000.00,
    "available_credit": 4139.42,
    "outstanding_balance": 860.58,
    "sufficient_credit": true
  },
  "payment_plans": [
    {
      "plan_id": "pay_full",
      "name": "Pay in Full",
      "type": "single_payment",
      "term": "Pay in Full",
      "number_of_payments": 1,
      "payment_amount": 139.42,
      "total_amount": 139.42,
      "interest_rate": 0.0,
      "interest_amount": 0.0,
      "first_payment_date": "2025-12-15T00:00:00Z",
      "schedule": [
        {
          "payment_number": 1,
          "amount": 139.42,
          "due_date": "2025-12-15T00:00:00Z"
        }
      ]
    },
    {
      "plan_id": "pay_in_4",
      "name": "Pay in 4",
      "type": "installment",
      "term": "4 bi-weekly payments",
      "number_of_payments": 4,
      "payment_amount": 34.86,
      "total_amount": 139.44,
      "interest_rate": 0.0,
      "interest_amount": 0.0,
      "first_payment_date": "2025-11-15T00:00:00Z",
      "schedule": [
        {
          "payment_number": 1,
          "amount": 34.86,
          "due_date": "2025-11-15T00:00:00Z",
          "description": "First payment (due today)"
        },
        {
          "payment_number": 2,
          "amount": 34.86,
          "due_date": "2025-11-29T00:00:00Z"
        },
        {
          "payment_number": 3,
          "amount": 34.86,
          "due_date": "2025-12-13T00:00:00Z"
        },
        {
          "payment_number": 4,
          "amount": 34.86,
          "due_date": "2025-12-27T00:00:00Z"
        }
      ]
    },
    {
      "plan_id": "12_month",
      "name": "12 Month Plan",
      "type": "installment",
      "term": "12 monthly payments",
      "number_of_payments": 12,
      "payment_amount": 12.45,
      "total_amount": 149.40,
      "interest_rate": 0.0714,
      "interest_amount": 9.98,
      "first_payment_date": "2025-12-15T00:00:00Z",
      "schedule": [
        {
          "payment_number": 1,
          "amount": 12.45,
          "due_date": "2025-12-15T00:00:00Z"
        }
      ]
    }
  ],
  "spending_limits": {
    "per_transaction": 500.00,
    "daily": 1000.00,
    "monthly": 5000.00,
    "remaining_today": 1000.00,
    "remaining_this_month": 4250.00
  },
  "approval_required": false,
  "quote_expires_at": "2025-11-15T16:00:00Z"
}
```

---

## Payment Authorization & Processing

**AP2 Role Clarification:**
- **Shopping Agent**: Gets quotes and user credentials, creates PaymentMandate
- **Merchant Payment Processor (SOHO)**: Receives PaymentMandate, calls payment endpoints, executes on-chain

### 13. Process Payment (Merchant Payment Processor)
**Endpoint:** `POST https://api.soho.finance/v1/pay`

**Purpose:** Merchant Payment Processor (SOHO) processes payment for purchase. Returns immediate payment_hash if amount is within agent limit, or approval_id if user approval needed.

**Internal Process When Approval Required:**
- Payment Processor detects `amount > agent_spend_limit`
- Automatically sends push notification to user's SOHO mobile app
- User approves via biometric (Face ID/Touch ID)
- OR user can scan QR code (see endpoint #23)

**Caller:** Merchant Payment Processor receives PaymentMandate from Shopping Agent and calls this endpoint.

**Request Headers:**
```
X-Merchant-API-Key: merchant_key_abc123
Content-Type: application/json
```

**Request Body:**
```json
{
  "user_id": "user_abc123",
  "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "amount": 139.42,
  "currency": "USD",
  "merchant_id": "merchant_shoes_store",
  "merchant_name": "Merchant Shoes Store",
  "cart_id": "cart_nike_001_xyz",
  "selected_plan": {
    "plan_id": "pay_in_4",
    "payment_amount": 34.86,
    "number_of_payments": 4
  },
  "cart_details": {
    "items": [
      {
        "name": "Nike Air Max 90 - White",
        "quantity": 1,
        "price": 120.00
      }
    ],
    "subtotal": 120.00,
    "shipping": 8.50,
    "tax": 10.92,
    "total": 139.42
  },
  "shipping_address": {
    "street": "123 Main St",
    "city": "San Francisco",
    "state": "CA",
    "zip": "94105"
  }
}
```

**Response (200 OK - Auto-Approved, Amount ≤ Agent Limit):**
```json
{
  "status": "approved",
  "payment_hash": "soho_pay_hash_abc123",
  "amount": 139.42,
  "agent_spend_limit": 500.00,
  "approval_required": false,
  "message": "Payment approved automatically - amount within agent spend limit",
  "transaction_hash": "0xabc123def456789...",
  "block_number": 12345678,
  "timestamp": "2025-11-15T15:32:00Z"
}
```

**Response (202 Accepted - Approval Required, Amount > Agent Limit):**
```json
{
  "status": "pending_approval",
  "approval_id": "approval_soho_xyz789",
  "amount": 1250.00,
  "agent_spend_limit": 500.00,
  "approval_required": true,
  "reason": "Amount exceeds agent spend limit",
  "approval_method": "mobile_app",
  "message": "Push notification sent to user's SOHO mobile app",
  "expires_at": "2025-11-15T16:00:00Z",
  "polling_url": "https://api.soho.finance/v1/pay/status?approval_id=approval_soho_xyz789"
}
```

**Business Logic:**
- If `amount ≤ user's agent_spend_limit`: Auto-approved, returns `payment_hash`
- If `amount > user's agent_spend_limit`: **Internally sends push notification to mobile app**, returns `approval_id`
- **Push notification** displays: transaction amount, merchant, payment plan
- User approves via **biometric authentication** (Face ID/Touch ID) on mobile app
- Alternative: User scans QR code (see endpoint #23) with mobile app
- If `amount > user's agent_spend_limit`: Requires approval, returns `approval_id`
- Agent spend limit set via endpoint #10: `POST /v1/user/set-agent-limit`

---

### 14. Check Payment Status (Polling)
**Endpoint:** `GET https://api.soho.finance/v1/pay/status?approval_id={approval_id}`

**Purpose:** Merchant Payment Processor (SOHO) polls for user approval status (only needed when amount > agent limit and approval_id was returned from /v1/pay)

**Caller:** Merchant Payment Processor polls this endpoint after receiving approval_id from `/v1/pay`.

**Request Headers:**
```
X-Merchant-API-Key: merchant_key_abc123
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `approval_id` | string | Yes | Approval ID returned from `/v1/pay` |

**Response While Pending (202 Accepted):**
```json
{
  "approval_id": "approval_soho_xyz789",
  "status": "pending_approval",
  "amount": 1250.00,
  "agent_spend_limit": 500.00,
  "created_at": "2025-11-15T15:30:00Z",
  "expires_at": "2025-11-15T16:00:00Z"
}
```

**Response After Approval (200 OK):**
```json
{
  "approval_id": "approval_soho_xyz789",
  "status": "completed",
  "payment_hash": "soho_pay_hash_approved_abc123",
  "payment_id": "soho_pay_abc123",
  "approved_at": "2025-11-15T15:31:00Z",
  "approval_method": "mobile_biometric",
  "transaction_hash": "0xabc123def456789...",
  "block_number": 12345678,
  "network": "base",
  "credit_tokens_minted": 1250.00,
  "attestation": {
    "device_id": "device_iphone_14_xyz",
    "biometric_type": "face_id",
    "signature": "0x8f7a9b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0",
    "timestamp": "2025-11-15T15:31:00Z"
  },
  "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "merchant_address": "0xMerchant789...",
  "amount": 1250.00,
  "timestamp": "2025-11-15T15:32:00Z"
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `status` | string | "completed" - Payment executed on-chain |
| `payment_id` | string | SOHO payment identifier |
| `transaction_hash` | string | Blockchain transaction hash from `Creditor.spend()` |
| `block_number` | integer | Block where transaction was confirmed |
| `credit_tokens_minted` | number | Amount of SOHOCredit tokens minted to merchant |

**Business Logic:**
- When user approves via mobile app, payment **automatically executes on-chain**
- No separate call needed - `/v1/pay` handles entire flow
- Polling `/v1/pay/status` returns final transaction details when complete

**Response If User Rejects (403 Forbidden):**
```json
{
  "approval_id": "approval_soho_xyz789",
  "status": "rejected",
  "rejected_at": "2025-11-15T15:32:00Z",
  "reason": "User declined the transaction in mobile app"
}
```

**Response If Timeout (408 Request Timeout):**
```json
{
  "approval_id": "approval_soho_xyz789",
  "status": "expired",
  "created_at": "2025-11-15T15:30:00Z",
  "expired_at": "2025-11-15T16:00:00Z",
  "reason": "User did not respond within 30 minutes"
}
```

---

### 15. Process Payment (Merchant Payment Processor)
**Endpoint:** `POST https://api.soho.finance/v1/process-payment`

**Purpose:** Merchant forwards PaymentMandate to SOHO for on-chain execution

**Request Headers:**
```
X-Merchant-API-Key: merchant_key_abc123
Content-Type: application/json
```

**Request Body:**
```json
{
  "merchant_id": "merchant_shoes_store",
  "merchant_address": "0xMerchant789...",
  "cart_mandate": {
    "contents": {
      "cart_id": "cart_nike_001_xyz",
      "total_amount": 139.42,
      "currency": "USD",
      "items": [
        {
          "product_id": "prod_nike_001",
          "name": "Nike Air Max 90 - White",
          "quantity": 1,
          "unit_price": 120.00
        }
      ],
      "shipping": 8.50,
      "tax": 10.92
    },
    "cart_signature": "0x1a2b3c4d...",
    "merchant_id": "merchant_shoes_store",
    "merchant_address": "0xMerchant789...",
    "timestamp": "2025-11-15T15:30:00Z"
  },
  "payment_mandate": {
    "cart_mandate_hash": "0x7f8e9d0c...",
    "payment_details": {
      "amount": 139.42,
      "currency": "USD",
      "authorization_token": "soho_auth_token_abc123",
      "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
      "payment_plan": {
        "plan_id": "pay_in_4",
        "payment_amount": 34.86,
        "number_of_payments": 4,
        "first_payment_date": "2025-11-15T00:00:00Z"
      }
    },
    "attestation": {
      "device_id": "device_iphone_14_xyz",
      "biometric_type": "face_id",
      "signature": "0x8f7a9b2c...",
      "timestamp": "2025-11-15T15:31:00Z"
    },
    "shopping_agent_id": "shopping_agent_123",
    "timestamp": "2025-11-15T15:31:30Z"
  }
}
```

**Response (200 OK - Payment Successful):**
```json
{
  "status": "success",
  "payment_id": "soho_pay_abc123",
  "purchase_id": "purchase_12345",
  "transaction_hash": "0xabc123def456789...",
  "block_number": 12345678,
  "network": "base",
  "amount": 139.42,
  "currency": "USD",
  "credit_tokens_minted": 139.42,
  "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "merchant_address": "0xMerchant789...",
  "payment_plan": {
    "plan_id": "pay_in_4",
    "payment_amount": 34.86,
    "number_of_payments": 4,
    "payments_remaining": 4,
    "next_payment_date": "2025-11-15T00:00:00Z"
  },
  "timestamp": "2025-11-15T15:32:00Z",
  "order_id": "order_12345_pending"
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `payment_id` | string | SOHO payment identifier |
| `purchase_id` | string | SOHO purchase record ID |
| `transaction_hash` | string | Blockchain transaction hash from `Creditor.spend()` |
| `block_number` | integer | Block where transaction was confirmed |
| `credit_tokens_minted` | number | Amount of SOHOCredit tokens minted to merchant |
| `order_id` | string | Merchant's order identifier |

**Error Response (400 Bad Request - Invalid Authorization):**
```json
{
  "status": "error",
  "error_code": "INVALID_AUTHORIZATION",
  "message": "Authorization token is invalid or expired",
  "authorization_id": "auth_soho_xyz789"
}
```

**Error Response (402 Payment Required - Insufficient Credit):**
```json
{
  "status": "error",
  "error_code": "INSUFFICIENT_CREDIT",
  "message": "User does not have sufficient credit for this purchase",
  "required_amount": 139.42,
  "available_credit": 50.00,
  "credit_limit": 5000.00
}
```

---

---

### 16. Verify Payment Credential Token
**Endpoint:** `POST https://api.soho.finance/v1/credentials/verify-token`

**Purpose:** Payment Processor verifies the payment credential token received in PaymentMandate and associates it with payment_mandate_id. Called by Merchant Payment Processor when processing payment.

**Request Headers:**
```
X-Merchant-API-Key: merchant_key_abc123
Content-Type: application/json
```

**Request Body:**
```json
{
  "token": "soho_token_0_user@example.com",
  "payment_mandate_id": "mandate_abc123"
}
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | Yes | Payment credential token from PaymentMandate |
| `payment_mandate_id` | string | Yes | Payment mandate identifier |

**Response (200 OK):**
```json
{
  "valid": true,
  "payment_method": {
    "type": "SOHO_CREDIT",
    "alias": "SOHO Credit - Pay in 4",
    "plan_id": "pay_in_4"
  },
  "user_info": {
    "user_email": "user@example.com",
    "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
  },
  "token_updated": true
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `valid` | boolean | Whether token is valid |
| `payment_method` | object | Associated payment method details |
| `user_info` | object | User information linked to token |
| `token_updated` | boolean | Whether token was associated with mandate |

**Error Response (401 Unauthorized - Invalid Token):**
```json
{
  "status": "error",
  "error_code": "INVALID_TOKEN",
  "message": "Payment credential token is invalid or expired"
}
```

**Business Logic:**
- Verifies token exists and is valid
- Associates token with payment_mandate_id (one-time use)
- Returns payment method and user details
- Token cannot be reused after association
- Called by Payment Processor before executing payment

---

## Payment Plan Management

### 16. Get User Payment Plans
**Endpoint:** `GET https://api.soho.finance/v1/user/payment-plans`

**Purpose:** Retrieve all active payment plans for user

**Request Headers:**
```
Authorization: Bearer soho_agent_token_abc123def456
```

**Response (200 OK):**
```json
{
  "payment_plans": [
    {
      "plan_instance_id": "plan_inst_001",
      "purchase_id": "purchase_12345",
      "merchant_name": "Merchant Shoes Store",
      "merchant_id": "merchant_shoes_store",
      "original_amount": 139.42,
      "total_amount": 139.44,
      "amount_paid": 34.86,
      "remaining_balance": 104.58,
      "plan_type": "pay_in_4",
      "payment_amount": 34.86,
      "payments_made": 1,
      "payments_remaining": 3,
      "next_payment_date": "2025-11-29T00:00:00Z",
      "status": "active",
      "created_at": "2025-11-15T15:32:00Z",
      "schedule": [
        {
          "payment_number": 1,
          "amount": 34.86,
          "due_date": "2025-11-15T00:00:00Z",
          "status": "paid",
          "paid_at": "2025-11-15T15:32:00Z"
        },
        {
          "payment_number": 2,
          "amount": 34.86,
          "due_date": "2025-11-29T00:00:00Z",
          "status": "scheduled"
        },
        {
          "payment_number": 3,
          "amount": 34.86,
          "due_date": "2025-12-13T00:00:00Z",
          "status": "scheduled"
        },
        {
          "payment_number": 4,
          "amount": 34.86,
          "due_date": "2025-12-27T00:00:00Z",
          "status": "scheduled"
        }
      ]
    }
  ],
  "summary": {
    "total_active_plans": 1,
    "total_owed": 104.58,
    "next_payment_amount": 34.86,
    "next_payment_date": "2025-11-29T00:00:00Z"
  }
}
```

---

### 17. Make Manual Payment
**Endpoint:** `POST https://api.soho.finance/v1/payment-plans/{plan_instance_id}/pay`

**Purpose:** User makes early payment or extra payment on plan

**Request Headers:**
```
Authorization: Bearer soho_agent_token_abc123def456
Content-Type: application/json
```

**Request Body:**
```json
{
  "amount": 34.86,
  "payment_method": "bank_account",
  "payment_source_id": "bank_account_xyz123"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "payment_id": "payment_manual_456",
  "plan_instance_id": "plan_inst_001",
  "amount_paid": 34.86,
  "transaction_hash": "0xdef456ghi789...",
  "remaining_balance": 69.72,
  "payments_remaining": 2,
  "next_payment_date": "2025-12-13T00:00:00Z",
  "timestamp": "2025-11-20T10:00:00Z"
}
```

---

## Transaction History

### 18. Get Purchase History
**Endpoint:** `GET https://api.soho.finance/v1/user/purchases`

**Purpose:** Retrieve user's complete purchase history

**Request Headers:**
```
Authorization: Bearer soho_agent_token_abc123def456
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Number of results (default: 20, max: 100) |
| `offset` | integer | No | Pagination offset (default: 0) |
| `status` | string | No | Filter by status: "completed", "active", "cancelled" |

**Response (200 OK):**
```json
{
  "purchases": [
    {
      "purchase_id": "purchase_12345",
      "merchant_name": "Merchant Shoes Store",
      "merchant_id": "merchant_shoes_store",
      "amount": 139.42,
      "currency": "USD",
      "payment_plan": "pay_in_4",
      "status": "active",
      "transaction_hash": "0xabc123def456...",
      "purchased_at": "2025-11-15T15:32:00Z",
      "items": [
        {
          "name": "Nike Air Max 90 - White",
          "quantity": 1,
          "price": 120.00
        }
      ],
      "payment_status": {
        "total_amount": 139.44,
        "amount_paid": 34.86,
        "remaining_balance": 104.58,
        "payments_made": 1,
        "payments_remaining": 3
      }
    }
  ],
  "pagination": {
    "total": 15,
    "limit": 20,
    "offset": 0,
    "has_more": false
  }
}
```

---

## Webhooks & Notifications

### 19. Register Webhook
**Endpoint:** `POST https://api.soho.finance/v1/webhooks/register`

**Purpose:** Shopping Agent registers callback URL for events

**Request Headers:**
```
Authorization: Bearer soho_agent_token_abc123def456
Content-Type: application/json
```

**Request Body:**
```json
{
  "webhook_url": "https://agent.example.com/webhooks/soho",
  "events": [
    "authorization.approved",
    "authorization.rejected",
    "payment.completed",
    "payment.failed",
    "payment_plan.payment_due"
  ],
  "secret": "webhook_secret_xyz789"
}
```

**Response (200 OK):**
```json
{
  "webhook_id": "webhook_001",
  "webhook_url": "https://agent.example.com/webhooks/soho",
  "events": [
    "authorization.approved",
    "authorization.rejected",
    "payment.completed",
    "payment.failed",
    "payment_plan.payment_due"
  ],
  "status": "active",
  "created_at": "2025-11-15T10:00:00Z"
}
```

---

### 20. Webhook Event: Payment Approved
**Sent To:** Shopping Agent's registered webhook URL

**Event Type:** `payment.approved`

**Payload:**
```json
{
  "event_id": "evt_payment_approved_001",
  "event_type": "payment.approved",
  "timestamp": "2025-11-15T15:31:00Z",
  "data": {
    "approval_id": "approval_soho_xyz789",
    "payment_hash": "soho_pay_hash_approved_abc123",
    "user_id": "user_abc123",
    "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "amount": 1250.00,
    "agent_spend_limit": 500.00,
    "approved_at": "2025-11-15T15:31:00Z",
    "approval_method": "mobile_biometric"
  }
}
```

---

### 21. Webhook Event: Payment Completed
**Sent To:** Shopping Agent's registered webhook URL

**Event Type:** `payment.completed`

**Payload:**
```json
{
  "event_id": "evt_payment_001",
  "event_type": "payment.completed",
  "timestamp": "2025-11-15T15:32:00Z",
  "data": {
    "payment_id": "soho_pay_abc123",
    "purchase_id": "purchase_12345",
    "user_id": "user_abc123",
    "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "merchant_id": "merchant_shoes_store",
    "amount": 139.42,
    "transaction_hash": "0xabc123def456...",
    "status": "completed"
  }
}
```

---

## Mobile App Integration

### 22. Generate QR Code for Approval (Merchant Payment Processor)
**Endpoint:** `GET https://api.soho.finance/v1/pay/qr?approval_id={approval_id}`

**Purpose:** Generate QR code for mobile app scanning (alternative to push notification) when approval required. This is an alternative flow if push notification fails or user prefers QR scanning.

**Caller:** Merchant Payment Processor can generate QR for user to scan if push notification fails.

**Request Headers:**
```
X-Merchant-API-Key: merchant_key_abc123
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `approval_id` | string | Yes | Approval ID from `/v1/pay` response |

**Response (200 OK):**
```json
{
  "approval_id": "approval_soho_xyz789",
  "qr_code_url": "https://api.soho.finance/qr/approval_soho_xyz789.png",
  "qr_code_data": "soho://approve/approval_soho_xyz789",
  "expires_at": "2025-11-15T16:00:00Z"
}
```

**QR Code Data Format:**
```
soho://approve/{approval_id}
```

---

## Merchant Integration (For Merchant Payment Processor)

### 23. Merchant: Verify Payment
**Endpoint:** `GET https://api.soho.finance/v1/merchants/verify-payment`

**Purpose:** Merchant verifies payment was executed on-chain

**Request Headers:**
```
X-Merchant-API-Key: merchant_key_abc123
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `payment_id` | string | No | SOHO payment ID |
| `transaction_hash` | string | No | Blockchain transaction hash |

**Response (200 OK):**
```json
{
  "verified": true,
  "payment_id": "soho_pay_abc123",
  "transaction_hash": "0xabc123def456...",
  "merchant_address": "0xMerchant789...",
  "amount": 139.42,
  "credit_tokens_received": 139.42,
  "status": "confirmed",
  "block_number": 12345678,
  "confirmations": 12,
  "timestamp": "2025-11-15T15:32:00Z"
}
```

---

### 24. Merchant: Get Settlement Info
**Endpoint:** `GET https://api.soho.finance/v1/merchants/settlements`

**Purpose:** Merchant checks available balance and settlement options

**Request Headers:**
```
X-Merchant-API-Key: merchant_key_abc123
```

**Response (200 OK):**
```json
{
  "merchant_id": "merchant_shoes_store",
  "merchant_address": "0xMerchant789...",
  "credit_token_balance": 5432.10,
  "available_for_withdrawal": 5432.10,
  "pending_settlements": 0,
  "total_sales": 15678.90,
  "last_settlement": {
    "settlement_id": "settle_001",
    "amount": 1000.00,
    "settled_at": "2025-11-10T10:00:00Z"
  }
}
```

---

## Complete AP2 Flow - Endpoint Sequence

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       AP2 ENDPOINT CALL SEQUENCE                             │
│         SOHO as Credentials Provider & Payment Processor                    │
└─────────────────────────────────────────────────────────────────────────────┘

1. USER ONBOARDING & SETUP
   POST /v1/user/register                     (#5 - Register new user)
   POST /v1/user/set-agent-limit              (#10 - Set agent spend limit)

2. AUTHENTICATION
   GET  /authorize                            (#1 - User grants access)
   POST /token                                (#2 - Get access token)
   GET  /v1/validate-token                    (#4 - Validate token)

3. PRE-PURCHASE - CREDENTIALS PROVIDER (Shopping Agent calls these)
   GET  /v1/user/shipping-addresses           (#6 - Get shipping address)
   GET  /v1/user/credit-status                (#6 - Check credit status & agent_spend_limit)

4. SHOPPING
   [Merchant Agent endpoints - not SOHO APIs]

5. PAYMENT PREPARATION (Shopping Agent → Credentials Provider)
   POST /v1/credit/quote                      (#12 - Get BNPL payment plan options)
   POST /v1/credentials/search-payment-methods        (#10 - Find compatible payment methods)
   POST /v1/credentials/create-token                  (#11 - Create payment credential token)   [Shopping Agent creates PaymentMandate with token and sends to Merchant]

6. PAYMENT PROCESSING (Merchant → Payment Processor → SOHO)
   POST /v1/credentials/verify-token          (#15 - Verify token from PaymentMandate)
   POST /v1/pay                               (#13 - Complete payment flow)
      → IF amount ≤ agent_spend_limit:
         • Executes payment on-chain immediately
         • Returns payment_hash + transaction_hash

      → IF amount > agent_spend_limit:
         • Sends push notification to user's mobile app
         • Returns approval_id
         • User approves via biometric
         • **Payment automatically executes on-chain after approval**

   IF approval_id returned:
      GET  /v1/pay/status?approval_id=...     (#14 - Poll for approval + final result)
      GET  /v1/pay/qr?approval_id=...         (#22 - Generate QR code if push fails)

      [When status returns "completed", payment is already on-chain]

   GET  /v1/merchants/verify-payment          (#23 - Merchant verifies on-chain)7. POST-PURCHASE
   GET  /v1/user/payment-plans                (#16 - View active payment plans)
   GET  /v1/user/purchases                    (#18 - View purchase history)
   POST /v1/payment-plans/{id}/pay            (#17 - Make manual payment)

8. WEBHOOKS (OPTIONAL)
   POST /v1/webhooks/register                 (#19 - Register for events)
   [Webhooks sent]:
      payment.approved                        (#20)
      payment.completed                       (#21)
```

---

## Credentials Provider Handler → API Endpoint Mapping

**From `samples/python/src/roles/soho_credentials_provider/`:**

| Handler Function | Maps to API Endpoint | Purpose |
|------------------|---------------------|---------|
| `handle_get_shipping_address` | `GET /v1/user/shipping-addresses` (#6) | Get user's shipping address |
| `handle_get_credit_status` | `GET /v1/user/credit-status` (#6) | Check user's credit limits and availability |
| `handle_get_bnpl_quote` | `POST /v1/credit/quote` (#12) | Get BNPL payment plan options |
| `handle_request_biometric_approval` | `POST /v1/credentials/request-biometric-approval` (#13) | Request biometric approval via mobile app |
| `handle_search_payment_methods` | `POST /v1/credentials/search-payment-methods` (#10) | Find compatible payment methods |
| `handle_create_payment_credential_token` | `POST /v1/credentials/create-token` (#11) | Create payment credential token |

**Account Manager Features:**
- **SOHO IS the credentials provider** - manages payment methods internally
- Supports: `SOHO_CREDIT` with multiple BNPL plans
- Other providers (PayPal, Google Pay) are managed by separate credentials provider agents
- All handlers use `account_manager.py` to access user data and spending limits

---

## Payment Processor Handler → API Endpoint Mapping

**From `samples/python/src/roles/merchant_agent/payment_processor/`:**

| Handler Function | Maps to API Endpoint | Purpose |
|------------------|---------------------|---------|
| `initiate_payment` | `POST /v1/pay` (#13) | Complete payment (checks limits, approvals, executes on-chain) |
| (internal) | `GET /v1/pay/status` (#14) | Poll for approval status and final result |
| `_complete_payment` | **(Internal to /v1/pay)** | Payment execution handled automatically by /v1/pay |
| (internal) | `POST /v1/credentials/verify-token` (#15) | Verify payment credential token |

**Payment Flow Logic:**
1. Payment Processor receives `PaymentMandate` from Merchant
2. If payment method is `SOHO_CREDIT`: Skip OTP challenge (biometric already done)
3. Extracts `token.value` from PaymentMandate
4. Verifies token with Credentials Provider
5. Executes payment on-chain via smart contract
6. Sends payment receipt back to Credentials Provider (A2A message, not REST)
```

---

## Authentication Summary

All endpoints (except OAuth authorization) require authentication:

**OAuth Bearer Token (Shopping Agent):**
```
Authorization: Bearer soho_agent_token_abc123def456
```

**API Key (Merchant):**
```
X-Merchant-API-Key: merchant_key_abc123
```

---

## Rate Limits

| Endpoint Type | Rate Limit | Window |
|--------------|------------|---------|
| OAuth endpoints | 10 requests | 1 minute |
| User profile endpoints | 100 requests | 1 minute |
| Payment processing | 50 requests | 1 minute |
| Webhook registration | 10 requests | 1 hour |
| Status polling | 60 requests | 1 minute |

---

## Error Codes

| HTTP Status | Error Code | Description |
|------------|------------|-------------|
| 400 | `INVALID_REQUEST` | Malformed request body or parameters |
| 401 | `UNAUTHORIZED` | Invalid or missing authentication |
| 402 | `INSUFFICIENT_CREDIT` | User doesn't have enough credit |
| 403 | `FORBIDDEN` | User rejected authorization |
| 404 | `NOT_FOUND` | Resource not found |
| 408 | `TIMEOUT` | Authorization expired |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server error |
| 503 | `SERVICE_UNAVAILABLE` | Service temporarily down |
