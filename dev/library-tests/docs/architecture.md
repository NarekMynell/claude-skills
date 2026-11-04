# Architecture

The capability map of the code library's domains, which `ProjectArchitectureTests` compares with the code when it runs here.

| Capability | Interface | Implemented by | Used by |
|---|---|---|---|
| Plays sounds | `IAudioService` | `AudioService` | whoever makes a sound |
| Saves and loads | `ISaveService` | `JsonSaveService` | whoever keeps progress |
| Stores save files | `ISaveStorage` | `FileSaveStorage` | `JsonSaveService` |
| Upgrades old saves | `ISaveMigration` | each project's migrations | `JsonSaveService` |
