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

"""SOHO Account Manager - In-memory manager of user SOHO Credit accounts.

Each account contains:
- User's SOHO Credit profile (credit limits, outstanding debt)
- Shipping addresses
- Payment methods (BNPL plans)
- Borrower blockchain address
"""

from typing import Any


# SOHO Credit user account database
_soho_account_db = {
    "user@example.com": {
        "user_id": "user_123",
        "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "kyc_verified": True,
        "shipping_address": {
            "recipient": "John Smith",
            "organization": "",
            "address_line": ["123 Main St"],
            "city": "San Francisco",
            "region": "CA",
            "postal_code": "94105",
            "country": "US",
            "phone_number": "+1-555-0100",
        },
        "contact": {
            "email": "user@example.com",
            "phone": "+1-555-0100",
        },
        "credit_profile": {
            "credit_limit": 5000.00,
            "available_credit": 4139.42,
            "outstanding_debt": 860.58,
            "credit_score": 750,
        },
        "payment_methods": {
            "soho_pay_in_full": {
                "type": "SOHO_CREDIT",
                "alias": "SOHO Credit - Pay in Full",
                "plan_id": "pay_in_full",
            },
            "soho_pay_in_4": {
                "type": "SOHO_CREDIT",
                "alias": "SOHO Credit - Pay in 4",
                "plan_id": "pay_in_4",
            },
            "soho_pay_in_12": {
                "type": "SOHO_CREDIT",
                "alias": "SOHO Credit - 12 Month Plan",
                "plan_id": "pay_in_12",
            },
        },
    },
    "bugsbunny@gmail.com": {
        "user_id": "user_bugs",
        "borrower_address": "0x1234567890abcdef1234567890abcdef12345678",
        "kyc_verified": True,
        "shipping_address": {
            "recipient": "Bugs Bunny",
            "organization": "Looney Tunes",
            "address_line": ["456 Carrot Lane"],
            "city": "Los Angeles",
            "region": "CA",
            "postal_code": "90001",
            "country": "US",
            "phone_number": "+1-555-0200",
        },
        "contact": {
            "email": "bugsbunny@gmail.com",
            "phone": "+1-555-0200",
        },
        "credit_profile": {
            "credit_limit": 3000.00,
            "available_credit": 2500.00,
            "outstanding_debt": 500.00,
            "credit_score": 720,
        },
        "payment_methods": {
            "soho_pay_in_full": {
                "type": "SOHO_CREDIT",
                "alias": "SOHO Credit - Pay in Full",
                "plan_id": "pay_in_full",
            },
            "soho_pay_in_4": {
                "type": "SOHO_CREDIT",
                "alias": "SOHO Credit - Pay in 4",
                "plan_id": "pay_in_4",
            },
        },
    },
}

# Token storage for payment credentials
_token_db = {}


def get_account(email_address: str) -> dict[str, Any] | None:
  """Gets the SOHO account for the given email address.

  Args:
    email_address: The account's email address.

  Returns:
    The SOHO account data or None if not found.
  """
  return _soho_account_db.get(email_address)


def get_account_shipping_address(email_address: str) -> dict[str, Any]:
  """Gets the shipping address for the given account email address.

  Args:
    email_address: The account's email address.

  Returns:
    The account's shipping address.
  """
  account = get_account(email_address)
  if not account:
    raise ValueError(f"Account not found: {email_address}")
  return account.get("shipping_address", {})


def get_account_payment_methods(email_address: str) -> list[dict[str, Any]]:
  """Returns a list of SOHO Credit payment methods for the account.

  Args:
    email_address: The account's email address.

  Returns:
    A list of the user's SOHO Credit payment methods.
  """
  account = get_account(email_address)
  if not account:
    raise ValueError(f"Account not found: {email_address}")
  return list(account.get("payment_methods", {}).values())


def get_credit_profile(email_address: str) -> dict[str, Any]:
  """Gets the SOHO Credit profile for the account.

  Args:
    email_address: The account's email address.

  Returns:
    The credit profile with limits and outstanding debt.
  """
  account = get_account(email_address)
  if not account:
    raise ValueError(f"Account not found: {email_address}")
  return account.get("credit_profile", {})


def get_borrower_address(email_address: str) -> str:
  """Gets the blockchain borrower address for the account.

  Args:
    email_address: The account's email address.

  Returns:
    The borrower's blockchain address.
  """
  account = get_account(email_address)
  if not account:
    raise ValueError(f"Account not found: {email_address}")
  return account.get("borrower_address", "")


def get_payment_method_by_alias(
    email_address: str, alias: str
) -> dict[str, Any] | None:
  """Returns the payment method for a given account and alias.

  Args:
    email_address: The account's email address.
    alias: The alias of the payment method to retrieve.

  Returns:
    The payment method or None if not found.
  """
  payment_methods = get_account_payment_methods(email_address)
  for method in payment_methods:
    if method.get("alias", "").casefold() == alias.casefold():
      return method
  return None


def create_token(email_address: str, payment_method_alias: str) -> str:
  """Creates and stores a token for a SOHO Credit payment method.

  Args:
    email_address: The email address of the account.
    payment_method_alias: The alias of the payment method.

  Returns:
    The token for the payment method.
  """
  token = f"soho_token_{len(_token_db)}_{email_address}"

  _token_db[token] = {
      "email_address": email_address,
      "payment_method_alias": payment_method_alias,
      "payment_mandate_id": None,
  }

  return token


def update_token(token: str, payment_mandate_id: str) -> None:
  """Updates the token with the payment mandate id.

  Args:
    token: The token to update.
    payment_mandate_id: The payment mandate id to associate with the token.
  """
  if token not in _token_db:
    raise ValueError(f"Token {token} not found")
  if _token_db[token].get("payment_mandate_id"):
    # Do not overwrite the payment mandate id if it is already set.
    return
  _token_db[token]["payment_mandate_id"] = payment_mandate_id


def verify_token(token: str, payment_mandate_id: str) -> dict[str, Any]:
  """Look up an account by token.

  Args:
    token: The token for look up.
    payment_mandate_id: The payment mandate id associated with the token.

  Returns:
    The payment method for the given token.
  """
  account_lookup = _token_db.get(token, {})
  if not account_lookup:
    raise ValueError("Invalid token")
  if account_lookup.get("payment_mandate_id") != payment_mandate_id:
    raise ValueError("Invalid token")
  email_address = account_lookup.get("email_address")
  alias = account_lookup.get("payment_method_alias")
  return get_payment_method_by_alias(email_address, alias)
