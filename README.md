# Creo MCP Server

Server MCP (Model Context Protocol) per PTC Creo Parametric, basato su [creopyson](https://github.com/Zappabad/creopyson) e CREOSON.

Utilizzato da [CreoAssist](https://github.com/Marco90DM/CreoAssistant) per integrare Claude AI con PTC Creo 11.

## Prerequisiti

- Python 3.9+
- PTC Creo Parametric 11.x
- CREOSON Server 3.0.0

## Installazione rapida

```bat
install.bat
```

### Manuale (venv)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Avvio

```powershell
.venv\Scripts\python.exe creo_mcp.py
```

La connessione a CREOSON è **lazy** — il server si avvia senza Creo aperto.  
La connessione viene stabilita solo quando viene chiamato `creo_connect`.

## Tool disponibili (21)

| Categoria | Tool |
|---|---|
| Connection | `creo_connect`, `creo_get_status` |
| File | `creo_open_file`, `creo_list_files` |
| Drawing | `creo_create_drawing`, `creo_add_model_to_drawing`, `creo_add_sheet` |
| Views | `creo_create_general_view`, `creo_create_projection_view`, `creo_list_views`, `creo_delete_view` |
| Export | `creo_export_pdf`, `creo_export_image`, `creo_export_step`, `creo_export_iges` |
| Layers | `creo_list_layers`, `creo_show_layer`, `creo_hide_layer` |
| Query | `creo_get_drawing_info`, `creo_get_model_info` |
| Appearance | `creo_set_standard_color` |

## Versioning

Segue [Semantic Versioning](https://semver.org/).  
La versione compatibile con CreoAssist è dichiarata in `package.json → creoMcpServer.version`.  
Vedi [ADR-001](https://github.com/Marco90DM/CreoAssistant/blob/main/docs/adr-001-creo-mcp-dependency.md).

## Autori

- Davide Vincon — sviluppo server MCP
- Marco (Marco90DM) — integrazione CreoAssist, fix creopyson 0.7.8
