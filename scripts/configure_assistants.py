"""Write this checkout's local MCP connection without changing global settings."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
command = sys.executable
script = str(ROOT/'scripts/archpipe_mcp.py')
path = ROOT/'.mcp.json'
config = json.loads(path.read_text()) if path.exists() else {}
config.setdefault('mcpServers', {})['archpipe'] = {
    'command': command, 'args': [script], 'env': {'PYTHONIOENCODING':'utf-8'}}
path.write_text(json.dumps(config, indent=2), encoding='utf-8')
path = ROOT/'.codex/config.toml'
existing = path.read_text(encoding='utf-8') if path.exists() else ''
start, end = '# BEGIN ARCHPIPE MCP\n', '# END ARCHPIPE MCP\n'
block = (start+'[mcp_servers.archpipe]\ncommand = '+json.dumps(command)+
         '\nargs = ['+json.dumps(script)+']\ntool_timeout_sec = 1200\n'+
         '[mcp_servers.archpipe.env]\nPYTHONIOENCODING = "utf-8"\n'+end)
if start in existing and end in existing:
    first, remaining = existing.split(start, 1)
    _, last = remaining.split(end, 1)
    content = first + block + last
elif '[mcp_servers.archpipe]' in existing:
    raise SystemExit('An existing archpipe connection needs an explicit merge; it was not replaced.')
else:
    content = existing + ('\n' if existing else '') + block
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(content, encoding='utf-8')
print('Configured project-local Claude and Codex MCP connections; restart/load this project to discover them.')
