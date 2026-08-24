"""Visor de animales afectados — Sismo del 10 de agosto, Pacífico colombiano (UNGRD).

Fuente de datos en línea (Google Sheets) + GeoJSON DIVIPOLA.
Ejecutar con:  streamlit run app.py
"""
from __future__ import annotations

import html as _html
import json
from datetime import datetime
from pathlib import Path

import branca.colormap as cm
import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

import data as D

APP_DIR = Path(__file__).resolve().parent
BASE_DIR = APP_DIR.parent
ASSETS = APP_DIR / "static"

# ---------------------------------------------------------------------------
# Paleta — categorías con buen contraste entre sí y sobre blanco;
# escala secuencial YlOrRd para intensidad sobre el mapa.
# ---------------------------------------------------------------------------
CAT_COLORS = {
    "prod": "#2E7D32",  # producción — verde
    "comp": "#6A1B9A",  # compañía — púrpura
    "aloj": "#E65100",  # alojamiento temporal — naranja profundo
    "silv": "#1565C0",  # silvestres — azul
}
STATUS_COLORS = {
    "Desaparecidos": "#F57F17",
    "Lesionados": "#E64A19",
    "Muertos": "#B71C1C",
    "Rescatados": "#2E7D32",
}
NODATA_COLOR = "#D8D8D8"
SEQ_COLORSCALE = [
    [0.00, "#fff7bc"],
    [0.25, "#fec44f"],
    [0.50, "#fe9929"],
    [0.75, "#e34a33"],
    [1.00, "#b30000"],
]

st.set_page_config(
    page_title="Animales en Emergencia — UNGRD",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}
.block-container {padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1360px;}
h1, h2, h3 { letter-spacing: -0.01em; }

.hero {
  background: linear-gradient(155deg, #16264a, #1f3460 130%);
  border-radius: 16px; padding: 22px 26px; color: #fff; margin-bottom: .9rem;
  display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
}
.hero img { height: 40px; background: #fff; border-radius: 8px; padding: 6px 10px; }
.hero .eyebrow { font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: rgba(255,255,255,.7); }
.hero h1 { font-size: 24px; font-weight: 800; color: #fff; margin: 2px 0 4px; }
.hero p { font-size: 13px; color: rgba(255,255,255,.85); margin: 0; max-width: 62ch; }
.hero .chips { margin-left: auto; display: flex; flex-direction: column; gap: 6px; align-items: flex-end; }
.hero .chip { background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.24); padding: 4px 11px;
              border-radius: 999px; font-size: 11.5px; font-weight: 600; white-space: nowrap; }

.cat-label { display: flex; align-items: center; gap: 8px; font-size: 11.5px; font-weight: 800;
             letter-spacing: .06em; text-transform: uppercase; color: #4b5468; margin: .55rem 0 .3rem; }
.cat-dot { width: 10px; height: 10px; border-radius: 3px; background: var(--cc, #1f3460); }

.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
@media (max-width: 1080px) { .kpi-row { grid-template-columns: repeat(2, 1fr); } }
.kpi { background: #fff; border: 1px solid rgba(16,24,44,.09); border-radius: 13px; padding: 13px 14px 11px;
       box-shadow: 0 1px 2px rgba(16,24,44,.05), 0 6px 18px -12px rgba(16,24,44,.18); position: relative; overflow: hidden; }
.kpi::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 4px; background: var(--kc, #1f3460); }
.kpi-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 6px; }
.kpi-value { font-size: 34px; font-weight: 800; line-height: 1; color: #10182c; font-variant-numeric: tabular-nums; }
.kpi-label { font-size: 13.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .02em; color: #4b5468; margin-top: 5px; }
.kpi img { width: 36px; height: 36px; object-fit: contain; }
.kpi-sub { font-size: 12px; color: #838a9c; margin-top: 6px; padding-top: 6px; border-top: 1px dashed rgba(16,24,44,.10); }
.kpi-wide { grid-column: 1 / -1; display: flex; align-items: center; gap: 14px; padding: 14px 18px; }
.kpi-wide .kpi-value { font-size: 40px; }

.section-title { font-size: 16px; font-weight: 800; color: #10182c; margin: 1.6rem 0 .5rem; }
.section-hint { font-size: 12px; color: #838a9c; font-weight: 500; }

.need-card { border: 1px solid rgba(16,24,44,.09); border-left: 4px solid #E65100; border-radius: 12px;
             padding: 10px 14px; background: #fff; }
.need-card .nhead { font-weight: 700; font-size: 13px; color: #10182c; }
.need-card .ndept { font-size: 11px; color: #838a9c; font-weight: 600; }
.need-card .ntxt { font-size: 12.5px; color: #333c50; margin-top: 5px; line-height: 1.45; }
.need-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 10px; }

.stButton>button { border-radius: 8px; }
iframe { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)


def icon_uri(name: str) -> str:
    return f"app/static/icons/{name}.png"


def fmt(n) -> str:
    """Formato miles estilo colombiano: 12345 -> '12.345'."""
    return f"{int(n):,}".replace(",", ".")


# ---------------------------------------------------------------------------
# Datos (descarga en línea; el botón "Actualizar datos" fuerza re-descarga)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Descargando y procesando la matriz de afectación…")
def _load(_refresh: int):
    return D.load_all(BASE_DIR)


refresh_n = st.session_state.setdefault("refresh_n", 0)
try:
    DATA = _load(refresh_n)
except RuntimeError as e:
    st.error(str(e))
    st.stop()

REG: pd.DataFrame = DATA["registros"]
NEC: pd.DataFrame = DATA["necesidades"]
GEO: dict = DATA["geo"]
FUENTES: list = DATA["fuentes"]
FETCHED_AT: datetime = DATA["fetched_at"]
CORTE_TXT = FETCHED_AT.strftime("%d %b %Y · %H:%M")

if REG.empty:
    st.warning("La matriz en línea todavía no tiene filas de datos.")
    st.stop()

# ---------------------------------------------------------------------------
# Estado de filtro
# ---------------------------------------------------------------------------
st.session_state.setdefault("sel_dept", None)
st.session_state.setdefault("sel_muni", None)
st.session_state.setdefault("_click_sig", {})


def _sig_once(key: str, payload) -> bool:
    """True si este clic es nuevo (no reprocesado en reruns previos)."""
    sig = json.dumps(payload, sort_keys=True, default=str)
    if st.session_state["_click_sig"].get(key) == sig:
        return False
    st.session_state["_click_sig"][key] = sig
    return True


def set_dept(dept):
    if dept != st.session_state.sel_dept:
        st.session_state.sel_dept = dept
        st.session_state.sel_muni = None
        st.rerun()


def set_muni(muni_norm):
    if muni_norm != st.session_state.sel_muni:
        st.session_state.sel_muni = muni_norm
        st.rerun()


# --- Point-in-polygon para traducir clics del mapa Folium a zona seleccionada ---
def _pip_ring(ring, lng, lat) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def feature_contains(feature, lng, lat) -> bool:
    geom = feature.get("geometry") or {}
    if geom.get("type") == "Polygon":
        polys = [geom["coordinates"]]
    elif geom.get("type") == "MultiPolygon":
        polys = geom["coordinates"]
    else:
        return False
    for poly in polys:
        if _pip_ring(poly[0], lng, lat) and not any(_pip_ring(h, lng, lat) for h in poly[1:]):
            return True
    return False


def features_bounds(feats) -> list[list[float]]:
    lats, lngs = [], []

    def walk(coords):
        if isinstance(coords[0], (int, float)):
            lats.append(coords[1]); lngs.append(coords[0])
        else:
            for c in coords:
                walk(c)

    for f in feats:
        walk(f["geometry"]["coordinates"])
    return [[min(lats), min(lngs)], [max(lats), max(lngs)]]


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image(str(ASSETS / "icons" / "LOGO_UNGRD.png"))
    st.markdown("#### Animales en Emergencia")
    st.caption("Sismo del 10 de agosto de 2026 · Pacífico colombiano")

    if st.button("🔄 Actualizar datos", width="stretch"):
        st.cache_data.clear()
        st.session_state.refresh_n += 1
        st.rerun()
    st.caption(f"Última actualización: {CORTE_TXT}")

    st.divider()
    st.markdown("**Filtrar por zona**")

    dept_order = REG.groupby("dept")["severidad"].sum().sort_values(ascending=False).index.tolist()
    dept_display = ["Todos los departamentos"] + [D.DEPT_SHORT.get(d, d) for d in dept_order]
    rev_dept = {D.DEPT_SHORT.get(d, d): d for d in dept_order}

    cur_label = "Todos los departamentos" if not st.session_state.sel_dept else D.DEPT_SHORT.get(st.session_state.sel_dept, st.session_state.sel_dept)
    idx = dept_display.index(cur_label) if cur_label in dept_display else 0
    choice = st.radio("Departamento", dept_display, index=idx, label_visibility="collapsed", key="dept_radio_widget")
    chosen_dept = rev_dept.get(choice)
    if chosen_dept != st.session_state.sel_dept:
        st.session_state.sel_dept = chosen_dept
        st.session_state.sel_muni = None
        st.rerun()

    if st.session_state.sel_dept:
        munis_dept = REG[REG["dept"] == st.session_state.sel_dept].sort_values("severidad", ascending=False)
        muni_display = ["Todos los municipios"] + munis_dept["muni"].tolist()
        cur_m = "Todos los municipios"
        if st.session_state.sel_muni:
            match = munis_dept[munis_dept["muni_norm"] == st.session_state.sel_muni]
            if not match.empty:
                cur_m = match["muni"].iloc[0]
        idxm = muni_display.index(cur_m) if cur_m in muni_display else 0
        choice_m = st.selectbox("Municipio", muni_display, index=idxm, key="muni_select_widget")
        chosen_muni_norm = None if choice_m == "Todos los municipios" else munis_dept.loc[munis_dept["muni"] == choice_m, "muni_norm"].iloc[0]
        if chosen_muni_norm != st.session_state.sel_muni:
            st.session_state.sel_muni = chosen_muni_norm
            st.rerun()

    if st.session_state.sel_dept:
        if st.button("✕ Quitar filtro", width="stretch"):
            st.session_state.sel_dept = None
            st.session_state.sel_muni = None
            st.rerun()

    st.divider()
    with st.expander("📎 Fuentes de información"):
        for f in FUENTES:
            n = int(REG["fuentes"].apply(lambda fl: f in fl).sum())
            st.caption(f"• {f} ({n} municipio{'s' if n != 1 else ''})")

    with st.expander("ℹ️ Notas metodológicas"):
        st.caption(
            "- Los datos provienen de la matriz de seguimiento publicada en línea; el botón "
            "\"Actualizar datos\" re-descarga la última versión y actualiza la fecha de corte.\n\n"
            "- El total oficial de la hoja fuente solo sumaba Quindío, Risaralda y Valle del Cauca. "
            "Este visor incorpora además Chocó (Medio Baudó), cerca del epicentro en San José del Palmar.\n\n"
            "- \"En alojamiento temporal\" no está desagregado por categoría de animal en la fuente, "
            "por eso es un indicador aparte.\n\n"
            "- Se corrigió el nombre de departamento \"Cocó\" a \"Chocó\".\n\n"
            "- En Chocó solo Medio Baudó tiene reporte en esta matriz; los demás municipios se muestran "
            "como \"sin información\", no como cero confirmado."
        )

# ---------------------------------------------------------------------------
# Datos filtrados (alcance actual)
# ---------------------------------------------------------------------------
SCOPE = REG
if st.session_state.sel_dept:
    SCOPE = SCOPE[SCOPE["dept"] == st.session_state.sel_dept]
if st.session_state.sel_muni:
    SCOPE = SCOPE[SCOPE["muni_norm"] == st.session_state.sel_muni]

NEC_SCOPE = NEC
if not NEC.empty:
    if st.session_state.sel_dept:
        NEC_SCOPE = NEC_SCOPE[NEC_SCOPE["dept"] == st.session_state.sel_dept]
    if st.session_state.sel_muni:
        NEC_SCOPE = NEC_SCOPE[NEC_SCOPE["muni_norm"] == st.session_state.sel_muni]

# ---------------------------------------------------------------------------
# Encabezado
# ---------------------------------------------------------------------------
scope_text = f"{DATA['n_depts']} departamentos · {DATA['n_munis']} municipios reportantes"
st.markdown(f"""
<div class="hero">
  <img src="{icon_uri('LOGO_UNGRD')}" />
  <div>
    <div class="eyebrow">Visor de control · Atención a animales en emergencia</div>
    <h1>Animales afectados — Sismo del 10 de agosto, Pacífico colombiano</h1>
    <p>Chocó, Valle del Cauca, Risaralda y Quindío — animales de producción, compañía y silvestres.</p>
  </div>
  <div class="chips">
    <span class="chip">Corte: {CORTE_TXT}</span>
    <span class="chip">Alcance: {scope_text}</span>
  </div>
</div>
""", unsafe_allow_html=True)

if st.session_state.sel_dept or st.session_state.sel_muni:
    crumbs = "Colombia · zona afectada"
    if st.session_state.sel_dept:
        crumbs += f"  →  {D.DEPT_SHORT.get(st.session_state.sel_dept, st.session_state.sel_dept)}"
    if st.session_state.sel_muni:
        m = REG[REG['muni_norm'] == st.session_state.sel_muni]['muni']
        if not m.empty:
            crumbs += f"  →  {m.iloc[0]}"
    st.caption(f"📍 {crumbs}")

# ---------------------------------------------------------------------------
# 13 tarjetas principales (categoría × estado + alojamiento temporal)
# ---------------------------------------------------------------------------

# Total de animales rescatados (suma transversal de las 3 categorías) — primera fila
res_total = int(sum(SCOPE[f"{k}Res"].sum() for k in D.CATEGORIES))
res_prod = int(SCOPE["prodRes"].sum())
res_comp = int(SCOPE["compRes"].sum())
res_silv = int(SCOPE["silvRes"].sum())
st.markdown(f"""
<div class="kpi-row">
  <div class="kpi kpi-wide" style="--kc:{STATUS_COLORS['Rescatados']}">
    <div>
      <div class="kpi-value">{fmt(res_total)}</div>
      <div class="kpi-label">Total animales rescatados</div>
    </div>
    <div class="kpi-sub" style="margin:0;border:none;padding:0;">Producción {fmt(res_prod)} · Compañía {fmt(res_comp)} · Silvestres {fmt(res_silv)} — actualizado en cada corte</div>
  </div>
</div>
""", unsafe_allow_html=True)

def kpi_card(col: str, label: str, icon: str, accent: str) -> str:
    val = fmt(SCOPE[col].sum())
    n_munis = int((SCOPE[col] > 0).sum())
    sub = f"Reportado en {n_munis} municipio{'s' if n_munis != 1 else ''}"
    return f"""
    <div class="kpi" style="--kc:{accent}">
      <div class="kpi-top">
        <div>
          <div class="kpi-value">{val}</div>
          <div class="kpi-label">{label}</div>
        </div>
        <img src="{icon_uri(icon)}" />
      </div>
      <div class="kpi-sub">{sub}</div>
    </div>"""


CARD_GROUPS = [
    ("Animales de producción", "prod", [
        ("prodDes", "Desaparecidos"), ("prodLes", "Lesionados"),
        ("prodMue", "Muertos"), ("prodRes", "Rescatados"),
    ]),
    ("Animales de compañía", "comp", [
        ("compDes", "Desaparecidos"), ("compLes", "Lesionados"),
        ("compMue", "Muertos"), ("compRes", "Rescatados"),
    ]),
    ("Animales silvestres", "silv", [
        ("silvDes", "Desaparecidos"), ("silvLes", "Lesionados"),
        ("silvMue", "Muertos"), ("silvRes", "Rescatados"),
    ]),
]

for gtitle, cat_key, cards in CARD_GROUPS:
    color = CAT_COLORS[cat_key]
    st.markdown(f'<div class="cat-label"><span class="cat-dot" style="--cc:{color}"></span>{gtitle}</div>',
                unsafe_allow_html=True)
    row_html = '<div class="kpi-row">'
    for col, label in cards:
        # nombres exactos de archivo en static/icons/ (sin tildes, con "_")
        icon = {
            "prod": {"Desaparecidos": "ANIMALES_DE_PRODUCCION_DESAPARECIDOS",
                     "Lesionados": "ANIMALES_DE_PRODUCCION_LESIONADOS",
                     "Muertos": "ANIMALES_DE_PRODUCCION_MUERTOS",
                     "Rescatados": "ANIMALES_DE_PRODUCCION_RESCATADOS"},
            "comp": {"Desaparecidos": "ANIMALES_DE_COMPANIA_DESAPARECIDOS",
                     "Lesionados": "ANIMALES_DE_COMPANIA_LESIONADOS",
                     "Muertos": "ANIMALES_DE_COMPANIA_MUERTOS",
                     "Rescatados": "ANIMALES_DE_COMPANIA_RESCATADOS"},
            "silv": {"Desaparecidos": "ANIMALES_SILVESTRES_DESAPARECIDOS",
                     "Lesionados": "ANIMALES_SILVESTRES_LESIONADOS",
                     "Muertos": "ANIMALES_SILVESTRES_MUERTOS",
                     "Rescatados": "ANIMALES_SILVESTRES_RESCATADOS"},
        }[cat_key][label]
        row_html += kpi_card(col, label, icon, color)
    row_html += "</div>"
    st.markdown(row_html, unsafe_allow_html=True)

aloj_val = int(SCOPE["aloj"].sum())
n_muni_aloj = int((SCOPE["aloj"] > 0).sum())
st.markdown(f"""
<div class="kpi-row">
  <div class="kpi kpi-wide" style="--kc:{CAT_COLORS['aloj']}">
    <img src="{icon_uri('EN_ALOJAMIENTOS_TEMPORALES')}" />
    <div>
      <div class="kpi-value">{fmt(aloj_val)}</div>
      <div class="kpi-label">En alojamiento temporal</div>
    </div>
    <div class="kpi-sub" style="margin:0;border:none;padding:0;">Indicador transversal — reportado en {n_muni_aloj} municipio{'s' if n_muni_aloj != 1 else ''} · la fuente no lo desagrega por categoría</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Mapa de afectación (Folium) + ranking
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">Mapa de afectación</div>', unsafe_allow_html=True)

map_col, rank_col = st.columns([1.4, 1])


def folium_choropleth(feats, value_by_key, key_prop, cmap, tooltip_fields, tooltip_aliases):
    """GeoJson con relleno según valor; sin dato -> gris neutro."""
    def style_fn(feature):
        v = value_by_key.get(feature["properties"][key_prop])
        fill = cmap(v) if v is not None and v > 0 else NODATA_COLOR  # branca devuelve hex
        return {"fillColor": fill, "color": "#ffffff", "weight": 1.4, "fillOpacity": 0.88}

    gj = folium.GeoJson(
        {"type": "FeatureCollection", "features": feats},
        style_function=style_fn,
        highlight_function=lambda _: {"weight": 3, "color": "#16264a", "fillOpacity": 0.95},
        tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases,
                                      localize=True, sticky=False, labels=True),
    )
    return gj


with map_col:
    if not st.session_state.sel_dept:
        st.caption("Colombia · departamentos con reporte — clic en un departamento para ver sus municipios")
        dept_sev = REG.groupby("dept_code")["severidad"].sum().to_dict()
        dept_name_by_code = {code: name for name, code in GEO["dep_name_to_code"].items()}
        feats = []
        for f in GEO["dep_geojson"]["features"]:
            code = f["properties"]["DPTO_CCDGO"]
            raw = next((d for d in dept_order if GEO["dep_name_to_code"].get(D.normalize(d)) == code), None)
            sev = int(dept_sev.get(code, 0))
            props = dict(f["properties"])
            props["sev"] = sev
            feats.append({**f, "properties": props})

        vmax = max(int(max(dept_sev.values())) if dept_sev else 1, 1)
        cmap = cm.linear.YlOrRd_09.scale(0, vmax)
        cmap.caption = "Animales afectados"

        m = folium.Map(tiles="CartoDB Voyager", control_scale=True)
        folium_choropleth(
            feats, dept_sev, "DPTO_CCDGO", cmap,
            ["DPTO_CNMBR", "sev"],
            ["Departamento:", "Animales afectados:"],
        ).add_to(m)
        folium.TileLayer("OpenStreetMap", control=False).add_to(m)
        folium.LayerControl(position="bottomright").add_to(m)
        cmap.add_to(m)
        m.fit_bounds(features_bounds(GEO["dep_geojson"]["features"]), padding=(12, 12))

        ev = st_folium(m, height=520, width="stretch", returned_objects=["last_clicked"], key="folium_depto")
        click = (ev or {}).get("last_clicked")
        if click and _sig_once("fl_dept", click):
            lat, lng = click["lat"], click["lng"]
            for f in GEO["dep_geojson"]["features"]:
                if feature_contains(f, lng, lat):
                    norm = D.normalize(f["properties"]["DPTO_CNMBR"])
                    match = REG[REG["dept_norm"] == norm]["dept"]
                    if not match.empty:
                        set_dept(match.iloc[0])
                    break

    else:
        dept_code = REG.loc[REG["dept"] == st.session_state.sel_dept, "dept_code"].iloc[0]
        dept_label = D.DEPT_SHORT.get(st.session_state.sel_dept, st.session_state.sel_dept)
        st.caption(f"Municipios de {dept_label} — clic en un municipio para filtrar el visor")

        feats = list(GEO["mun_features_by_dept"].get(dept_code, []))
        reg_dept = REG[REG["dept"] == st.session_state.sel_dept]
        sev_by_code = reg_dept.set_index("muni_code")["severidad"].to_dict()
        info_by_code = reg_dept.set_index("muni_code")[["aloj", "total_Des", "total_Les", "total_Mue", "total_Res"]].to_dict("index")

        enriched = []
        for f in feats:
            code = f["properties"]["MPIO_CCNCT"]
            inf = info_by_code.get(code, {})
            props = dict(f["properties"])
            props.update({
                "sev": int(sev_by_code.get(code, 0)),
                "aloj": int(inf.get("aloj", 0)),
                "des": int(inf.get("total_Des", 0)),
                "les": int(inf.get("total_Les", 0)),
                "mue": int(inf.get("total_Mue", 0)),
                "res": int(inf.get("total_Res", 0)),
            })
            enriched.append({**f, "properties": props})

        vmax = max(int(reg_dept["severidad"].max()) if not reg_dept.empty else 0, 1)
        cmap = cm.linear.YlOrRd_09.scale(0, vmax)
        cmap.caption = "Animales afectados"

        m = folium.Map(tiles="CartoDB Voyager", control_scale=True)
        folium_choropleth(
            enriched, sev_by_code, "MPIO_CCNCT", cmap,
            ["MPIO_CNMBR", "sev", "des", "les", "mue", "res", "aloj"],
            ["Municipio:", "Afectados:", "Desaparecidos:", "Lesionados:", "Muertos:", "Rescatados:", "En albergue:"],
        ).add_to(m)
        folium.TileLayer("OpenStreetMap", control=False).add_to(m)
        folium.LayerControl(position="bottomright").add_to(m)
        cmap.add_to(m)
        m.fit_bounds(features_bounds(feats), padding=(12, 12))

        ev = st_folium(m, height=520, width="stretch", returned_objects=["last_clicked"], key=f"folium_muni_{dept_code}")
        click = (ev or {}).get("last_clicked")
        if click and _sig_once(f"fl_muni_{dept_code}", click):
            lat, lng = click["lat"], click["lng"]
            for f in feats:
                if feature_contains(f, lng, lat):
                    norm = D.normalize(f["properties"]["MPIO_CNMBR"])
                    match = reg_dept[reg_dept["muni_norm"] == norm]["muni_norm"]
                    if not match.empty:
                        set_muni(match.iloc[0])
                    break

        if st.button("← Ver todos los departamentos"):
            st.session_state.sel_dept = None
            st.session_state.sel_muni = None
            st.rerun()

with rank_col:
    if not st.session_state.sel_dept:
        st.caption("Ranking por departamento — total de animales afectados")
        d = REG.groupby("dept", as_index=False)["severidad"].sum()
        d = d[d["severidad"] > 0].sort_values("severidad")
        d["label"] = d["dept"].map(lambda x: D.DEPT_SHORT.get(x, x))
        if d.empty:
            st.info("Sin afectación registrada todavía.")
        else:
            fig = go.Figure(go.Bar(
                x=d["severidad"], y=d["label"], orientation="h",
                marker=dict(color=d["severidad"], colorscale=SEQ_COLORSCALE, cmin=0, cmax=max(d["severidad"].max(), 1)),
                text=d["severidad"].map(fmt), textposition="outside",
                customdata=d[["dept"]],
                hovertemplate="<b>%{y}</b><br>Animales afectados: %{x:,}<extra></extra>",
            ))
            fig.update_layout(height=max(220, 60 * len(d)), margin=dict(l=0, r=36, t=6, b=0),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
            st.plotly_chart(fig, config={"displayModeBar": False}, key="rank_dept")
    else:
        dept_label = D.DEPT_SHORT.get(st.session_state.sel_dept, st.session_state.sel_dept)
        st.caption(f"Ranking en {dept_label} — solo municipios con afectación reportada")
        d = REG[(REG["dept"] == st.session_state.sel_dept) & (REG["severidad"] > 0)].sort_values("severidad")
        if d.empty:
            st.info("Ningún municipio de este departamento registra afectación mayor a cero.")
        else:
            fig = go.Figure(go.Bar(
                x=d["severidad"], y=d["muni"], orientation="h",
                marker=dict(color=d["severidad"], colorscale=SEQ_COLORSCALE, cmin=0, cmax=max(d["severidad"].max(), 1)),
                text=d["severidad"].map(fmt), textposition="outside",
                hovertemplate="<b>%{y}</b><br>Animales afectados: %{x:,}<extra></extra>",
            ))
            fig.update_layout(height=max(220, 34 * len(d)), margin=dict(l=0, r=36, t=6, b=0),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
            st.plotly_chart(fig, config={"displayModeBar": False}, key=f"rank_muni_{st.session_state.sel_dept}")
        n_zero = int((REG["dept"] == st.session_state.sel_dept).sum()) - len(d)
        if n_zero > 0:
            st.caption(f"+ {n_zero} municipios de {dept_label} sin afectación registrada (no se grafican).")

# ---------------------------------------------------------------------------
# Composición por categoría
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">Composición por categoría de animal <span class="section-hint">· perfil de cada categoría según el estado reportado</span></div>', unsafe_allow_html=True)

cat_sev = {label: int(sum(SCOPE[f"{key}{s}"].sum() for s in D.STATUS_KEYS)) for key, label in D.CATEGORIES.items()}
if sum(cat_sev.values()) == 0:
    st.info("Sin reportes de Desaparecidos/Lesionados/Muertos/Rescatados en esta selección.")
else:
    cats_present = [c for c in D.CATEGORIES.values() if cat_sev[c] > 0]
    fig = go.Figure()
    for s in D.STATUS_KEYS:
        label = D.STATUS_LABELS[s]
        xs, cds = [], []
        for key, clabel in D.CATEGORIES.items():
            if clabel not in cats_present:
                continue
            val = int(SCOPE[f"{key}{s}"].sum())
            pct = (val / cat_sev[clabel] * 100) if cat_sev[clabel] else 0
            xs.append(pct)
            cds.append(val)
        fig.add_trace(go.Bar(
            name=label, y=cats_present, x=xs, orientation="h", marker_color=STATUS_COLORS[label],
            customdata=cds, hovertemplate="<b>%{y}</b><br>" + label + ": %{customdata:,} (%{x:.0f}%)<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack", height=120 + 60 * len(cats_present), margin=dict(l=0, r=0, t=6, b=0),
        xaxis=dict(ticksuffix="%", range=[0, 100], showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, config={"displayModeBar": False}, key="composicion")

# ---------------------------------------------------------------------------
# Necesidades reportadas (Q-V de la fuente)
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">Necesidades reportadas <span class="section-hint">· insumos y apoyo solicitado por los territorios</span></div>', unsafe_allow_html=True)

if NEC_SCOPE.empty:
    st.info("No hay necesidades reportadas para esta selección.")
else:
    def _sum(col) -> float:
        s = pd.to_numeric(NEC_SCOPE[col], errors="coerce").dropna() if col in NEC_SCOPE else []
        return float(s.sum())

    kg_perro = _sum("kg_perro")
    kg_gato = _sum("kg_gato")
    med_unid = _sum("med_unid")
    n_munis_nec = int(NEC_SCOPE.drop_duplicates(["dept", "muni_norm"]).shape[0])
    sin_req_n = int(NEC_SCOPE["sin_requerimiento"].fillna(False).sum()) if "sin_requerimiento" in NEC_SCOPE else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Alimento para perro", f"{kg_perro:,.0f} kg".replace(",", "."))
    m2.metric("Alimento para gato", f"{kg_gato:,.0f} kg".replace(",", "."))
    m3.metric("Medicamentos veterinarios", fmt(med_unid))
    m4.metric("Municipios que reportan", n_munis_nec)

    bar_df = NEC_SCOPE.copy()
    for c in ("kg_perro", "kg_gato"):
        bar_df[c] = pd.to_numeric(bar_df[c], errors="coerce").fillna(0)
    bar_df = bar_df.groupby(["dept", "muni"], as_index=False)[["kg_perro", "kg_gato"]].sum()
    bar_df = bar_df[(bar_df["kg_perro"] > 0) | (bar_df["kg_gato"] > 0)].sort_values("kg_perro")
    if not bar_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Alimento perro (kg)", y=bar_df["muni"], x=bar_df["kg_perro"], orientation="h",
            marker_color="#6A1B9A",
            hovertemplate="<b>%{y}</b><br>Perro: %{x:,.0f} kg<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            name="Alimento gato (kg)", y=bar_df["muni"], x=bar_df["kg_gato"], orientation="h",
            marker_color="#F57F17",
            hovertemplate="<b>%{y}</b><br>Gato: %{x:,.0f} kg<extra></extra>",
        ))
        fig.update_layout(barmode="group", height=max(220, 36 * len(bar_df)),
                          margin=dict(l=0, r=30, t=6, b=0),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          xaxis=dict(showgrid=False),
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
        st.plotly_chart(fig, config={"displayModeBar": False}, key="necesidades_bar")

    otros_rows = NEC_SCOPE[NEC_SCOPE["otros_text"].notna()] if "otros_text" in NEC_SCOPE else NEC_SCOPE.head(0)
    otros_rows = otros_rows[(otros_rows["otros_text"].fillna("") != "") | (pd.to_numeric(otros_rows["otros_unid"], errors="coerce").fillna(0) > 0)] if not otros_rows.empty else otros_rows
    if sin_req_n:
        st.caption(f"✔ {sin_req_n} municipio{'s' if sin_req_n != 1 else ''} confirmaron que NO requieren apoyo.")
    if otros_rows.empty:
        st.caption("Sin otros requerimientos adicionales registrados en esta selección.")
    else:
        st.markdown("**Otros requerimientos**")
        cards = '<div class="need-grid">'
        for _, rrow in otros_rows.iterrows():
            qty = ""
            try:
                q = float(rrow.get("otros_unid"))
                qty = f" — <b>{q:,.0f}</b>".replace(",", ".")
            except (TypeError, ValueError):
                pass
            txt = _html.escape(str(rrow["otros_text"]))
            cards += f"""<div class="need-card">
              <div class="nhead">{_html.escape(str(rrow['muni']))}</div>
              <div class="ndept">{_html.escape(D.DEPT_SHORT.get(rrow['dept'], str(rrow['dept'])))}</div>
              <div class="ntxt">{txt}{qty}</div>
            </div>"""
        cards += "</div>"
        st.markdown(cards, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Datos fuente (opcional, colapsado)
# ---------------------------------------------------------------------------
with st.expander("🔎 Ver matriz de datos fuente (detalle completo)"):
    solo_afectados = st.checkbox("Mostrar solo municipios con afectación reportada", value=True)
    d = SCOPE.copy()
    if solo_afectados:
        d = d[(d["severidad"] > 0) | (d["aloj"] > 0)]
    d = d.sort_values("severidad", ascending=False)
    d["Fuente"] = d["fuentes"].apply(lambda fl: "; ".join(fl) if fl else "—")
    show_cols = {
        "dept": "Departamento", "muni": "Municipio",
        "prodDes": "Prod. Des.", "prodLes": "Prod. Les.", "prodMue": "Prod. Muer.", "prodRes": "Prod. Resc.",
        "compDes": "Comp. Des.", "compLes": "Comp. Les.", "compMue": "Comp. Muer.", "compRes": "Comp. Resc.",
        "silvDes": "Silv. Des.", "silvLes": "Silv. Les.", "silvMue": "Silv. Muer.", "silvRes": "Silv. Resc.",
        "aloj": "Albergue", "severidad": "Total", "Fuente": "Fuente",
    }
    st.dataframe(d[list(show_cols)].rename(columns=show_cols), width="stretch", hide_index=True)

st.divider()
st.caption(
    f"Visor construido a partir de la matriz de seguimiento \"Afectaciones animales\" publicada en línea "
    f"(corte {CORTE_TXT}) para apoyo a la toma de decisiones — Unidad Nacional para la Gestión del Riesgo de Desastres."
)
