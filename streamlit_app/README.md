# Visor de animales afectados — Sismo del 10 de agosto (UNGRD)

Visor en Streamlit para apoyar decisiones sobre la atención a animales de
producción, compañía y silvestres afectados en Chocó, Valle del Cauca,
Risaralda y Quindío. Lee directamente el Excel fuente (no guarda copias):
cada vez que se actualice la matriz, basta con guardar el archivo y
presionar **"Actualizar datos"** en el visor.

## Archivos

- `app.py` — la aplicación (ejecútala con `streamlit run app.py`).
- `data.py` — lee el Excel y los GeoJSON, y arma las tablas que usa el visor.
- `insights.py` — calcula los "hallazgos clave" a partir de los datos.
- `static/icons/` — logo UNGRD e íconos (ya recortados, fondo transparente).
  Streamlit los sirve como archivos estáticos (`server.enableStaticServing`
  en `.streamlit/config.toml`), por eso deben llamarse `static/` exactamente.
- Este visor espera encontrar, en la carpeta **de arriba** (`..`):
  `Afectaciones animales18082026.xlsx`, `Departamentos.geojson` y
  `Municipios.geojson` — los mismos archivos que ya tienes en
  `visor_animales_emergencias_agosto/`.

## Cómo ejecutarlo

⚠️ La carpeta del proyecto está en una unidad **exFAT** (el USB Kingston),
que no soporta enlaces simbólicos — por eso el entorno virtual de Python
**no se puede crear ahí mismo**. Créalo en tu carpeta de usuario y apunta a
`app.py` con la ruta completa:

```bash
# una sola vez
python3 -m venv ~/.venvs/ungrd-visor
source ~/.venvs/ungrd-visor/bin/activate
pip install -r "/ruta/a/streamlit_app/requirements.txt"

# cada vez que quieras abrir el visor
source ~/.venvs/ungrd-visor/bin/activate
streamlit run "/run/media/moises-santizo/KINGSTON/UNGRD/visor_animales_emergencias_agosto/streamlit_app/app.py"
```

Se abre solo en el navegador en `http://localhost:8501`.

## Qué muestra

- **Hallazgos clave**: 4–5 lecturas automáticas de la matriz (concentración
  geográfica, categoría más golpeada, brechas de cobertura o de reporte de
  necesidades) — se recalculan solas, no son texto fijo.
- **Mapa**: departamentos de Colombia con contexto geográfico real (costa,
  países vecinos); clic en un departamento entra a sus municipios, clic en
  un municipio filtra todo el visor. Los municipios sin ningún reporte en
  la matriz (todo Chocó salvo Medio Baudó) se pintan distinto a los que
  reportaron cero afectación.
- **Ranking**: solo entra afectación real — los municipios en cero no se
  grafican, solo se cuentan aparte.
- **Composición por categoría**: qué tan resuelto está cada categoría
  (desapariciones vs. lesiones/muertes/rescates).
- **Necesidades**: kg solicitados por municipio + el detalle de cada
  requerimiento, sin las filas vacías.
- **Matriz de datos fuente**: queda disponible pero colapsada — para
  auditoría, no como vista principal.

## Notas sobre los datos (ver también el visor → "Notas metodológicas")

- El total de la fila "TOTAL" de la hoja fuente no incluye Chocó (su rango
  de fórmulas es `C3:C71`); este visor sí lo incluye, por ser la zona más
  cercana al epicentro en San José del Palmar.
- Se corrigió el departamento "Cocó" → "Chocó".
- "En alojamiento temporal" no viene desagregado por categoría de animal en
  la hoja fuente, así que se muestra como indicador único.
