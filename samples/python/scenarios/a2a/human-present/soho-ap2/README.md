# SOHO Credit Shopping Agent

This example demonstrates the Agent Payments Protocol (AP2) with **SOHO Credit** as the Credentials Provider and Payment Processor.

## Overview

This implementation showcases a complete shopping flow using:
- **SOHO Credit**: On-chain credit system with flexible BNPL (Buy Now Pay Later) plans
- **AP2 Protocol**: IntentMandate → CartMandate → PaymentMandate flow
- **Biometric Authentication**: Simulated Face ID/Touch ID approval via SOHO mobile app
- **Blockchain Settlement**: On-chain credit transactions via Creditor.sol on Base

## SOHO Credit (AP2) Shopping Flow - Implementation Status

1. User Prompt - DONE
2. Sign Intent Mandate - DONE
3. Find Products - DONE
4. Sign Cart Mandate - DONE
5. Get Credentials Provider: SOHO Credit - DONE
6. Get Shipping Address - DONE
7. Update Cart Mandate - DONE
8. Get BNPL Options - DONE
9. Select BNPL Plan - DONE
10. Request Biometric Approval - DONE
11. Create Payment Credential Token - DONE
12. Sign Payment Mandate - DONE
13. Complete Purchase - NOT YET DONE



## Key Features

### 1. **BNPL Payment Plans**
Users can choose from multiple payment options:
- **Pay in Full**: Single payment, 0% interest
- **Pay in 4**: Four equal installments, 0% interest
- **12 Month Plan**: Monthly payments, 5.99% interest

### 2. **Biometric Approval**
- Simulates push notification to SOHO mobile app
- User approves purchase with Face ID/Touch ID
- Device attestation signature attached to payment mandate

### 3. **On-Chain Credit**
- Instant settlement on Base blockchain
- No traditional card network fees
- Non-reversible transactions (no chargeback fraud)
- Transparent credit limits and debt tracking

## Architecture

```
┌──────────┐  ┌────────────────┐  ┌──────────────────┐  ┌──────────┐
│   User   │  │ SOHO Shopping  │  │ SOHO Credentials │  │ Merchant │
│          │  │     Agent      │  │    Provider      │  │  Agent   │
└────┬─────┘  └───────┬────────┘  └────────┬─────────┘  └────┬─────┘
     │                │                     │                 │
     │ "Buy shoes"    │                     │                 │
     │───────────────>│                     │                 │
     │                │                     │                 │
     │                │  Search products    │                 │
     │                │─────────────────────────────────────> │
     │                │                     │                 │
     │                │  Get shipping addr  │                 │
     │                │────────────────────>│                 │
     │                │                     │                 │
     │                │  Get BNPL options   │                 │
     │                │────────────────────>│                 │
     │                │                     │                 │
     │ Select plan    │                     │                 │
     │───────────────>│                     │                 │
     │                │                     │                 │
     │                │  Request biometric  │                 │
     │                │────────────────────>│                 │
     │                │                     │                 │
     │ [Face ID] ✓    │  Attestation        │                 │
     │───────────────>│<────────────────────│                 │
     │                │                     │                 │
     │ Confirm        │  Initiate payment   │                 │
     │───────────────>│─────────────────────────────────────> │
     │                │                     │                 │
     │ Receipt ✓      │                     │                 │
     │<───────────────│                     │                 │
```

## Agents

### 1. **SOHO Shopping Agent** (Port: ADK Web UI)
Main agent that coordinates the shopping experience:
- Collects user intent and product preferences
- Presents BNPL payment plan options
- Manages biometric approval workflow
- Creates payment mandate with SOHO Credit details
- Initiates payment with merchant

**Tools:**
- `get_bnpl_options` - Fetch payment plan options from SOHO
- `select_payment_plan` - Store user's selected plan
- `request_biometric_approval` - Request Face ID/Touch ID approval
- `update_cart` - Update cart with shipping address
- `create_soho_payment_mandate` - Create payment mandate with SOHO Credit
- `attach_biometric_attestation` - Attach biometric signature
- `initiate_payment` - Send payment to merchant

**Sub-agents:**
- `shopper` - Searches for products matching user intent
- `shipping_address_collector` - Gets shipping address from SOHO
- `payment_method_collector` - Gets payment credentials from SOHO

### 2. **SOHO Credentials Provider** (Port: 8005)
Manages user authentication, credit, and payment credentials:
- Credit status and availability checks
- BNPL payment plan generation
- Shipping address management
- Biometric approval simulation
- Payment credential tokens

**Functions:**
- `get_shipping_address` - Returns user's default shipping address
- `get_credit_status` - Returns credit limits and availability
- `get_bnpl_quote` - Generates payment plan options
- `request_biometric_approval` - Simulates mobile app approval
- `search_payment_methods` - Returns SOHO Credit payment methods
- `create_payment_credential_token` - Creates payment token

### 3. **Merchant Agent** (Port: 8001)
Represents the merchant's backend:
- Product catalog and search
- Cart creation and management
- CartMandate signing
- Payment processing (forwards to SOHO)
- Order fulfillment

## Setup

### 0. Prerequisites

- Python 3.10+
- `uv` package manager
- Google API key (for Gemini LLM) from https://aistudio.google.com

### 1. Install Dependencies

From the repository root:

```bash
cd samples/python
uv sync
```

### 2. Configure Environment

Go back to the repository root,

Create a `.env` file:

```bash
# Google API Key for Gemini LLM
GOOGLE_API_KEY=your_api_key_here

# Or use Vertex AI with Application Default Credentials
# GOOGLE_GENAI_USE_VERTEXAI=true

# Gemini model for LLM tool selection and agent processing
# Options: gemini-3-pro-previw, gemini-2.5-pro (powerful), gemini-2.5-flash, gemini-2.0-flash-exp (fast),   gemini-1.5-pro, gemini-1.5-flash
GEMINI_MODEL=gemini-2.5-pro

# SOHO API URL
SOHO_API_URL=https://api.sohopay.xyz
```

### 3. Run the Example

from the root i.e `/AP2`

```bash
samples/python/scenarios/a2a/human-present/soho-ap2/run.sh
```

This will:
1. Start the Merchant Agent (port 8001)
2. Start the SOHO Credentials Provider (port 8005)
3. Launch the SOHO Shopping Agent web UI
4. Open your browser to http://localhost:8080

## Usage

### Example Conversation

**You:** "I want to buy white running shoes under $150"

**Agent:** Shows search results from merchant

**You:** "I'll take the Nike Air Max 90"

**Agent:** Shows cart with shipping address from SOHO

**Agent:** Shows BNPL payment plan options:
```
1️⃣ Pay in Full - $139.42
   • Due: Dec 15, 2025
   • Interest: 0%

2️⃣ Pay in 4 - $34.86 x 4 payments
   • Due: Nov 15, Nov 29, Dec 13, Dec 27
   • Interest: 0%

3️⃣ 12 Month Plan - $12.45/month
   • Starting: Dec 15, 2025
   • Interest: 5.99%
```

**You:** "I'll go with Pay in 4"

**Agent:** Requests biometric approval (simulated)

**You:** "Approve purchase"

**Agent:** Shows order confirmation with:
- Order number
- Product details
- Payment plan schedule
- Blockchain transaction hash
- Credit status update
- Shipping tracking

## Mock Data

The SOHO Credentials Provider uses mock user data:

```python
{
  "user_id": "user_123",
  "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "credit_profile": {
    "credit_limit": 5000.00,
    "available_credit": 4139.42,
    "outstanding_debt": 860.58
  },
  "shipping_addresses": [
    {
      "street": "123 Main St",
      "city": "San Francisco",
      "state": "CA",
      "zip": "94105"
    }
  ]
}
```

## BNPL Algorithm

The credentials provider generates payment plans dynamically:

```python
# Pay in 4
installment = total_amount / 4
due_dates = [today, today+14, today+28, today+42]

# 12 Month Plan
monthly_payment = (total_amount * 1.0599) / 12
due_dates = [today+30*i for i in range(1, 13)]
```

## Biometric Approval Flow

1. Shopping Agent requests approval
2. SOHO sends push notification (simulated)
3. User authenticates with Face ID/Touch ID (simulated)
4. SOHO returns attestation signature:
   ```json
   {
     "type": "device_biometric",
     "authentication_method": "face_id",
     "signature": "0x9f8e7d6c...",
     "timestamp": "2025-11-15T15:36:00Z",
     "device_id": "iphone_user123"
   }
   ```
5. Attestation attached to PaymentMandate
6. Merchant verifies attestation before processing

## Payment Mandate Structure

```json
{
  "payment_mandate_contents": {
    "payment_mandate_id": "abc123...",
    "payment_response": {
      "method_name": "SOHO_CREDIT",
      "details": {
        "authorization_token": "soho_auth_xyz789...",
        "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "payment_plan": {
          "plan_id": "pay_in_4",
          "installments": 4,
          "amount_per_installment": 34.86
        }
      }
    }
  },
  "user_authorization": {
    "type": "device_biometric",
    "signature": "0x9f8e7d6c..."
  }
}
```

## Stopping the Example

Press `Ctrl+C` in the terminal. The script will automatically clean up all background processes.

## Logs

Log files are stored in `.logs/` directory:
- `merchant_agent.log` - Merchant agent logs
- `soho_credentials_provider.log` - SOHO credentials provider logs

## Troubleshooting

### Missing GOOGLE_API_KEY
```
Error: Please set your GOOGLE_API_KEY environment variable
```
**Solution:** Add `GOOGLE_API_KEY=your_key` to `.env` file in repository root

### Port Already in Use
```
Error: Address already in use
```
**Solution:** Kill processes on ports 8001, 8005, or 8080:
```bash
lsof -ti:8001,8005,8080 | xargs kill -9
```

### Agent Not Responding
**Solution:** Check log files in `.logs/` directory for errors

## Production Considerations

This is a demo implementation. For production:

1. **Replace mock data** with real database queries
2. **Implement actual biometric** approval via mobile SDK
3. **Add smart contract integration** for on-chain settlement
4. **Implement proper cryptographic** hashing and signing
5. **Add comprehensive error** handling and retry logic
6. **Implement rate limiting** and fraud detection
7. **Add transaction monitoring** and reconciliation
8. **Secure API endpoints** with proper authentication

## Related Documentation

- [AP2 Payment Flow](../../../../docs/AP2_PAYMENT_FLOW.md)
- [AP2 Specification](https://ap2-protocol.net)
- [A2A Protocol](https://a2aprotocol.ai)
- [SOHO Credit Documentation](../../../../docs/Architecture.md)

## License

Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0
