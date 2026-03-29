import hre from "hardhat";

async function main() {
  const AuditRegistry = await hre.ethers.getContractFactory("AuditRegistry");
  const registry = await AuditRegistry.deploy();
  await registry.waitForDeployment();
  const address = await registry.getAddress();
  console.log(`AuditRegistry deployed to: ${address}`);
  console.log(`View on BaseScan: https://sepolia.basescan.org/address/${address}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
