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

"""SOHO Credentials Provider Agent.

This agent manages SOHO Credit as the credentials provider, handling:
- User credit limits and availability
- Shipping addresses
- BNPL (Buy Now Pay Later) payment plans
- Biometric authentication and approval
- OAuth token management
"""

from collections.abc import Sequence

from absl import app
from roles.soho_credentials_provider.agent_executor import SohoCredentialsProviderExecutor
from common import server

AGENT_PORT = 8005


def main(argv: Sequence[str]) -> None:
  agent_card = server.load_local_agent_card(__file__)
  server.run_agent_blocking(
      port=AGENT_PORT,
      agent_card=agent_card,
      executor=SohoCredentialsProviderExecutor(agent_card.capabilities.extensions),
      rpc_url="/a2a/soho_credentials_provider",
  )


if __name__ == "__main__":
  app.run(main)
