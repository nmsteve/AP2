# AP2 Payment Flow - SOHO as Merchant Payment Processor

## Overview
This document details the complete Agent Payments Protocol (AP2) flow using SOHO as the Merchant Payment Processor. This implementation follows Google's AP2 specification for secure, trusted payments between AI agents.

---

## Key Actors & Roles

| Actor | Role in AP2 | Implementation | Description |
|-------|-------------|----------------|-------------|
| **User** | Human Authority | End User | Individual who delegates payment task to agent |
| **Shopping Agent (SA)** | User Agent | ChatGPT, Claude, Custom Agent | AI that interacts with user and coordinates purchase |
| **Credentials Provider (CP)** | Payment Credentials Manager | **SOHO Credit Platform** | Manages user credit, shipping address, and authentication |
| **Merchant Agent (MA)** | Merchant Endpoint | Merchant's AI/API | Represents merchant, showcases products, creates CartMandate |
| **Merchant** | Seller | E-commerce Store | Business entity selling products/services |
| **Merchant Payment Processor (MPP)** | Transaction Processor | **SOHO Payment Facilitator** | Processes payment authorization and settlement |
| **Creditor Contract** | On-Chain Credit System | Creditor.sol on Base | Smart contract that manages credit issuance and debt tracking |

---

## Prerequisites

### Merchant Onboarding with SOHO

**Before accepting payments, merchants must register with SOHO:**

**Step 1: Merchant Registration**
```
POST https://api.soho.finance/v1/merchants/register
```

**Request:**
```json
{
  "business_name": "Nike Shoe Store",
  "business_id": "merchant_shoes_store",
  "business_email": "payments@merchant-shoes.com",
  "business_type": "e-commerce",
  "website": "https://merchant-shoes.com",
  "contact": {
    "name": "John Smith",
    "email": "john@merchant-shoes.com",
    "phone": "+1-555-0200"
  },
  "wallet_option": "generate" // or "connect"
}
```

**Response:**
```json
{
  "merchant_id": "merchant_shoes_store",
  "merchant_address": "0xMerchant789...",
  "private_key_encrypted": "encrypted_key_...",
  "status": "pending_verification",
  "api_key": "soho_merchant_key_xyz789"
}
```

**Step 2: SOHO Admin Registers Merchant On-Chain**
```solidity
// SOHO admin calls Creditor.sol
Creditor.registerMerchant(
  merchantAddress: 0xMerchant789...,
  merchantId: "merchant_shoes_store"
)
```

**Step 3: Merchant Verification Complete**
```json
{
  "merchant_id": "merchant_shoes_store",
  "merchant_address": "0xMerchant789...",
  "status": "verified",
  "can_accept_payments": true,
  "registered_on_chain": true,
  "registration_date": "2025-11-01T10:00:00Z"
}
```

**Merchant Profile:**
```json
{
  "merchant_id": "merchant_shoes_store",
  "merchant_address": "0xMerchant789...",
  "business_name": "Nike Shoe Store",
  "wallet": {
    "address": "0xMerchant789...",
    "network": "Base",
    "balance_soho_credit": 0
  },
  "payment_settings": {
    "accepts_soho_credit": true,
    "settlement_preference": "instant",
    "withdrawal_address": "0xMerchant789..."
  },
  "status": "active"
}
```

---

## Authentication & User Identity

### User Setup with SOHO (Credentials Provider)

```
User → SOHO Platform → Profile Setup → On-chain Registration
```

**Process:**
1. User creates account on SOHO platform
2. Completes KYC/verification
3. **Provides shipping details**:
   - Primary shipping address
   - Billing address (if different)
   - Phone number
   - Email
4. Wallet assigned (connected or generated):
   - **Option A**: User connects existing wallet (MetaMask, etc.)
   - **Option B**: Backend generates identifier address
5. SOHO admin calls `Creditor.registerBorrower(userWalletAddress)`
6. System creates:
   - **Off-chain**: `user_id` (user_abc123)
   - **Off-chain**: Shipping addresses (stored in SOHO database)
   - **On-chain**: `borrower_address` (0x123...abc)
   - **Mapping**: `user_id ↔ borrower_address ↔ shipping_info`

**User Profile in SOHO (Credentials Provider):**
```json
{
  "user_id": "user_abc123",
  "borrower_address": "0xBorrower456...",
  "kyc_verified": true,
  "shipping_addresses": [
    {
      "id": "addr_primary",
      "street": "123 Main St",
      "city": "San Francisco",
      "state": "CA",
      "zip": "94105",
      "country": "US",
      "is_default": true
    }
  ],
  "contact": {
    "email": "user@example.com",
    "phone": "+1-555-0100"
  },
  "credit_profile": {
    "credit_limit": 5000.00,
    "available_credit": 4139.42,
    "outstanding_debt": 860.58
  }
}
```

### Shopping Agent Authentication (OAuth 2.0)

**Flow:**
```
1. User → Shopping Agent: "Connect SOHO Credit"
2. Shopping Agent → SOHO: OAuth authorization request
3. SOHO → User: Approval screen (spending limits, permissions)
4. User → SOHO: Approve
5. SOHO → Shopping Agent: Authorization code
6. Shopping Agent → SOHO: Exchange code for access token
7. SOHO → Shopping Agent: { access_token, user_id, spending_limits }
```

**Access Token Payload:**
```json
{
  "access_token": "soho_agent_token_abc123def456",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user_id": "user_abc123",
  "borrower_address": "0xBorrower456...",
  "spending_limits": {
    "per_transaction": 500.00,
    "daily": 1000.00,
    "monthly": 5000.00
  }
}
```

---

## Complete AP2 Flow (Human Present)

### 1. User Request
**Actor:** User → Shopping Agent

```
User: "Find me white running shoes under $150"
```

**Shopping Agent Actions:**
- Receives natural language request
- Prepares to create IntentMandate

---

### 2. IntentMandate Confirmation
**Actor:** Shopping Agent → User

**Shopping Agent Response:**
```json
{
  "intent_summary": "Search for white running shoes with max price $150",
  "natural_language_description": "I'll help you find white running shoes under $150",
  "merchants": null,
  "price_range": { "max": 150.00, "currency": "USD" },
  "requires_confirmation": true
}
```

**User sees:**
```
🤖 Shopping Agent: "I understand you want white running shoes under $150. 
Should I proceed with this search?"
```

---

### 3. User Confirms Intent
**Actor:** User → Shopping Agent

```
User: "Yes, proceed"
```

**Shopping Agent Creates IntentMandate:**
```json
{
  "user_cart_confirmation_required": true,
  "natural_language_description": "White running shoes under $150",
  "merchants": null,
  "skus": null,
  "required_refundability": false,
  "intent_expiry": "2025-11-15T18:00:00Z",
  "user_id": "user_abc123"
}
```

---

### 4. Credential Provider (SOHO Credit)
**Actor:** User → Shopping Agent (Pre-configured)

**Note:** User is already authenticated with SOHO Credit via OAuth token (from authentication step). SOHO Credit is the Credentials Provider managing:
- User credit limits
- Shipping addresses
- Payment authorization

**Shopping Agent already has:**
```json
{
  "credentials_provider": "soho_credit",
  "cp_endpoint": "https://api.soho.finance/v1",
  "user_context": {
    "user_id": "user_abc123",
    "borrower_address": "0xBorrower456...",
    "available_credit": 4139.42
  }
}
```

---

### 5. Get Shipping Address
**Actor:** Shopping Agent → SOHO Credit (Credentials Provider)

**Shopping Agent Request:**
```http
GET /v1/user/shipping-addresses HTTP/1.1
Host: api.soho.finance
Authorization: Bearer soho_agent_token_abc123def456
```

**SOHO Credit (CP) Response:**
```json
{
  "shipping_addresses": [
    {
      "id": "addr_primary",
      "street": "123 Main St",
      "city": "San Francisco",
      "state": "CA",
      "zip": "94105",
      "country": "US",
      "is_default": true,
      "label": "Home"
    },
    {
      "id": "addr_work",
      "street": "456 Market St",
      "city": "San Francisco",
      "state": "CA",
      "zip": "94103",
      "country": "US",
      "is_default": false,
      "label": "Work"
    }
  ],
  "contact": {
    "email": "user@example.com",
    "phone": "+1-555-0100"
  }
}
```

**Shopping Agent uses default address:**
```json
{
  "shipping_address": {
    "street": "123 Main St",
    "city": "San Francisco",
    "state": "CA",
    "zip": "94105",
    "country": "US"
  }
}
```

---

### 6. Get Credit Availability
**Actor:** Shopping Agent → SOHO Credit (Credentials Provider)

**Shopping Agent Request:**
```http
GET /v1/user/credit-status HTTP/1.1
Host: api.soho.finance
Authorization: Bearer soho_agent_token_abc123def456
```

**SOHO Credit (CP) Response:**
```json
{
  "user_id": "user_123",
  "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "credit_profile": {
    "total_credit_limit": "5000.00",
    "available_credit": "4200.00",
    "outstanding_balance": "800.00",
    "credit_score": 750,
    "payment_history": "excellent"
  },
  "spending_limits": {
    "per_transaction": "1000.00",
    "per_day": "2000.00",
    "per_month": "5000.00"
  },
  "status": "active"
}
```

---

### 7. Search Products
**Actor:** Shopping Agent → Merchant Agent → Merchant

**Shopping Agent Request to Merchant Agent:**
```http
POST /api/v1/search HTTP/1.1
Host: merchant-agent.openai.com
Content-Type: application/json
```

```json
{
  "intent_mandate": {
    "natural_language_description": "White running shoes under $150",
    "filters": {
      "color": "white",
      "category": "running shoes",
      "max_price": 150.00
    }
  },
  "shipping_address": {
    "city": "San Francisco",
    "state": "CA",
    "zip": "94105"
  }
}
```

**Merchant Agent queries Merchant's Product Catalog:**
```http
GET /products?category=running_shoes&color=white&max_price=150
Host: api.merchant-shoes.com
```

**Merchant returns product data:**
```json
{
  "products": [
    {
      "product_id": "prod_nike_001",
      "name": "Nike Air Max 90 - White",
      "price": 120.00,
      "currency": "USD",
      "in_stock": true,
      "shipping_cost": 8.50
    },
    {
      "product_id": "prod_adidas_002",
      "name": "Adidas Ultraboost 22 - White",
      "price": 145.00,
      "currency": "USD",
      "in_stock": true,
      "shipping_cost": 8.50
    }
  ]
}
```

**Merchant Agent returns to Shopping Agent:**
```json
{
  "search_results": [
    {
      "product_id": "prod_nike_001",
      "name": "Nike Air Max 90 - White",
      "price": 120.00,
      "currency": "USD",
      "image_url": "https://cdn.merchant.com/nike-air-max-90.jpg",
      "in_stock": true,
      "shipping_cost": 8.50
    },
    {
      "product_id": "prod_adidas_002",
      "name": "Adidas Ultraboost 22 - White",
      "price": 145.00,
      "currency": "USD",
      "image_url": "https://cdn.merchant.com/adidas-ultraboost.jpg",
      "in_stock": true,
      "shipping_cost": 8.50
    }
  ]
}
```

---

### 8. Present Options to User
**Actor:** Shopping Agent → User

```
🤖 Shopping Agent: "I found these white running shoes:

1. Nike Air Max 90 - White
   Price: $120.00 + $8.50 shipping = $128.50
   ⭐⭐⭐⭐⭐ (4.8/5)

2. Adidas Ultraboost 22 - White
   Price: $145.00 + $8.50 shipping = $153.50
   ⭐⭐⭐⭐⭐ (4.9/5)

Which would you like?"
```

**User Response:**
```
User: "I'll take the Nike Air Max 90"
```

---

### 9. Request Cart Creation
**Actor:** Shopping Agent → Merchant Agent → Merchant

**Shopping Agent Request to Merchant Agent:**
```http
POST /api/v1/cart/create HTTP/1.1
Host: merchant-agent.openai.com
Content-Type: application/json
```

```json
{
  "product_id": "prod_nike_001",
  "quantity": 1,
  "shipping_address": {
    "street": "123 Main St",
    "city": "San Francisco",
    "state": "CA",
    "zip": "94105",
    "country": "US"
  }
}
```

**Merchant Agent forwards to Merchant:**
```http
POST /api/v1/cart HTTP/1.1
Host: api.merchant-shoes.com
Content-Type: application/json
```

```json
{
  "product_id": "prod_nike_001",
  "quantity": 1,
  "shipping_address": {
    "street": "123 Main St",
    "city": "San Francisco",
    "state": "CA",
    "zip": "94105",
    "country": "US"
  }
}
```

---

### 10. Merchant Creates CartMandate
**Actor:** Merchant → Merchant Agent

**Merchant Agent calculates:**
```
Subtotal:     $120.00
Shipping:     $  8.50
Tax (8.5%):   $ 10.92
─────────────────────
Total:        $139.42
```

**CartMandate Structure:**
```json
{
  "contents": {
    "id": "cart_nike_001_xyz",
    "user_signature_required": true,
    "payment_request": {
      "method_data": [
        {
          "supported_methods": "SOHO_CREDIT",
          "data": {
            "payment_processor_url": "https://api.soho.finance/v1/process",
            "supported_currencies": ["USD", "USDC"]
          }
        },
        {
          "supported_methods": "CARD",
          "data": {
            "supported_networks": ["visa", "mastercard", "amex"],
            "payment_processor_url": "https://api.stripe.finance/v1/process"
          }
        }
      ],
      "details": {
        "id": "order_12345_pending",
        "displayItems": [
          {
            "label": "Nike Air Max 90 - White",
            "amount": { "currency": "USD", "value": 120.00 }
          },
          {
            "label": "Shipping",
            "amount": { "currency": "USD", "value": 8.50 }
          },
          {
            "label": "Tax",
            "amount": { "currency": "USD", "value": 10.92 }
          }
        ],
        "total": {
          "label": "Total",
          "amount": { "currency": "USD", "value": 139.42 }
        }
      },
      "options": {
        "requestPayerName": true,
        "requestPayerEmail": true,
        "requestShipping": true
      }
    }
  },
  "timestamp": "2025-11-15T15:30:00Z"
}
```

---

### 11. Merchant Signs CartMandate
**Actor:** Merchant → Merchant Agent

**Merchant Backend:**
```javascript
const cartMandate = { /* from step 10 */ };

// Merchant signs with private key
const signature = await merchantWallet.signMessage(
  JSON.stringify(cartMandate)
);

const signedCartMandate = {
  ...cartMandate,
  merchant_signature: signature,
  merchant_id: "merchant_shoes_store",
  merchant_address: "0xMerchant789..."
};
```

**Signed CartMandate:**
```json
{
  "contents": { /* ... */ },
  "merchant_signature": "0x1a2b3c4d5e6f...",
  "merchant_id": "merchant_shoes_store",
  "merchant_address": "0xMerchant789...",
  "timestamp": "2025-11-15T15:30:00Z"
}
```

---

### 12. Return Signed CartMandate
**Actor:** Merchant Agent → Shopping Agent

**Response:**
```json
{
  "status": "cart_ready",
  "cart_mandate": {
    "contents": {
      "id": "cart_nike_001_xyz",
      "payment_request": {
        "details": {
          "total": {
            "amount": { "currency": "USD", "value": 139.42 }
          }
        }
      }
    },
    "merchant_signature": "0x1a2b3c4d5e6f...",
    "merchant_id": "merchant_shoes_store"
  }
}
```

---

### 13. Request BNPL Quote
**Actor:** Shopping Agent → SOHO Credit (Credentials Provider)

**Shopping Agent Request:**
```http
POST /v1/credit/quote HTTP/1.1
Host: api.soho.finance
Authorization: Bearer soho_agent_token_abc123def456
Content-Type: application/json
```

```json
{
  "amount": 139.42,
  "currency": "USD",
  "merchant_id": "merchant_shoes_store",
  "user_id": "user_123",
  "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
}
```

**SOHO Credit (CP) Response with BNPL Options:**
```json
{
  "validation_status": "approved",
  "available_credit": "4200.00",
  "transaction_amount": "139.42",
  "bnpl_options": [
    {
      "plan_id": "pay_in_full",
      "name": "Pay in Full",
      "installments": 1,
      "amount_per_installment": "139.42",
      "interest_rate": "0.00%",
      "total_amount": "139.42",
      "due_dates": ["2025-12-15"]
    },
    {
      "plan_id": "pay_in_4",
      "name": "Pay in 4",
      "installments": 4,
      "amount_per_installment": "34.86",
      "interest_rate": "0.00%",
      "total_amount": "139.44",
      "due_dates": ["2025-11-15", "2025-11-29", "2025-12-13", "2025-12-27"]
    },
    {
      "plan_id": "pay_in_12",
      "name": "12 Month Plan",
      "installments": 12,
      "amount_per_installment": "12.45",
      "interest_rate": "5.99%",
      "total_amount": "149.40",
      "due_dates": ["2025-12-15", "2026-01-15", "..."]
    }
  ],
  "credit_authorization_token": "soho_auth_xyz789abc123",
  "limits_check": {
    "per_transaction_limit": "1000.00",
    "per_day_remaining": "1860.58",
    "per_month_remaining": "4860.58"
  }
}
```

---

### 14. Present BNPL Options to User
**Actor:** Shopping Agent → User

```
🤖 Shopping Agent: "Choose your payment plan:

Nike Air Max 90 - White       $120.00
Shipping                      $  8.50
Tax                           $ 10.92
─────────────────────────────────────
Total                         $139.42

Payment Options:

1️⃣ Pay in Full - $139.42
   • Due: Dec 15, 2025
   • Interest: 0%

2️⃣ Pay in 4 - $34.86 x 4 payments
   • Due: Nov 15, Nov 29, Dec 13, Dec 27
   • Interest: 0%
   • Total: $139.44

3️⃣ 12 Month Plan - $12.45/month
   • Starting: Dec 15, 2025
   • Interest: 5.99%
   • Total: $149.40

Which payment plan would you like?"
```

---

### 15. User Selects Payment Plan
**Actor:** User → Shopping Agent

```
User: "I'll go with Pay in 4"
```

**Shopping Agent stores selected plan:**
```json
{
  "selected_plan": {
    "plan_id": "pay_in_4",
    "installments": 4,
    "amount_per_installment": "34.86",
    "interest_rate": "0.00%",
    "total_amount": "139.44"
  }
}
```

---

### 16. Present Cart with Selected Plan to User
**Actor:** Shopping Agent → User

```
🤖 Shopping Agent: "Ready to checkout:

Nike Air Max 90 - White       $120.00
Shipping                      $  8.50
Tax                           $ 10.92
─────────────────────────────────────
Total                         $139.42

Payment Plan: Pay in 4 ($34.86 x 4 payments)
First payment today: $34.86
Ship to: 123 Main St, San Francisco, CA 94105

Approve this purchase?"
```
**User initiates approval:**
```
User: "Yes, approve purchase"
```
---

### 17. Request Authorization via SOHO Mobile App
**Actor:** User → Shopping Agent → SOHO Credit → SOHO Mobile App

**Shopping Agent sends authorization request:**
```http
POST /v1/credit/authorize HTTP/1.1
Host: api.soho.finance
Authorization: Bearer soho_agent_token_abc123def456
Content-Type: application/json
```

```json
{
  "user_id": "user_123",
  "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "approval_request": {
    "type": "purchase_authorization",
    "merchant": "Merchant Shoes Store",
    "amount": "139.42",
    "currency": "USD",
    "payment_plan": {
      "plan_id": "pay_in_4",
      "first_payment": "34.86",
      "installments": 4
    },
    "items": [
      {
        "name": "Nike Air Max 90 - White",
        "price": "120.00"
      }
    ]
  }
}
```

**SOHO Credit pushes notification to user's mobile device:**

```
┌─────────────────────────────────────┐
│  📱 SOHO App - Push Notification    │
├─────────────────────────────────────┤
│  Purchase Approval Required         │
│                                     │
│  Merchant Shoes Store               │
│  Amount: $139.42                    │
│  Payment: 4x $34.86                 │
│                                     │
│  Tap to approve                     │
└─────────────────────────────────────┘
```

**User can approve via:**
1. **Push Notification**: Tap the notification to open approval screen
2. **Approvals Menu**: Open SOHO app → Approvals → View pending purchase

**SOHO Mobile App displays approval screen:**

```
┌─────────────────────────────────────┐
│  SOHO Credit - Approve Purchase     │
├─────────────────────────────────────┤
│  Nike Air Max 90 - White            │
│  Total: $139.42                     │
│                                     │
│  Payment Plan: Pay in 4             │
│  First payment: $34.86 (today)      │
│  Remaining: 3x $34.86               │
│                                     │
│  Merchant: Merchant Shoes Store     │
│  Ship to: 123 Main St, SF CA 94105  │
│                                     │
│  ┌─────────────────────────────┐   │
│  │   Approve with Face ID      │   │
│  └─────────────────────────────┘   │
│                                     │
│         [Decline]                   │
└─────────────────────────────────────┘
```

**User authenticates with biometric:**
- Face ID / Touch ID (iOS)
- Fingerprint / Face Unlock (Android)
- Or Device PIN as fallback

**After successful biometric authentication:**
```json
{
  "approval_status": "authorized",
  "attestation": {
    "type": "device_biometric",
    "signature": "0x9f8e7d6c5b4a...",
    "timestamp": "2025-11-15T15:36:00Z",
    "device_id": "iphone_user123"
  }
}
```
---

### 18. Create PaymentMandate
**Actor:** Shopping Agent (Internal Process)

**Shopping Agent creates complete PaymentMandate with attestation:**
```json
{
  "payment_mandate": {
    "payment_details": {
      "cart_mandate_hash": "<SHA256 hash of signed CartMandate>",
      "payment_request_id": "order_12345_pending",
      "merchant_agent_card": {
        "name": "MerchantShoesStore",
        "merchant_id": "merchant_shoes_store"
      },
      "payment_method": {
        "supported_methods": "SOHO_CREDIT",
        "data": {
          "provider": "soho_credit",
          "authorization_token": "soho_auth_xyz789abc123",
          "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
          "payment_plan": {
            "plan_id": "pay_in_4",
            "name": "Pay in 4",
            "installments": 4,
            "amount_per_installment": "34.86",
            "interest_rate": "0.00%",
            "total_amount": "139.44",
            "first_payment_due": "2025-11-15",
            "remaining_payments": [
              {
                "amount": "34.86",
                "due_date": "2025-11-29"
              },
              {
                "amount": "34.86",
                "due_date": "2025-12-13"
              },
              {
                "amount": "34.86",
                "due_date": "2025-12-27"
              }
            ]
          }
        }
      },
      "amount": {
        "currency": "USD",
        "value": 139.42
      },
      "credit_details": {
        "available_credit": "4200.00",
        "credit_limit": "5000.00",
        "outstanding_balance": "800.00"
      },
      "risk_info": {
        "user_agent": "ChatGPT/4.0",
        "session_id": "session_xyz789",
        "device_fingerprint": "fp_mobile_ios_123"
      },
      "transaction_mode": "human_present"
    },
    "attestation": {
      "type": "device_biometric",
      "authentication_method": "face_id",
      "signature": "0x9f8e7d6c5b4a...",
      "timestamp": "2025-11-15T15:36:00Z",
      "device_id": "iphone_user123",
      "device_certificate": {
        "issuer": "Apple",
        "serial": "CERT_APPLE_XYZ",
        "valid_until": "2026-11-15"
      }
    },
    "creation_time": "2025-11-15T15:35:00Z"
  }
}
```

---

### 19. Initiate Purchase with Merchant
**Actor:** Shopping Agent → Merchant Agent

**Shopping Agent sends complete PaymentMandate to Merchant:**
```http
POST /api/v1/purchase HTTP/1.1
Host: merchant-agent.openai.com
Content-Type: application/json
```

```json
{
  "cart_id": "cart_nike_001_xyz",
  "payment_mandate": {
    "payment_details": {
      "cart_mandate_hash": "<SHA256 hash of signed CartMandate>",
      "payment_request_id": "order_12345_pending",
      "merchant_id": "merchant_shoes_store",
      "payment_method": {
        "supported_methods": "SOHO_CREDIT",
        "provider": "soho_credit",
        "authorization_token": "soho_auth_xyz789abc123",
        "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "payment_plan": {
          "plan_id": "pay_in_4",
          "installments": 4,
          "amount_per_installment": "34.86",
          "total_amount": "139.44"
        }
      },
      "amount": 139.42,
      "currency": "USD"
    },
    "attestation": {
      "type": "device_biometric",
      "authentication_method": "face_id",
      "signature": "0x9f8e7d6c5b4a...",
      "timestamp": "2025-11-15T15:36:00Z",
      "device_id": "iphone_user123"
    },
    "transaction_mode": "human_present",
    "creation_time": "2025-11-15T15:35:00Z"
  }
}
```

---

### 20. Forward to SOHO Payment Processor
**Actor:** Merchant Agent → SOHO Payment Facilitator (MPP)

**Merchant Agent forwards PaymentMandate to SOHO:**
```http
POST /v1/process-payment HTTP/1.1
Host: api.soho.finance
X-Merchant-API-Key: merchant_key_abc123
Content-Type: application/json
```

```json
{
  "merchant_id": "merchant_shoes_store",
  "merchant_address": "0xMerchant789...",
  "order_id": "order_12345_pending",
  "amount": 139.42,
  "currency": "USD",
  "payment_mandate": {
    "payment_details": {
      "cart_mandate_hash": "<hash>",
      "payment_request_id": "order_12345_pending",
      "authorization_token": "soho_auth_xyz789abc123",
      "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
      "payment_plan": {
        "plan_id": "pay_in_4",
        "installments": 4,
        "amount_per_installment": "34.86"
      }
    },
    "attestation": {
      "type": "device_biometric",
      "signature": "0x9f8e7d6c5b4a...",
      "timestamp": "2025-11-15T15:36:00Z",
      "device_id": "iphone_user123"
    },
    "transaction_mode": "human_present"
  }
}
```

---

### 21. SOHO Validates Payment Mandate
**Actor:** SOHO (MPP) - Internal Processing

**SOHO validates the PaymentMandate:**
- Verifies attestation signature (Face ID biometric from step 17)
- Confirms authorization token is valid and not expired
- Validates borrower_address matches the authorization
- Checks payment plan details match the quote from step 13
- Verifies merchant is authorized
- Confirms amount matches CartMandate

**Validation successful, ready for on-chain execution**

---

### 22. SOHO Calls spend() on Behalf of Borrower
**Actor:** SOHO (MPP) - Internal Processing

**SOHO processes payment by calling spend() on behalf of the borrower:**

**Step 22a: Extract Borrower Identity from PaymentMandate**
```javascript
// SOHO extracts borrower_address from PaymentMandate (received in step 20)
const paymentMandate = request.payment_mandate;
const borrowerAddress = paymentMandate.payment_details.borrower_address;
// "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"

const merchantAddress = request.merchant_address;
// "0xMerchant789..."

const amount = paymentMandate.payment_details.amount; // 139.42
const paymentPlan = paymentMandate.payment_details.payment_plan; // pay_in_4
```

**Step 22b: Validate Authorization and Attestation**
```javascript
// Verify authorization token from step 17
const authToken = paymentMandate.payment_details.authorization_token;
const isValid = await validateAuthToken(
  authToken,
  borrowerAddress,
  amount
);

if (!isValid) {
  throw new Error("Invalid or expired authorization token");
}

// Verify biometric attestation signature
const attestation = paymentMandate.attestation;
const isAttestationValid = await verifyBiometricSignature(
  attestation.signature,
  attestation.device_id,
  borrowerAddress,
  attestation.timestamp
);

if (!isAttestationValid) {
  throw new Error("Invalid biometric attestation");
}

console.log("Authorization validated for borrower:", borrowerAddress);
```

**Step 22c: Execute spend() on Behalf of Borrower**
```javascript
// SOHO backend (with ADMIN_ROLE) calls Creditor.spend() 
// on behalf of the borrower who authorized via biometric approval
const creditor = new ethers.Contract(CREDITOR_ADDRESS, CREDITOR_ABI, provider);

const tx = await creditor.connect(sohoAdminWallet).spend(
  borrowerAddress,        // 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
  merchantAddress,        // 0xMerchant789...
  ethers.utils.parseUnits("139.42", 6) // amount in USDC (6 decimals)
);

console.log("Submitted transaction:", tx.hash);

// Wait for blockchain confirmation
const receipt = await tx.wait();

console.log("✅ Transaction confirmed!");
console.log("Transaction Hash:", receipt.transactionHash);
console.log("Block Number:", receipt.blockNumber);
console.log("Gas Used:", receipt.gasUsed.toString());

// Extract Spent event from receipt
const spendEvent = receipt.events.find(e => e.event === "Spent");
```

**Note:** SOHO acts as a **trusted intermediary** with ADMIN_ROLE to execute `spend()` on behalf of the borrower. The borrower has pre-authorized this action through:
1. OAuth authorization with spending limits (Authentication step)
2. BNPL plan selection (step 15)
3. Biometric approval in SOHO mobile app (step 17)
4. Device attestation signature (step 17)

---

### 23. SOHO Stores Purchase Record with Payment Plan
**Actor:** SOHO (MPP) - Internal Processing

**SOHO stores the purchase with payment plan details in database:**

```json
{
  "purchase_id": "purchase_12345",
  "user_id": "user_123",
  "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "merchant": "merchant_shoes_store",
  "order_id": "order_12345_pending",
  "purchase_details": {
    "product": "Nike Air Max 90 - White",
    "total_amount": 139.42,
    "currency": "USD",
    "purchase_date": "2025-11-15T15:37:00Z"
  },
  "payment_plan": {
    "plan_type": "Pay in 4",
    "total_installments": 4,
    "installment_amount": 34.86,
    "interest_rate": 0,
    "total_amount": 139.44
  },
  "installment_schedule": [
    {
      "installment_number": 1,
      "amount": 34.86,
      "due_date": "2025-11-15",
      "status": "paid",
      "paid_date": "2025-11-15",
      "transaction_hash": "0xabc123def456789..."
    },
    {
      "installment_number": 2,
      "amount": 34.86,
      "due_date": "2025-11-29",
      "status": "pending",
      "paid_date": null,
      "transaction_hash": null
    },
    {
      "installment_number": 3,
      "amount": 34.86,
      "due_date": "2025-12-13",
      "status": "pending",
      "paid_date": null,
      "transaction_hash": null
    },
    {
      "installment_number": 4,
      "amount": 34.86,
      "due_date": "2025-12-27",
      "status": "pending",
      "paid_date": null,
      "transaction_hash": null
    }
  ],
  "payment_tracking": {
    "total_paid": 34.86,
    "remaining_balance": 104.58,
    "payments_made": 1,
    "total_payments": 4,
    "next_payment_due": "2025-11-29",
    "status": "active"
  },
  "blockchain": {
    "network": "Base",
    "initial_transaction": "0xabc123def456789...",
    "block_number": 12345678,
    "contract_address": "0xCreditor789..."
  }
}
```

---

### 24. SOHO Creates Payment Receipt
**Actor:** SOHO (MPP) - Internal Processing

**Payment Receipt:**

```json
{
  "payment_id": "soho_pay_abc123",
  "purchase_id": "purchase_12345",
  "status": "completed",
  "payment_type": "on_chain_credit",
  "timestamp": "2025-11-15T15:37:05Z",
  "blockchain": {
    "network": "Base",
    "transaction_hash": "0xabc123def456789...",
    "block_number": 12345678,
    "contract_address": "0xCreditor789...",
    "gas_used": 185432
  },
  "transaction_details": {
    "borrower": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "merchant": "0xMerchant789...",
    "amount": 139.42,
    "currency": "USDC",
    "credit_tokens_minted": 139.42
  },
  "payment_plan": {
    "plan_type": "Pay in 4",
    "first_payment": 34.86,
    "first_payment_status": "paid_today",
    "total_installments": 4,
    "remaining_payments": 3,
    "next_due_date": "2025-11-29"
  },
  "credit_profile": {
    "previous_outstanding_debt": 860.58,
    "new_outstanding_debt": 1000.00,
    "available_credit": 4000.00,
    "credit_limit": 5000.00
  }
}
```

---

### 25. SOHO Returns Receipt to Shopping Agent
**Actor:** SOHO (MPP) → Shopping Agent

**SOHO returns payment receipt:**
- Status: Payment Successful
- Payment ID: soho_pay_abc123
- Purchase ID: purchase_12345
- Transaction Hash: 0xabc123def456789...
- Block Number: 12345678
- Amount: 139.42 USDC
- Credit Tokens Minted: 139.42
- Order ID: order_12345_pending

---

### 26. Shopping Agent Forwards Receipt to Merchant
**Actor:** Shopping Agent → Merchant Agent

**Shopping Agent forwards payment receipt to merchant:**
- Order ID: order_12345_pending
- Payment ID: soho_pay_abc123
- Transaction Hash: 0xabc123def456789...
- Amount: 139.42 USDC
- Status: Confirmed

---

### 27. Merchant Verifies Payment and Confirms Order
**Actor:** Merchant Agent → Merchant

**Merchant verifies payment on blockchain:**
- Checks transaction hash: 0xabc123def456789...
- Confirms SOHOCredit tokens received: 139.42 tokens
- Validates amount matches order: ✅

**Merchant confirms order:**
- Updates order status: `pending` → `confirmed`
- Assigns order number: `ORD-2025-11-15-0001`
- Initiates fulfillment process
- Generates tracking number: 1Z999AA10123456784
- Estimated delivery: Nov 20, 2025

---

### 28. Merchant Returns Confirmation to Shopping Agent
**Actor:** Merchant Agent → Shopping Agent

**Merchant returns order confirmation:**
- Status: Order Confirmed
- Order Number: ORD-2025-11-15-0001
- Product: Nike Air Max 90 - White
- Total: $139.42
- Payment Confirmed: soho_pay_abc123 (TX: 0xabc123...)
- Shipping: UPS - Tracking #1Z999AA10123456784
- Estimated Delivery: Nov 20, 2025

---

### 29. Shopping Agent Notifies User
**Actor:** Shopping Agent → User

```
🎉 Purchase Complete!

✅ Order Confirmed: ORD-2025-11-15-0001

Nike Air Max 90 - White
Total: $139.42

💳 Payment Details:
Payment Plan: Pay in 4 ($34.86 x 4 payments)
First Payment: $34.86 (paid today)
Next Payment: $34.86 on Nov 29, 2025

Paid with SOHO Credit
Transaction: 0xabc123...789
Network: Base
View on Explorer: https://basescan.org/tx/0xabc123...

📊 Credit Status:
Available Credit: $4,000.00
Outstanding Balance: $1,000.00
Credit Limit: $5,000.00

📦 Shipping:
Ship to: 123 Main St, San Francisco, CA 94105
Carrier: UPS
Tracking: 1Z999AA10123456784
Estimated Delivery: Nov 20, 2025

Receipt sent to your email.
```

---

## Payment Flow Summary

**Simple Flow:**
1. User → Shopping Agent: "Find white running shoes"
2. Shopping Agent → Merchant Agent → Merchant: Search products
3. Shopping Agent → User: Show options
4. User → Shopping Agent: Select product
5. Shopping Agent → Merchant Agent → Merchant: Create CartMandate
6. Shopping Agent → SOHO Credit: Get BNPL options
7. Shopping Agent → User: Show payment plans
8. User: Select "Pay in 4" plan
9. User → SOHO Mobile App: Approve with Face ID
10. Shopping Agent: Create PaymentMandate (with attestation)
11. Shopping Agent → Merchant Agent: Send PaymentMandate
12. Merchant Agent → SOHO: Forward for payment
13. **SOHO → Blockchain**: Execute spend() on behalf of borrower
14. **SOHO → Shopping Agent**: Return payment receipt
15. **Shopping Agent → Merchant Agent**: Forward receipt
16. **Merchant → Merchant Agent**: Verify payment & confirm order
17. **Merchant Agent → Shopping Agent**: Return order confirmation
18. **Shopping Agent → User**: Show success with tracking info

---

## Complete Flow Diagram

```
┌──────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│   User   │  │   Shopping   │  │Credentials │  │ Merchant │  │   SOHO   │  │  Creditor    │
│          │  │    Agent     │  │  Provider  │  │  Agent   │  │   (MPP)  │  │  Contract    │
└────┬─────┘  └──────┬───────┘  └─────┬──────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘
     │               │                 │              │             │              │
     │ 1. Request    │                 │              │             │              │
     │──────────────>│                 │              │             │              │
     │               │                 │              │             │              │
     │ 2. Intent     │                 │              │             │              │
     │<──────────────│                 │              │             │              │
     │               │                 │              │             │              │
     │ 3. Confirm    │                 │              │             │              │
     │──────────────>│                 │              │             │              │
     │               │                 │              │             │              │
     │               │ 6. Get Methods  │              │             │              │
     │               │────────────────>│              │             │              │
     │               │<────────────────│              │             │              │
     │               │                 │              │             │              │
     │               │ 7. Search Products             │             │              │
     │               │───────────────────────────────>│             │              │
     │               │<───────────────────────────────│             │              │
     │               │                 │              │             │              │
     │ 8. Present    │                 │              │             │              │
     │<──────────────│                 │              │             │              │
     │               │                 │              │             │              │
     │ 9. Select     │                 │              │             │              │
     │──────────────>│                 │              │             │              │
     │               │                 │              │             │              │
     │               │ 10-12. Create & Sign CartMandate             │              │
     │               │───────────────────────────────>│             │              │
     │               │<───────────────────────────────│             │              │
     │               │                 │              │             │              │
     │               │ 13. Get Options │              │             │              │
     │               │────────────────>│              │             │              │
     │               │<────────────────│              │             │              │
     │               │                 │              │             │              │
     │ 14. Show Cart │                 │              │             │              │
     │<──────────────│                 │              │             │              │
     │               │                 │              │             │              │
     │ 15. Approve   │                 │              │             │              │
     │──────────────>│                 │              │             │              │
     │               │                 │              │             │              │
     │               │ 16. Get Token   │              │             │              │
     │               │────────────────>│              │             │              │
     │               │<────────────────│              │             │              │
     │               │                 │              │             │              │
     │ 18. Approve   │                 │              │             │              │
     │<──────────────│ (Trusted UI)    │              │             │              │
     │               │                 │              │             │              │
     │ 19. Attest    │                 │              │             │              │
     │──────────────>│                 │              │             │              │
     │               │                 │              │             │              │
     │               │ 21. PaymentMandate              │             │              │
     │               │────────────────>│              │             │              │
     │               │                 │              │             │              │
     │               │ 22. Purchase    │              │             │              │
     │               │───────────────────────────────>│             │              │
     │               │                 │              │             │              │
     │               │                 │              │ 23. Process │              │
     │               │                 │              │────────────>│              │
     │               │                 │              │             │              │
     │               │                 │              │             │ 26. Check Credit
     │               │                 │              │             │ 27. Execute  │
     │               │                 │              │             │────────────> │
     │               │                 │              │             │              │
     │               │                 │              │             │ (On-Chain)   │
     │               │                 │              │             │ - Mint tokens│
     │               │                 │              │             │ - Update debt│
     │               │                 │              │             │<─────────────│
     │               │                 │              │             │              │
     │               │                 │              │             │ 31. Receipt  │
     │               │                 │<──────────────────────────│              │
     │               │                 │              │             │              │
     │               │                 │              │ 32. Receipt │              │
     │               │                 │              │<────────────│              │
     │               │                 │              │             │              │
     │               │ 33. Confirmed   │              │             │              │
     │               │<───────────────────────────────│             │              │
     │               │                 │              │             │              │
     │ 34. Success!  │                 │              │             │              │
     │<──────────────│                 │              │             │              │
     │               │                 │              │             │              │
```

---

## Key Benefits of AP2 with SOHO

### 1. **Trust & Accountability**
- **IntentMandate**: Proves user authorized agent to search for shoes
- **CartMandate**: Proves merchant committed to fulfill this exact order
- **PaymentMandate**: Proves payment was authorized with device attestation
- **Blockchain Proof**: Immutable on-chain transaction record
- **Complete Audit Trail**: From intent → cart → payment → fulfillment

### 2. **On-Chain Credit Benefits**
- **Instant Settlement**: No T+2 waiting, immediate on-chain confirmation
- **Lower Fees**: Network gas fees only, no 2.9% + $0.30 card fees
- **Non-Reversible**: No chargeback fraud (blockchain finality)
- **Transparent Credit**: On-chain credit limits and debt tracking
- **Cryptographic Proof**: Transaction hash is irrefutable evidence

### 3. **Privacy by Design**
- **Role Separation**: Shopping Agent never sees payment credentials
- **Credentials Provider**: Manages user authentication securely
- **Merchant**: Receives SOHOCredit tokens, no sensitive user data
- **On-Chain Privacy**: Wallet addresses, not personal information

### 4. **Flexibility**
- **Multiple Credit Sources**: SOHO credit, other BNPL, direct crypto
- **Any Credentials Provider**: Google Wallet, Apple Pay, MetaMask, etc.
- **Blockchain Agnostic**: Works on Base, Ethereum, other EVM chains
- **Stablecoin Settlement**: USDC-based for price stability

### 5. **User Experience**
- **Single Flow**: Works across all merchants and payment types
- **Transparent**: User sees credit status in real-time
- **Fast**: Immediate on-chain settlement, no approval delays
- **Smart Limits**: Automated approval for amounts within limits

---

## SOHO-Specific Features

### As On-Chain Merchant Payment Processor (MPP)

**SOHO On-Chain Credit System:**
```javascript
// SOHO provides on-chain credit via smart contracts
const creditSystem = {
  protocol: "on-chain credit",
  blockchain: "Base (Ethereum L2)",
  creditToken: "SOHOCredit",
  stablecoin: "USDC",
  
  smartContracts: {
    creditor: "Creditor.sol - Credit issuance & management",
    vault: "SOHOVault.sol - Liquidity & yield generation",
    token: "SOHOCredit.sol - ERC20 credit token",
    accessControl: "SOHOAccessControl.sol - Role management"
  }
};

// SOHO settlement
const settlement = {
  merchant_receives: {
    asset: "SOHOCredit tokens",
    timeline: "immediate (on-chain)",
    fees: "network gas fees only"
  },
  merchant_withdrawal: {
    asset: "USDC stablecoin",
    method: "merchantWithdraw()",
    fees: "2.5% withdrawal fee",
    timeline: "immediate"
  }
};
```

### AP2 Integration Benefits

1. **Decentralized Processing**: Smart contracts, no central authority
2. **Blockchain Settlement**: Immediate on-chain finality
3. **Transparent Credit**: All credit operations verifiable on-chain
4. **Low Cost**: No traditional card network fees
5. **Enhanced Security**: Cryptographic proofs, non-reversible transactions
6. **AP2 Compatibility**: Full support for IntentMandate, CartMandate, PaymentMandate

---

## Error Scenarios

### 1. Insufficient Credit
```
Step 27: Smart contract validation fails

Creditor.spend() reverts: "Creditor__InsufficientCredit"

SOHO → Merchant: {
  "status": "declined",
  "reason": "insufficient_credit",
  "error_code": "INSUFFICIENT_CREDIT",
  "credit_info": {
    "available_credit": 50.00,
    "requested_amount": 139.42,
    "shortfall": 89.42
  }
}

Merchant → Shopping Agent: {
  "status": "payment_failed",
  "reason": "insufficient_credit"
}

Shopping Agent → User: {
  "error": "Insufficient SOHO credit. Available: $50.00, Required: $139.42
           Would you like to:
           1. Make a payment to increase your credit
           2. Use a different payment method?"
}
```

### 2. Exceeds Spending Limit (Requires Approval)
```
Step 26c: Amount exceeds per-transaction limit

$600 > $500 (per-transaction limit)

SOHO → Merchant: {
  "status": "pending_approval",
  "approval_id": "appr_xyz789",
  "approval_url": "soho://approve/appr_xyz789",
  "expires_at": "2025-11-15T16:00:00Z"
}

[Push notification sent to user]

User → SOHO App: Approve/Reject

If Approved:
- SOHO executes spend()
- Returns payment receipt

If Rejected:
- SOHO cancels transaction
- Notifies merchant
```

### 3. Blockchain Network Issues
```
Step 27: RPC node timeout or network congestion

SOHO attempts transaction:
Error: "Transaction timeout" or "Gas price too high"

SOHO → SOHO: {
  "retry_strategy": "exponential_backoff",
  "max_retries": 3,
  "gas_price_adjustment": "+10%"
}

If all retries fail:

SOHO → Merchant: {
  "status": "network_error",
  "reason": "blockchain_unavailable",
  "retry_after": 60
}

[SOHO queues transaction for retry]
```

### 4. Global Credit Limit Reached
```
Step 27: Smart contract validation fails

Creditor.spend() reverts: "Creditor__ExceedsMaxSupply"

Reason: Total SOHOCredit supply would exceed 70% of vault TVL

SOHO → Merchant: {
  "status": "declined",
  "reason": "system_limit_reached",
  "error_code": "EXCEEDS_MAX_SUPPLY",
  "message": "SOHO credit limit temporarily reached. Please try again later."
}
```

---

## Settlement & Reconciliation

### On-Chain Settlement (SOHO)

**Immediate Settlement:**
```
Transaction: 2025-11-15 15:37:00 PST

┌─────────────────────────────────────────────────┐
│  On-Chain Credit Transaction                    │
├─────────────────────────────────────────────────┤
│  Borrower: 0xBorrower456...                     │
│  Merchant: 0xMerchant789...                     │
│  Amount: 139.42 USDC                            │
│  SOHOCredit Minted: 139.42 tokens               │
│  Transaction Hash: 0xabc123def456...            │
│  Block Number: 12345678                         │
│  Status: CONFIRMED (3 blocks)                   │
│  Settlement: IMMEDIATE                          │
└─────────────────────────────────────────────────┘

Merchant Balance Update:
┌──────────────────────┬───────────┬─────────────┐
│ Merchant             │ Before    │ After       │
├──────────────────────┼───────────┼─────────────┤
│ merchant_shoes_store │ 0 tokens  │ 139.42 tokens│
│ SOHOCredit Balance   │           │             │
└──────────────────────┴───────────┴─────────────┘

No Settlement Delay: Tokens received instantly on-chain
```

### Merchant Withdrawal (Convert to USDC)

**When merchant wants to withdraw:**
```
Merchant → SOHO: merchantWithdraw(139.42 SOHOCredit)

Smart Contract Process:
1. Burns 139.42 SOHOCredit tokens
2. Calculates fee: 139.42 * 2.5% = $3.49
3. Withdraws from Aave if needed
4. Transfers 135.93 USDC to merchant
5. Sends 3.49 USDC to Treasury

Result:
┌──────────────────────────────────────────┐
│ Merchant Receives: 135.93 USDC           │
│ Protocol Fee: 3.49 USDC (2.5%)           │
│ Timeline: Immediate (same transaction)   │
│ Method: On-chain transfer                │
└──────────────────────────────────────────┘
```

### Daily Reconciliation

```
End of Day: 2025-11-15 23:59:59 PST

┌─────────────────────────────────────────┐
│  SOHO On-Chain Credit Summary           │
├─────────────────────────────────────────┤
│  Total Transactions: 1,234              │
│  Total Credit Issued: 456,789.00 USDC   │
│  SOHOCredit Minted: 456,789.00 tokens   │
│  Total Gas Fees: 42.37 USD              │
│  Active Borrowers: 892                  │
│  Total Outstanding Debt: 1,234,567.89   │
└─────────────────────────────────────────┘

No Daily Settlement Required:
- All transactions settled immediately on-chain
- Merchants hold SOHOCredit tokens
- Withdrawals processed on-demand
- No batching, no T+2 delay
```

---

## Dispute Resolution with AP2

### Chargeback Scenario

**User disputes charge via SOHO App:**
```
User → SOHO App: "I didn't authorize this $139.42 charge"
```

**SOHO reviews transaction with AP2 evidence:**
```json
{
  "dispute_id": "dispute_12345",
  "purchase_id": "purchase_12345",
  "user_claim": "unauthorized_transaction",
  "amount": 139.42,
  "ap2_evidence": {
    "intent_mandate": {
      "user_id": "user_123",
      "natural_language": "Find white running shoes under $150",
      "timestamp": "2025-11-15T15:25:00Z"
    },
    "cart_mandate": {
      "merchant_signed": true,
      "user_approved": true,
      "products": ["Nike Air Max 90 - White"],
      "total": 139.42,
      "timestamp": "2025-11-15T15:30:00Z"
    },
    "payment_mandate": {
      "transaction_mode": "human_present",
      "device_attestation": {
        "type": "face_id",
        "device_id": "device_iphone_abc123",
        "verified": true,
        "timestamp": "2025-11-15T15:36:00Z"
      }
    },
    "fulfillment_proof": {
      "shipped": true,
      "tracking": "1Z999AA10123456784",
      "delivered": "2025-11-19T14:30:00Z",
      "signature": "J. Smith"
    }
  }
}
```

**SOHO reviews evidence:**
```
Evidence Score: STRONG
- ✅ Intent Mandate: User initiated shopping request
- ✅ Cart Mandate: User approved final cart
- ✅ Device Attestation: Face ID verified on user's device
- ✅ Human Present: Not autonomous transaction
- ✅ Fulfillment: Delivered and signed for

Decision: DENY CHARGEBACK
Reason: Strong evidence of authorized transaction
```

---

## On-Chain Chargeback Scenario

**When paid with SOHO Credit (on-chain), chargebacks are handled directly on the blockchain:**

**User disputes transaction or merchant issues refund:**

```json
{
  "dispute_id": "dispute_12345",
  "purchase_id": "purchase_12345",
  "reason": "fraud" | "merchant_refund" | "product_not_received",
  "amount": 139.42
}
```

**SOHO Admin executes on-chain chargeback:**

```solidity
// Admin calls chargeback function with ADMIN_ROLE
Creditor.chargeback(
  borrower: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb,
  merchant: 0xMerchant789...,
  amount: 139.42 USDC
)
```

**On-Chain State Changes:**
- ✅ Burns 139.42 SOHOCredit tokens from merchant
- ✅ Reduces borrower's outstanding debt: $1,000.00 → $860.58
- ✅ Restores borrower's available credit: $4,000.00 → $4,139.42
- ✅ Updates transaction status to `refunded`
- ✅ Emits `Chargeback` event with transaction hash

**Result:** Instant reversal with full blockchain transparency and auditability.

---

## Related Documentation

- [AP2 Protocol Specification](https://ap2-protocol.net/en/specification)
- [A2A Protocol](https://a2aprotocol.ai/)
- [HTTP 402 Payment Flow](./HTTP_402_PAYMENT_FLOW.md)
- [SOHO Credit Architecture](./docs/Architecture.md)
- [Creditor Contract](../src/Creditor.sol)

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2025-11-15 | 1.0 | Initial AP2 flow documentation with SOHO as MPP |
