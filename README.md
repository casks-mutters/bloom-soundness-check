# README.md
# bloom-soundness-check

## Overview
This tiny tool performs a **soundness-style check** against an Ethereum block’s `logsBloom`. Given a block number and either an **address** and/or **topic0**, it tests whether those elements are **consistent** with the block’s bloom filter. Optionally, it can fetch logs for that exact block to provide a stricter verification. This mirrors how rollups/Aztec-like systems use compact commitments (blooms/roots) to quickly test statements before deeper verification.

## What it does
- Connects to an Ethereum-compatible RPC
- Loads the block header and reads `logsBloom`
- Tests membership of:
  - Address bytes (the emitting contract/address)
  - Event `topic0` (e.g., `keccak("Transfer(address,address,uint256)")`)
- Optionally fetches logs at that block to compare bloom results with actual events

## Installation
1) Install Python 3.10+
2) Install dependency:
   pip install web3
3) Configure RPC (optional):
   export RPC_URL="https://mainnet.infura.io/v3/<KEY>"

## Usage
   python app.py <block_number> [--address 0x...] [--topic0 0x...] [--rpc URL] [--verify]

### Examples
1) Check if a token's Transfer topic is present in a block’s bloom:
   python app.py 18000000 --topic0 0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef

2) Check if a specific address appears in the bloom (any event from that address):
   python app.py 18000000 --address 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48

3) Strict verification by fetching logs at that block:
   python app.py 18000000 --address 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 --topic0 0xddf252ad... --verify

## Expected output
- Network name and chain ID
- Block number
- Bloom membership results for address/topic0 (✅ present / ❌ not set)
- If `--verify` is used, the actual number of logs at that block matching the filters
- Elapsed time

## Notes
- **Bloom filters are probabilistic:** they can yield **false positives** (bloom says present, but zero logs). They must not yield false negatives; if you observe that, double-check inputs/provider.
- `topic0` is the keccak hash of the event signature (e.g., `Transfer(address,address,uint256)`).
- Use this as a fast pre-check: if bloom says “not set”, the block **cannot** contain relevant logs; if it says “present”, fetch logs to confirm.
- Works with Mainnet, Sepolia, and other EVM chains; just change the RPC URL.
- This is a soundness/commitment demo, not a ZK proof. You can embed the same checks in circuits to privately attest event presence in the future.
