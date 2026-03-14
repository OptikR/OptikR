# Project Structure and Config (`clean`)

## High-Level Layout

Current structure in `D:/1/clean` uses:

- `app/` for application logic
- `ui/` for UI components
- `plugins/stages/` for capture/ocr/translation/vision/llm stage plugins
- `plugins/enhancers/` for optimizer and text-processor plugins
- `user_data/` for user-owned runtime data
- `system_data/` for system-managed runtime data

## Config File Location

Primary config path is:

- `user_data/config/user_config.json`

The config helper default confirms this:

- `app/utils/path_utils.py` -> `get_config_file(filename: str = "user_config.json")`

## Config API Import

Use the config facade from:

- `app.core.config`

Backward-compatible aliases are exported there:

- `ConfigManager = ConfigFacade`
- `SimpleConfigManager = ConfigFacade`

## Important Migration Note

Older docs often mention:

- `config/system_config.json`
- `core.config_manager`
- `src/` and `components/`

Those references are legacy and do not describe the current `clean` layout.
