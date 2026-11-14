# Dead Code Report

**Project**: deep-rts (old engine, pinned `6bfbfd5`)  
**Generated**: 2026-11-14  
**Candidates**: 100

> Candidates have `fan_in = 0` and are not entry points. **This is a library and a game engine**, so many candidates are public API that external C++ consumers or Python could call: the C++ build also ships as `DeepRTSLib` and as a standalone executable. Python-reachable C++ methods are already excluded (they are `python-binding` entry points). Virtual overrides count as called when any caller of the base method exists (class-hierarchy edges).

## Summary

| Risk | Count | Description |
|---|---|---|
| Low | 83 | internal helpers / example code with no callers: likely removable |
| Review first | 17 | public header API, Python wrapper API or pybind trampolines: external consumers possible |
| Recently orphaned (file < 6 months) | 0 | |
| `extraction_method = ai` | 0 | all static |

Note on dates: `code/deep-rts` is the upstream clone and its last commit is 2023-05-16, so every file is more than a year old. File age carries no signal here. Use `git log -L` on a function before deleting.

## Inventory

| Function | Location | File last modified | Risk |
|---|---|---|---|
| `Game._on_tile_deplete` | `DeepRTS/python/game.py:145` | 2021-09-10 | Review first |
| `PyPlayer::getScore` | `bindings/trampolines/PyPlayer.h:17` | 2021-09-11 | Review first (pybind trampoline) |
| `PyScenarioCriteria::evaluate` | `bindings/trampolines/PyScenarioCriteria.h:20` | 2021-09-11 | Review first (pybind trampoline) |
| `PyScenarioCriteria::reward` | `bindings/trampolines/PyScenarioCriteria.h:24` | 2021-09-11 | Review first (pybind trampoline) |
| `Scenario182Data.reset` | `examples/example_03/scenario182.py:19` | 2023-05-17 | Low (example code) |
| `Scenario182.__init__` | `examples/example_03/scenario182.py:25` | 2023-05-17 | Low (example code) |
| `Scenario182NoRewards.__init__` | `examples/example_03/scenario182norewards.py:25` | 2023-05-17 | Low (example code) |
| `RandomAgent.__init__` | `examples/example_04/random_agent.py:7` | 2023-05-17 | Low (example code) |
| `RandomAgent.get_state` | `examples/example_04/random_agent.py:10` | 2023-05-17 | Low (example code) |
| `RandomAgent.get_action` | `examples/example_04/random_agent.py:13` | 2023-05-17 | Low (example code) |
| `RandomAgent.state_preprocess` | `examples/example_04/random_agent.py:16` | 2023-05-17 | Low (example code) |
| `RandomAgent.memorize` | `examples/example_04/random_agent.py:20` | 2023-05-17 | Low (example code) |
| `QNetwork.forward` | `examples/example_05/torch/conv_agent.py:44` | 2023-05-17 | Low (example code) |
| `ReplayBuffer.__len__` | `examples/example_05/torch/conv_agent.py:98` | 2023-05-17 | Low (example code) |
| `DiegoConvAgent.__init__` | `examples/example_05/torch/conv_agent.py:103` | 2023-05-17 | Low (example code) |
| `DiegoConvAgent.update` | `examples/example_05/torch/conv_agent.py:123` | 2023-05-17 | Low (example code) |
| `DiegoConvAgent.get_action` | `examples/example_05/torch/conv_agent.py:178` | 2023-05-17 | Low (example code) |
| `DiegoConvAgent.load` | `examples/example_05/torch/conv_agent.py:199` | 2023-05-17 | Low (example code) |
| `DiegoConvAgent.save` | `examples/example_05/torch/conv_agent.py:203` | 2023-05-17 | Low (example code) |
| `QNetworkMedium.forward` | `examples/example_05/torch/fc_agent.py:38` | 2023-05-17 | Low (example code) |
| `QNetworkSmall.forward` | `examples/example_05/torch/fc_agent.py:62` | 2023-05-17 | Low (example code) |
| `ReplayBuffer.add` | `examples/example_05/torch/fc_agent.py:84` | 2023-05-17 | Low (example code) |
| `ReplayBuffer.sample` | `examples/example_05/torch/fc_agent.py:88` | 2023-05-17 | Low (example code) |
| `ReplayBuffer.__len__` | `examples/example_05/torch/fc_agent.py:110` | 2023-05-17 | Low (example code) |
| `TorchDQNAgent.__init__` | `examples/example_05/torch/fc_agent.py:115` | 2023-05-17 | Low (example code) |
| `TorchDQNAgent.update` | `examples/example_05/torch/fc_agent.py:143` | 2023-05-17 | Low (example code) |
| `TorchDQNAgent.get_action` | `examples/example_05/torch/fc_agent.py:196` | 2023-05-17 | Low (example code) |
| `TorchDQNAgent.save` | `examples/example_05/torch/fc_agent.py:217` | 2023-05-17 | Low (example code) |
| `TorchDQNAgent.load` | `examples/example_05/torch/fc_agent.py:220` | 2023-05-17 | Low (example code) |
| `ImageToPyTorch.__init__` | `examples/example_05/wrappers.py:6` | 2023-05-17 | Low (example code) |
| `ImageToPyTorch.observation` | `examples/example_05/wrappers.py:20` | 2023-05-17 | Low (example code) |
| `gpu_count` | `examples/old/util.py:13` | 2023-05-17 | Low (example code) |
| `TensorBoardTool.__init__` | `examples/old/util.py:18` | 2023-05-17 | Low (example code) |
| `TensorBoardTool.run` | `examples/old/util.py:22` | 2023-05-17 | Low (example code) |
| `LimitedDiscrete.__init__` | `examples/old/util.py:37` | 2023-05-17 | Low (example code) |
| `LimitedDiscrete.sample` | `examples/old/util.py:45` | 2023-05-17 | Low (example code) |
| `LimitedDiscrete.contains` | `examples/old/util.py:48` | 2023-05-17 | Low (example code) |
| `LimitedDiscrete.__repr__` | `examples/old/util.py:57` | 2023-05-17 | Low (example code) |
| `LimitedDiscrete.__eq__` | `examples/old/util.py:60` | 2023-05-17 | Low (example code) |
| `Config::setAnimationEnabled` | `include/DeepRTS/Config.h:60` | 2021-09-11 | Review first (public header API) |
| `Config::setYieldModifierGold` | `include/DeepRTS/Config.h:68` | 2021-09-11 | Review first (public header API) |
| `Config::setYieldModifierStone` | `include/DeepRTS/Config.h:72` | 2021-09-11 | Review first (public header API) |
| `Config::setYieldModifierLumber` | `include/DeepRTS/Config.h:76` | 2021-09-11 | Review first (public header API) |
| `ResourceLoader::ResourceLoader` | `include/DeepRTS/ResourceLoader.h:50` | 2021-09-11 | Review first (public header API) |
| `AddUnit::AddUnit` | `include/DeepRTS/gamestate/AddUnit.h:19` | 2021-09-11 | Review first (public header API) |
| `StateChange::apply` | `include/DeepRTS/gamestate/StateChange.h:13` | 2021-09-11 | Review first (public header API) |
| `StateChange::apply_reverse` | `include/DeepRTS/gamestate/StateChange.h:17` | 2021-09-11 | Review first (public header API) |
| `BLend2DUnitDirection::get` | `include/DeepRTS/gui/Blend2DGUI.h:118` | 2021-09-11 | Low (internal) |
| `Blend2DTile::Blend2DTile` | `include/DeepRTS/gui/Blend2DGUI.h:905` | 2021-09-11 | Low (internal) |
| `ColorConverter::hsv` | `include/DeepRTS/util/ColorConverter.hpp:15` | 2021-09-04 | Review first (public header API) |
| `Position::Position` | `include/DeepRTS/util/Position.h:9` | 2021-09-04 | Review first (public header API) |
| `Position::Position#L10` | `include/DeepRTS/util/Position.h:10` | 2021-09-04 | Review first (public header API) |
| `PriorityQueue::clear` | `include/DeepRTS/util/PriorityQueue.hpp:29` | 2021-09-04 | Review first (public header API) |
| `matrix::matrix` | `include/DeepRTS/util/matrix.h:37` | 2021-09-04 | Review first (public header API) |
| `Player::getFoodConsumption` | `src/Player.cpp:130` | 2021-09-11 | Low (internal) |
| `Player::getFood` | `src/Player.cpp:134` | 2021-09-11 | Low (internal) |
| `Player::getGold` | `src/Player.cpp:138` | 2021-09-11 | Low (internal) |
| `Player::getStone` | `src/Player.cpp:142` | 2021-09-11 | Low (internal) |
| `Player::getLumber` | `src/Player.cpp:146` | 2021-09-11 | Low (internal) |
| `Player::getUnitCount` | `src/Player.cpp:150` | 2021-09-11 | Low (internal) |
| `Tile::setResources` | `src/Tile.cpp:225` | 2021-09-11 | Low (internal) |
| `Tile::getDepleteTile` | `src/Tile.cpp:254` | 2021-09-11 | Low (internal) |
| `Tilemap::operator()` | `src/Tilemap.cpp:190` | 2021-09-11 | Low (internal) |
| `Unit::moveRelative` | `src/Unit.cpp:39` | 2021-09-11 | Low (internal) |
| `Unit::rightClickRelative` | `src/Unit.cpp:50` | 2021-09-11 | Low (internal) |
| `Unit::operator==` | `src/Unit.cpp:447` | 2021-09-11 | Low (internal) |
| `Unit::getVisionTileIDs` | `src/Unit.cpp:555` | 2021-09-11 | Low (internal) |
| `AddUnit::apply` | `src/gamestate/AddUnit.cpp:11` | 2021-09-11 | Low (internal) |
| `AddUnit::apply_reverse` | `src/gamestate/AddUnit.cpp:16` | 2021-09-11 | Low (internal) |
| `DamageDone::evaluate` | `src/scenario/criteria/DamageDone.cpp:13` | 2021-09-08 | Low (internal) |
| `DamageDone::reward` | `src/scenario/criteria/DamageDone.cpp:18` | 2021-09-08 | Low (internal) |
| `DamageDoneIncrement::evaluate` | `src/scenario/criteria/DamageDoneIncrement.cpp:13` | 2021-09-08 | Low (internal) |
| `DamageDoneIncrement::reward` | `src/scenario/criteria/DamageDoneIncrement.cpp:19` | 2021-09-08 | Low (internal) |
| `DamageTaken::evaluate` | `src/scenario/criteria/DamageTaken.cpp:13` | 2021-09-08 | Low (internal) |
| `DamageTaken::reward` | `src/scenario/criteria/DamageTaken.cpp:18` | 2021-09-08 | Low (internal) |
| `DamageTakenIncrement::evaluate` | `src/scenario/criteria/DamageTakenIncrement.cpp:14` | 2021-09-08 | Low (internal) |
| `DamageTakenIncrement::reward` | `src/scenario/criteria/DamageTakenIncrement.cpp:20` | 2021-09-08 | Low (internal) |
| `FoodConsumption::evaluate` | `src/scenario/criteria/FoodConsumption.cpp:14` | 2021-09-08 | Low (internal) |
| `FoodConsumption::reward` | `src/scenario/criteria/FoodConsumption.cpp:19` | 2021-09-08 | Low (internal) |
| `FoodCount::evaluate` | `src/scenario/criteria/FoodCount.cpp:14` | 2021-09-08 | Low (internal) |
| `FoodCount::reward` | `src/scenario/criteria/FoodCount.cpp:19` | 2021-09-08 | Low (internal) |
| `GameEnd::evaluate` | `src/scenario/criteria/GameEnd.cpp:8` | 2023-01-18 | Low (internal) |
| `GameEnd::reward` | `src/scenario/criteria/GameEnd.cpp:17` | 2023-01-18 | Low (internal) |
| `GoldCollect::evaluate` | `src/scenario/criteria/GoldCollect.cpp:14` | 2021-09-08 | Low (internal) |
| `GoldCollect::reward` | `src/scenario/criteria/GoldCollect.cpp:19` | 2021-09-08 | Low (internal) |
| `LumberCollect::evaluate` | `src/scenario/criteria/LumberCollect.cpp:13` | 2021-09-08 | Low (internal) |
| `LumberCollect::reward` | `src/scenario/criteria/LumberCollect.cpp:18` | 2021-09-08 | Low (internal) |
| `NumUnitTypeCreated::evaluate` | `src/scenario/criteria/NumUnitTypeCreated.cpp:8` | 2021-09-08 | Low (internal) |
| `NumUnitTypeCreated::reward` | `src/scenario/criteria/NumUnitTypeCreated.cpp:42` | 2021-09-08 | Low (internal) |
| `ResourceIncrement::evaluate` | `src/scenario/criteria/ResourceIncrement.cpp:14` | 2021-09-08 | Low (internal) |
| `ResourceIncrement::reward` | `src/scenario/criteria/ResourceIncrement.cpp:34` | 2021-09-08 | Low (internal) |
| `StoneCollect::evaluate` | `src/scenario/criteria/StoneCollect.cpp:14` | 2021-09-08 | Low (internal) |
| `StoneCollect::reward` | `src/scenario/criteria/StoneCollect.cpp:19` | 2021-09-08 | Low (internal) |
| `UnitIncrement::evaluate` | `src/scenario/criteria/UnitIncrement.cpp:13` | 2021-09-08 | Low (internal) |
| `UnitIncrement::reward` | `src/scenario/criteria/UnitIncrement.cpp:52` | 2021-09-08 | Low (internal) |
| `UnitsCreated::evaluate` | `src/scenario/criteria/UnitsCreated.cpp:13` | 2021-09-08 | Low (internal) |
| `UnitsCreated::reward` | `src/scenario/criteria/UnitsCreated.cpp:18` | 2021-09-08 | Low (internal) |
| `Pathfinder::aStar` | `src/util/Pathfinder.cpp:19` | 2021-09-11 | Low (internal) |
| `Pathfinder::find_closest_walkable_tile` | `src/util/Pathfinder.cpp:80` | 2021-09-11 | Low (internal) |
| `Pathfinder::find_first_attackable_tile` | `src/util/Pathfinder.cpp:184` | 2021-09-11 | Low (internal) |

## Removal Guidance

1. **Confirm with git blame**: check whether call sites were recently removed.
2. **Search for string references**: pybind names and Python `getattr` use strings, which the graph cannot see.
3. **Check the examples**: `examples/` consumers are in the graph, but external user code is not.
4. **Header-only inline getters** (`Player::getGold` etc.) are cheap and API-shaped: removing them is low value.
