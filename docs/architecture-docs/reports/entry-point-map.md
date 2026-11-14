# Entry Point Map

**Project**: deep-rts (old engine, pinned `6bfbfd5`)  
**Generated**: 2026-11-14  
**Entry Points**: 166

Entry-point rules used (project-specific; the skill's HTTP/cron rules do not apply to a game engine):

| Type | Rule | Count |
|---|---|---|
| `python-binding` | C++ method/lambda exposed to Python by a pybind11 `.def*` registration | 110 |
| `api` | public (non-underscore) function/method of the `DeepRTS/python` package | 44 |
| `script` | module-level code of an example or package script | 9 |
| `python-module-init` | `PYBIND11_MODULE` / `PYBIND11_EMBEDDED_MODULE` (runs on `import`) | 2 |
| `cli` | `main()` of the standalone C++ executable (`src/main.cpp`) | 1 |

## Summary (all entry points except individual python-binding methods)

| Entry Point | Type | Reachable functions | External-touching | Conditional edges |
|---|---|---|---|---|
| `main` | cli | 274 | 67 | 234 |
| `<module>` | script | 237 | 51 | 227 |
| `Game.update` | api | 132 | 24 | 136 |
| `Game.__init__` | api | 97 | 18 | 45 |
| `<module>` | script | 20 | 1 | 5 |
| `PYBIND11_MODULE` | python-module-init | 14 | 14 | 0 |
| `PYBIND11_EMBEDDED_MODULE` | python-module-init | 14 | 14 | 0 |
| `GUI.__init__` | api | 8 | 0 | 1 |
| `AbstractGUI.__init__` | api | 7 | 0 | 1 |
| `AbstractGUI.setup` | api | 6 | 0 | 1 |
| `AbstractGUI.on_tile_change` | api | 4 | 0 | 2 |
| `Game.view` | api | 3 | 0 | 2 |
| `Game.event` | api | 3 | 0 | 2 |
| `Game.capture` | api | 3 | 0 | 2 |
| `AbstractGUI.render` | api | 3 | 0 | 2 |
| `Game.get_state` | api | 2 | 0 | 1 |
| `Game.set_player` | api | 2 | 0 | 0 |
| `AbstractGUI.event` | api | 2 | 0 | 2 |
| `AbstractGUI.draw_unit` | api | 2 | 0 | 0 |
| `Config.__init__` | api | 1 | 0 | 0 |
| `Game.players` | api | 1 | 0 | 0 |
| `Game.sample_action` | api | 1 | 0 | 0 |
| `Game.set_render_frequency` | api | 1 | 0 | 0 |
| `Game.set_view_every` | api | 1 | 0 | 0 |
| `Game.set_capture_every` | api | 1 | 0 | 0 |
| `<module>` | script | 1 | 0 | 0 |
| `AbstractGUI.sprite_definitions` | api | 1 | 0 | 0 |
| `AbstractGUI.tile_definitions` | api | 1 | 0 | 0 |
| `AbstractGUI.capture` | api | 1 | 0 | 0 |
| `AbstractGUI.draw_tile` | api | 1 | 0 | 0 |
| `AbstractGUI.view` | api | 1 | 0 | 0 |
| `GUI.sprite_definitions` | api | 1 | 0 | 0 |
| `<module>` | script | 1 | 0 | 0 |
| `BaseAgent.__init__` | api | 1 | 0 | 0 |
| `BaseAgent.get_state` | api | 1 | 0 | 0 |
| `BaseAgent.get_action` | api | 1 | 0 | 0 |
| `BaseAgent.set_player` | api | 1 | 0 | 0 |
| `BaseAgent.set_env` | api | 1 | 0 | 0 |
| `BaseAgent.memorize` | api | 1 | 0 | 0 |
| `BaseAgent.state_preprocess` | api | 1 | 0 | 0 |
| `BaseAgent.save` | api | 1 | 0 | 0 |
| `BaseAgent.load` | api | 1 | 0 | 0 |
| `Elo.rating_difference` | api | 1 | 0 | 0 |
| `Elo.expected` | api | 1 | 0 | 0 |
| `Elo.calculate` | api | 1 | 0 | 0 |
| `Tournament.__init__` | api | 1 | 0 | 0 |
| `Tournament.reset` | api | 1 | 0 | 0 |
| `Tournament.start` | api | 1 | 0 | 0 |
| `Tournament.add_agent` | api | 1 | 0 | 0 |
| `Tournament.is_pow_2` | api | 1 | 0 | 0 |
| `Tournament.divide_chunks` | api | 1 | 0 | 0 |
| `<module>` | script | 1 | 0 | 0 |
| `<module>` | script | 1 | 0 | 0 |
| `<module>` | script | 1 | 0 | 0 |
| `<module>` | script | 1 | 0 | 0 |
| `<module>` | script | 1 | 0 | 0 |

## Bound C++ surface by Python class (the `python-binding` entry points)

| Python class | Bound C++ nodes | Largest reach | Methods |
|---|---|---|---|
| `Game` | 31 | 147 (`Game::reset`) | Game, Game#L26, setMaxFPS, start, stop, reset, update, render … |
| `Config` | 19 | 18 (`Config::defaults`) | setGUI, setConsoleCaptionEnabled, setPOMDP, setTickModifier, setInstantTownHall, setInstantBuilding, setHarvestForever, setAutoAttack … |
| `Player` | 14 | 141 (`Player::Player`) | Player, spawnUnitNearSpawnPoint, getId, getScore, evaluatePlayerState, setState, addUnit, setName … |
| `Tile` | 12 | 20 (`Tile::Tile`) | Tile, hasOccupant, getOccupant, getResources, isAttackable, isWalkable, isHarvestable, getOccupantID … |
| `Scenario` | 7 | 204 (`Scenario::computeOptimalStrategy`) | Scenario, evaluate, reward, optimalStrategy, computeOptimalStrategy, optimalPlayGameStep, update |
| `Unit` | 5 | 57 (`Unit::rightClick`) | Unit, spawn, rightClick, getNextTile, getPlayer |
| `Tilemap` | 2 | 21 (`Tilemap::Tilemap`) | Tilemap, getTile |
| `Map` | 1 | 7 (`Map::Map`) | Map |
| `UnitManager` | 1 | 9 (`UnitManager::constructUnit`) | constructUnit |
| `DamageDone` | 1 | 2 (`DamageDone::DamageDone`) | DamageDone |
| `DamageDoneIncrement` | 1 | 2 (`DamageDoneIncrement::DamageDoneIncrement`) | DamageDoneIncrement |
| `DamageTaken` | 1 | 2 (`DamageTaken::DamageTaken`) | DamageTaken |
| `DamageTakenIncrement` | 1 | 2 (`DamageTakenIncrement::DamageTakenIncrement`) | DamageTakenIncrement |
| `FoodConsumption` | 1 | 2 (`FoodConsumption::FoodConsumption`) | FoodConsumption |
| `FoodCount` | 1 | 2 (`FoodCount::FoodCount`) | FoodCount |
| `GameEnd` | 1 | 2 (`GameEnd::GameEnd`) | GameEnd |
| `GoldCollect` | 1 | 2 (`GoldCollect::GoldCollect`) | GoldCollect |
| `LumberCollect` | 1 | 2 (`LumberCollect::LumberCollect`) | LumberCollect |
| `NumUnitTypeCreated` | 1 | 4 (`NumUnitTypeCreated::NumUnitTypeCreated`) | NumUnitTypeCreated |
| `ResourceIncrement` | 1 | 2 (`ResourceIncrement::ResourceIncrement`) | ResourceIncrement |
| `ScenarioCriteria` | 1 | 1 (`ScenarioCriteria::ScenarioCriteria`) | ScenarioCriteria |
| `StoneCollect` | 1 | 2 (`StoneCollect::StoneCollect`) | StoneCollect |
| `UnitIncrement` | 1 | 4 (`UnitIncrement::UnitIncrement`) | UnitIncrement |
| `UnitsCreated` | 1 | 2 (`UnitsCreated::UnitsCreated`) | UnitsCreated |
| `GeneralAIOneVersusOne` | 1 | 109 (`GeneralAIOneVersusOne::GeneralAIOneVersusOne`) | GeneralAIOneVersusOne |
| `GoldCollectFifteen` | 1 | 117 (`GoldCollectFifteen::GoldCollectFifteen`) | GoldCollectFifteen |
| `(free)` | 1 | 1 (`Random.get<lambda>`) | get<lambda> |

## Deepest chains (top 8 by reach)

### `main` (cli), reaches 274 functions

**Handler**: `src/main.cpp:14`

```
→ main
→ Config::defaults
→ Config::setTickModifier
→ Config::setInstantTownHall
→ Config::setInstantBuilding
→ Config::setHarvestForever
→ Config::setAutoAttack
→ Config::setFoodLimit
→ Config::setFarm
→ Config::setBarracks
→ Config::setFootman
→ Config::setArcher
→ Config::setConsoleCaptionEnabled
→ Config::setStartGold
→ Config::setStartLumber
→ Config::setStartStone
→ Config::setTerminalSignal
→ Config::setPOMDP
→ Config::setGUI
→ LavaMaze::LavaMaze
→ Scenario::Scenario
→ Game::Game#L26
→ Map::Map
→ ResourceLoader::loadMapJSON
→ ResourceLoader::getFilePath
… 249 more (query `view_entry_traces` for the full path)
```

| Aspect | Detail |
|---|---|
| Reachable functions | 274 |
| Data stores accessed | None |
| External-touching functions | 67 |
| Async boundaries | 0 (single-threaded game loop; no async in the engine) |
| Conditional edges in reach | 234 |
| Virtual-dispatch edges in reach | 115 |

### `<module>` (script), reaches 237 functions

**Handler**: `examples/example_01/basic_01.py:1`

```
→ <module>
→ Config::defaults
→ Config::setTickModifier
→ Config::setInstantTownHall
→ Config::setInstantBuilding
→ Config::setHarvestForever
→ Config::setAutoAttack
→ Config::setFoodLimit
→ Config::setFarm
→ Config::setBarracks
→ Config::setFootman
→ Config::setArcher
→ Config::setConsoleCaptionEnabled
→ Config::setStartGold
→ Config::setStartLumber
→ Config::setStartStone
→ Config::setTerminalSignal
→ Config::setPOMDP
→ Config::setGUI
→ Game::Game
→ Map::Map
→ ResourceLoader::loadMapJSON
→ ResourceLoader::getFilePath
→ GetCurrentWorkingDir
→ ResourceLoader::getInstance
… 212 more (query `view_entry_traces` for the full path)
```

| Aspect | Detail |
|---|---|
| Reachable functions | 237 |
| Data stores accessed | None |
| External-touching functions | 51 |
| Async boundaries | 0 (single-threaded game loop; no async in the engine) |
| Conditional edges in reach | 227 |
| Virtual-dispatch edges in reach | 96 |

### `Scenario::computeOptimalStrategy` (python-binding), reaches 204 functions

**Handler**: `src/scenario/Scenario.cpp:55`

```
→ Scenario::computeOptimalStrategy
→ Scenario::optimalStrategy
→ GoldCollectFifteen::optimalStrategy
→ LavaMaze::optimalStrategy
→ Game::setSelectedPlayer
→ Game::getUnitByNameID
→ Scenario::optimalPlayGameStep
→ Scenario::update
→ Game::update
→ Game::tick
→ Unit::update
→ BaseState::update
→ Building::update
→ Unit::getBuildEntity
→ Pathfinder::find_first_walkable_tile
→ Tile::isWalkable
→ Tilemap::neighbors
→ Tile::isAttackable
→ Tile::getOccupant
→ Player::getId
→ Tile::isHarvestable
→ Tile::getTilemap
→ Unit::setPosition
→ Unit::clearTiles
→ Tilemap::getTileArea
… 179 more (query `view_entry_traces` for the full path)
```

| Aspect | Detail |
|---|---|
| Reachable functions | 204 |
| Data stores accessed | None |
| External-touching functions | 52 |
| Async boundaries | 0 (single-threaded game loop; no async in the engine) |
| Conditional edges in reach | 199 |
| Virtual-dispatch edges in reach | 111 |

### `Game::reset` (python-binding), reaches 147 functions

**Handler**: `src/Game.cpp:79`

```
→ Game::reset
→ Tilemap::reset
→ Tile::reset
→ Tile::hasOccupant
→ Unit::clearStateForTile
→ Tile::getOccupant
→ Tile::setDepleted
→ Tile::triggerOnTileChange
→ Game::_onTileChange
→ Blend2DGUI::onTileChange
→ Blend2DTileset::at
→ Tile::getTypeId
→ Tile::getOccupantID
→ Blend2DWrapper::blit
→ Player::getId
→ PyGame::_onTileChange
→ Game._on_tile_change
→ AbstractGUI.on_tile_change
→ AbstractGUI.render
→ AbstractGUI.draw_unit
→ AbstractGUI.draw_tile
→ Player::reset
→ Player::spawnPlayer
→ Tilemap::getSpawnTile
→ Player::spawn
… 122 more (query `view_entry_traces` for the full path)
```

| Aspect | Detail |
|---|---|
| Reachable functions | 147 |
| Data stores accessed | None |
| External-touching functions | 32 |
| Async boundaries | 0 (single-threaded game loop; no async in the engine) |
| Conditional edges in reach | 150 |
| Virtual-dispatch edges in reach | 87 |

### `Player::Player` (python-binding), reaches 141 functions

**Handler**: `src/Player.cpp:14`

```
→ Player::Player
→ Player::setName
→ Player::reset
→ Player::spawnPlayer
→ Tilemap::getSpawnTile
→ Player::getId
→ Player::spawn
→ Player::addUnit
→ UnitManager::constructUnit
→ UnitManager::constructTownHall
→ Unit::Unit
→ Player::getGame
→ UnitManager::constructPeasant
→ UnitManager::constructFarm
→ UnitManager::constructBarracks
→ UnitManager::constructFootman
→ UnitManager::constructArcher
→ UnitManager::updateUnitCount
→ Game::_onUnitCreate
→ PyGame::_onUnitCreate
→ Game._on_unit_create
→ Player::spawnUnit
→ Unit::spawn
→ Unit::transitionState#L313
→ BaseState::end
… 116 more (query `view_entry_traces` for the full path)
```

| Aspect | Detail |
|---|---|
| Reachable functions | 141 |
| Data stores accessed | None |
| External-touching functions | 34 |
| Async boundaries | 0 (single-threaded game loop; no async in the engine) |
| Conditional edges in reach | 145 |
| Virtual-dispatch edges in reach | 82 |

### `Game.update` (api), reaches 132 functions

**Handler**: `DeepRTS/python/game.py:90`

```
→ Game.update
→ Game::tick
→ Game.event
→ AbstractGUI.event
→ AbstractGUI.view
→ Game::update
→ Unit::update
→ BaseState::update
→ Building::update
→ Unit::getBuildEntity
→ Pathfinder::find_first_walkable_tile
→ Tile::isWalkable
→ Tilemap::neighbors
→ Tile::isAttackable
→ Tile::getOccupant
→ Player::getId
→ Tile::isHarvestable
→ Tile::getTilemap
→ Unit::setPosition
→ Unit::clearTiles
→ Tilemap::getTileArea
→ Tilemap::getTile
→ Unit::clearStateForTile
→ Tile::setOccupant
→ Tile::setOccupantID
… 107 more (query `view_entry_traces` for the full path)
```

| Aspect | Detail |
|---|---|
| Reachable functions | 132 |
| Data stores accessed | None |
| External-touching functions | 24 |
| Async boundaries | 0 (single-threaded game loop; no async in the engine) |
| Conditional edges in reach | 136 |
| Virtual-dispatch edges in reach | 88 |

### `Player::spawnUnitNearSpawnPoint` (python-binding), reaches 129 functions

**Handler**: `src/Player.cpp:116`

```
→ Player::spawnUnitNearSpawnPoint
→ Tilemap::getSpawnTile
→ Player::getId
→ Tilemap::neighbors
→ Tile::isWalkable
→ Tile::isAttackable
→ Tile::getOccupant
→ Tile::isHarvestable
→ Player::addUnit
→ UnitManager::constructUnit
→ UnitManager::constructTownHall
→ Unit::Unit
→ Player::getGame
→ UnitManager::constructPeasant
→ UnitManager::constructFarm
→ UnitManager::constructBarracks
→ UnitManager::constructFootman
→ UnitManager::constructArcher
→ UnitManager::updateUnitCount
→ Game::_onUnitCreate
→ PyGame::_onUnitCreate
→ Game._on_unit_create
→ Player::spawnUnit
→ Unit::spawn
→ Unit::transitionState#L313
… 104 more (query `view_entry_traces` for the full path)
```

| Aspect | Detail |
|---|---|
| Reachable functions | 129 |
| Data stores accessed | None |
| External-touching functions | 30 |
| Async boundaries | 0 (single-threaded game loop; no async in the engine) |
| Conditional edges in reach | 129 |
| Virtual-dispatch edges in reach | 82 |

### `Scenario::optimalPlayGameStep` (python-binding), reaches 121 functions

**Handler**: `src/scenario/Scenario.cpp:107`

```
→ Scenario::optimalPlayGameStep
→ Scenario::update
→ Game::update
→ Game::tick
→ Unit::update
→ BaseState::update
→ Building::update
→ Unit::getBuildEntity
→ Pathfinder::find_first_walkable_tile
→ Tile::isWalkable
→ Tilemap::neighbors
→ Tile::isAttackable
→ Tile::getOccupant
→ Player::getId
→ Tile::isHarvestable
→ Tile::getTilemap
→ Unit::setPosition
→ Unit::clearTiles
→ Tilemap::getTileArea
→ Tilemap::getTile
→ Unit::clearStateForTile
→ Tile::setOccupant
→ Tile::setOccupantID
→ Game::_onTileChange
→ Blend2DGUI::onTileChange
… 96 more (query `view_entry_traces` for the full path)
```

| Aspect | Detail |
|---|---|
| Reachable functions | 121 |
| Data stores accessed | None |
| External-touching functions | 25 |
| Async boundaries | 0 (single-threaded game loop; no async in the engine) |
| Conditional edges in reach | 127 |
| Virtual-dispatch edges in reach | 84 |

