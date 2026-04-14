import os
import json
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import opengradient as og
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are an expert smart contract security auditor with deep knowledge of Solidity, Rust (Anchor/Solana), and all major blockchain security vulnerabilities including reentrancy, integer overflow, access control issues, flash loan attacks, oracle manipulation, and more.

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
Always provide at least 1 finding. For secure contracts use INFO severity for gas optimizations."""

llm: og.LLM = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm
    try:
        llm = og.LLM(private_key=os.environ.get("PRIVATE_KEY"))
        try:
            result = llm.ensure_opg_approval(min_allowance=5)
            print(f"OpenGradient LLM initialized. OPG allowance: {result.allowance_after}")
        except Exception as e:
            print(f"WARNING: OPG approval check failed: {e}")
            print("Wallet may have insufficient OPG. Fund at https://faucet.opengradient.ai/ if inference fails.")
    except Exception as e:
        print(f"ERROR: Failed to initialize OpenGradient LLM: {e}")
        print("Server will start but /api/audit will return 503 until PRIVATE_KEY is set correctly.")
        llm = None
    yield


app = FastAPI(title="AuditShield API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuditRequest(BaseModel):
    contractCode: str
    contractName: str
    chain: str = "Ethereum"
    additionalContext: str = ""


@app.post("/api/audit")
async def audit_contract(req: AuditRequest):
    if llm is None:
        raise HTTPException(status_code=503, detail="OpenGradient LLM not initialized. Check PRIVATE_KEY environment variable.")
    if not req.contractCode or not req.contractName:
        raise HTTPException(status_code=400, detail="Contract code and name are required")

    user_prompt = f"""Audit this smart contract:

Contract Name: {req.contractName}
Blockchain: {req.chain}
{f"Additional Context: {req.additionalContext}" if req.additionalContext else ""}

Contract Code:
```
{req.contractCode}
```

Provide your complete security audit as a JSON object only."""

    try:
        llm.ensure_opg_approval(min_allowance=5)
    except Exception as e:
        print(f"WARNING: pre-call OPG approval failed: {e}")

    try:
        result = await llm.chat(
            model=og.TEE_LLM.CLAUDE_HAIKU_4_5,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=4000,
            temperature=0.1,
        )
    except Exception as e:
        print(f"ERROR: llm.chat() failed: {e}")
        raise HTTPException(status_code=502, detail=f"OpenGradient inference failed: {str(e)}")

    try:
        raw_text = result.chat_output["content"]
    except (KeyError, TypeError, AttributeError) as e:
        print(f"ERROR: Unexpected result structure: {result!r} — {e}")
        raise HTTPException(status_code=502, detail=f"Unexpected response structure from OpenGradient: {str(e)}")

    clean_json = raw_text.replace("```json\n", "").replace("```json", "").replace("```\n", "").replace("```", "").strip()
    try:
        audit_result = json.loads(clean_json)
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON parse failed. Raw text: {raw_text!r}")
        raise HTTPException(status_code=502, detail=f"LLM returned non-JSON response: {str(e)}")

    tee_attestation = (
        getattr(result, "payment_hash", None)
        or getattr(result, "transaction_hash", None)
        or f"OG-TEE-{getattr(result, 'tee_id', 'unknown')}"
    )

    return {
        "success": True,
        "auditResult": audit_result,
        "teeAttestation": tee_attestation,
        "teeSignature": getattr(result, "tee_signature", None),
        "teeTimestamp": getattr(result, "tee_timestamp", None),
        "model": str(og.TEE_LLM.CLAUDE_HAIKU_4_5),
        "inferenceProvider": "OpenGradient TEE",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"AuditShield Python backend running on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port)
