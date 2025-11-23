#!/usr/bin/env python3
"""Simple standalone test to reproduce the log error with mock data only."""

import json


def test_real_soho_payment_mandate():
    """Test that shows the exact payment mandate structure from the log."""

    print("=" * 70)
    print("REAL PAYMENT MANDATE DATA FROM LOG")
    print("=" * 70)

    # This is the exact data from your log
    payment_mandate = {
        "payment_mandate_contents": {
            "payment_mandate_id": "95b7b096716e4f74a828e04cda0d410c",
            "payment_details_id": "order_3",
            "payment_details_total": {
                "label": "Total",
                "amount": {
                    "currency": "GBP",
                    "value": 48.5
                },
                "pending": None,
                "refund_period": 30
            },
            "payment_response": {
                "request_id": "order_3",
                "method_name": "SOHO_CREDIT",
                "details": {
                    "token": {
                        "value": "soho_token_0_user@example.com",
                        "raw": {
                            "payment_credential_token": {
                                "type": "soho_credit",
                                "value": "soho_token_0_user@example.com",
                                "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
                                "plan_id": None
                            }
                        },
                        "provider_url": "http://localhost:8005/a2a/soho_credentials_provider"
                    },
                    "authorization_token": "soho_auth_user_123_1763932810.869312",
                    "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
                    "payment_plan": {
                        "plan_id": "pay_in_4",
                        "name": "Pay in 4",
                        "installments": 4,
                        "amount_per_installment": 12.12,
                        "interest_rate": "0.00%",
                        "total_amount": 48.48,
                        "due_dates": [
                            "2025-11-24",
                            "2025-12-08",
                            "2025-12-22",
                            "2026-01-05"
                        ]
                    }
                },
                "shipping_address": {
                    "city": "San Francisco",
                    "country": "US",
                    "dependent_locality": None,
                    "organization": "",
                    "phone_number": None,
                    "postal_code": None,
                    "recipient": "John Smith",
                    "region": "CA",
                    "sorting_code": None,
                    "address_line": []
                },
                "shipping_option": None,
                "payer_name": None,
                "payer_email": "user@example.com",
                "payer_phone": None
            },
            "merchant_agent": "Generic Merchant",
            "timestamp": "2025-11-23T21:20:53.910244+00:00"
        },
        "user_authorization": '{"type": "device_biometric", "authentication_method": "face_id", "signature": "0x9f8e7d6c5b4a_user_123", "timestamp": "2025-11-24T00:20:33.943635", "device_id": "iphone_user_123", "device_certificate": {"issuer": "Apple", "serial": "CERT_APPLE_XYZ", "valid_until": "2026-11-15"}}'
    }

    print("\n✓ Payment Mandate Structure:")
    print(json.dumps(payment_mandate, indent=2))

    print("\n" + "=" * 70)
    print("DATA PARTS FOR initiate_payment()")
    print("=" * 70)

    data_parts = [
        {
            "key": "ap2.mandates.PaymentMandate",
            "value": payment_mandate
        },
        {
            "key": "risk_data",
            "value": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...fake_risk_data"
        }
    ]

    print("\ndata_parts structure:")
    print(f"  Length: {len(data_parts)}")
    for i, part in enumerate(data_parts):
        print(f"  [{i}] key: {part['key']}")
        if part['key'] == 'ap2.mandates.PaymentMandate':
            print(f"       method_name: {part['value']['payment_mandate_contents']['payment_response']['method_name']}")
            print(f"       provider_url: {part['value']['payment_mandate_contents']['payment_response']['details']['token']['provider_url']}")
            print(f"       amount: {part['value']['payment_mandate_contents']['payment_details_total']['amount']}")

    print("\n" + "=" * 70)
    print("ERROR ANALYSIS")
    print("=" * 70)

    print("""
From the log, the error occurs at:
  Line: "An error occurred: Failed to find the payment method data."

This happens in the _request_payment_credential() function when:
  payment_credential = artifact_utils.get_first_data_part(task.artifacts)

Root Cause:
  The credentials provider (http://localhost:8005/a2a/soho_credentials_provider)
  is returning a response where task.artifacts is empty or None.

Expected Flow:
  1. initiate_payment() receives payment mandate with SOHO_CREDIT method
  2. Bypasses OTP challenge (line 95-98 in tools.py)
  3. Calls _complete_payment()
  4. Calls _request_payment_credential() to get credentials from provider
  5. Provider should return task with artifacts containing credential data
  6. **FAILS HERE** - artifacts are empty/None

To Test This Function:
  You need to mock the PaymentRemoteA2aClient to return a task with:
  - Properly structured artifacts list
  - At least one artifact containing a DataPart
  - The DataPart should have the credential data

Example Mock Response Structure:
  task = Mock()
  task.artifacts = [
    Artifact(parts=[
      Part(root=DataPart(data={
        "credential": "soho_credential_xyz",
        "token": "soho_token_0_user@example.com"
      }))
    ])
  ]
    """)

    print("\n" + "=" * 70)
    print("QUICK TEST COMMAND")
    print("=" * 70)
    print("""
To test with this exact data:

1. Copy the data_parts structure above
2. Mock TaskUpdater and PaymentRemoteA2aClient
3. Ensure the mocked client returns artifacts with DataPart
4. Call: await initiate_payment(data_parts, updater, None, True)

Key parameters:
  - data_parts: list[dict[str, Any]] (shown above)
  - updater: TaskUpdater (mock with context_id, failed(), complete(), etc.)
  - current_task: None (first call, no existing task)
  - debug_mode: True
    """)


if __name__ == "__main__":
    test_real_soho_payment_mandate()
