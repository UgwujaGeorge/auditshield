# AuditShield — Wallet Transaction Fix
## Instructions for Claude Code

---

## What Needs to Be Fixed

Currently when the user clicks "INITIATE AUDIT", the audit runs silently through the backend with no wallet interaction. This needs to change. There should be TWO MetaMask popups every time a user runs an audit:

### Popup 1 — $OPG Token Payment Approval (BEFORE the audit runs)
Before calling the backend, the frontend must request the user to approve spending $OPG tokens on Base Sepolia to pay for the x402 LLM inference.

### Popup 2 — On-Chain Registry Transaction (AFTER the audit completes)
After the audit result comes back, the frontend calls AuditRegistry.submitAudit() on Base Sepolia to record the audit hash on-chain.

---

## OPG Token Details (from OpenGradient docs)

```
Payment Network:  Base Sepolia
Token:            $OPG
Token Address:    0x240b09731D96979f50B2C649C9CE10FcF9C7987F
Chain ID:         84532
```

---

## Full Corrected Flow

1. User connects MetaMask wallet
2. App checks user is on Base Sepolia (Chain ID 84532) — if not, prompts switch
3. User fills in contract details and clicks "INITIATE AUDIT"
4. **POPUP 1** — MetaMask asks user to approve $OPG token spending:
   - Call the $OPG ERC20 token contract's `approve()` function
   - Spender: the backend's payment address OR a fixed small amount (e.g. 0.1 OPG)
   - Token contract: `0x240b09731D96979f50B2C649C9CE10FcF9C7987F` on Base Sepolia
   - User clicks Confirm in MetaMask
5. After approval, frontend sends the audit request to backend (POST /api/audit)
6. Backend calls Gemini API, returns audit result + TEE attestation
7. Loading state shows log lines one by one while waiting
8. Results received from backend
9. **POPUP 2** — MetaMask asks user to confirm the on-chain registry transaction:
   - Calls AuditRegistry.submitAudit() at `0x8ee076D6a063f6d5c73387527b0DE2Ea65babe99`
   - Records the keccak256 hash of the audit JSON on-chain
   - User clicks Confirm in MetaMask
10. Transaction confirmed — show tx hash as clickable link to https://sepolia.basescan.org/tx/TXHASH
11. Full audit results displayed with TEE attestation box showing both the attestation ID and tx hash
12. Audit saved to localStorage keyed by wallet address

---

## OPG Token ABI (only need approve and allowance)

```javascript
const OPG_TOKEN_ABI = [
  "function approve(address spender, uint256 amount) returns (bool)",
  "function allowance(address owner, address spender) view returns (uint256)",
  "function balanceOf(address account) view returns (uint256)"
];

const OPG_TOKEN_ADDRESS = "0x240b09731D96979f50B2C649C9CE10FcF9C7987F";
const OPG_PAYMENT_AMOUNT = ethers.parseUnits("0.1", 18); // 0.1 OPG per audit
```

---

## AuditRegistry Contract (already deployed)

```javascript
const CONTRACT_ADDRESS = "0x8ee076D6a063f6d5c73387527b0DE2Ea65babe99";
const CONTRACT_ABI = [
  "function submitAudit(bytes32 auditHash, string contractName, string chain, uint8 score, string riskLevel, string teeAttestation) returns (uint256)",
  "function getMyAudits() view returns (tuple(bytes32 auditHash, string contractName, string chain, uint8 score, string riskLevel, string teeAttestation, uint256 timestamp)[])",
  "function getMyAuditCount() view returns (uint256)"
];
```

---

## Implementation in index.html

### Step 1 — Check OPG Balance Before Audit
```javascript
async function checkOPGBalance(signer, address) {
  const opgToken = new ethers.Contract(OPG_TOKEN_ADDRESS, OPG_TOKEN_ABI, signer);
  const balance = await opgToken.balanceOf(address);
  if (balance < OPG_PAYMENT_AMOUNT) {
    throw new Error(`Insufficient $OPG balance. You need at least 0.1 OPG on Base Sepolia. Get tokens from https://faucet.opengradient.ai`);
  }
  return balance;
}
```

### Step 2 — Approve OPG Spending (Popup 1)
```javascript
async function approveOPGPayment(signer) {
  const opgToken = new ethers.Contract(OPG_TOKEN_ADDRESS, OPG_TOKEN_ABI, signer);
  
  // Check existing allowance first
  const signerAddress = await signer.getAddress();
  const existingAllowance = await opgToken.allowance(signerAddress, CONTRACT_ADDRESS);
  
  if (existingAllowance >= OPG_PAYMENT_AMOUNT) {
    console.log("Sufficient OPG allowance already exists, skipping approval");
    return null;
  }
  
  // Request approval — this triggers MetaMask Popup 1
  showLoadingLog("> Requesting $OPG payment approval...");
  const approveTx = await opgToken.approve(CONTRACT_ADDRESS, OPG_PAYMENT_AMOUNT);
  showLoadingLog("> Waiting for approval confirmation...");
  await approveTx.wait();
  showLoadingLog("> $OPG payment approved ✓");
  return approveTx.hash;
}
```

### Step 3 — Submit Audit On-Chain (Popup 2)
```javascript
async function submitAuditOnChain(auditResult, teeAttestation, contractName, chain) {
  const provider = new ethers.BrowserProvider(window.ethereum);
  const signer = await provider.getSigner();
  const registry = new ethers.Contract(CONTRACT_ADDRESS, CONTRACT_ABI, signer);
  
  const auditHash = ethers.keccak256(ethers.toUtf8Bytes(JSON.stringify(auditResult)));
  const score = Math.min(255, Math.max(0, auditResult.overall_score));
  
  // This triggers MetaMask Popup 2
  showLoadingLog("> Recording audit on Base Sepolia...");
  const tx = await registry.submitAudit(
    auditHash,
    contractName,
    chain,
    score,
    auditResult.risk_level,
    teeAttestation
  );
  
  showLoadingLog("> Waiting for transaction confirmation...");
  const receipt = await tx.wait();
  showLoadingLog("> Audit recorded on-chain ✓");
  return receipt.hash;
}
```

### Full runAudit() Function
```javascript
async function runAudit() {
  try {
    // Validate inputs
    if (!walletAddress) throw new Error("Please connect your wallet first");
    if (!contractCode.trim()) throw new Error("Please paste your contract code");
    
    showLoadingState();
    
    const provider = new ethers.BrowserProvider(window.ethereum);
    const signer = await provider.getSigner();
    
    // Check OPG balance
    showLoadingLog("> Checking $OPG balance...");
    await checkOPGBalance(signer, walletAddress);
    showLoadingLog("> $OPG balance sufficient ✓");
    
    // Popup 1 — Approve OPG payment
    await approveOPGPayment(signer);
    
    // Call backend for AI audit
    showLoadingLog("> Connecting to OpenGradient network...");
    showLoadingLog("> Initializing TEE environment...");
    showLoadingLog("> Running x402 LLM inference...");
    
    const response = await fetch("http://localhost:3001/api/audit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contractCode, contractName, chain, additionalContext })
    });
    
    if (!response.ok) throw new Error("Backend audit failed");
    const { auditResult, teeAttestation } = await response.json();
    
    showLoadingLog("> Generating attestation proof...");
    showLoadingLog("> Compiling audit report...");
    
    // Popup 2 — Record on-chain
    const txHash = await submitAuditOnChain(auditResult, teeAttestation, contractName, chain);
    
    showLoadingLog("> Audit recorded on-chain ✓");
    
    // Save and display results
    saveAuditToStorage(walletAddress, auditResult, txHash, teeAttestation);
    displayResults(auditResult, txHash, teeAttestation);
    
  } catch (error) {
    showError(error.message);
  }
}
```

---

## Error Messages to Show Users

- No MetaMask: "Please install MetaMask to use AuditShield"
- Wrong network: "Please switch to Base Sepolia to continue"
- Insufficient OPG: "Insufficient $OPG balance. Get tokens from faucet.opengradient.ai"
- User rejects Popup 1: "Payment approval rejected — audit cancelled"
- User rejects Popup 2: "Transaction rejected — audit results still shown below" (still display results)
- Backend fails: Show the specific error message from backend

---

## UI Updates Needed

1. After wallet connects, show $OPG balance next to wallet address in header
2. During audit loading, log lines should reflect the two-popup flow:
   - "> Checking $OPG balance..."
   - "> Requesting payment approval..." (during Popup 1)
   - "> Connecting to OpenGradient network..."
   - "> Running x402 LLM inference..."
   - "> Generating attestation proof..."
   - "> Recording audit on-chain..." (during Popup 2)
   - "> Complete ✓"
3. TEE Attestation box should show:
   - Attestation ID
   - Payment approval tx hash (from Popup 1) if available
   - Registry tx hash (from Popup 2) as clickable link to basescan

---

## Important Notes

- ethers.js v6 uses `ethers.BrowserProvider` and `ethers.parseUnits` — make sure the correct version is used consistently throughout index.html
- If the user already approved enough OPG allowance in a previous session, skip Popup 1 and go straight to the audit
- Never store private keys anywhere in the frontend
- The backend .env GEMINI_API_KEY stays as is — backend handles AI, frontend handles wallet interactions
