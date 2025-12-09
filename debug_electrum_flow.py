#!/usr/bin/env python3
"""
Electrum-BTX Flow Debugger

This script mimics the exact connection flow used by Electrum to identify
where the connection process differs between versions.
"""

import asyncio
import ssl
import socket
import json
import time
import logging
import sys
import hashlib
import struct
from typing import Optional, Dict, Any, List

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('BTX_FLOW')

class MockElectrumInterface:
    """Mimics Electrum's Interface class connection flow"""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.ready = asyncio.Future()
        self.got_disconnected = asyncio.Event()
        self.tip_header = None
        self.tip = 0
        self.session = None
        self.blockchain = None

    def diagnostic_name(self):
        return f"{self.host}:{self.port}"

    async def _get_ssl_context(self) -> ssl.SSLContext:
        """Get SSL context (mimics Electrum's _get_ssl_context)"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context

    async def _save_certificate(self, session):
        """Mock certificate saving"""
        logger.info(f"[*] Certificate handling skipped for diagnostics")

    def client_name(self) -> str:
        """Return client name like Electrum does"""
        return "electrum-btx-debug/4.6.2"

    def hash_header(self, header: dict) -> str:
        """Hash a block header (simplified)"""
        # This is a simplified version - Electrum uses full blockchain hashing
        header_hex = header.get('hex', '')
        return hashlib.sha256(header_hex.encode()).hexdigest()

    def check_header(self, header: dict) -> bool:
        """Check if header is valid (simplified)"""
        # In real Electrum, this checks against known blockchain
        # For debugging, we'll just check if it has required fields
        return 'hex' in header and 'height' in header

    def _mark_ready(self) -> None:
        """Mark connection as ready (mimics Electrum's _mark_ready)"""
        logger.info(f"[*] _mark_ready called for {self.diagnostic_name()}")

        if self.ready.cancelled():
            raise Exception('conn establishment was too slow')
        if self.ready.done():
            logger.info(f"[!] Ready already set for {self.diagnostic_name()}")
            return

        assert self.tip_header
        logger.info(f"[*] Checking header: height={self.tip}, header_hash={self.hash_header(self.tip_header)[:16]}...")

        # Simplified blockchain check
        chain = self.check_header(self.tip_header)
        if not chain:
            logger.warning(f"[!] Header not in known chain for {self.diagnostic_name()}")
            # In real Electrum, this would create/get best chain
            self.blockchain = f"mock_chain_at_height_{self.tip}"
        else:
            self.blockchain = "existing_chain"

        logger.info(f"[*] Setting blockchain with height {self.tip} for {self.diagnostic_name()}")
        self.ready.set_result(1)
        logger.info(f"[+] Connection marked as READY for {self.diagnostic_name()}")

    async def monitor_connection(self):
        """Monitor connection health"""
        logger.info(f"[*] Starting connection monitor for {self.diagnostic_name()}")
        while True:
            await asyncio.sleep(1)
            if not self.session or self.session.is_closing():
                logger.warning(f"[!] Session closed for {self.diagnostic_name()}")
                return

    async def run_fetch_blocks(self):
        """Fetch blockchain headers (mimics Electrum's run_fetch_blocks)"""
        logger.info(f"[*] Starting block fetch for {self.diagnostic_name()}")

        # Create a queue for subscription results
        header_queue = asyncio.Queue()

        # Subscribe to headers
        try:
            await self.session.subscribe('blockchain.headers.subscribe', [], header_queue)
            logger.info(f"[+] Subscribed to headers for {self.diagnostic_name()}")
        except Exception as e:
            logger.error(f"[-] Failed to subscribe to headers: {e}")
            raise

        # Process header notifications
        while True:
            try:
                item = await header_queue.get()
                logger.info(f"[*] Got header notification: {item}")

                # Parse header (Electrum gets raw_header dict)
                raw_header = item[0]
                if isinstance(raw_header, dict):
                    height = raw_header.get('height')
                    header_hex = raw_header.get('hex')
                    self.tip_header = raw_header
                    self.tip = height if height is not None else 0

                    logger.info(f"[+] Received header: height={self.tip}, hex={header_hex[:32]}...")

                    # This is the key step - mark connection as ready
                    self._mark_ready()

                else:
                    logger.error(f"[-] Unexpected header format: {type(raw_header)}")

            except Exception as e:
                logger.error(f"[-] Error processing header: {e}")
                raise

    async def connect_and_run(self) -> Dict[str, Any]:
        """Run the complete connection flow"""
        logger.info(f"[*] Starting connection flow for {self.diagnostic_name()}")
        result = {
            "server": self.diagnostic_name(),
            "steps": {},
            "success": False,
            "error": None
        }

        try:
            # Step 1: Get SSL context
            result["steps"]["ssl_context"] = "success"
            ssl_context = await self._get_ssl_context()
            logger.info(f"[+] SSL context obtained")

            # Step 2: Create session and connect
            result["steps"]["session_create"] = "attempting"

            # Create a mock session that mimics NotificationSession
            class MockSession:
                def __init__(self, reader, writer):
                    self.reader = reader
                    self.writer = writer
                    self._id_counter = 0
                    self._subscriptions = {}
                    self._closing = False

                async def send_request(self, method: str, params: List = None):
                    if params is None:
                        params = []
                    self._id_counter += 1
                    request = {
                        "id": self._id_counter,
                        "method": method,
                        "params": params
                    }
                    message = json.dumps(request) + "\n"
                    self.writer.write(message.encode())
                    await self.writer.drain()

                    # Read response
                    response = await self.reader.readline()
                    response_data = json.loads(response.decode())

                    if response_data.get("id") == self._id_counter:
                        if "error" in response_data:
                            raise Exception(f"RPC Error: {response_data['error']}")
                        return response_data.get("result")
                    return None

                async def subscribe(self, method: str, params: List, queue: asyncio.Queue):
                    # Subscribe and put notifications in queue
                    result = await self.send_request(method, params)
                    self._subscriptions[method] = queue
                    queue.put([result])  # Initial result

                    # Start a task to read notifications
                    asyncio.create_task(self._read_notifications(queue, method))

                async def _read_notifications(self, queue: asyncio.Queue, method: str):
                    while not self._closing:
                        try:
                            line = await asyncio.wait_for(self.reader.readline(), timeout=30)
                            if not line:
                                break
                            notification = json.loads(line.decode())
                            if "method" in notification and notification["method"] == method:
                                queue.put([notification.get("params", [])])
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            logger.error(f"Error reading notification: {e}")
                            break

                def is_closing(self):
                    return self._closing

                async def close(self):
                    self._closing = True
                    if not self.writer.is_closing():
                        self.writer.close()
                        await self.writer.wait_closed()

            # Connect with SSL
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port, ssl=ssl_context),
                timeout=30
            )

            self.session = MockSession(reader, writer)
            result["steps"]["session_create"] = "success"
            logger.info(f"[+] Session created and connected")

            # Step 3: Server version negotiation
            result["steps"]["version"] = "attempting"
            ver = await self.session.send_request('server.version', [self.client_name(), "1.4"])
            result["steps"]["version"] = f"success: {ver}"
            logger.info(f"[+] Server version: {ver}")

            # Step 4: Start the main tasks
            result["steps"]["tasks"] = "starting"

            # Create tasks
            tasks = [
                asyncio.create_task(self.monitor_connection()),
                asyncio.create_task(self.run_fetch_blocks())
            ]

            # Wait for connection to be ready or timeout
            try:
                await asyncio.wait_for(self.ready, timeout=30)
                result["success"] = True
                result["steps"]["ready"] = "success"
                logger.info(f"[+] Connection fully established for {self.diagnostic_name()}")
            except asyncio.TimeoutError:
                result["steps"]["ready"] = "timeout"
                result["error"] = "Connection not marked as ready within 30 seconds"
                logger.error(f"[-] Connection timeout for {self.diagnostic_name()}")
            except Exception as e:
                result["steps"]["ready"] = f"error: {e}"
                result["error"] = str(e)
                logger.error(f"[-] Connection error for {self.diagnostic_name()}: {e}")

            # Cancel tasks
            for task in tasks:
                task.cancel()

            # Close session
            if self.session:
                await self.session.close()

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"[-] Connection failed for {self.diagnostic_name()}: {e}")
            import traceback
            traceback.print_exc()

        return result


async def debug_servers():
    """Debug connection to all BTX servers"""
    servers = [
        ("ele1.bitcore.cc", 50001),
        ("ele2.bitcore.cc", 50001),
        ("ele3.bitcore.cc", 50001),
        ("ele4.bitcore.cc", 50001),
    ]

    logger.info("=" * 60)
    logger.info("ELECTRUM-BTX FLOW DEBUGGER")
    logger.info("=" * 60)

    results = []

    for host, port in servers:
        logger.info(f"\n{'='*20} {host}:{port} {'='*20}")

        interface = MockElectrumInterface(host, port)
        result = await interface.connect_and_run()
        results.append(result)

        # Print result summary
        logger.info(f"\n--- Result for {host}:{port} ---")
        logger.info(f"Success: {'✓' if result['success'] else '✗'}")
        if result["error"]:
            logger.error(f"Error: {result['error']}")
        logger.info("Steps:")
        for step, status in result["steps"].items():
            logger.info(f"  {step}: {status}")

    # Overall analysis
    logger.info("\n" + "=" * 60)
    logger.info("ANALYSIS")
    logger.info("=" * 60)

    successful = [r for r in results if r["success"]]
    if successful:
        logger.info(f"[+] {len(successful)} server(s) connected successfully!")
        logger.info("[!] The issue is likely in Electrum's state management or the way it checks readiness")

        # Check where failures occur
        for r in results:
            if not r["success"]:
                server = r["server"]
                if "ready" in r["steps"] and "timeout" in r["steps"]["ready"]:
                    logger.info(f"[!] {server}: Connected but not marked as ready (timeout)")
                elif "version" in r["steps"] and "error" in r["steps"]["version"]:
                    logger.info(f"[!] {server}: Version negotiation failed")
                else:
                    logger.info(f"[!] {server}: Failed at early stage - {r.get('error', 'unknown')}")
    else:
        logger.info(f"[-] No servers connected successfully!")

        # Check what stage failures occur at
        stages = {}
        for r in results:
            for step, status in r["steps"].items():
                if "error" in str(status).lower() or "timeout" in str(status).lower():
                    stages.setdefault(step, 0)
                    stages[step] += 1

        if stages:
            logger.info("\nFailure stages:")
            for stage, count in stages.items():
                logger.info(f"  {stage}: {count} servers")

    return results


if __name__ == "__main__":
    asyncio.run(debug_servers())