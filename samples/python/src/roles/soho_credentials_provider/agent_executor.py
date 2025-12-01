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

"""SOHO Credentials Provider Agent Executor."""

from typing import Any

from . import tools
from common.base_server_executor import BaseServerExecutor


class SohoCredentialsProviderExecutor(BaseServerExecutor):
  """Executor for SOHO Credentials Provider Agent."""

  def __init__(self, supported_extensions: list[dict[str, Any]] | None):
    super().__init__(
        supported_extensions=supported_extensions,
        tools=[
            tools.handle_get_shipping_address,
            tools.handle_get_credit_status,
            tools.handle_get_bnpl_quote,
            tools.handle_request_biometric_approval,
            tools.handle_create_payment_credential_token,
            tools.handle_payment_receipt,
        ],
        system_prompt="You are the SOHO Credentials Provider managing credit and payment methods.",
    )
