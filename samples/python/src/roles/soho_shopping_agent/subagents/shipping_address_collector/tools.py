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

"""Tools used by the shipping address collector subagent.

Each agent uses individual tools to handle distinct tasks throughout the
shopping and purchasing process.
"""

from a2a.types import Artifact
from google.adk.tools.tool_context import ToolContext

from ap2.types.contact_picker import CONTACT_ADDRESS_DATA_KEY
from ap2.types.contact_picker import ContactAddress
from common import artifact_utils
from common.a2a_message_builder import A2aMessageBuilder
from roles.soho_shopping_agent.remote_agents import soho_credentials_provider_client as credentials_provider_client


async def get_shipping_addresses(
    user_email: str,
    tool_context: ToolContext,
) -> dict:
  """Gets all available shipping addresses from the credentials provider.

  Args:
    user_email: The ID of the user to get the shipping addresses for.
    tool_context: The ADK supplied tool context.

  Returns:
    A dictionary with shipping addresses keyed by location (home, upcountry, office).
  """
  message = (
      A2aMessageBuilder()
      .set_context_id(tool_context.state["shopping_context_id"])
      .add_text("Get all of the user's shipping addresses.")
      .add_data("user_email", user_email)
      .build()
  )
  task = await credentials_provider_client.send_a2a_message(message)
  addresses = _parse_addresses(task.artifacts)
  # Return all addresses as a dictionary
  result = {}
  for addr in addresses:
    # Assume the tool returns addresses with a 'label' or 'id' field
    if hasattr(addr, 'label'):
      key = addr.label.lower()
    elif hasattr(addr, 'organization'):
      key = 'office'
    else:
      key = 'home'
    result[key] = addr
  return result


async def select_shipping_address(
    user_email: str,
    address_key: str,
    tool_context: ToolContext,
) -> ContactAddress:
  """Selects a specific shipping address for the user.

  Args:
    user_email: The ID of the user.
    address_key: The key of the address to select (home, upcountry, office).
    tool_context: The ADK supplied tool context.

  Returns:
    The selected shipping address.
  """
  message = (
      A2aMessageBuilder()
      .set_context_id(tool_context.state["shopping_context_id"])
      .add_text(f"Get the user's {address_key} shipping address.")
      .add_data("user_email", user_email)
      .add_data("address_key", address_key)
      .build()
  )
  task = await credentials_provider_client.send_a2a_message(message)
  shipping_address = artifact_utils.only(_parse_addresses(task.artifacts))
  return shipping_address


def _parse_addresses(artifacts: list[Artifact]) -> list[ContactAddress]:
  """Parses a list of artifacts into a list of ContactAddress objects."""
  return artifact_utils.find_canonical_objects(
      artifacts, CONTACT_ADDRESS_DATA_KEY, ContactAddress
  )
