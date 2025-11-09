# app.py
import os
import sys
import argparse
import time
from typing import Optional
from web3 import Web3

# RPC configuration (env override or --rpc flag)
DEFAULT_RPC = os.getenv("RPC_URL", "https://mainnet.infura.io/v3/your_api_key")

NETWORKS = {
    1: "Ethereum Mainnet",
    11155111: "Sepolia Testnet",
    10: "Optimism",
    137: "Polygon",
    42161: "Arbitrum One",
}

def network_name(cid: int) -> str:
    return NETWORKS.get(cid, f"Unknown (chain ID {cid})")

def bloom_indexes(data: bytes):
    """
    Ethereum log bloom uses 3 indices derived from keccak(data).
    Each index = uint16(hash[2*i] << 8 | hash[2*i+1]) % 2048  for i in {0,1,2}
    """
    h = Web3.keccak(data)
    return [(((h[2*i] << 8) | h[2*i + 1]) & 2047) for i in range(3)]

def bloom_check(bloom_int: int, data: bytes) -> bool:
    for idx in bloom_indexes(data):
        if ((bloom_int >> idx) & 1) == 0:
            return False
    return True

def connect(rpc: str) -> Web3:
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
    if not w3.is_connected():
        print("❌ Failed to connect to RPC. Use --rpc or set RPC_URL.")
        sys.exit(1)
    return w3

def parse_hex(s: str, kind: str) -> bytes:
    if not s.startswith("0x"):
        raise ValueError(f"{kind} must be 0x-prefixed hex")
    h = s[2:]
    return bytes.fromhex(h)

def fetch_logs_count(w3: Web3, block_number: int, address: Optional[str], topic0: Optional[str]) -> int:
    params = {
        "fromBlock": block_number,
        "toBlock": block_number,
    }
    if address:
        params["address"] = Web3.to_checksum_address(address)
    if topic0:
        params["topics"] = [topic0]
    logs = w3.eth.get_logs(params)
    return len(logs)

def main():
    ap = argparse.ArgumentParser(
        description="Block bloom soundness check: verify if (address/topic) is consistent with a block's logsBloom."
    )
    ap.add_argument("block", type=int, help="Block number to check")
    ap.add_argument("--address", help="Contract/event address to test (0x...)")
    ap.add_argument("--topic0", help="Event topic0 to test (0x...)")
    ap.add_argument("--rpc", default=DEFAULT_RPC, help="RPC endpoint URL (default from RPC_URL env)")
    ap.add_argument("--verify", action="store_true", help="Also fetch logs for strict verification at this block")
    args = ap.parse_args()

    if not args.address and not args.topic0:
        print("❌ Provide at least one of --address or --topic0")
        sys.exit(1)

    w3 = connect(args.rpc)
    print(f"🌐 Connected to {network_name(w3.eth.chain_id)} (chainId {w3.eth.chain_id})")

    t0 = time.time()
    try:
        header = w3.eth.get_block(args.block)
    except Exception as e:
        print(f"❌ Failed to load block {args.block}: {e}")
        sys.exit(2)

    bloom_bytes = bytes(header.logsBloom)
    bloom_int = int.from_bytes(bloom_bytes, "big")

    addr_ok = None
    topic_ok = None

    if args.address:
        try:
            addr_bytes = bytes.fromhex(Web3.to_checksum_address(args.address)[2:])
        except Exception:
            print("❌ Invalid --address")
            sys.exit(1)
        addr_ok = bloom_check(bloom_int, addr_bytes)

    if args.topic0:
        try:
            topic_bytes = parse_hex(args.topic0, "topic0")
        except Exception as e:
            print(f"❌ {e}")
            sys.exit(1)
        topic_ok = bloom_check(bloom_int, topic_bytes)

    print(f"\n🧱 Block: {args.block}")
    if args.address:
        print(f"🏷️  Address: {Web3.to_checksum_address(args.address)}  → Bloom says: {'✅ present' if addr_ok else '❌ not set'}")
    if args.topic0:
        print(f"🧩 Topic0: {args.topic0}  → Bloom says: {'✅ present' if topic_ok else '❌ not set'}")

    if args.verify:
        try:
            count = fetch_logs_count(w3, args.block, args.address, args.topic0)
            print(f"🔎 Exact on-chain logs found at block {args.block}: {count}")
            if (addr_ok is False or topic_ok is False) and count > 0:
                print("⚠️  Bloom false-negative would violate soundness; re-check inputs/provider.")
            if (addr_ok is True or topic_ok is True) and count == 0:
                print("ℹ️  Bloom can have false positives (expected by design).")
        except Exception as e:
            print(f"⚠️  Log fetch failed: {e}")

    print(f"\n⏱️  Elapsed: {time.time() - t0:.2f}s")

if __name__ == "__main__":
    main()
