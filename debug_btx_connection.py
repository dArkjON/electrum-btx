#!/usr/bin/env python3
"""
Electrum-BTX Connection Diagnostic Tool

This script isolates and tests each step of the connection process to BTX servers
to identify why the connection status remains false despite server communication.
"""

import asyncio
import ssl
import socket
import json
import time
import logging
import sys
from typing import Optional, Tuple, Any

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('BTX_DIAG')

# BTX Servers
BTX_SERVERS = [
    ("ele1.bitcore.cc", 50001),
    ("ele2.bitcore.cc", 50001),
    ("ele3.bitcore.cc", 50001),
    ("ele4.bitcore.cc", 50001),
]

class ElectrumDiagnostic:
    """Diagnostic tool for Electrum-BTX connection issues"""

    def __init__(self):
        # Disable SSL certificate verification for BTX compatibility
        ssl._create_default_https_context = ssl._create_unverified_context

    async def test_tcp_connection(self, host: str, port: int) -> Tuple[bool, str]:
        """Test basic TCP connectivity to server"""
        logger.info(f"[*] Testing TCP connection to {host}:{port}")
        try:
            start_time = time.time()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=30
            )
            connect_time = time.time() - start_time
            writer.close()
            await writer.wait_closed()
            logger.info(f"[+] TCP connection successful in {connect_time:.2f}s")
            return True, f"TCP connection successful in {connect_time:.2f}s"
        except Exception as e:
            logger.error(f"[-] TCP connection failed: {e}")
            return False, f"TCP connection failed: {e}"

    async def test_ssl_connection(self, host: str, port: int) -> Tuple[bool, str]:
        """Test SSL/TLS handshake with server"""
        logger.info(f"[*] Testing SSL/TLS connection to {host}:{port}")
        try:
            # Create SSL context that doesn't verify certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            start_time = time.time()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, ssl=ssl_context),
                timeout=30
            )
            connect_time = time.time() - start_time

            # Get certificate info
            ssl_object = writer.get_extra_info('ssl_object')
            if ssl_object:
                cipher = ssl_object.cipher()
                version = ssl_object.version()
                logger.info(f"[+] SSL connection successful: {version} - {cipher}")

            writer.close()
            await writer.wait_closed()
            return True, f"SSL connection successful in {connect_time:.2f}s"
        except Exception as e:
            logger.error(f"[-] SSL connection failed: {e}")
            return False, f"SSL connection failed: {e}"

    async def test_raw_protocol(self, host: str, port: int) -> Tuple[bool, Any]:
        """Test raw Electrum protocol communication"""
        logger.info(f"[*] Testing raw Electrum protocol with {host}:{port}")

        # Try both SSL and non-SSL
        for use_ssl in [True, False]:
            protocol_str = "SSL" if use_ssl else "plain"
            logger.info(f"[*] Trying {protocol_str} connection...")

            try:
                if use_ssl:
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(host, port, ssl=ssl_context),
                        timeout=30
                    )
                else:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(host, port),
                        timeout=30
                    )

                # Send server.version request
                request = {
                    "id": 1,
                    "method": "server.version",
                    "params": ["electrum-btx-diagnostic", "1.4"]
                }

                message = json.dumps(request) + "\n"
                writer.write(message.encode())
                await writer.drain()

                # Read response
                response = await asyncio.wait_for(reader.readline(), timeout=30)
                response_data = json.loads(response.decode())

                logger.info(f"[+] Server response ({protocol_str}): {response_data}")

                # Try blockchain.headers.subscribe
                request2 = {
                    "id": 2,
                    "method": "blockchain.headers.subscribe",
                    "params": []
                }

                message2 = json.dumps(request2) + "\n"
                writer.write(message2.encode())
                await writer.drain()

                # Read subscription response
                response2 = await asyncio.wait_for(reader.readline(), timeout=30)
                response2_data = json.loads(response2.decode())

                logger.info(f"[+] Header subscription response ({protocol_str}): {response2_data}")

                writer.close()
                await writer.wait_closed()

                return True, {
                    "protocol": protocol_str,
                    "version": response_data,
                    "header": response2_data
                }

            except Exception as e:
                logger.error(f"[-] {protocol_str} protocol test failed: {e}")
                continue

        return False, "All protocol attempts failed"

    async def test_full_connection_flow(self, host: str, port: int) -> dict:
        """Test the complete connection flow like Electrum does"""
        logger.info(f"[*] Testing full connection flow to {host}:{port}")

        results = {
            "server": f"{host}:{port}",
            "tcp": False,
            "ssl": False,
            "protocol": False,
            "subscription": False,
            "errors": []
        }

        try:
            # Step 1: TCP Connection
            success, msg = await self.test_tcp_connection(host, port)
            results["tcp"] = success
            if not success:
                results["errors"].append(msg)
                return results

            # Step 2: Try raw protocol
            success, protocol_data = await self.test_raw_protocol(host, port)
            results["protocol"] = success

            if success:
                logger.info(f"[+] Protocol test successful!")

                # Check if we got a header subscription response
                if "header" in protocol_data and protocol_data["header"]:
                    header = protocol_data["header"]
                    if "result" in header and header["result"]:
                        results["subscription"] = True
                        height = header["result"].get("height", "unknown")
                        logger.info(f"[+] Got blockchain header subscription! Height: {height}")
                    else:
                        results["errors"].append("No header in subscription response")
                else:
                    results["errors"].append("No subscription response")
            else:
                results["errors"].append(str(protocol_data))

        except Exception as e:
            logger.error(f"[-] Full connection test failed: {e}")
            results["errors"].append(str(e))

        return results

    async def diagnose_servers(self):
        """Run diagnostics on all BTX servers"""
        logger.info("=" * 60)
        logger.info("Starting Electrum-BTX Connection Diagnostics")
        logger.info("=" * 60)

        all_results = []

        for host, port in BTX_SERVERS:
            logger.info(f"\n{'='*20} Testing {host}:{port} {'='*20}")
            results = await self.test_full_connection_flow(host, port)
            all_results.append(results)

            # Summary for this server
            logger.info(f"\n--- Summary for {host}:{port} ---")
            logger.info(f"TCP Connection: {'✓' if results['tcp'] else '✗'}")
            logger.info(f"Protocol: {'✓' if results['protocol'] else '✗'}")
            logger.info(f"Header Subscription: {'✓' if results['subscription'] else '✗'}")
            if results["errors"]:
                logger.error("Errors:")
                for error in results["errors"]:
                    logger.error(f"  - {error}")

        # Overall summary
        logger.info("\n" + "=" * 60)
        logger.info("OVERALL SUMMARY")
        logger.info("=" * 60)

        for result in all_results:
            server = result["server"]
            if result["subscription"]:
                logger.info(f"[+] {server}: FULLY CONNECTED ✓")
            elif result["protocol"]:
                logger.info(f"[!] {server}: Protocol works, no subscription")
            elif result["tcp"]:
                logger.info(f"[!] {server}: TCP works, no protocol")
            else:
                logger.info(f"[-] {server}: FAILED TO CONNECT")

        return all_results

async def main():
    """Main diagnostic routine"""
    diagnostic = ElectrumDiagnostic()

    try:
        results = await diagnostic.diagnose_servers()

        # Check if any server succeeded
        any_connected = any(r["subscription"] for r in results)
        if any_connected:
            logger.info("\n[+] At least one server connected successfully!")
            logger.info("[!] The issue might be in Electrum's connection state management")
        else:
            logger.info("\n[-] No servers connected successfully!")
            logger.info("[!] There might be a fundamental connectivity or protocol issue")

    except KeyboardInterrupt:
        logger.info("\n[!] Diagnostics interrupted by user")
    except Exception as e:
        logger.error(f"\n[-] Diagnostic error: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())