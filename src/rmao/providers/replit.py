
---

### 📂 2. Replit Execution Provider (Core Fix)
**Location:** `replica-pro/src/rmao/providers/replit.py`

```python
import asyncio
import json
import time
from typing import Dict, Any

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from rmao.config import settings
from rmao.providers.base import BaseProvider


class ReplitProvider(BaseProvider):
    """Execution provider for Replit using GraphQL API with SID authentication."""

    def __init__(self, account_sids: list):
        self.account_sids = account_sids or settings.ACCOUNT_SIDS
        if not self.account_sids or len(self.account_sids) < 4:
            raise ValueError("At least 4 Replit SIDs required for parallel execution.")
        self.base_url = "https://replit.com/graphql"

    def _get_headers(self, sid: str) -> Dict:
        return {
            "Cookie": f"connect.sid={sid}",
            "Content-Type": "application/json",
            "User-Agent": "Replica-Pro-Orchestrator/1.0",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _graphql_request(self, sid: str, query: str) -> Dict:
        """Async GraphQL request with retry logic."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url, headers=self._get_headers(sid), json={"query": query}
            ) as resp:
                if resp.status == 429:  # Rate limit
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    await asyncio.sleep(retry_after)
                    raise Exception("Rate limited")
                data = await resp.json()
                if "errors" in data:
                    raise Exception(f"GraphQL Error: {data['errors']}")
                return data

    async def create_repl(self, account_index: int, title: str, language: str = "nodejs") -> str:
        """Create a new Repl on a specific account."""
        sid = self.account_sids[account_index]
        mutation = f"""
        mutation {{
            createRepl(input: {{title: "{title}", language: "{language}"}}) {{
                id
                url
            }}
        }}
        """
        result = await self._graphql_request(sid, mutation)
        return result["data"]["createRepl"]["id"]

    async def write_file(self, account_index: int, repl_id: str, path: str, content: str) -> bool:
        """Write content to a file in the Repl."""
        sid = self.account_sids[account_index]
        escaped_content = json.dumps(content)[1:-1]  # Escape for JSON string
        mutation = f"""
        mutation {{
            writeFile(input: {{replId: "{repl_id}", path: "{path}", content: "{escaped_content}"}}) {{
                success
            }}
        }}
        """
        result = await self._graphql_request(sid, mutation)
        return result["data"]["writeFile"]["success"]

    async def run_command(self, account_index: int, repl_id: str, command: str) -> str:
        """Execute a shell command (e.g., npm install) on the Repl."""
        sid = self.account_sids[account_index]
        mutation = f"""
        mutation {{
            runShellCommand(input: {{replId: "{repl_id}", command: "{command}"}}) {{
                output
            }}
        }}
        """
        result = await self._graphql_request(sid, mutation)
        return result["data"]["runShellCommand"]["output"]

    async def deploy_to_replit(self, account_index: int, code_dict: Dict[str, str]) -> str:
        """Full workflow: Create Repl, write files, run install, start server."""
        # 1. Create Repl
        repl_id = await self.create_repl(account_index, f"task-{account_index}")

        # 2. Write all files
        tasks = []
        for path, content in code_dict.items():
            tasks.append(self.write_file(account_index, repl_id, path, content))
        await asyncio.gather(*tasks)

        # 3. Run npm install if package.json exists
        if "package.json" in code_dict:
            await self.run_command(account_index, repl_id, "npm install")

        # 4. Return Repl URL
        return f"https://replit.com/@user/{repl_id}"
