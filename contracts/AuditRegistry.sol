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
