# Revit 2027 — the built-in MCP surface

Measured on 2026-09-22 by `revit/dump_mcp_tools.py`, which loads
`Autodesk.Assistant.Tools.dll` inside Revit and calls
`Autodesk.MCP.Tools.ToolsExposer.GetPublicToolDefinitions()` by reflection.
Not read from marketing material and not inferred from strings in a DLL.

Revit 2027 ships an AI Assistant built on the official Model Context
Protocol SDK (`ModelContextProtocol` 1.0.0.0, loaded at runtime on
.NET 10). It both **hosts** MCP tools and, via
`ModelContextProtocol.Client.StdioClientTransport`, can act as an MCP
**client** of external servers.

## The distinction that matters

There are **78 tool classes**, but `GetPublicToolDefinitions()`
returns only **6**. The public set is read, navigate and export.
Everything that creates or modifies the model is private to Autodesk's
own assistant. Anyone planning on this should plan on the public six.

## Public tools (the ones a third-party MCP client is offered)

### `open_view` — Open View

Opens a view (sets it as the active view).

```json
{"type":"object","properties":{"viewId":{"description":"Id of the view to open. Template views and browser views cannot be open.","type":"integer"}},"required":["viewId"]}
```

### `query_model` — Query Model

Gets element Ids by querying the model with multi-criteria filtering including spatial, parametric, and categorical filters. The 'results' section consist of two parts: 'Element Ids' and 'analysis'. 'Element Ids' can be passed to other tools, like get_element_data; obtaining element Ids is needed for most non-trival tasks. The 'analysis' section shows element counts and breakdowns by category, level, etc. It is computed for the matching elements and always output in full. 'analysis' helps to narrow down more detailed queries.

```json
{"type":"object","properties":{"input":{"description":"Query parameters defining search criteria and filters.","type":"object","properties":{"searchScope":{"description":"Scope of search: \u0027CurrentView\u0027, \u0027SpecificView\u0027 or \u0027AllViews\u0027.","type":"string","enum":["CurrentView","AllViews","SpecificView"]},"viewId":{"description":"Id of the view to search elements in ; only used if SearchScope value is \u0027SpecificView\u0027.","type":"integer"},"selectedOnly":{"description":"Whether to search only through selected elements.","type":"boolean"},"elementInclusionMode":{"description":"Which elements to include: \u0027InstancesOnly\u0027 (default), \u0027TypesOnly\u0027 or...
```

### `export_views` — Export Views

Exports printable views or the visible region to image files (PNG, JPG, BMP, TIFF). Exports printable views to separate PDF files. Exports schedule views to CSV. Note: All given files are exported to the same file format.

```json
{"type":"object","properties":{"exportMode":{"description":"(optional) Export mode: \u0027ByViewList\u0027 (export list of views by Ids), \u0027CurrentView\u0027 (export current active view), \u0027VisibleRegion\u0027 (export visible portion of current window as user sees it on screen). Default is \u0027ByViewList\u0027.","type":"string","enum":["ByViewList","CurrentView","VisibleRegion"],"default":"ByViewList"},"viewIds":{"description":"(optional) Ids of the views to export. Required for \u0027ByViewList\u0027 mode, ignored for other modes.","type":"array","items":{"type":"integer"},"default":null},"directoryPath":{"description":"(optional) The fully qualified directory path where the expor...
```

### `get_element_data` — Get Element Data

Gets comprehensive parameters information for elements.

```json
{"type":"object","properties":{"elementIds":{"description":"Id of the elements to get parameters information for.","type":"array","items":{"type":"integer"}},"outputOptions":{"description":"(optional) Output options controlling which element data to include. If not provided, only BasicElementInfo will be returned.","type":"object","properties":{"basicElementInfo":{"description":"Whether to include the element name, category, family, type and level in output.","type":"boolean"},"elementClass":{"description":"Whether to include the element class in output.","type":"boolean"},"boundingBox":{"description":"Whether to include element bounding box in output.","type":"boolean"},"gridGeometry":{"des...
```

### `select_elements` — Select Elements

Selects elements by their Ids.

```json
{"type":"object","properties":{"elementIds":{"description":"Ids of the elements to select.","type":"array","items":{"type":"integer"}}},"required":["elementIds"]}
```

### `zoom_to_elements` — Zoom to Elements

Zoom in on or focus the current view on specific elements by their Ids.

```json
{"type":"object","properties":{"elementIds":{"description":"Ids of the elements to show.","type":"array","items":{"type":"integer"}}},"required":["elementIds"]}
```

## All tool classes, by area

Private unless listed above. Useful as a map of what Revit 2027 can do
natively, and of how much of our pending work Autodesk has already built.

**(ungrouped)** (27)

- `CreateConduitTool`
- `CreateDuctTool`
- `CreateGridSystemTool`
- `CreateMultipleLevelsTool`
- `CreatePipeTool`
- `DeleteMEPMarkValuesTool`
- `DuplicateMaterialTool`
- `FormatValueToProjectUnitsTool`
- `GetAllCircuitsTool`
- `GetAllTextNotesTool`
- `GetConduitTypesTool`
- `GetCurrentViewTextNotesTool`
- `GetDuctSystemTypesTool`
- `GetDuctSystemsTool`
- `GetDuctTypesTool`
- `GetDuctsFromSystemTool`
- `GetMEPElementsWithMarksTool`
- `GetPipeTypesTool`
- `GetProjectInformationTool`
- `GetProjectUnitsTool`
- `GetWireTypesTool`
- `IMCPTool`
- `LinkCADFileTool`
- `ManageLinkedFilesTool`
- `SetProjectInformationTool`
- `SetupProjectBasePointTool`
- `TriggerPanelScheduleCreationTool`

**Annotations** (1)

- `TagElementsTool`

**ElementOperations** (5)

- `DeleteElementsTool`
- `MoveElementsTool`
- `RotateElementsTool`
- `SelectElementsTool`
- `ShowElementsTool`

**ElementParameters** (4)

- `ChangeElementTypeTool`
- `CopyParametersTool`
- `GetElementDataTool`
- `ModifyElementParametersTool`

**Interoperability** (2)

- `ExportViewsToPdfTool`
- `ExportViewsTool`

**MEP** (2)

- `AddDuctInsulationToSystemTool`
- `BulkDeleteMEPMarksByCategoryTool`

**ProjectSetup** (1)

- `AdjustLevelElevationsTool`

**ReadModel** (2)

- `GroupElementsTool`
- `QueryModelTool`

**Rooms** (3)

- `ColorRoomTool`
- `GetRoomsTool`
- `SetRoomNameTool`

**Schedule** (8)

- `AddScheduleFiltersTool`
- `AddScheduleGroupingTool`
- `AddScheduleSortingTool`
- `CreateSchedulePortTool`
- `CreateScheduleTool`
- `GetAllSchedulesTool`
- `GetSchedulableFieldsTool`
- `GetScheduleByNameTool`

**SheetView** (15)

- `ApplyViewTemplateToViewTool`
- `CreatePlanViewsTool`
- `CreateSectionViewTool`
- `CreateSheetTool`
- `CreateViewPortsTool`
- `GetAllPlacedViewsForSheetsTool`
- `GetAllViewPortsForASheetTool`
- `GetAllViewTemplatesTool`
- `GetSheetTitleBlockIdTool`
- `GetSheetsTool`
- `GetViewsTool`
- `OpenViewTool`
- `RemoveViewTemplateFromViewTool`
- `RenameSheetTool`
- `SetSheetNumberTool`

**TextNote** (1)

- `CapitalizeTextNotesTool`

**ViewVisibility** (5)

- `GetViewVisibilityStateTool`
- `RestoreViewVisibilityStateTool`
- `SetElementVisibilityTool`
- `SetViewDetailLevelTool`
- `ToggleCategoryVisibilityTool`

**VisualGraphics** (2)

- `GetFillAndLinePatternsTool`
- `OverrideElementsGraphicsTool`

## The extension point

`Autodesk.Assistant.ServerRegistry` exposes **`AddCustomServer`** and an
**`ICustomTransportServer`** interface. That is how a Revit add-in would
register its own MCP server into the Assistant — which is the route by
which archpipe's rule engine, lighting engine and Neufert catalogue could
be made callable from Revit's own AI. Not yet attempted.

## What is NOT established

- whether the hosted server is reachable by an external MCP client
  (the type is named `PrivateMcpServer`)
- whether external servers can be registered without writing a .NET add-in
- whether any of it needs an Autodesk AI entitlement beyond the licence
- `ToolsExposer.With{All,Public,Private}Tools` take an `IMcpServerBuilder`,
  so enumerating the private set needs an actual MCP server to be built;
  `ToolDiscovery.DiscoverAll()` takes arguments and was not pursued.