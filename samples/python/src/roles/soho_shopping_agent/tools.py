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

  message = (
      A2aMessageBuilder()
      .set_context_id(tool_context.state["shopping_context_id"])
      .add_text("Get the BNPL quote for the user")
      .add_data("user_email", "user@example.com")  # In production, get from auth
      .add_data("amount", total_amount)
      .add_data("merchant_name", merchant_name)
      .add_data("debug_mode", debug_mode)
      .build()
  )

  task = await soho_credentials_provider_client.send_a2a_message(message)
  bnpl_quote = artifact_utils.find_data_part("bnpl_quote", task.artifacts)

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

  total_amount = cart_mandate.contents.payment_request.details.total.amount.value
  merchant_name = cart_mandate.contents.merchant_name

  message = (
      A2aMessageBuilder()
      .set_context_id(tool_context.state["shopping_context_id"])
      .add_text("Request biometric approval for purchase")
      .add_data("user_email", "user@example.com")
      .add_data("amount", total_amount)
      .add_data("merchant", merchant_name)
      .add_data("payment_plan", selected_plan)
      .add_data("debug_mode", debug_mode)
      .build()
  )

  task = await soho_credentials_provider_client.send_a2a_message(message)
  biometric_approval = artifact_utils.find_data_part("biometric_approval", task.artifacts)

  tool_context.state["biometric_approval"] = biometric_approval
  return biometric_approval


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
  payment_mandate.user_authorization = biometric_approval["attestation"]

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
  return task.status


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
