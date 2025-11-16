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

"""Tools for the SOHO Credentials Provider Agent."""

from typing import Any
from datetime import datetime, timedelta

from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import DataPart
from a2a.types import Part
from a2a.types import Task

from ap2.types.contact_picker import CONTACT_ADDRESS_DATA_KEY, ContactAddress
from ap2.types.mandate import PAYMENT_MANDATE_DATA_KEY
from ap2.types.mandate import PaymentMandate
from ap2.types.payment_request import PAYMENT_METHOD_DATA_DATA_KEY
from ap2.types.payment_request import PaymentMethodData
from common import message_utils

from . import account_manager


async def handle_get_shipping_address(
    data_parts: list[dict[str, Any]],
    updater: TaskUpdater,
    current_task: Task | None,
) -> None:
  """Handles a request to get the user's shipping address from SOHO.

  Args:
    data_parts: DataPart contents containing user_email.
    updater: The TaskUpdater instance for updating the task state.
    current_task: The current task if there is one.
  """
  user_email = message_utils.find_data_part("user_email", data_parts)
  if not user_email:
    raise ValueError("user_email is required for get_shipping_address")

  # Use account manager to get shipping address
  shipping_address = account_manager.get_account_shipping_address(user_email)

  contact_address = ContactAddress(
      recipient=shipping_address["recipient"],
      organization=shipping_address.get("organization", ""),
      addressLine=shipping_address["address_line"],
      city=shipping_address["city"],
      region=shipping_address["region"],
      postalCode=shipping_address["postal_code"],
      country=shipping_address["country"],
      phoneNumber=shipping_address.get("phone_number", "")
  )

  await updater.add_artifact(
      [Part(root=DataPart(data={CONTACT_ADDRESS_DATA_KEY: contact_address.model_dump()}))]
  )
  await updater.complete()


async def handle_get_credit_status(
    data_parts: list[dict[str, Any]],
    updater: TaskUpdater,
    current_task: Task | None,
) -> None:
  """Returns the user's SOHO Credit status.

  Args:
    data_parts: DataPart contents containing user_email.
    updater: The TaskUpdater instance for updating the task state.
    current_task: The current task if there is one.
  """
  user_email = message_utils.find_data_part("user_email", data_parts)
  if not user_email:
    raise ValueError("user_email is required for get_credit_status")

  # Use account manager to get account details
  account = account_manager.get_account(user_email)
  if not account:
    raise ValueError(f"User not found: {user_email}")

  credit_profile = account_manager.get_credit_profile(user_email)
  borrower_address = account_manager.get_borrower_address(user_email)

  credit_status = {
      "user_id": account["user_id"],
      "borrower_address": borrower_address,
      "credit_profile": credit_profile,
      "spending_limits": {
          "per_transaction": 1000.00,
          "per_day": 2000.00,
          "per_month": 5000.00
      },
      "status": "active"
  }

  await updater.add_artifact([Part(root=DataPart(data={"credit_status": credit_status}))])
  await updater.complete()


async def handle_get_bnpl_quote(
    data_parts: list[dict[str, Any]],
    updater: TaskUpdater,
    current_task: Task | None,
) -> None:
  """Returns BNPL (Buy Now Pay Later) payment plan options.

  Args:
    data_parts: DataPart contents containing user_email, amount, and merchant_id.
    updater: The TaskUpdater instance for updating the task state.
    current_task: The current task if there is one.
  """
  user_email = message_utils.find_data_part("user_email", data_parts)
  amount = message_utils.find_data_part("amount", data_parts)
  merchant_id = message_utils.find_data_part("merchant_id", data_parts)

  if not user_email or amount is None:
    raise ValueError("user_email and amount are required for get_bnpl_quote")

  # Use account manager to get account details
  account = account_manager.get_account(user_email)
  if not account:
    raise ValueError(f"User not found: {user_email}")

  credit_profile = account_manager.get_credit_profile(user_email)

  # Check if user has sufficient credit
  available_credit = credit_profile["available_credit"]
  if amount > available_credit:
    bnpl_quote = {
        "validation_status": "declined",
        "reason": "insufficient_credit",
        "available_credit": available_credit,
        "requested_amount": amount
    }
  else:
    # Generate BNPL options
    current_date = datetime.now()

    bnpl_quote = {
        "validation_status": "approved",
        "available_credit": available_credit,
        "transaction_amount": amount,
        "bnpl_options": [
            {
                "plan_id": "pay_in_full",
                "name": "Pay in Full",
                "installments": 1,
                "amount_per_installment": round(amount, 2),
                "interest_rate": "0.00%",
                "total_amount": round(amount, 2),
                "due_dates": [(current_date + timedelta(days=30)).strftime("%Y-%m-%d")]
            },
            {
                "plan_id": "pay_in_4",
                "name": "Pay in 4",
                "installments": 4,
                "amount_per_installment": round(amount / 4, 2),
                "interest_rate": "0.00%",
                "total_amount": round(amount / 4, 2) * 4,
                "due_dates": [
                    current_date.strftime("%Y-%m-%d"),
                    (current_date + timedelta(days=14)).strftime("%Y-%m-%d"),
                    (current_date + timedelta(days=28)).strftime("%Y-%m-%d"),
                    (current_date + timedelta(days=42)).strftime("%Y-%m-%d")
                ]
            },
            {
                "plan_id": "pay_in_12",
                "name": "12 Month Plan",
                "installments": 12,
                "amount_per_installment": round((amount * 1.0599) / 12, 2),
                "interest_rate": "5.99%",
                "total_amount": round(amount * 1.0599, 2),
                "due_dates": [
                    (current_date + timedelta(days=30*i)).strftime("%Y-%m-%d")
                    for i in range(1, 13)
                ]
            }
        ],
        "credit_authorization_token": f"soho_auth_{account['user_id']}_{current_date.timestamp()}",
        "limits_check": {
            "per_transaction_limit": 1000.00,
            "per_day_remaining": 2000.00 - amount,
            "per_month_remaining": 5000.00 - amount
        }
    }

  await updater.add_artifact([Part(root=DataPart(data={"bnpl_quote": bnpl_quote}))])
  await updater.complete()


async def handle_request_biometric_approval(
    data_parts: list[dict[str, Any]],
    updater: TaskUpdater,
    current_task: Task | None,
) -> None:
  """Simulates requesting biometric approval via SOHO mobile app.

  In a real implementation, this would:
  1. Send push notification to user's SOHO mobile app
  2. Display purchase details with payment plan
  3. Request Face ID / Touch ID authentication
  4. Return signed attestation

  Args:
    data_parts: DataPart contents containing user_email, amount, merchant, and payment_plan.
    updater: The TaskUpdater instance for updating the task state.
    current_task: The current task if there is one.
  """
  user_email = message_utils.find_data_part("user_email", data_parts)
  amount = message_utils.find_data_part("amount", data_parts)
  merchant = message_utils.find_data_part("merchant", data_parts)
  payment_plan = message_utils.find_data_part("payment_plan", data_parts)

  if not all([user_email, amount, merchant, payment_plan]):
    raise ValueError("user_email, amount, merchant, and payment_plan are required")

  # Use account manager to get account
  account = account_manager.get_account(user_email)
  if not account:
    raise ValueError(f"User not found: {user_email}")

  # Simulate biometric approval
  approval_timestamp = datetime.now().isoformat()

  attestation = {
      "approval_status": "authorized",
      "attestation": {
          "type": "device_biometric",
          "authentication_method": "face_id",
          "signature": f"0x9f8e7d6c5b4a_{account['user_id']}",
          "timestamp": approval_timestamp,
          "device_id": f"iphone_{account['user_id']}",
          "device_certificate": {
              "issuer": "Apple",
              "serial": "CERT_APPLE_XYZ",
              "valid_until": "2026-11-15"
          }
      }
  }

  await updater.add_artifact([Part(root=DataPart(data={"biometric_approval": attestation}))])
  await updater.complete()


async def handle_search_payment_methods(
    data_parts: list[dict[str, Any]],
    updater: TaskUpdater,
    current_task: Task | None,
) -> None:
  """Returns SOHO Credit payment methods that match merchant's accepted methods.

  Args:
    data_parts: DataPart contents containing user_email and merchant's PaymentMethodData.
    updater: The TaskUpdater instance for updating the task state.
    current_task: The current task if there is one.
  """
  user_email = message_utils.find_data_part("user_email", data_parts)
  method_data = message_utils.find_data_parts(
      PAYMENT_METHOD_DATA_DATA_KEY, data_parts
  )

  if not user_email:
    raise ValueError("user_email is required for search_payment_methods")
  if not method_data:
    raise ValueError("method_data is required for search_payment_methods")

  # Use account manager to get payment methods
  payment_methods = account_manager.get_account_payment_methods(user_email)

  merchant_method_data_list = [
      PaymentMethodData.model_validate(data) for data in method_data
  ]

  # Check if merchant accepts SOHO_CREDIT
  accepts_soho = any(
      "SOHO_CREDIT" in method.supported_methods
      for method in merchant_method_data_list
  )

  if accepts_soho:
    # Return all SOHO Credit payment method aliases
    eligible_aliases = {
        "payment_method_aliases": [
            method["alias"] for method in payment_methods
        ]
    }
  else:
    eligible_aliases = {"payment_method_aliases": []}

  await updater.add_artifact([Part(root=DataPart(data=eligible_aliases))])
  await updater.complete()


async def handle_create_payment_credential_token(
    data_parts: list[dict[str, Any]],
    updater: TaskUpdater,
    current_task: Task | None,
) -> None:
  """Creates a payment credential token for the selected payment method.

  Args:
    data_parts: DataPart contents containing user_email and payment_method_alias.
    updater: The TaskUpdater instance for updating the task state.
    current_task: The current task if there is one.
  """
  user_email = message_utils.find_data_part("user_email", data_parts)
  payment_method_alias = message_utils.find_data_part(
      "payment_method_alias", data_parts
  )

  if not user_email or not payment_method_alias:
    raise ValueError(
        "user_email and payment_method_alias are required"
    )

  # Use account manager to get payment method
  payment_method = account_manager.get_payment_method_by_alias(
      user_email, payment_method_alias
  )

  if not payment_method:
    raise ValueError(f"Payment method not found: {payment_method_alias}")

  # Get account details
  account = account_manager.get_account(user_email)
  borrower_address = account_manager.get_borrower_address(user_email)

  # Create token using account manager
  token_value = account_manager.create_token(user_email, payment_method_alias)

  # Create token response
  token = {
      "payment_credential_token": {
          "type": "soho_credit",
          "value": token_value,
          "borrower_address": borrower_address,
          "plan_id": payment_method["plan_id"]
      }
  }

  await updater.add_artifact([Part(root=DataPart(data=token))])
  await updater.complete()
