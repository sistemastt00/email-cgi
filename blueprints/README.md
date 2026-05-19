# blueprints/

Carpeta para los blueprints exportados de Make.com.

## Convención de nombres

| Archivo                              | Escenario Make                              |
|--------------------------------------|---------------------------------------------|
| `blueprint_1_clasificacion.json`     | Escenario 1 — Clasificación principal       |
| `blueprint_1_0_correo_clasif.json`   | Escenario 1.0 — Correo interno equipo       |
| `blueprint_1_1_nuevo_hilo.json`      | Escenario 1.1 — Hilo nuevo (Bitrix + datos) |
| `blueprint_1_2_cadena.json`          | Escenario 1.2 — Hilo existente (cadena)     |
| `blueprint_1_4_area_general.json`    | Escenario 1.4 — Área General CTAs           |
| `blueprint_1_5_bot_humano.json`      | Escenario 1.5 — Router bot/humano           |

## Workflow para validar cambios

1. Exporta el blueprint actualizado desde Make.com (botón "Export Blueprint").
2. Guarda el `.json` en esta carpeta con el nombre de la tabla anterior.
3. Dile a Claude: **"valida los blueprints contra el código"** o **"ha cambiado el blueprint X, actualiza el código"**.
4. Claude leerá los JSON, comparará filtros y condiciones con el Python, e informará discrepancias o aplicará los cambios.

## Qué valida Claude

- Condiciones de filtro entre nodos (groups = OR, conditions dentro del group = AND)
- Gates de tipo, categoría, bot_humano, cliente
- Orden de las ramas y fallback paths
- Campos que se actualizan en Airtable / Bitrix
- Asuntos y destinatarios de emails enviados
