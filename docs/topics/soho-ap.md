# SOHO – On-Chain Credit Layer for Humans & AI Agents

SOHO is a **stablecoin credit layer** that lets:

- 🧍 Humans get **spending power** (BNPL-style) without prefunding.
- 🤖 AI agents pay using **SOHO credit**, not a prefunded wallet.
- 🏪 Merchants accept **“Pay with SOHO”** online / in-app / POS and get stablecoin settlement.

There are **two main product surfaces**:

1. **SOHO Consumer + Merchant App (Phase 1)**
   - Borrowers get credit (spending power) and repay later.
   - Merchants accept SOHO payments (QR / button / API) and receive funds.

2. **Agentic Commerce / x402 Integration (Phase 2)**
   - AI agents integrate via SDK / APIs.
   - Agents can ping SOHO to pay merchants using credit, no prefunded wallet.

---

## 1. High-Level Architecture

### On-Chain Layer (EVM, likely Base L2)

Core contracts:

- `Vault.sol`
  - ERC-4626 vault that accepts **USDC** deposits from lenders.
  - Mints **Vault Shares** (LP tokens) representing proportional ownership.
  - Integrates with yield source (e.g. Aave on Base) to generate yield.
  - Yield automatically increases `totalAssets()`, so each share is worth more over time.

- `CreditManager.sol`
  - Tracks **human credit limits** and **used credit** (spending power).
  - Authorizes credit pulls for:
    - Human-initiated payments (SOHO app / web checkout).
    - Agent-initiated payments (x402 / MCP / SDK).
  - Enforces risk rules:
    - Per-user monthly credit cap.
    - Micro-limit for agents (e.g. $10/day).
    - Status: `ACTIVE`, `PAST_DUE`, `FROZEN`.

- `MerchantSettlement.sol`
  - Tracks **merchant balances** on SOHO.
  - When a payment is authorized:
    - Pulls funds from `Vault` (USDC) or internal accounting pool.
    - Credits merchant’s **internal SOHO balance**.
  - Merchant can request:
    - On-chain withdrawal (USDC to their wallet).
    - Off-ramp (via Coinflow / other partner → fiat bank).

- `AccountRegistry.sol`
  - Maps identities:
    - `userId` → `walletAddress` (e.g. MetaMask via Privy).
    - `agentId` → `userId` (agent credit belongs to a KYC’d human).
    - `merchantId` → `merchantWallet` (embedded or external).

Tools / Frameworks:

- **Language**: Solidity
- **Framework**: Foundry
- **Standards**: ERC-20, ERC-4626
- **Security**:
  - OpenZeppelin: `ReentrancyGuard`, `Ownable`, `Pausable`.
  - CEI (Checks-Effects-Interactions) pattern.
  - Role-based admin functions.

---

## 2. Off-Chain Backend

Backend = the **orchestration layer** between app / agents and on-chain contracts.

- **Tech Stack**
  - Node.js + TypeScript
  - NestJS (or Express) for API
  - PostgreSQL (users, risk, KYC, transactions, logs)
  - Redis (rate limiting, session/state)
  - Message queue (e.g. BullMQ / RabbitMQ) for async jobs
  - Privy (or similar) for identity & wallet linking
  - Coinflow (or similar) for ACH / off-ramp / card repayments

Responsibilities:

- **User mgmt**: sign-up, role (lender / borrower / merchant), KYC state.
- **Credit engine**: assign & update credit limits, track utilization.
- **Payment orchestration**: map API calls → contract calls → confirmations.
- **Webhooks**: from on-chain events (via Alchemy/Blocknative/Tenderly).
- **Risk & controls**: per-user & per-agent spending limits.
- **Audit logging**: all critical API calls & AI actions for compliance.

---

## 3. Frontend Surfaces

### 3.1 SOHO Consumer App (Mobile – Flutter / React Native)

Core UX:

- Sign up / Login
- Connect wallet (MetaMask / Privy embedded)
- KYC flow
- See **Spending Power** (credit limit, used vs remaining)
- Transaction list (what they spent, where, when, via human or agent)
- Repayment:
  - Pay statement now (USDC / card / bank)
  - See next due date & schedule
- Agent connections:
  - See linked agents (ChatGPT, Claude, Replit agent, etc.)
  - Set agent limits:
    - e.g. “Maximum micro-spend: $5/day”
    - Require approval for > $X

### 3.2 Merchant Dashboard (Web – Next.js)

Core UX:

- Register business
- KYC/boarding (light at first, stricter later)
- Generate **API keys** & **Merchant ID**
- See “Pay with SOHO” integration docs + SDK
- Transaction history (SOHO payments, refunds, disputes)
- Balance view:
  - On-chain wallet balance
  - SOHO internal balance (settled but not yet withdrawn)
- Withdraw options:
  - Withdraw USDC → wallet
  - Off-ramp → fiat (via Coinflow or similar)
- Settings:
  - Webhook URLs (payment succeeded / failed)
  - Allowed currencies (USDC first, more later)

---

## 4. Core User Journeys

### 4.1 Lender Journey (Vault)

1. Lender connects wallet and deposits **USDC**.
2. Backend calls `Vault.deposit()` and mints **Vault Shares** to lender.
3. Yield is generated automatically over time via Aave integration.
4. When lender withdraws:
   - `Vault.redeem(shares)` → lender receives principal + yield.
   - A small % of yield can be skimmed to protocol treasury.

---

### 4.2 Borrower Journey (Human Credit)

1. User signs up in SOHO app.
2. Passes KYC via Privy / 3rd party.
3. Backend creates `userId`, registers in `AccountRegistry`.
4. Risk engine assigns initial **Spending Power** (e.g. $100).
5. User sees `$100 Spending Power` in app (but no stablecoins in their wallet).
6. User “Pays with SOHO” online or QR:
   - Backend calls `CreditManager.authorizePayment(userId, amount)`.
   - If approved, `MerchantSettlement` credits merchant + `Vault` debits.
7. User later repays in:
   - USDC from wallet, or
   - Fiat via ACH / card (Coinflow/etc), which backend converts to USDC and returns to `Vault`.

---

### 4.3 Merchant Journey

1. Merchant signs up on SOHO Merchant Dashboard.
2. Gets `merchantId` + API keys.
3. Integrates:
   - “Pay with SOHO” button on checkout, **or**
   - POS plugin (Square/Toast/Clover later).
4. When consumer/agent pays:
   - Merchant receives confirmed payment + callback.
   - Merchant dashboard shows new balance.
5. Merchant keeps funds in SOHO (optional yield or XP in future)
   or withdraws to wallet / fiat.

---

### 4.4 Agentic Commerce Journey (Agent Using SOHO Credit)

**This is the new piece Philip is pushing.**

Example:
Sara has a SOHO account & $100 credit limit. She connects her SOHO account to an AI shopping agent.

1. Sara links SOHO inside ChatGPT / Claude / Replit agent:
   - OAuth-style: SOHO account → grants agent an `agentId`,
   - Sets micro-limit: e.g. `$10/day for API/micro transactions`.

2. Agent wants to access an x402-protected API or buy a digital product:
   - Calls SOHO `POST /agent/pay` with:
     - `agentId`, `merchantId/merchantWallet`, `amount`, `reason`.

3. Backend flow:
   - Resolve `agentId → userId` via `AccountRegistry`.
   - Check:
     - user’s total credit limit and used credit.
     - micro-limit for that agent and day.
   - If OK:
     - Call `CreditManager.authorizeAgentPayment(userId, agentId, amount)`.
     - Call settlement contract to pay merchant in USDC.

4. Merchant receives stablecoin as usual (no difference from human-initiated flow).

5. Sara sees:
   - “Agent Purchase – $0.37 – ‘Data API calls’” in her SOHO app.
   - Weekly/biweekly repayment schedule.

6. If agent hits the daily limit (e.g. $10), SOHO:
   - Rejects further payments, and/or
   - Sends push: “Your agent used $10. Approve more?”

---

## 5. Backend API – Minimum Spec (v1)

> These should be REST (or GraphQL) APIs behind auth (JWT/session).

### 5.1 Auth & Identity

**POST `/auth/signup`**

- Inputs: email, password, role(s): `["borrower"] | ["lender"] | ["merchant"] | combo`
- Output: `userId`, auth tokens.

**POST `/auth/login`**

- Standard credentials → tokens.

**POST `/auth/link-wallet`**

- Wallet signature → link `walletAddress` to `userId`.

---

### 5.2 Lender APIs

**POST `/lender/deposit`**

- Inputs: `amount`
- Flow:
  - Generate on-chain tx / contract call data
  - Lender signs & sends
  - Backend listens to `Deposit` event and updates DB.

**POST `/lender/withdraw`**

- Inputs: `shares` or `amount`
- Flow:
  - Call `Vault.redeem()`
  - Return to lender wallet.

---

### 5.3 Borrower / Credit APIs

**GET `/credit/limit`**

- Returns:
  - `totalLimit`
  - `usedAmount`
  - `availableAmount`
  - `dueDate`, `minPayment`, etc.

**POST `/credit/pay`** (human-initiated payment)

- Inputs:
  - `userId`
  - `merchantId` or `merchantWallet`
  - `amount`
  - `description`

- Flow:
  1. Validate `amount <= availableAmount`.
  2. Call `CreditManager.authorizePayment`.
  3. Call `MerchantSettlement.creditMerchant`.
  4. Return `status: "approved"` + txn ID.

---

### 5.4 Agentic Commerce APIs (Important)

**POST `/agent/register`**

- Used when user links SOHO with an external AI app.
- Inputs:
  - `userId`
  - `agentName` (e.g. "Claude Shopping Agent")
  - `microLimitPerDay`
- Output:
  - `agentId` + `agentSecret` (for the external app).

**POST `/agent/pay`**

- Called by the agent’s backend when it hits an x402 402-payment-required endpoint.
- Inputs:
  ```json
  {
    "agentId": "a_123",
    "merchantId": "m_456",  // or merchantWallet
    "amount": 0.37,
    "currency": "USDC",
    "memo": "API calls for product discovery",
    "type": "micro"        // or "normal"
  }


let create a new branch soho-ap2-v1.0 . What we need to do is update from step 8 where we   need first call
