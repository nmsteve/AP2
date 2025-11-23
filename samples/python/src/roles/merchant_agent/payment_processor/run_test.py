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

"""Quick test runner for initiate_payment with minimal mocking."""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from test_tools import (
    test_initiate_payment_missing_mandate,
    test_initiate_payment_card_first_call,
    test_initiate_payment_card_with_valid_challenge,
    test_initiate_payment_card_with_invalid_challenge,
    test_initiate_payment_soho_credit,
)


async def main():
    """Run individual tests or all tests."""
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        tests = {
            "missing": test_initiate_payment_missing_mandate,
            "card_first": test_initiate_payment_card_first_call,
            "valid_challenge": test_initiate_payment_card_with_valid_challenge,
            "invalid_challenge": test_initiate_payment_card_with_invalid_challenge,
            "soho": test_initiate_payment_soho_credit,
        }

        if test_name in tests:
            await tests[test_name]()
        else:
            print(f"Unknown test: {test_name}")
            print(f"Available tests: {', '.join(tests.keys())}")
    else:
        # Run all tests
        print("Running all tests...")
        await test_initiate_payment_missing_mandate()
        await test_initiate_payment_card_first_call()
        await test_initiate_payment_card_with_valid_challenge()
        await test_initiate_payment_card_with_invalid_challenge()
        await test_initiate_payment_soho_credit()
        print("\n✓ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
