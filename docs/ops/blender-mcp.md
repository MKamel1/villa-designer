# Official Blender Lab MCP: isolated Blender 5.2 evaluation

The Model Context Protocol (MCP) server is installed only under
`out/blender52/`, from the [official Blender Lab repository](https://projects.blender.org/lab/blender_mcp),
revision `dbbf836ad4b1025f14a2b3b504c43903f39e0b04`.
The source licence is GPL-3.0-or-later. Its extension manifest requires
Blender 5.1 or newer. The installed Python package is `blender-mcp 1.0.2`;
`out/blender52/mcp-packages.txt` records its separate virtual environment.
The project virtual environment was not modified.

The add-on is installed as `blender_mcp_addon` in
`out/blender52/mcp-user/scripts/addons/`, enabled in the separate
`out/blender52/mcp-user/config/userpref.blend`. Both `BLENDER_USER_CONFIG`
and `BLENDER_USER_SCRIPTS` must be set when using it. No default Blender
preferences, Blender 4.5 installation, renderer pin, or agent configuration
was changed. This checkout's untracked `out/` installation must be retained
on the workstation; the committed launcher alone does not install it.

## Attach from Claude Code on the Windows laptop

Run this registration command on the laptop, using its existing
`ai-workstation` SSH alias. SSH means Secure Shell; `-T` disables terminal
allocation so standard input and output carry only MCP messages.

```powershell
claude mcp add --transport stdio blender52 -- ssh -T ai-workstation /home/omar/archpipe/work/laneA/scripts/blender_mcp_stdio.sh
```

This composes [Claude Code's documented stdio registration](https://code.claude.com/docs/en/mcp#option-3-add-a-local-stdio-server)
with SSH remote-command execution. It has not been registered in the laptop's
configuration by this evaluation. Confirm connection with `/mcp` in Claude
Code. The workstation wrapper selects the explicit 5.2.2 executable and
isolated preferences. It launches the official server over standard input
and output, with no HTTP listener or SSH port forwarding.

Background tools ending in `_for_cli` start Blender themselves and accept an
absolute workstation path to a `.blend` **copy**. They do not require a
bridge server or a graphical session. Start by asking
`get_blendfile_summary_datablocks_for_cli` to inspect
`/home/omar/archpipe/work/laneA/out/blender52/mcp-villa-copy.blend`.

For tools without `_for_cli`, open that copy in a separate headless Blender
bridge on the workstation:

```bash
cd /home/omar/archpipe/work/laneA
BLENDER_USER_CONFIG="$PWD/out/blender52/mcp-user/config" \
BLENDER_USER_SCRIPTS="$PWD/out/blender52/mcp-user/scripts" \
/home/omar/opt/blender-5.2.2-linux-x64/blender \
  --background "$PWD/out/blender52/mcp-villa-copy.blend" \
  --online-mode --addons blender_mcp_addon \
  --command blender_mcp --host 127.0.0.1 --port 9877
```

The upstream bridge requires Blender's online mode even for localhost.
Do not enable HTTP transport, bind to all addresses, or forward port 9877.
Stop this bridge with Ctrl+C when finished. Background execution is
synchronous; deferred interactive operations and interface screenshots
cannot be assumed to work headlessly. GPU work still needs the project's
shared graphics lock and coordination with render batches.

## Tool inventory

The installed source declares 26 tools. `out/blender52/mcp-tools.json` is the
runtime discovery receipt, with full argument schemas.

| Purpose | Tools |
|---|---|
| Python execution | `execute_blender_code`, `execute_blender_code_for_cli` |
| Data-block summary | `get_blendfile_summary_datablocks`, `get_blendfile_summary_datablocks_for_cli` |
| Missing external files | `get_blendfile_summary_missing_files`, `get_blendfile_summary_missing_files_for_cli` |
| Linked libraries | `get_blendfile_summary_of_linked_libraries`, `get_blendfile_summary_of_linked_libraries_for_cli` |
| File path and save status | `get_blendfile_summary_path_info`, `get_blendfile_summary_path_info_for_cli` |
| Usage estimate | `get_blendfile_summary_usage_guess`, `get_blendfile_summary_usage_guess_for_cli` |
| Objects | `get_object_detail_summary`, `get_objects_summary` |
| Documentation | `get_python_api_docs`, `search_api_docs`, `search_manual_docs` |
| Interface capture | `get_screenshot_of_area_as_image`, `get_screenshot_of_window_as_image`, `get_screenshot_of_window_as_json` |
| Navigation | `jump_to_tab_by_name`, `jump_to_tab_by_space_type`, `jump_to_view3d_object_by_name`, `jump_to_view3d_object_data_by_name` |
| Rendering | `render_thumbnail_to_path`, `render_viewport_to_path` |

## Safety and verification

The server executes arbitrary Python as the workstation user. Localhost
restricts network reach, not filesystem access. Tool read-only hints are
metadata, not a security boundary. Give it only disposable copies; never
request saves to production scenes, shared asset directories, or the
4.5.14 installation. Do not run untrusted blend files or unreviewed code.
The add-on's weak sandbox is not an operating-system security boundary.

The installation and package logs are under `out/blender52/mcp-*`.
`mcp-smoke.json` records actual CLI and bridge summary calls on the copied
villa; its presence and successful results are required before claiming
that villa inspection works. `mcp-bridge.log` records background startup.
This integration provides tooling, not design acceptance or permission to
switch the production renderer.

Measured 2026-10-15: the stdio client discovered 26 tools, and both summary
calls returned successfully for the disposable built-villa copy. The host
process receipt records exit zero and a live localhost bridge before its
controlled shutdown. This verifies the two headless paths; it does not
certify interface-only tools in background mode.
