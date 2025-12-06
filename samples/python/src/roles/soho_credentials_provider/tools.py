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
import logging
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

logger = logging.getLogger(__name__)


async def handle_get_shipping_address(
    data_parts: list[dict[str, Any]],
    updater: TaskUpdater,
    current_task: Task | None,
) -> None:
  """Handles a request to get the user's shipping address(es) from SOHO.

  Args:
    data_parts: DataPart contents containing user_email and optional address_key.
    updater: The TaskUpdater instance for updating the task state.
    current_task: The current task if there is one.
  """
  user_email = message_utils.find_data_part("user_email", data_parts)
  if not user_email:
    raise ValueError("user_email is required for get_shipping_address")

  address_key = message_utils.find_data_part("address_key", data_parts)

  # Use account manager to get shipping address(es)
  account = account_manager.get_account(user_email)
  if not account:
    raise ValueError(f"User not found: {user_email}")

  # Check if requesting all addresses or a specific one
  if address_key:
    # Get specific address
    shipping_addresses = account.get("shipping_addresses", {})
    if address_key not in shipping_addresses:
      # Fall back to default address
      shipping_address = account_manager.get_account_shipping_address(user_email)
    else:
      shipping_address = shipping_addresses[address_key]
  else:
    # Check if request is for all addresses
    shipping_addresses = account.get("shipping_addresses", {})
    if shipping_addresses and "all" in str(current_task.message.parts[0]).lower():
      # Return all addresses
      contact_addresses = []
      for key, addr in shipping_addresses.items():
        contact_address = ContactAddress(
            recipient=addr["recipient"],
            organization=addr.get("organization", ""),
            addressLine=addr["address_line"],
            city=addr["city"],
            region=addr["region"],
            postalCode=addr["postal_code"],
            country=addr["country"],
            phoneNumber=addr.get("phone_number", "")
        )
        contact_addresses.append(contact_address)

      # Add all addresses as artifacts
      for contact_address in contact_addresses:
        await updater.add_artifact(
            [Part(root=DataPart(data={CONTACT_ADDRESS_DATA_KEY: contact_address.model_dump()}))]
        )
      await updater.complete()
      return
    else:
      # Get default shipping address
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

  # Log the created token for debugging on the credentials provider side.
  # This helps trace the token value produced by `account_manager.create_token`.
  try:
    logger.info("Created payment credential token for user %s: %s", user_email, token_value)
  except Exception:
    # Ensure logging can't break the task flow.
    pass

  await updater.add_artifact([Part(root=DataPart(data=token))])
  await updater.complete()


async def handle_payment_receipt(
    data_parts: list[dict[str, Any]],
    updater: TaskUpdater,
    current_task: Task | None,
) -> None:
  """Handles payment receipt from Payment Processor and executes on-chain payment.

  This function:
  1. Validates the payment amount is under $100
  2. Authenticates with the SOHO API using borrower credentials
  3. Calls the /api/v1/agent/pay endpoint to execute on-chain payment

  Args:
    data_parts: DataPart contents containing payment_receipt.
    updater: The TaskUpdater instance for updating the task state.
    current_task: The current task if there is one.
  """
  import os
  import httpx
  from ap2.types.payment_receipt import PAYMENT_RECEIPT_DATA_KEY

  payment_receipt_data = message_utils.find_data_part(
      PAYMENT_RECEIPT_DATA_KEY, data_parts
  )

  if not payment_receipt_data:
    logger.warning("No payment receipt found in message")
    await updater.complete()
    return

  # Extract payment details - amount is a dict with 'currency' and 'value'
  amount_data = payment_receipt_data.get("amount", {})
  if isinstance(amount_data, dict):
    amount_usd = float(amount_data.get("value", 0))
  else:
    # Fallback if amount is already a number
    amount_usd = float(amount_data)

  # Step 0: Ensure product price is below $100
  if amount_usd >= 100.00:
    error_msg = f"Payment amount ${amount_usd} exceeds $100 limit for mock API"
    logger.error(error_msg)
    await updater.add_artifact([
        Part(root=DataPart(data={"error": error_msg, "status": "failed"}))
    ])
    await updater.complete()
    return

  # Convert USD to USDC smallest unit (USDC has 6 decimal places)
  # 1 USD = 1,000,000 micro-USDC
  amount_wei = str(int(amount_usd * 1_000_000))

  # Get SOHO API base URL from environment or use default
  api_base_url = os.environ.get("SOHO_API_URL", "http://localhost:32775")
  logger.info(f"Using SOHO API URL: {api_base_url}")

  # Step 1 & 2: Usestephennjugi18@gmail.com credentials
  borrower_email = "stephennjugi18@gmail.com"
  borrower_password = "Furaha45$%"

  # Mock merchant address
  merchant_address = "0x029241b72abab1b29fecdd1c609920bb8706e7b2"
  payment_plan_id = "0"  # Pay in full

  try:
    # Increase timeout to 120 seconds for blockchain transactions which can be slow
    async with httpx.AsyncClient(timeout=120.0) as client:
      # Step 3a: Login to get access token
      logger.info(f"Authenticating with SOHO API as {borrower_email}...")
      login_response = await client.post(
          f"{api_base_url}/api/v1/auth/login",
          json={"email": borrower_email, "password": borrower_password},
          headers={"Content-Type": "application/json"}
      )

      if login_response.status_code != 200:
        error_msg = f"Login failed: {login_response.status_code} - {login_response.text}"
        logger.error(error_msg)
        await updater.add_artifact([
            Part(root=DataPart(data={"error": error_msg, "status": "failed"}))
        ])
        await updater.complete()
        return

      login_data = login_response.json()
      access_token = login_data.get("data", {}).get("tokens", {}).get("accessToken")

      if not access_token:
        error_msg = "No access token in login response"
        logger.error(error_msg)
        await updater.add_artifact([
            Part(root=DataPart(data={"error": error_msg, "status": "failed"}))
        ])
        await updater.complete()
        return

      logger.info(f"Successfully authenticated. Access token obtained.")

      # Step 3b: Call /api/v1/agent/pay endpoint
      logger.info(f"Executing payment: merchant={merchant_address}, amount={amount_wei} wei (${amount_usd}), plan={payment_plan_id}")
      pay_response = await client.post(
          f"{api_base_url}/api/v1/agent/pay",
          json={
              "merchant": merchant_address,
              "amount": amount_wei,
              "paymentPlanId": payment_plan_id
          },
          headers={
              "Content-Type": "application/json",
              "Authorization": f"Bearer {access_token}"
          }
      )

      if pay_response.status_code not in [200, 201]:
        error_msg = f"Payment failed: {pay_response.status_code} - {pay_response.text}"
        logger.error(error_msg)
        await updater.add_artifact([
            Part(root=DataPart(data={"error": error_msg, "status": "failed"}))
        ])
        await updater.complete()
        return

      pay_data = pay_response.json()
      logger.info(f"Payment successful: {pay_data}")

      # Extract transaction details from response
      transaction_hash = pay_data.get("transactionHash") or (pay_data.get("data", {}).get("transactionHash"))
      transaction_id = pay_data.get("data", {}).get("transactionId")
      block_number = pay_data.get("data", {}).get("blockNumber")
      gas_used = pay_data.get("data", {}).get("gasUsed")
      amount_formatted = pay_data.get("data", {}).get("amountFormatted")

      # Log transaction details prominently for easy copying
      logger.info(f"=" * 80)
      logger.info(f"PAYMENT SUCCESSFUL!")
      logger.info(f"Transaction Hash: {transaction_hash}")
      logger.info(f"Transaction ID: {transaction_id}")
      logger.info(f"Block Number: {block_number}")
      logger.info(f"Gas Used: {gas_used}")
      logger.info(f"Amount: {amount_formatted} USDC (${amount_usd})")
      logger.info(f"=" * 80)

      # Add successful payment data to artifacts
      await updater.add_artifact([
          Part(root=DataPart(data={
              "status": "success",
              "transaction_hash": transaction_hash,
              "transaction_id": transaction_id,
              "block_number": block_number,
              "gas_used": gas_used,
              "amount_formatted": amount_formatted,
              "payment_result": pay_data,
              "amount_usd": amount_usd,
              "amount_wei": amount_wei,
              "merchant": merchant_address,
              "payment_plan_id": payment_plan_id
          }))
      ])

  except httpx.ConnectError as e:
    error_msg = f"Failed to connect to SOHO API at {api_base_url}. Is the SOHO API server running? Error: {str(e)}"
    logger.error(error_msg)
    await updater.add_artifact([
        Part(root=DataPart(data={"error": error_msg, "status": "failed"}))
    ])
  except httpx.RequestError as e:
    error_msg = f"API request failed: {type(e).__name__} - {str(e)}"
    logger.error(error_msg)
    await updater.add_artifact([
        Part(root=DataPart(data={"error": error_msg, "status": "failed"}))
    ])
  except Exception as e:
    error_msg = f"Unexpected error during payment: {str(e)}"
    logger.error(error_msg, exc_info=True)
    await updater.add_artifact([
        Part(root=DataPart(data={"error": error_msg, "status": "failed"}))
    ])

  await updater.complete()
