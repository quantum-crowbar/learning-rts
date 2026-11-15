# Entry Point Map

**Project**: ejaj-boj (pinned `fde9d3c`)  
**Generated**: 2026-11-15  
**Entry points**: 57

Entry types: `http` / `websocket` = FastAPI route handlers; `framework` = callbacks given to FastAPI; `script` = a `__main__` module; `browser-load` = the inline script that runs when the page loads; `event` = DOM / WebSocket event handlers (`addEventListener`, `ws.onmessage = ...`); `timer` = `setTimeout`/`setInterval`/`requestAnimationFrame` callbacks. **The game loop is not an entry type here**: `GameEngine._game_loop` is reached through `GameEngine.start` (an `asyncio` task created there), so it appears in the traces of `POST /start`.

| Entry | Type | Location | Reach (functions) | External-call functions | Max CC on path |
|---|---|---|---|---|---|
| `<handler:click@1687>` | event | `client/index.html:1687` | 88 | 67 | 58 |
| `<handler:click@1671>` | event | `client/index.html:1671` | 86 | 65 | 58 |
| `start` | http | `server/main.py:95` | 82 | 61 | 58 |
| `<module>` | browser-load | `client/index.html:374` | 53 | 41 | 36 |
| `<handler:click@1874>` | event | `client/index.html:1874` | 32 | 26 | 36 |
| `<handler:input@1880>` | event | `client/index.html:1880` | 31 | 26 | 36 |
| `ReplayController._startPlay.<handler:setInterval@1842>` | timer | `client/index.html:1842` | 31 | 26 | 36 |
| `GameClient.connect.<handler:onmessage@1428>` | event | `client/index.html:1428` | 29 | 24 | 36 |
| `GameClient._initPointerEvents.<handler:dblclick@1359>` | event | `client/index.html:1359` | 27 | 22 | 36 |
| `GameClient._initPointerEvents.<handler:mousemove@1319>` | event | `client/index.html:1319` | 27 | 22 | 36 |
| `GameClient.constructor.<handler:resize@629>` | event | `client/index.html:629` | 27 | 22 | 36 |
| `<handler:click@1716>` | event | `client/index.html:1716` | 26 | 22 | 36 |
| `<handler:click@1723>` | event | `client/index.html:1723` | 26 | 22 | 36 |
| `GameClient._initPointerEvents.<handler:touchmove@1387>` | event | `client/index.html:1387` | 26 | 22 | 36 |
| `GameClient._initPointerEvents.<handler:wheel@1342>` | event | `client/index.html:1342` | 26 | 22 | 36 |
| `<handler:change@1622>` | event | `client/index.html:1622` | 16 | 9 | 16 |
| `GameClient.connect.<handler:onclose@1442>.<handler:setTimeout@1445>` | timer | `client/index.html:1445` | 16 | 8 | 16 |
| `GameClient.connect.<handler:setTimeout@1445>` | timer | `client/index.html:1445` | 16 | 8 | 16 |
| `ws_endpoint` | websocket | `server/main.py:135` | 13 | 6 | 16 |
| `<handler:change@1657>` | event | `client/index.html:1657` | 4 | 3 | 5 |
| `<handler:click@1697>` | event | `client/index.html:1697` | 4 | 4 | 3 |
| `<module>` | script | `scripts/setup_assets.py:1` | 4 | 4 | 2 |
| `<handler:change@1885>` | event | `client/index.html:1885` | 3 | 2 | 2 |
| `<handler:click@1875>` | event | `client/index.html:1875` | 3 | 2 | 1 |
| `<handler:click@1876>` | event | `client/index.html:1876` | 3 | 2 | 2 |
| `<handler:click@1638>` | event | `client/index.html:1638` | 2 | 1 | 2 |
| `<handler:click@1643>` | event | `client/index.html:1643` | 2 | 2 | 2 |
| `<handler:click@1778>` | event | `client/index.html:1778` | 2 | 2 | 9 |
| `<handler:click@1884>` | event | `client/index.html:1884` | 2 | 1 | 2 |
| `GameClient.connect.<handler:onclose@1442>` | event | `client/index.html:1442` | 2 | 2 | 1 |
| `GameClient.connect.<handler:onopen@1426>` | event | `client/index.html:1426` | 2 | 1 | 1 |
| `buildParamRows.<handler:input@1564>` | event | `client/index.html:1564` | 2 | 1 | 6 |
| `health` | http | `server/main.py:90` | 2 | 1 | 1 |
| `reset` | http | `server/main.py:116` | 2 | 2 | 3 |
| `<handler:change@1649>` | event | `client/index.html:1649` | 1 | 1 | 2 |
| `<handler:click@1707>` | event | `client/index.html:1707` | 1 | 1 | 1 |
| `<handler:click@1782>` | event | `client/index.html:1782` | 1 | 1 | 1 |
| `<handler:click@1785>` | event | `client/index.html:1785` | 1 | 1 | 2 |
| `<handler:onerror@417>` | event | `client/index.html:417` | 1 | 0 | 1 |
| `<handler:onload@395>` | event | `client/index.html:395` | 1 | 0 | 2 |
| `<handler:onload@416>` | event | `client/index.html:416` | 1 | 0 | 2 |
| `<handler:onload@423>` | event | `client/index.html:423` | 1 | 0 | 2 |
| `<handler:onload@440>` | event | `client/index.html:440` | 1 | 0 | 2 |
| `<handler:onload@449>` | event | `client/index.html:449` | 1 | 0 | 2 |
| `<handler:onload@457>` | event | `client/index.html:457` | 1 | 0 | 2 |
| `<handler:onload@470>` | event | `client/index.html:470` | 1 | 0 | 2 |
| `GameClient._initPointerEvents.<handler:mousedown@1316>` | event | `client/index.html:1316` | 1 | 0 | 1 |
| `GameClient._initPointerEvents.<handler:mouseleave@1339>` | event | `client/index.html:1339` | 1 | 0 | 2 |
| `GameClient._initPointerEvents.<handler:mouseup@1338>` | event | `client/index.html:1338` | 1 | 0 | 1 |
| `GameClient._initPointerEvents.<handler:touchend@1405>` | event | `client/index.html:1405` | 1 | 0 | 1 |
| `GameClient._initPointerEvents.<handler:touchstart@1374>` | event | `client/index.html:1374` | 1 | 1 | 3 |
| `GameClient.connect.<handler:onerror@1448>` | event | `client/index.html:1448` | 1 | 1 | 1 |
| `preloadSprites.<handler:onerror@231>` | event | `client/lib/sprites.mjs:231` | 1 | 1 | 1 |
| `preloadSprites.<handler:onload@226>` | event | `client/lib/sprites.mjs:226` | 1 | 1 | 1 |
| `get_replay` | http | `server/main.py:122` | 1 | 1 | 2 |
| `index` | http | `server/main.py:85` | 1 | 1 | 1 |
| `lifespan` | framework | `server/main.py:48` | 1 | 0 | 1 |

## Server entry points in detail

### `<module>`

Type `script`; reaches 4 functions.

Reached: `<module>`, `create_placeholder_assets`, `_make_png`, `_make_png.chunk`

### `lifespan`

Type `framework`; reaches 1 functions.

Reached: `lifespan`

### `index` (GET `/`)

Type `http`; reaches 1 functions.

Reached: `index`

### `health` (GET `/health`)

Type `http`; reaches 2 functions.

Reached: `health`, `GameEngine.tick`

### `start` (POST `/start`)

Type `http`; reaches 82 functions.

Reached: `start`, `GameEngine.start`, `GameEngine._game_loop`, `GameEngine.serialize`, `Agent.resource_priority`, `Agent.current_goal`, `BuildPlanner.current_goal`, `Player.to_dict`, `FogOfWar.get_visible_entities`, `GameMap.to_dict`, `Tile.to_dict`, `GameEngine._broadcast`, `FogOfWar.to_wire`, `FogOfWar.get_delta`, `GameEngine._run_tick`, `GameEngine._check_win_condition`, `Player.remove_dead`, `FogOfWar.update`, `FogOfWar._reveal_circle`, `Agent.tick`, `Agent._manage_combat`, `_find_nearest_enemy`, `Entity.distance_to`, `Unit.step_path`, `Unit.move_towards` ...

### `reset` (POST `/reset`)

Type `http`; reaches 2 functions.

Reached: `reset`, `GameEngine.reset`

### `get_replay` (GET `/replay`)

Type `http`; reaches 1 functions.

Reached: `get_replay`

### `ws_endpoint` (WS `/ws`)

Type `websocket`; reaches 13 functions.

Reached: `ws_endpoint`, `GameEngine.remove_connection`, `FogOfWar.to_wire`, `FogOfWar.get_delta`, `GameEngine.serialize`, `Agent.resource_priority`, `Agent.current_goal`, `BuildPlanner.current_goal`, `Player.to_dict`, `FogOfWar.get_visible_entities`, `GameMap.to_dict`, `Tile.to_dict`, `GameEngine.add_connection`

