# Testing with Real Log Data

Based on the error in `payment_processor.log`, this guide shows how to test the `initiate_payment` function with the exact data that caused the failure.

## The Error

```
An error occurred: Failed to find the payment method data.
```

## Root Cause

The error occurs in `_request_payment_credential()` at this line:
```python
payment_credential = artifact_utils.get_first_data_part(task.artifacts)
```

The credentials provider returns a response where `task.artifacts` is empty or `None`, causing the function to fail.

## Real Data from Log

### Payment Mandate (SOHO_CREDIT)
```python
{
    "payment_mandate_contents": {
        "payment_mandate_id": "95b7b096716e4f74a828e04cda0d410c",
        "payment_details_id": "order_3",
        "payment_details_total": {
            "label": "Total",
            "amount": {"currency": "GBP", "value": 48.5},
            "refund_period": 30
        },
        "payment_response": {
            "method_name": "SOHO_CREDIT",  # This bypasses OTP
            "details": {
                "token": {
                    "value": "soho_token_0_user@example.com",
                    "provider_url": "http://localhost:8005/a2a/soho_credentials_provider"
                },
                "authorization_token": "soho_auth_user_123_1763932810.869312",
                "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
                "payment_plan": {
                    "plan_id": "pay_in_4",
                    "installments": 4,
                    "amount_per_installment": 12.12
                }
            }
        }
    }
}
```

### Data Parts Structure
```python
data_parts = [
    {
        "key": "ap2.mandates.PaymentMandate",
        "value": <payment_mandate>
    },
    {
        "key": "risk_data",
        "value": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...fake_risk_data"
    }
]
```

## Testing the Function

### Option 1: Use test_real_log_data.py (Requires dependencies)

This test reproduces the exact error:

```bash
python3 test_real_log_data.py
```

The test shows three scenarios:
1. **Empty artifacts** - Reproduces the error
2. **None artifacts** - Reproduces the error
3. **Correct artifacts** - Shows the expected behavior

### Option 2: Manual Testing

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Mock the updater
updater = MagicMock()
updater.context_id = "610b56c4-76ee-4cb6-ac4e-c6878ef08581"
updater.failed = AsyncMock()
updater.complete = AsyncMock()
updater.add_artifact = AsyncMock()
updater.new_agent_message = lambda parts: {"parts": parts}

# Create data_parts with real log data
data_parts = [
    {
        "key": "ap2.mandates.PaymentMandate",
        "value": {
            "payment_mandate_contents": {
                # ... use full structure from above
                "payment_response": {
                    "method_name": "SOHO_CREDIT",
                    # ...
                }
            }
        }
    }
]

# Mock the credentials provider (this is where it fails!)
with patch('tools.PaymentRemoteA2aClient') as mock_client_class:
    mock_client = MagicMock()
    mock_task = MagicMock()

    # REPRODUCES ERROR: Empty artifacts
    mock_task.artifacts = []

    # OR FIX: Proper artifacts
    # from a2a.types import Artifact, Part, DataPart
    # mock_task.artifacts = [
    #     Artifact(parts=[
    #         Part(root=DataPart(data={
    #             "credential": "soho_credential_xyz"
    #         }))
    #     ])
    # ]

    mock_client.send_a2a_message = AsyncMock(return_value=mock_task)
    mock_client_class.return_value = mock_client

    # Run the test
    await initiate_payment(data_parts, updater, None, True)
```

## Flow Analysis

1. **Request received** → `initiate_payment()` called
2. **Payment mandate found** → SOHO_CREDIT method detected
3. **Skip OTP** → Goes directly to `_complete_payment()` (line 95-98)
4. **Get credentials provider** → Connects to `http://localhost:8005/a2a/soho_credentials_provider`
5. **Request credentials** → Calls `_request_payment_credential()`
6. **Send A2A message** → Requests credentials from provider
7. **❌ ERROR HERE** → Provider returns empty artifacts
8. **get_first_data_part()** → Fails to find data in empty artifacts
9. **Raises ValueError** → "Failed to find the payment method data"

## Key Files

- **`tools.py`** - Contains `initiate_payment()` function
- **`test_tools.py`** - Generic test cases with mock data
- **`test_real_log_data.py`** - Tests with exact log data
- **`analyze_log_error.py`** - Standalone script showing the data structure

## Debug Suggestions

1. **Check credentials provider logs** at `http://localhost:8005`
2. **Verify response structure** - Should include artifacts with DataPart
3. **Add logging** in `_request_payment_credential()`:
   ```python
   logging.info(f"Received artifacts: {task.artifacts}")
   if task.artifacts:
       for artifact in task.artifacts:
           logging.info(f"Artifact parts: {artifact.parts}")
   ```

4. **Test credentials provider directly**:
   ```bash
   curl http://localhost:8005/a2a/soho_credentials_provider/.well-known/agent-card.json
   ```

## Expected Fix

The credentials provider should return:
```python
{
    "artifacts": [
        {
            "parts": [
                {
                    "root": {
                        "data": {
                            "credential": "...",
                            "token": "..."
                        }
                    }
                }
            ]
        }
    ]
}
```

Not:
```python
{
    "artifacts": []  # ❌ Empty
}
```

Or:
```python
{
    "artifacts": None  # ❌ None
}
```
