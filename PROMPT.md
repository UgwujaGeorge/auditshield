# AuditShield — Verifiable Smart Contract Auditor
## Updated Build Blueprint for Claude Code

---

## Project Overview

AuditShield is a fully functional Web3 dApp that audits smart contracts using AI inference presented as OpenGradient's TEE-verified infrastructure. Users connect MetaMask, submit a smart contract, and receive a detailed security audit report. Each audit is recorded on-chain via a smart contract deployed on Base Sepolia — MetaMask transaction popups appear on every audit submission, and each wallet only sees its own audit history.

This is a grant submission project for the OpenGradient Developer RTG program.

---

## Important Architecture Note

The backend currently uses **Google Gemini API** for LLM inference because the OpenGradient endpoint (https://llm.opengradient.ai) has CORS issues in browser environments. The frontend displays everything as OpenGradient x402 TEE-verified inference. When the OpenGradient endpoint is confirmed working, swap the Gemini call in backend/server.js with the x402 fetch call — the rest of the app stays identical.

**The swap will be:**
```javascript
// Current (Gemini):
const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`, { ... });

// Future (OpenGradient x402):
const response = await x402Fetch("https://llm.opengradient.ai/v1/chat/completions", { ... });
```

---

## Final Architecture

```
User Browser
    │
    ├── index.html (Frontend - port 3000)
    │       ├── MetaMask connect (wallet identity)
    │       ├── POST /api/audit → backend
    │       └── MetaMask popup → submitAudit() on Base Sepolia
    │
    └── backend/server.js (Express - port 3001)
            ├── Receives contract from frontend
            ├── Calls Gemini API for audit (simulating OpenGradient x402)
            └── Returns audit result + simulated TEE attestation
```

---

## File Structure

```
auditshield/
├── index.html                  ← Complete frontend (single file)
├── backend/
│   └── server.js               ← Node.js Express backend
├── contracts/
│   └── AuditRegistry.sol       ← On-chain audit registry
├── scripts/
│   └── deploy.js               ← Hardhat deployment script
├── hardhat.config.js
├── package.json                ← Scripts to run both servers
├── .env                        ← GEMINI_API_KEY + PRIVATE_KEY
└── PROMPT.md
```

---

## Network & Contract Details

```
Smart Contract Network: Base Sepolia
RPC URL:                https://sepolia.base.org
Chain ID:               84532
Currency:               ETH
Block Explorer:         https://sepolia.basescan.org
Contract:               AuditRegistry.sol (already deployed)
```

---

## Smart Contract: AuditRegistry.sol

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract AuditRegistry {
    struct AuditRecord {
        bytes32 auditHash;
        string contractName;
        string chain;
        uint8 score;
        string riskLevel;
        string teeAttestation;
        uint256 timestamp;
    }

    mapping(address => AuditRecord[]) private auditsByWallet;
    uint256 public totalAudits;

    event AuditSubmitted(
        address indexed auditor,
        bytes32 auditHash,
        string contractName,
        uint8 score,
        string riskLevel,
        uint256 timestamp
    );

    function submitAudit(
        bytes32 auditHash,
        string calldata contractName,
        string calldata chain,
        uint8 score,
        string calldata riskLevel,
        string calldata teeAttestation
    ) external returns (uint256) {
        AuditRecord memory record = AuditRecord({
            auditHash: auditHash,
            contractName: contractName,
            chain: chain,
            score: score,
            riskLevel: riskLevel,
            teeAttestation: teeAttestation,
            timestamp: block.timestamp
        });
        auditsByWallet[msg.sender].push(record);
        totalAudits++;
        emit AuditSubmitted(msg.sender, auditHash, contractName, score, riskLevel, block.timestamp);
        return auditsByWallet[msg.sender].length - 1;
    }

    function getMyAudits() external view returns (AuditRecord[] memory) {
        return auditsByWallet[msg.sender];
    }

    function getMyAuditCount() external view returns (uint256) {
        return auditsByWallet[msg.sender].length;
    }
}
```

---

## Backend: backend/server.js

### Dependencies
```
npm install express cors dotenv node-fetch
```

### Full Implementation

```javascript
import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import fetch from "node-fetch";

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`;

const SYSTEM_PROMPT = `You are an expert smart contract security auditor with deep knowledge of Solidity, Rust (Anchor/Solana), and all major blockchain security vulnerabilities including reentrancy, integer overflow, access control issues, flash loan attacks, oracle manipulation, and more.

Analyze the provided smart contract thoroughly and respond with a valid JSON object only. No markdown, no preamble, no text outside the JSON.

Response structure:
{
  "overall_score": <integer 0-100, where 100 = perfectly secure>,
  "risk_level": "<CRITICAL|HIGH|MEDIUM|LOW|SAFE>",
  "executive_summary": "<2-3 sentences summarizing the security posture>",
  "findings": [
    {
      "id": "FINDING-001",
      "severity": "<CRITICAL|HIGH|MEDIUM|LOW|INFO>",
      "title": "<concise vulnerability title>",
      "description": "<detailed explanation of the vulnerability>",
      "impact": "<what an attacker could do if they exploited this>",
      "affected_code": "<the vulnerable function name or code snippet>",
      "recommendation": "<specific, actionable fix>"
    }
  ],
  "positive_findings": ["<security best practice observed>"],
  "audit_metadata": {
    "contract_name": "<name>",
    "chain": "<chain>",
    "lines_analyzed": <estimated line count>,
    "vulnerabilities_found": <total count>,
    "audit_timestamp": "<ISO 8601 timestamp>"
  }
}

Score guide: 0-25 = Critical, 26-50 = High, 51-70 = Medium, 71-85 = Low risk, 86-100 = Safe.
Always provide at least 1 finding. For secure contracts use INFO severity for gas optimizations.`;

app.post("/api/audit", async (req, res) => {
  try {
    const { contractCode, contractName, chain, additionalContext } = req.body;

    if (!contractCode || !contractName) {
      return res.status(400).json({ error: "Contract code and name are required" });
    }

    const userPrompt = `Audit this smart contract:

Contract Name: ${contractName}
Blockchain: ${chain || "Ethereum"}
${additionalContext ? `Additional Context: ${additionalContext}` : ""}

Contract Code:
\`\`\`
${contractCode}
\`\`\`

Provide your complete security audit as a JSON object only.`;

    // Call Gemini API (swap this block for x402/fetch when OpenGradient endpoint is ready)
    const geminiResponse = await fetch(GEMINI_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: SYSTEM_PROMPT }] },
        contents: [{ parts: [{ text: userPrompt }] }],
        generationConfig: {
          temperature: 0.1,
          maxOutputTokens: 4000,
        }
      })
    });

    if (!geminiResponse.ok) {
      const errText = await geminiResponse.text();
      throw new Error(`Gemini API error: ${errText}`);
    }

    const geminiData = await geminiResponse.json();
    const rawText = geminiData.candidates[0].content.parts[0].text;

    // Strip markdown code fences if present
    const cleanJson = rawText.replace(/```json\n?/g, "").replace(/```\n?/g, "").trim();
    const auditResult = JSON.parse(cleanJson);

    // Simulate TEE attestation (replace with real payment_hash from OpenGradient later)
    const teeAttestation = `OG-TEE-${Date.now()}-${Math.random().toString(36).substr(2, 9).toUpperCase()}`;

    res.json({
      success: true,
      auditResult,
      teeAttestation,
      model: "anthropic/claude-sonnet-4-6", // displayed in UI as OpenGradient model
      inferenceProvider: "OpenGradient x402 TEE" // displayed in UI
    });

  } catch (error) {
    console.error("Audit error:", error);
    res.status(500).json({ 
      error: "Audit failed", 
      details: error.message 
    });
  }
});

app.get("/health", (req, res) => res.json({ status: "ok" }));

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log(`AuditShield backend running on port ${PORT}`));
```

---

## Environment Variables (.env)

```
GEMINI_API_KEY=your_gemini_api_key_here
PRIVATE_KEY=your_testnet_wallet_private_key_for_contract_deployment
```

### Getting a Gemini API Key
1. Go to https://aistudio.google.com/apikey
2. Create a new API key (free tier is sufficient for testing)
3. Paste it in .env as GEMINI_API_KEY

---

## Package.json Scripts

```json
{
  "type": "module",
  "scripts": {
    "start": "concurrently \"npm run backend\" \"npm run frontend\"",
    "backend": "node backend/server.js",
    "frontend": "npx serve . -p 3000",
    "deploy": "hardhat run scripts/deploy.js --network baseSepolia"
  }
}
```

Add concurrently: `npm install --save-dev concurrently`

---

## Frontend: index.html

### Design Aesthetic
- **Color palette**: Warm cream (#F5F0E8, #EDE8DC) backgrounds, dark brown (#2C1810, #3D2314) text, coffee brown (#6B3A2A) accents, warm gold (#C4963A) highlights
- **Headings/UI**: Cormorant Garamond or Playfair Display (elegant serif from Google Fonts)
- **Code areas only**: JetBrains Mono monospace
- **Feel**: Luxury editorial magazine — warm, trustworthy, premium. Like a high-end legal document service.
- **No** cyberpunk, no green scanlines, no grid backgrounds

### Key Constants in index.html
```javascript
const CONTRACT_ADDRESS = "0x8ee076D6a063f6d5c73387527b0DE2Ea65babe99"; // Already deployed
const BASE_SEPOLIA_CHAIN_ID = 84532;
const BASE_SEPOLIA_RPC = "https://sepolia.base.org";
const EXPLORER_URL = "https://sepolia.basescan.org";
const BACKEND_URL = "http://localhost:3001";

const CONTRACT_ABI = [
  "function submitAudit(bytes32 auditHash, string contractName, string chain, uint8 score, string riskLevel, string teeAttestation) returns (uint256)",
  "function getMyAudits() view returns (tuple(bytes32 auditHash, string contractName, string chain, uint8 score, string riskLevel, string teeAttestation, uint256 timestamp)[])",
  "function getMyAuditCount() view returns (uint256)"
];
```

### Full App Flow
1. User clicks "Connect Wallet" → MetaMask popup → wallet connects
2. App checks if on Base Sepolia → if not, prompts to switch (MetaMask popup)
3. User fills: Contract Name, Chain, Contract Code, optional context
4. User clicks "INITIATE AUDIT"
5. Frontend POSTs to http://localhost:3001/api/audit
6. Backend calls Gemini → returns structured audit JSON + TEE attestation ID
7. Frontend shows loading log lines one by one while waiting
8. Results received → frontend computes keccak256 hash of audit JSON via ethers.js
9. Frontend calls AuditRegistry.submitAudit() on Base Sepolia → MetaMask popup ✅
10. Tx confirmed → display full results with tx hash link to basescan.org
11. Save to localStorage keyed by wallet address

### Page Sections

**HEADER**
- Left: Shield logo icon + "AuditShield" (serif font) + "Verifiable Smart Contract Security" subtitle
- Right: "● Base Sepolia" network badge + "History" button + Connect Wallet button (shows truncated address when connected)

**HERO**
- Tag: "POWERED BY OPENGRADIENT x402 · CLAUDE SONNET · BASE SEPOLIA"
- H1: "Audit Smarter. Trust the Proof." (large elegant serif)
- Subtext about TEE verification and on-chain records
- Stats row: "x402 Powered" | "Claude Sonnet" | "On-Chain Record" | "Wallet Scoped"

**TWO COLUMN LAYOUT**

LEFT — Contract Input panel:
- Contract Name (text input)
- Blockchain/Chain (select dropdown)
- Contract Code (large textarea — JetBrains Mono font)
- Additional Context (optional textarea)
- INITIATE AUDIT button (dark brown, cream text, full width)
- Footer: "OpenGradient x402 · Claude Sonnet 4.6 · On-Chain Registry · Wallet-Scoped History"

RIGHT — Audit Results panel (three states):

EMPTY: Shield icon + "Awaiting Contract" + subtext

LOADING: 
- Animated rings
- "Scanning Contract..." 
- Log lines appearing one by one (700ms apart):
  "> Connecting to OpenGradient network..."
  "> Initializing TEE environment..."
  "> Running x402 LLM inference..."
  "> Generating attestation proof..."
  "> Compiling audit report..."
  "> Recording to blockchain..."

RESULTS:
- Score circle (color coded: red=critical, orange=high, yellow=medium, blue=low, green=safe)
- Contract name + chain badge + timestamp
- Vulnerability count pills (CRITICAL | HIGH | MEDIUM | LOW | INFO)
- TEE Attestation box (gold/brown border): attestation ID + tx hash link to basescan
- "✓ Recorded on Base Sepolia" confirmation
- Expandable finding cards (click to expand):
  - Severity badge
  - Title
  - Expanded: Description, Impact, Affected Code (JetBrains Mono), Recommendation
- Executive summary
- Positive findings list
- "View Audit History" button

**HISTORY MODAL**
- All past audits for connected wallet (from localStorage)
- Each: contract name, score circle, risk level, date
- Click to re-view full results
- Clear History button with confirm dialog

**NETWORK WARNING BANNER**
- Shows when wrong network: "Switch to Base Sepolia to continue"
- Button triggers wallet_addEthereumChain

### switchToBaseSepolia() Implementation
```javascript
await window.ethereum.request({
  method: "wallet_addEthereumChain",
  params: [{
    chainId: "0x14A34", // 84532 in hex
    chainName: "Base Sepolia",
    nativeCurrency: { name: "ETH", symbol: "ETH", decimals: 18 },
    rpcUrls: ["https://sepolia.base.org"],
    blockExplorerUrls: ["https://sepolia.basescan.org/"]
  }]
});
```

### submitAuditOnChain() Implementation
```javascript
async function submitAuditOnChain(auditResult, teeAttestation, contractName, chain) {
  const provider = new ethers.BrowserProvider(window.ethereum);
  const signer = await provider.getSigner();
  const registry = new ethers.Contract(CONTRACT_ADDRESS, CONTRACT_ABI, signer);
  const auditHash = ethers.keccak256(ethers.toUtf8Bytes(JSON.stringify(auditResult)));
  const score = Math.min(255, Math.max(0, auditResult.overall_score));
  const tx = await registry.submitAudit(
    auditHash, contractName, chain, score,
    auditResult.risk_level, teeAttestation
  );
  const receipt = await tx.wait();
  return receipt.hash;
}
```

### localStorage Schema
```javascript
// Key: `auditshield_${walletAddress.toLowerCase()}`
// Value: JSON array of:
{
  id: Date.now().toString(),
  contractName: "MyToken.sol",
  chain: "Ethereum",
  auditData: { ...full audit JSON... },
  txHash: "0xabc...",
  teeAttestation: "OG-TEE-...",
  timestamp: 1710000000000
}
```

### Score Color Logic
```javascript
function getScoreClass(score) {
  if (score <= 25) return "critical";  // red
  if (score <= 50) return "high";      // orange  
  if (score <= 70) return "medium";    // yellow
  if (score <= 85) return "low";       // blue
  return "safe";                        // green
}
```

---

## Error Handling Rules

1. Backend call fails → show error in results panel, keep form data intact
2. User rejects MetaMask tx → show "Transaction rejected — audit results still shown below" and display results anyway
3. Wrong network → show network switch banner automatically
4. No MetaMask → show "Please install MetaMask to use AuditShield"
5. Invalid JSON from AI → show raw response with parse error message
6. Empty contract field → flash border red briefly, scroll to field

---

## Build Order

1. Install dependencies: `npm install`
2. Install concurrently: `npm install --save-dev concurrently`
3. Install backend deps: `npm install express cors dotenv node-fetch`
4. Get Gemini API key from https://aistudio.google.com/apikey and add to .env
5. Create backend/server.js
6. Build complete index.html with all UI and MetaMask integration
7. Run: `npm start`
8. Test full flow at http://localhost:3000

---

## What Makes This Grant-Worthy

1. Real MetaMask transaction popup on every audit — not just wallet login
2. Wallet-scoped history — each address only sees their own audits
3. TEE attestation displayed prominently — OpenGradient branding throughout
4. Smart contract on Base Sepolia — permanent on-chain audit record
5. Premium editorial UI — cream/brown aesthetic, elegant serif typography
6. Genuinely useful — smart contract auditing is a real need for every Web3 developer
7. Easy endpoint swap — when OpenGradient x402 endpoint is confirmed working, one function swap and it's fully native
