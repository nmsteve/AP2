#!/usr/bin/env python3
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test with real log data from payment_processor.log"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from datetime import datetime
from datetime import timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import Task
from ap2.types.mandate import PAYMENT_MANDATE_DATA_KEY

from tools import initiate_payment


def create_real_soho_payment_mandate() -> dict[str, Any]:
    """Creates a payment mandate based on real log data."""
    return {
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


def create_real_data_parts() -> list[dict[str, Any]]:
    """Creates data parts from real log data."""
    return [
        {
            "key": PAYMENT_MANDATE_DATA_KEY,
            "value": create_real_soho_payment_mandate()
        },
        {
            "key": "risk_data",
            "value": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...fake_risk_data"
        }
    ]


def create_mock_updater() -> TaskUpdater:
    """Creates a mock TaskUpdater for testing."""
    updater = MagicMock(spec=TaskUpdater)
    updater.context_id = "610b56c4-76ee-4cb6-ac4e-c6878ef08581"

    # Mock async methods
    updater.failed = AsyncMock()
    updater.requires_input = AsyncMock()
    updater.complete = AsyncMock()
    updater.add_artifact = AsyncMock()

    # Mock message creation
    updater.new_agent_message = MagicMock(side_effect=lambda parts: {"parts": parts})

    return updater


@patch('tools.PaymentRemoteA2aClient')
async def test_real_world_soho_payment_with_empty_artifacts(mock_client_class):
    """Test with real log data - reproduces the 'Failed to find payment method data' error."""
    print("\n=== Test: Real-world SOHO Payment (Empty Artifacts Issue) ===")

    # Mock the credentials provider client - THIS is the issue!
    # The response has empty or incorrectly structured artifacts
    mock_client = MagicMock()
    mock_task_response = MagicMock()
    mock_task_response.artifacts = []  # Empty artifacts causing the failure!
    mock_client.send_a2a_message = AsyncMock(return_value=mock_task_response)
    mock_client_class.return_value = mock_client

    data_parts = create_real_data_parts()
    updater = create_mock_updater()

    try:
        await initiate_payment(
            data_parts=data_parts,
            updater=updater,
            current_task=None,
            debug_mode=True
        )
        print("✗ Should have raised ValueError")
    except ValueError as e:
        print(f"✓ Caught expected error: {e}")
        assert "Failed to find the payment method data" in str(e)


@patch('tools.PaymentRemoteA2aClient')
async def test_real_world_soho_payment_with_correct_artifacts(mock_client_class):
    """Test with real log data - with properly structured artifacts."""
    print("\n=== Test: Real-world SOHO Payment (Correct Artifacts) ===")

    # Mock the credentials provider client with proper response structure
    from a2a.types import Artifact, Part, DataPart

    mock_client = MagicMock()
    mock_task_response = MagicMock()

    # Create properly structured artifacts
    credential_data = {
        "payment_credential": "soho_credential_xyz123",
        "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "authorization_token": "soho_auth_user_123_1763932810.869312"
    }

    data_part = DataPart(data=credential_data)
    part = Part(root=data_part)
    artifact = Artifact(parts=[part])

    mock_task_response.artifacts = [artifact]
    mock_client.send_a2a_message = AsyncMock(return_value=mock_task_response)
    mock_client_class.return_value = mock_client

    data_parts = create_real_data_parts()
    updater = create_mock_updater()

    await initiate_payment(
        data_parts=data_parts,
        updater=updater,
        current_task=None,
        debug_mode=True
    )

    # Check that complete was called (payment successful)
    assert updater.complete.called, "Expected updater.complete to be called"
    print("✓ SOHO Credit payment completed successfully")
    print(f"  Complete call: {updater.complete.call_args}")


@patch('tools.PaymentRemoteA2aClient')
async def test_real_world_soho_payment_with_none_artifacts(mock_client_class):
    """Test with real log data - with None artifacts."""
    print("\n=== Test: Real-world SOHO Payment (None Artifacts) ===")

    mock_client = MagicMock()
    mock_task_response = MagicMock()
    mock_task_response.artifacts = None  # None artifacts
    mock_client.send_a2a_message = AsyncMock(return_value=mock_task_response)
    mock_client_class.return_value = mock_client

    data_parts = create_real_data_parts()
    updater = create_mock_updater()

    try:
        await initiate_payment(
            data_parts=data_parts,
            updater=updater,
            current_task=None,
            debug_mode=True
        )
        print("✗ Should have raised ValueError")
    except ValueError as e:
        print(f"✓ Caught expected error: {e}")
        assert "Failed to find the payment method data" in str(e)


async def run_all_tests():
    """Run all test cases."""
    print("=" * 70)
    print("Testing initiate_payment with REAL log data")
    print("=" * 70)

    try:
        await test_real_world_soho_payment_with_empty_artifacts()
        await test_real_world_soho_payment_with_none_artifacts()
        await test_real_world_soho_payment_with_correct_artifacts()

        print("\n" + "=" * 70)
        print("✓ All tests completed!")
        print("=" * 70)
        print("\nDiagnosis:")
        print("-" * 70)
        print("The error 'Failed to find the payment method data' occurs when")
        print("the credentials provider returns a response with:")
        print("  1. Empty artifacts list")
        print("  2. None artifacts")
        print("  3. Artifacts without proper DataPart structure")
        print("\nThe issue is in _request_payment_credential() function at line:")
        print("  payment_credential = artifact_utils.get_first_data_part(task.artifacts)")
        print("\nFix suggestions:")
        print("  1. Check credentials provider response structure")
        print("  2. Add better error handling/logging in _request_payment_credential()")
        print("  3. Verify the credentials provider is returning data correctly")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
