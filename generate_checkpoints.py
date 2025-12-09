#!/usr/bin/env python3
import requests
import json

API_KEY = "8cba736e-6c52-4978-a670-215180582997"
BASE_URL = "https://bitcore.wtf/api/v1/block"

def get_block_data(height):
    """Fetch block data from BTX API"""
    url = f"{BASE_URL}/{height}"
    headers = {"X-API-Key": API_KEY}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()['data']
    except Exception as e:
        print(f"Error fetching block {height}: {e}")
        return None

def bits_to_target(bits_hex):
    """Convert bits hex to target decimal"""
    bits = int(bits_hex, 16)
    exponent = bits >> 24
    mantissa = bits & 0x00FFFFFF
    target = mantissa << (8 * (exponent - 3))
    return target

def main():
    checkpoints = []

    # Start from 2015 and go every 2016 blocks
    start_height = 2015
    current_height = 1711732  # Current approximate height

    for height in range(start_height, current_height + 1, 2016):
        print(f"Fetching block {height}...")
        block_data = get_block_data(height)

        if block_data:
            block_hash = block_data['hash']
            bits_hex = block_data['bits']
            target_decimal = bits_to_target(bits_hex)

            checkpoint = [
                block_hash,
                target_decimal
            ]
            checkpoints.append(checkpoint)
            print(f"  Added checkpoint for height {height}")

    # Write to file (direct list, no dict wrapper)
    with open("electrum/chains/mainnet/checkpoints.json", "w") as f:
        json.dump(checkpoints, f, indent=4)

    print(f"\nGenerated {len(checkpoints)} checkpoints")
    print(f"From height {start_height} to {height}")
    print("Saved to electrum/chains/mainnet/checkpoints.json")

if __name__ == "__main__":
    main()