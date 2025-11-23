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

"""Test script for the initiate_payment function with mock data."""

import asyncio
from datetime import datetime
from datetime import timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import Task
from ap2.types.mandate import PAYMENT_MANDATE_DATA_KEY

from tools import initiate_payment


def create_mock_payment_mandate() -> dict[str, Any]:
    """Creates a mock payment mandate for testing."""
    return {
        "payment_mandate_contents": {
            "payment_mandate_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payment_details_total": {
                "amount": "100.00",
                "currency": "USD"
            },
            "payment_response": {
                "method_name": "CARD",  # Use "CARD" for OTP flow or "SOHO_CREDIT" to skip OTP
                "details": {
                    "token": {
                        "provider_url": "http://localhost:8002",
                        "token_value": "test_token_12345"
                    },
                    "last4": "1234",
                    "brand": "Visa"
                }
            },
            "merchant_reference": "ORDER-12345"
        }
    }


def create_mock_data_parts(
    include_mandate: bool = True,
    include_challenge_response: bool = False,
    challenge_value: str = "123"
) -> list[dict[str, Any]]:
    """Creates mock data_parts for testing.

    Args:
        include_mandate: Whether to include a payment mandate
        include_challenge_response: Whether to include a challenge response
        challenge_value: The value of the challenge response (default "123" is valid)

    Returns:
        List of data parts for testing
    """
    data_parts = []

    if include_mandate:
        data_parts.append({
            "key": PAYMENT_MANDATE_DATA_KEY,
            "value": create_mock_payment_mandate()
        })

    if include_challenge_response:
        data_parts.append({
            "key": "challenge_response",
            "value": challenge_value
        })

    return data_parts


def create_mock_updater() -> TaskUpdater:
    """Creates a mock TaskUpdater for testing."""
    updater = MagicMock(spec=TaskUpdater)
    updater.context_id = str(uuid.uuid4())

    # Mock async methods
    updater.failed = AsyncMock()
    updater.requires_input = AsyncMock()
    updater.complete = AsyncMock()
    updater.add_artifact = AsyncMock()

    # Mock message creation
    updater.new_agent_message = MagicMock(side_effect=lambda parts: {"parts": parts})

    return updater


def create_mock_task(state: str = "input_required") -> Task:
    """Creates a mock Task for testing.

    Args:
        state: The task state (e.g., "input_required", "completed")

    Returns:
        A mock Task object
    """
    task = MagicMock(spec=Task)
    task.status = MagicMock()
    task.status.state = state
    task.artifacts = []
    return task


async def test_initiate_payment_missing_mandate():
    """Test initiate_payment with missing payment mandate."""
    print("\n=== Test 1: Missing Payment Mandate ===")

    data_parts = []  # Empty data parts
    updater = create_mock_updater()

    await initiate_payment(
        data_parts=data_parts,
        updater=updater,
        current_task=None,
        debug_mode=True
    )

    # Check that failed was called
    assert updater.failed.called, "Expected updater.failed to be called"
    print("✓ Failed correctly with missing mandate")
    print(f"  Failed call: {updater.failed.call_args}")


async def test_initiate_payment_card_first_call():
    """Test initiate_payment with card payment (first call, should raise challenge)."""
    print("\n=== Test 2: Card Payment - First Call (Challenge) ===")

    data_parts = create_mock_data_parts(include_mandate=True)
    updater = create_mock_updater()

    await initiate_payment(
        data_parts=data_parts,
        updater=updater,
        current_task=None,  # First call, no current task
        debug_mode=True
    )

    # Check that requires_input was called (challenge raised)
    assert updater.requires_input.called, "Expected updater.requires_input to be called"
    print("✓ Challenge raised successfully")
    print(f"  Requires input call: {updater.requires_input.call_args}")


@patch('tools.PaymentRemoteA2aClient')
async def test_initiate_payment_card_with_valid_challenge(mock_client_class):
    """Test initiate_payment with card payment and valid challenge response."""
    print("\n=== Test 3: Card Payment - Valid Challenge Response ===")

    # Mock the credentials provider client
    mock_client = MagicMock()
    mock_client.send_a2a_message = AsyncMock(return_value=MagicMock(
        artifacts=[MagicMock(parts=[MagicMock(root=MagicMock(data={"credential": "test_credential"}))])]
    ))
    mock_client_class.return_value = mock_client

    data_parts = create_mock_data_parts(
        include_mandate=True,
        include_challenge_response=True,
        challenge_value="123"  # Valid challenge
    )
    updater = create_mock_updater()
    current_task = create_mock_task(state="input_required")

    await initiate_payment(
        data_parts=data_parts,
        updater=updater,
        current_task=current_task,
        debug_mode=True
    )

    # Check that complete was called (payment successful)
    assert updater.complete.called, "Expected updater.complete to be called"
    print("✓ Payment completed successfully with valid challenge")
    print(f"  Complete call: {updater.complete.call_args}")


async def test_initiate_payment_card_with_invalid_challenge():
    """Test initiate_payment with card payment and invalid challenge response."""
    print("\n=== Test 4: Card Payment - Invalid Challenge Response ===")

    data_parts = create_mock_data_parts(
        include_mandate=True,
        include_challenge_response=True,
        challenge_value="999"  # Invalid challenge
    )
    updater = create_mock_updater()
    current_task = create_mock_task(state="input_required")

    await initiate_payment(
        data_parts=data_parts,
        updater=updater,
        current_task=current_task,
        debug_mode=True
    )

    # Check that requires_input was called again (challenge failed)
    assert updater.requires_input.called, "Expected updater.requires_input to be called"
    print("✓ Challenge rejected correctly")
    print(f"  Requires input call: {updater.requires_input.call_args}")


@patch('tools.PaymentRemoteA2aClient')
async def test_initiate_payment_soho_credit(mock_client_class):
    """Test initiate_payment with SOHO_CREDIT payment (skips challenge)."""
    print("\n=== Test 5: SOHO Credit Payment (No Challenge) ===")

    # Mock the credentials provider client
    mock_client = MagicMock()
    mock_client.send_a2a_message = AsyncMock(return_value=MagicMock(
        artifacts=[MagicMock(parts=[MagicMock(root=MagicMock(data={"credential": "test_credential"}))])]
    ))
    mock_client_class.return_value = mock_client

    # Create mandate with SOHO_CREDIT method
    mandate = create_mock_payment_mandate()
    mandate["payment_mandate_contents"]["payment_response"]["method_name"] = "SOHO_CREDIT"

    data_parts = [{
        "key": PAYMENT_MANDATE_DATA_KEY,
        "value": mandate
    }]

    updater = create_mock_updater()

    await initiate_payment(
        data_parts=data_parts,
        updater=updater,
        current_task=None,  # First call but should skip challenge
        debug_mode=True
    )

    # Check that complete was called (no challenge, direct payment)
    assert updater.complete.called, "Expected updater.complete to be called"
    assert not updater.requires_input.called, "Should not require input for SOHO_CREDIT"
    print("✓ SOHO Credit payment completed without challenge")
    print(f"  Complete call: {updater.complete.call_args}")


async def run_all_tests():
    """Run all test cases."""
    print("=" * 60)
    print("Running initiate_payment tests with mock data")
    print("=" * 60)

    try:
        await test_initiate_payment_missing_mandate()
        await test_initiate_payment_card_first_call()
        await test_initiate_payment_card_with_valid_challenge()
        await test_initiate_payment_card_with_invalid_challenge()
        await test_initiate_payment_soho_credit()

        print("\n" + "=" * 60)
        print("✓ All tests completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
