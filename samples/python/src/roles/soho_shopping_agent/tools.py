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

"""SOHO Shopping Agent Tools.

Tools specific to SOHO Credit integration including BNPL plan selection
and biometric approval workflow.
"""

from datetime import datetime
from datetime import timezone
import json
import uuid

from a2a.types import Artifact
from google.adk.tools.tool_context import ToolContext

from .remote_agents import soho_credentials_provider_client
from .remote_agents import merchant_agent_client
from ap2.types.contact_picker import ContactAddress
from ap2.types.mandate import CART_MANDATE_DATA_KEY
from ap2.types.mandate import CartMandate
from ap2.types.mandate import PAYMENT_MANDATE_DATA_KEY
from ap2.types.mandate import PaymentMandate
from ap2.types.mandate import PaymentMandateContents
from ap2.types.payment_receipt import PAYMENT_RECEIPT_DATA_KEY
from ap2.types.payment_receipt import PaymentReceipt
from ap2.types.payment_request import PaymentResponse
from common import artifact_utils
from common.a2a_message_builder import A2aMessageBuilder
import logging


async def load_test_payment_mandate(
    tool_context: ToolContext,
) -> dict:
  """Loads a pre-configured test payment mandate for testing initiate_payment.

  This tool loads a complete payment mandate with all required data including:
  - Payment details
  - User authorization (biometric attestation)
  - Borrower address
  - Payment plan details

  Args:
    tool_context: The ADK supplied tool context.

  Returns:
    Success message with payment mandate summary.
  """
  # Load the test payment mandate data
  test_mandate_data = {
      'payment_mandate_id': '043254041f4d46759f0e7497761c9ee1',
      'payment_details_id': 'order_1',
      'payment_details_total': {
          'label': 'Total',
          'amount': {'currency': 'USD', 'value': 2.49},
          'pending': None,
          'refund_period': 30
      },
      'payment_response': {
          'request_id': 'order_1',
          'method_name': 'SOHO_CREDIT',
          'details': {
              'token': {
                  'value': 'soho_token_1_borrower1@example.com',
                  'raw': {},
                  'provider_url': 'http://localhost:8005/a2a/soho_credentials_provider'
              },
              'authorization_token': 'soho_auth_borrower_001_1764692463.890651',
              'borrower_address': '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb',
              'payment_plan': {
                  'plan_id': 'pay_in_full',
                  'name': 'Pay in Full',
                  'installments': 1,
                  'amount_per_installment': 28.49,
                  'interest_rate': '0.00%',
                  'total_amount': 28.49,
                  'due_dates': ['2026-01-01']
              }
          },
          'shipping_address': {
              'city': 'San Francisco',
              'country': 'US',
              'dependent_locality': None,
              'organization': None,
              'phone_number': None,
              'postal_code': None,
              'recipient': 'Borrower One',
              'region': 'CA',
              'sorting_code': None,
              'address_line': None
          },
          'shipping_option': None,
          'payer_name': None,
          'payer_email': 'borrower1@example.com',
          'payer_phone': None
      },
      'merchant_agent': 'Generic Merchant',
      'timestamp': '2025-12-02T16:23:25.770039+00:00'
  }

  user_authorization = {
      "type": "device_biometric",
      "authentication_method": "face_id",
      "signature": "0x9f8e7d6c5b4a_borrower_001",
      "timestamp": "2025-12-02T19:22:01.408090",
      "device_id": "iphone_borrower_001",
      "device_certificate": {
          "issuer": "Apple",
          "serial": "CERT_APPLE_XYZ",
          "valid_until": "2026-11-15"
      }
  }

  # Create PaymentMandateContents object
  payment_mandate_contents = PaymentMandateContents.model_validate(test_mandate_data)

  # Create PaymentMandate with user authorization
  payment_mandate = PaymentMandate(
      payment_mandate_contents=payment_mandate_contents,
      user_authorization=json.dumps(user_authorization)
  )

  # Create risk data (required by initiate_payment)
  risk_data = {
      "device_id": "iphone_borrower_001",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
      "timestamp": datetime.now(timezone.utc).isoformat(),
      "risk_score": 0.15,
      "risk_level": "LOW"
  }

  # Store in tool context state
  tool_context.state["signed_payment_mandate"] = payment_mandate.model_dump()
  tool_context.state["risk_data"] = risk_data
  tool_context.state["shopping_context_id"] = str(uuid.uuid4())

  return {
      "status": "success",
      "message": "Test payment mandate loaded successfully",
      "amount": 5.49,
      "payment_plan": "Pay in Full",
      "borrower_email": "borrower1@example.com",
      "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
  }


async def get_bnpl_options(
    tool_context: ToolContext,
    debug_mode: bool = False,
) -> dict:
  """Gets BNPL (Buy Now Pay Later) payment plan options from SOHO Credit.

  Args:
    tool_context: The ADK supplied tool context.
    debug_mode: Whether the agent is in debug mode.

  Returns:
    BNPL quote with payment plan options.
  """
  cart_mandate = tool_context.state.get("cart_mandate")
  if not cart_mandate:
    raise RuntimeError("No cart mandate found in tool context state.")

  total_amount = cart_mandate.contents.payment_request.details.total.amount.value
  merchant_name = cart_mandate.contents.merchant_name

  # Validate that total amount is under $100 for mock API integration
  if total_amount >= 100.00:
    raise RuntimeError(
        f"Total amount ${total_amount:.2f} exceeds $100.00 limit for SOHO API demo. "
        "Please select products with a lower total price."
    )

  message = (
      A2aMessageBuilder()
      .set_context_id(tool_context.state["shopping_context_id"])
      .add_text("Get the BNPL quote for the user")
      .add_data("user_email", "borrower1@example.com")  # In production, get from auth
      .add_data("amount", total_amount)
      .add_data("merchant_name", merchant_name)
      .add_data("debug_mode", debug_mode)
      .build()
  )

  task = await soho_credentials_provider_client.send_a2a_message(message)
  data = artifact_utils.get_first_data_part(task.artifacts)
  bnpl_quote = data.get("bnpl_quote")

  tool_context.state["bnpl_quote"] = bnpl_quote
  return bnpl_quote


async def select_payment_plan(
    plan_id: str,
    tool_context: ToolContext,
) -> dict:
  """Stores the user's selected BNPL payment plan.

  Args:
    plan_id: The ID of the selected payment plan.
    tool_context: The ADK supplied tool context.

  Returns:
    The selected payment plan details.
  """
  bnpl_quote = tool_context.state.get("bnpl_quote")
  if not bnpl_quote:
    raise RuntimeError("No BNPL quote found in tool context state.")

  selected_plan = next(
      (plan for plan in bnpl_quote["bnpl_options"] if plan["plan_id"] == plan_id),
      None
  )

  if not selected_plan:
    raise ValueError(f"Invalid plan_id: {plan_id}")

  tool_context.state["selected_payment_plan"] = selected_plan
  tool_context.state["credit_authorization_token"] = bnpl_quote["credit_authorization_token"]

  return selected_plan


async def request_biometric_approval(
    tool_context: ToolContext,
    debug_mode: bool = False,
) -> dict:
  """Requests biometric approval via SOHO mobile app.

  This simulates sending a push notification to the user's mobile device
  requesting Face ID/Touch ID authentication.

  Args:
    tool_context: The ADK supplied tool context.
    debug_mode: Whether the agent is in debug mode.

  Returns:
    Biometric approval attestation.
  """
  cart_mandate = tool_context.state.get("cart_mandate")
  selected_plan = tool_context.state.get("selected_payment_plan")

  if not cart_mandate or not selected_plan:
    raise RuntimeError("Missing cart_mandate or selected_payment_plan in state.")

  # Ensure cart_mandate is a CartMandate object, not a dict
  if isinstance(cart_mandate, dict):
    cart_mandate = CartMandate(**cart_mandate)
    tool_context.state["cart_mandate"] = cart_mandate

  total_amount = cart_mandate.contents.payment_request.details.total.amount.value
  merchant_name = cart_mandate.contents.merchant_name

  message = (
      A2aMessageBuilder()
      .set_context_id(tool_context.state["shopping_context_id"])
      .add_text("Request biometric approval for purchase")
      .add_data("user_email", "borrower1@example.com")
      .add_data("amount", total_amount)
      .add_data("merchant", merchant_name)
      .add_data("payment_plan", selected_plan)
      .add_data("debug_mode", debug_mode)
      .build()
  )

  task = await soho_credentials_provider_client.send_a2a_message(message)
  data = artifact_utils.get_first_data_part(task.artifacts)
  biometric_approval = data.get("biometric_approval")

  tool_context.state["biometric_approval"] = biometric_approval
  return biometric_approval


async def create_payment_credential_token(
  user_email: str,
  payment_method_alias: str,
  tool_context: ToolContext,
) -> dict:
  """Requests a payment credential token from the SOHO credentials provider.

  This stores the returned token in `tool_context.state["payment_credential_token"]`.

  Args:
    user_email: The user's email address.
    payment_method_alias: The payment method alias to tokenize.
    tool_context: The ADK supplied tool context.

  Returns:
    A dict with status and token value.
  """
  message = (
    A2aMessageBuilder()
    .set_context_id(tool_context.state["shopping_context_id"])
    .add_text("Create a payment credential token for the user's payment method.")
    .add_data("user_email", user_email)
    .add_data("payment_method_alias", payment_method_alias)
    .build()
  )

  task = await soho_credentials_provider_client.send_a2a_message(message)
  data = artifact_utils.get_first_data_part(task.artifacts)
  # The credentials provider may return different shapes depending on the
  # provider implementation. Normalize both cases:
  # - legacy provider: {"token": "..."}
  # - soho provider: {"payment_credential_token": {"type":..., "value":...}}
  credentials_provider_agent_card = await soho_credentials_provider_client.get_agent_card()

  token_value = None
  if isinstance(data, dict):
    if "token" in data:
      token_value = data.get("token")
    elif "payment_credential_token" in data:
      pct = data.get("payment_credential_token")
      # token may be nested under different keys; try common patterns
      if isinstance(pct, dict):
        token_value = pct.get("value") or pct.get("token")
      else:
        token_value = pct

  # Try a recursive search for token-like values if not found yet
  def _find_token(obj):
    if obj is None:
      return None
    if isinstance(obj, str):
      # Heuristic: treat any long hex-like or prefixed string as token
      if len(obj) > 8:
        return obj
      return None
    if isinstance(obj, dict):
      for k, v in obj.items():
        if k in ("token", "value", "payment_credential_token") and isinstance(v, (str, dict)):
          if isinstance(v, str):
            return v
          if isinstance(v, dict):
            # prefer `value` or `token` inside
            return v.get("value") or v.get("token") or _find_token(v)
      for v in obj.values():
        found = _find_token(v)
        if found:
          return found
    if isinstance(obj, list):
      for item in obj:
        found = _find_token(item)
        if found:
          return found
    return None

  if not token_value:
    token_value = _find_token(data)

  # Store raw response for debugging even if token_value is missing
  tool_context.state["payment_credential_token"] = {
      "value": token_value,
      "raw": data,
      "provider_url": getattr(credentials_provider_agent_card, "url", None),
  }

  if not token_value:
    # Return an error status instead of raising to allow the caller to
    # handle the failure and inspect `tool_context.state["payment_credential_token"]`.
    return {"status": "error", "reason": "no_token_returned", "raw": data}

  return {"status": "success", "token": token_value}

  tool_context.state["payment_credential_token"] = {
    "value": token_value,
    "raw": data,
    "provider_url": getattr(credentials_provider_agent_card, "url", None),
  }
  logging.info(f"Created payment credential token: {token_value}")
  return {"status": "success", "token": token_value}


async def update_cart(
    shipping_address: ContactAddress,
    tool_context: ToolContext,
    debug_mode: bool = False,
) -> str:
  """Notifies the merchant agent of a shipping address selection for a cart.

  Args:
    shipping_address: The user's selected shipping address.
    tool_context: The ADK supplied tool context.
    debug_mode: Whether the agent is in debug mode.

  Returns:
    The updated CartMandate.
  """
  chosen_cart_id = tool_context.state["chosen_cart_id"]
  if not chosen_cart_id:
    raise RuntimeError("No chosen cart mandate found in tool context state.")

  message = (
      A2aMessageBuilder()
      .set_context_id(tool_context.state["shopping_context_id"])
      .add_text("Update the cart with the user's shipping address.")
      .add_data("cart_id", chosen_cart_id)
      .add_data("shipping_address", shipping_address)
      .add_data("shopping_agent_id", "soho_shopping_agent")
      .add_data("debug_mode", debug_mode)
      .build()
  )
  task = await merchant_agent_client.send_a2a_message(message)

  updated_cart_mandate = artifact_utils.only(
      _parse_cart_mandates(task.artifacts)
  )

  # Ensure it's a CartMandate object, not a dict
  if isinstance(updated_cart_mandate, dict):
    updated_cart_mandate = CartMandate(**updated_cart_mandate)

  tool_context.state["cart_mandate"] = updated_cart_mandate
  tool_context.state["shipping_address"] = shipping_address

  return updated_cart_mandate


def create_soho_payment_mandate(
    payment_method_alias: str,
    user_email: str,
    tool_context: ToolContext,
) -> str:
  """Creates a payment mandate with SOHO Credit details.

  Args:
    payment_method_alias: The SOHO Credit payment method alias.
    user_email: The user's email address.
    tool_context: The ADK supplied tool context.

  Returns:
    The payment mandate.
  """
  cart_mandate = tool_context.state["cart_mandate"]
  selected_plan = tool_context.state["selected_payment_plan"]
  credit_auth_token = tool_context.state["credit_authorization_token"]

  payment_request = cart_mandate.contents.payment_request
  shipping_address = tool_context.state["shipping_address"]

  # Create payment response with SOHO Credit details
  payment_response = PaymentResponse(
      request_id=payment_request.details.id,
      method_name="SOHO_CREDIT",
      details={
          "token": tool_context.state["payment_credential_token"],
          "authorization_token": credit_auth_token,
          "borrower_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",  # From SOHO
          "payment_plan": selected_plan,
      },
      shipping_address=shipping_address,
      payer_email=user_email,
  )

  payment_mandate = PaymentMandate(
      payment_mandate_contents=PaymentMandateContents(
          payment_mandate_id=uuid.uuid4().hex,
          timestamp=datetime.now(timezone.utc).isoformat(),
          payment_details_id=payment_request.details.id,
          payment_details_total=payment_request.details.total,
          payment_response=payment_response,
          merchant_agent=cart_mandate.contents.merchant_name,
      ),
  )

  tool_context.state["payment_mandate"] = payment_mandate
  return payment_mandate


def attach_biometric_attestation(tool_context: ToolContext) -> str:
  """Attaches biometric attestation to the payment mandate.

  This simulates the secure signing that would happen on a user's device.
  In production, this would use the device's secure element.

  Args:
      tool_context: The context object used for state management.

  Returns:
      A string representing the biometric attestation.
  """
  payment_mandate: PaymentMandate = tool_context.state["payment_mandate"]
  cart_mandate: CartMandate = tool_context.state["cart_mandate"]
  biometric_approval = tool_context.state["biometric_approval"]

  cart_mandate_hash = _generate_cart_mandate_hash(cart_mandate)
  payment_mandate_hash = _generate_payment_mandate_hash(
      payment_mandate.payment_mandate_contents
  )

  # Attach the biometric attestation from SOHO mobile app
  # Convert the attestation dict to a JSON string as PaymentMandate.user_authorization expects a string
  payment_mandate.user_authorization = json.dumps(biometric_approval["attestation"])

  tool_context.state["signed_payment_mandate"] = payment_mandate
  return str(payment_mandate.user_authorization)


async def initiate_payment(tool_context: ToolContext, debug_mode: bool = False):
  """Initiates a payment using the payment mandate from state.

  Args:
    tool_context: The ADK supplied tool context.
    debug_mode: Whether the agent is in debug mode.

  Returns:
    The status of the payment initiation.
  """
  payment_mandate = tool_context.state["signed_payment_mandate"]
  if not payment_mandate:
    raise RuntimeError("No signed payment mandate found in tool context state.")
  risk_data = tool_context.state["risk_data"]
  if not risk_data:
    raise RuntimeError("No risk data found in tool context state.")

  outgoing_message_builder = (
      A2aMessageBuilder()
      .set_context_id(tool_context.state["shopping_context_id"])
      .add_text("Initiate a payment with SOHO Credit")
      .add_data(PAYMENT_MANDATE_DATA_KEY, payment_mandate)
      .add_data("risk_data", risk_data)
      .add_data("shopping_agent_id", "soho_shopping_agent")
      .add_data("debug_mode", debug_mode)
      .build()
  )
  task = await merchant_agent_client.send_a2a_message(outgoing_message_builder)
  store_receipt_if_present(task, tool_context)
  tool_context.state["initiate_payment_task_id"] = task.id

  # Extract transaction details from artifacts
  all_data = artifact_utils.get_first_data_part(task.artifacts)
  transaction_hash = all_data.get("transaction_hash", "N/A")
  transaction_id = all_data.get("transaction_id", "N/A")
  block_number = all_data.get("block_number", "N/A")
  gas_used = all_data.get("gas_used", "N/A")
  amount_formatted = all_data.get("amount_formatted", "N/A")

  return {
      "status": str(task.status),
      "transaction_hash": transaction_hash,
      "transaction_id": transaction_id,
      "block_number": block_number,
      "gas_used": gas_used,
      "amount_formatted": amount_formatted,
      "payment_result": all_data.get("payment_result", {})
  }


def store_receipt_if_present(task, tool_context: ToolContext) -> None:
  """Stores the payment receipt in state."""
  payment_receipts = artifact_utils.find_canonical_objects(
      task.artifacts, PAYMENT_RECEIPT_DATA_KEY, PaymentReceipt
  )
  if payment_receipts:
    payment_receipt = artifact_utils.only(payment_receipts)
    tool_context.state["payment_receipt"] = payment_receipt


def _generate_cart_mandate_hash(cart_mandate: CartMandate) -> str:
  """Generates a cryptographic hash of the CartMandate.

  Note: This is a placeholder implementation for development.
  """
  return "fake_cart_mandate_hash_" + cart_mandate.contents.id


def _generate_payment_mandate_hash(
    payment_mandate_contents: PaymentMandateContents,
) -> str:
  """Generates a cryptographic hash of the PaymentMandateContents.

  Note: This is a placeholder implementation for development.
  """
  return (
      "fake_payment_mandate_hash_" + payment_mandate_contents.payment_mandate_id
  )


def _parse_cart_mandates(artifacts: list[Artifact]) -> list[CartMandate]:
  """Parses a list of artifacts into a list of CartMandate objects."""
  return artifact_utils.find_canonical_objects(
      artifacts, CART_MANDATE_DATA_KEY, CartMandate
  )
