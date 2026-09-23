"""Exercise the real standard-input/output MCP connection, including errors."""
import asyncio
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


def payload(result):
    if result.isError:
        raise AssertionError(str(result.content))
    if result.structuredContent:
        return result.structuredContent
    return json.loads(result.content[0].text)


async def main():
    if '--cached-run' in sys.argv:
        # This transport regression must not accidentally start Revit or
        # remote rendering when evidence is stale. Refresh it separately.
        from run_bedroom import input_hashes, artifacts_match
        saved = json.loads((ROOT/'out/bedroom-acceptance.json').read_text())
        assert (saved.get('passed') and saved.get('samples') == 512
                and saved.get('input_hashes') == input_hashes()
                and artifacts_match(saved.get('artifacts', {}))), 'Run the pipeline before testing its cached transport'
    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT/'scripts/archpipe_mcp.py')],
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}, cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            tools = await client.list_tools()
            assert len(tools.tools) == 7
            print('PASS real MCP handshake and seven typed tools')
            resources = await client.list_resources()
            assert {str(r.uri) for r in resources.resources} == {'archpipe://method', 'archpipe://learnings'}
            learned = await client.read_resource('archpipe://learnings')
            assert 'world bounding box' in learned.contents[0].text
            print('PASS shared learning and method resources')
            model = payload(await client.call_tool('read_model', {}))
            assert len(model['furniture']) == 6
            reviewed = payload(await client.call_tool('review_model', {'scope': 'room'}))
            assert reviewed['passed'] and reviewed['furniture_count'] == 6
            full = payload(await client.call_tool('review_model', {}))
            assert not full['passed']
            assert any(f['rule'] == 'SAN-01' for f in full['findings'])
            print('PASS measured model review and explicit scope difference')
            item = payload(await client.call_tool('catalogue_item', {'type_id':'bed_double'}))
            assert item['clearance']['left'] == 750 and item['source']
            light = payload(await client.call_tool('lighting_at', {'x_mm':1725, 'y_mm':3300, 'height_mm':900}))
            assert 300 < light['direct_lux'] < 500
            print('PASS cited catalogue and real photometric point')
            spec = ROOT/'spec/bedroom-test.yaml'
            before = hashlib.sha256(spec.read_bytes()).hexdigest()
            proposed = payload(await client.call_tool('propose_example_edit', {
                'item_id':'FN-BED', 'x_mm':2300, 'y_mm':2600}))
            assert (ROOT/proposed['proposal']).is_file()
            assert hashlib.sha256(spec.read_bytes()).hexdigest() == before
            print('PASS candidate edit writes proposal and preserves current specification')
            for name, args in [
                ('read_model', {'path':'../.claude/settings.json'}),
                ('review_model', {'scope':'silence-errors'}),
                ('catalogue_item', {'type_id':'invented'}),
                ('propose_example_edit', {'item_id':'FN-BED','x_mm':-10,'y_mm':0})]:
                failed = await client.call_tool(name, args)
                assert failed.isError, name
            print('PASS path escape, invalid scope, unknown requirement and outside-room edits fail')
            status = payload(await client.call_tool('project_status', {}))
            assert 'villa' in status['roadmap'].lower()
            # Rebuild is expensive; invoke only when cached evidence exists.
            # This proves the one-call transport uses the validated resume path.
            if '--cached-run' in sys.argv:
                result = payload(await client.call_tool('run_bedroom_example', {'resume':True},
                    read_timeout_seconds=timedelta(seconds=30)))
                assert result['exit_code'] == 0 and result['acceptance']['passed']
                assert 'reused complete verified run' in result['log']
                print('PASS one MCP operation reuses matching verified artifacts')
    print('MCP RESULT: ALL PASS')


if __name__ == '__main__':
    asyncio.run(main())
