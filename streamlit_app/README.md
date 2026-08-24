# Visor de animales afectados — Sismo del 10 de agosto (UNGRD)

Visor en Streamlit para apoyar decisiones sobre la atención a animales de
producción, compañía y silvestres afectados en Chocó, Valle del Cauca,
Risaralda y Quindío.

**Fuente de datos en línea**: la app descarga directamente la matriz publicada
en Google Sheets (no guarda copias). Cada vez que la matriz se actualice,
basta con presionar **"Actualizar datos"** en el visor: re-descarga los datos
y actualiza la fecha de corte mostrada.

## Arquitectura

- `app.py` — la aplicación (ejecútala con `streamlit run app.py`).
- `data.py` — descarga el Excel desde Google Drive, lo procesa y cruza contra
  los GeoJSON; arma las tablas que usa el visor.
- `static/icons/` — logo UNGRD e íconos de las 13 tarjetas (servidos como
  archivos estáticos vía `server.enableStaticServing`).
- El visor espera encontrar en la carpeta **de arriba** (`..`):
  `Departamentos.geojson` y `Municipios.geojson` (DIVIPOLA).

## Qué muestra

- **13 tarjetas principales**: producción, compañía y silvestres ×
- **Total animales rescatados**: suma transversal de las 3 categorías,
  recalculada en cada corte.
  (desaparecidos / lesionados / muertos / rescatados) + alojamiento temporal.
- **Mapa de afectación** (Folium, basemap CartoDB Voyager): clic en un
  departamento entra a sus municipios; clic en un municipio filtra todo el
  visor. Escala secuencial YlOrRd; municipios sin reporte se pintan gris
  (distinto a cero confirmado).
- **Ranking**: solo afectación real — municipios en cero no se grafican.
- **Composición por categoría**: perfil de desaparecidos / lesionados /
  muertos / rescatados por categoría.
- **Necesidades reportadas**: kg de alimento para perro y gato, medicamentos
  veterinarios y otros requerimientos (columnas Q–V de la matriz).
- **Matriz de datos fuente**: disponible pero colapsada, para auditoría.

## Ejecución local

```bash
python3 -m venv ~/.venvs/ungrd-visor
source ~/.venvs/ungrd-visor/bin/activate
pip install -r streamlit_app/requirements.txt
streamlit run streamlit_app/app.py
```

## Despliegue público (Streamlit Community Cloud)

1. El código ya está en GitHub: `masantizof/visor-animales-emergencias` (público).
2. Entra a [share.streamlit.io](https://share.streamlit.io) con tu cuenta.
3. "Create app" → "Deploy a public app from GitHub".
4. Repository: `masantizof/visor-animales-emergencias`
   - Branch: `main`
   - Main file path: `streamlit_app/app.py`
5. Click **Deploy**. La URL pública queda lista para compartir.

La hoja de Google debe permanecer con acceso "cualquiera con el enlace"
para que la app pueda descargarla.

## Notas sobre los datos (ver también el visor → "Notas metodológicas")

- La fila "TOTAL" de la hoja fuente excluye Chocó (rango de fórmulas corto);
  este visor recalcula todos los totales desde el detalle, incluido Medio
  Baudó (Chocó), zona cercana al epicentro en San José del Palmar.
- Se corrigió el departamento "Cocó" → "Chocó".
- "En alojamiento temporal" no viene desagregado por categoría de animal en
  la hoja fuente, así que se muestra como indicador único.
