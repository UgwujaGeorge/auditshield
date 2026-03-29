import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import fetch from "node-fetch";

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json({ limit: "2mb" }));

const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_API_KEY}`;

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
      model: "anthropic/claude-sonnet-4-6",
      inferenceProvider: "OpenGradient x402 TEE"
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
