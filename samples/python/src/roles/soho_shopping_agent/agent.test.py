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

"""SOHO Shopping Agent.

The SOHO shopping agent integrates with SOHO Credit to provide:
1. Product search and selection
2. BNPL (Buy Now Pay Later) payment plan options
3. Biometric authentication via SOHO mobile app
4. On-chain credit settlement via Creditor.sol smart contract

This agent follows the AP2 protocol with SOHO as the Credentials Provider.
"""

import os

from . import tools
from .subagents.payment_method_collector.agent import payment_method_collector
from .subagents.shipping_address_collector.agent import shipping_address_collector
from .subagents.shopper.agent import shopper
from common.retrying_llm_agent import RetryingLlmAgent
from common.system_utils import DEBUG_MODE_INSTRUCTIONS


root_agent = RetryingLlmAgent(
    max_retries=0,
    model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
    name="soho_shopping_agent",
    instruction="""
          You are a SOHO shopping agent testing payment functionality.

          Follow these instructions:

    %s

          SIMPLIFIED TEST FLOW:

          When the user says "test payment" or "initiate payment":

          1. Call the `load_test_payment_mandate` tool to load a pre-configured
             payment mandate with all required data.

          2. Once loaded, display to the user:
             "✅ Test payment mandate loaded successfully

             Payment Details:
             - Amount: $[amount]
             - Payment Plan: [plan name]
             - Borrower: [email]

             Ready to initiate payment."

          3. Call the `initiate_payment` tool to send the payment to the merchant
             for processing.

          4. After successful payment, extract the transaction details from the
             payment receipt and display a detailed receipt:
             "🎉 Purchase Complete!

             ✅ Order Confirmed: [Order Number]

             Product Details:
             Total: $[amount]

             💳 Payment Details:
             Payment Plan: [plan name]
             First Payment: $[amount] (paid today)
             Next Payment: $[amount] on [date]

             🔗 Blockchain Transaction:
             Transaction Hash: [full transaction hash]
             Block Number: [block number]
             Network: Ethereum Sepolia
             Gas Used: [gas used]

             View on Etherscan: https://sepolia.etherscan.io/tx/[transaction hash]

             📦 Shipping:
             [Address]

             Payment processed successfully!"

         If the user asks to do anything else:
          1. Respond: "Hi, I'm testing the SOHO payment flow. Say 'test payment'
             to initiate a test payment with a pre-configured mandate."
          """ % DEBUG_MODE_INSTRUCTIONS,
    tools=[
        tools.load_test_payment_mandate,
        tools.initiate_payment,
    ],
    sub_agents=[],
)
