#!/usr/bin/env python3
"""
Test script to verify the BTX connection fix
"""

import asyncio
import sys
import os

# Add electrum to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from electrum.interface import ServerAddr, PREFERRED_NETWORK_PROTOCOL
from electrum.constants import net
from electrum.network import filter_protocol

def test_protocol_selection():
    """Test that BTX servers are correctly using plain text protocol"""

    print("=" * 60)
    print("Testing BTX Protocol Fix")
    print("=" * 60)

    # Check preferred protocol
    print(f"\nPREFERRED_NETWORK_PROTOCOL = '{PREFERRED_NETWORK_PROTOCOL}'")
    if PREFERRED_NETWORK_PROTOCOL == 't':
        print("✓ Correctly set to 't' (plain text)")
    else:
        print("✗ Still set to 's' (SSL) - fix not applied")
        return False

    # Test server filtering
    servers = net.DEFAULT_SERVERS
    print(f"\nFound {len(servers)} default servers")

    # Filter with preferred protocol
    filtered_servers = filter_protocol(servers, allowed_protocols={PREFERRED_NETWORK_PROTOCOL})
    print(f"Filtered to {len(filtered_servers)} servers using '{PREFERRED_NETWORK_PROTOCOL}' protocol")

    # Check BTX servers
    btx_servers = [(host, ports) for host, ports in servers.items() if 'bitcore' in host]
    print(f"\nBTX servers found: {len(btx_servers)}")

    for host, ports in btx_servers:
        protocol = PREFERRED_NETWORK_PROTOCOL
        port = ports.get(protocol)
        if port:
            server_addr = ServerAddr(host, port, protocol=protocol)
            print(f"  {host}:{port} ({protocol}) - ✓")
        else:
            print(f"  {host} - No port for protocol '{protocol}'")

    print("\n" + "=" * 60)
    print("Connection test with fixed protocol:")
    print("=" * 60)

    # Test connection to one server
    if filtered_servers:
        server = filtered_servers[0]
        print(f"\nTesting connection to {server}...")

        async def test_connection():
            try:
                import ssl
                if server.protocol == 't':
                    # Plain text connection
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(server.host, server.port),
                        timeout=10
                    )
                    print(f"✓ Plain text connection successful to {server}")
                    writer.close()
                    await writer.wait_closed()
                    return True
                else:
                    # SSL connection
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(server.host, server.port, ssl=ssl_context),
                        timeout=10
                    )
                    print(f"✓ SSL connection successful to {server}")
                    writer.close()
                    await writer.wait_closed()
                    return True
            except Exception as e:
                print(f"✗ Connection failed to {server}: {e}")
                return False

        result = asyncio.run(test_connection())
        return result

    return False

if __name__ == "__main__":
    success = test_protocol_selection()
    if success:
        print("\n✓ Fix appears to be working correctly!")
        print("BTX servers should now connect using plain text protocol.")
    else:
        print("\n✗ Fix may not be working correctly.")
        sys.exit(1)