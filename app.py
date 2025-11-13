# -*- coding: utf-8 -*-
"""Aplicación Streamlit para el análisis del Índice KCDI + KRATOS."""

from __future__ import annotations

import warnings
from io import BytesIO
from pathlib import Path
from typing import Dict

import gender_guesser.detector as gender
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from country_converter import convert

# ==============================================================================
# Configuración general de la página
# ==============================================================================
st.set_page_config(page_title="KCDI + KRATOS", layout="wide", page_icon="📊")
st.title("Análisis de Justicia Epistémica: Índices KCDI + KRATOS")

st.markdown(
    """
    Esta aplicación permite analizar la **diversidad de contribución al conocimiento** (KCDI)
    y el indicador complementario **KRATOS**, que monitorea balance de representación,
    colaboración e impacto en los datos de Scopus. Sube un archivo `.csv` o `.xlsx`
    que contenga, al menos, las columnas `Authors` y `Country`.
    """
)

# ==============================================================================
# Funciones utilitarias y de procesamiento
# ==============================================================================


def _infer_gender(detector: gender.Detector, author: str) -> str:
    if pd.isna(author) or not isinstance(author, str) or not author.strip():
        return "unknown"
    first_name = author.split()[0].replace("-", "")
    return detector.get_gender(first_name)


@st.cache_data(show_spinner=False)
def load_and_process_data(uploaded_file) -> pd.DataFrame | None:
    """Carga y preprocesa el archivo de Scopus."""

    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file, encoding="utf-8")
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as exc:  # pragma: no cover - mensaje amigable
        st.error(
            "Error al leer el archivo. Asegúrate de que sea un CSV o XLSX válido:"
            f" {exc}"
        )
        return None

    # Normaliza encabezados y valida columnas obligatorias.
    df.columns = [col.strip() for col in df.columns]
    required_cols = {"Authors", "Country"}
    if not required_cols.issubset(df.columns):
        st.error("El archivo debe contener las columnas 'Authors' y 'Country'.")
        return None

    df = df.copy()
    df["Authors"] = df["Authors"].fillna("")
    df["Country"] = df["Country"].fillna("")

    # Solo se toma el primer autor listado por registro.
    df["Authors"] = df["Authors"].astype(str).str.split(";").str[0].str.strip()
    df = df[(df["Authors"] != "") & (df["Country"] != "")]

    detector = gender.Detector(case_sensitive=False)
    df["inferred_gender"] = df["Authors"].apply(lambda x: _infer_gender(detector, x))

    def get_global_south_status(country: str) -> str:
        if pd.isna(country) or not isinstance(country, str):
            return "Unknown"
        country_name = convert(names=country, to="name_short", not_found=None)
        if country_name is None:
            return "Unknown"
        continent = convert(names=country_name, to="continent", not_found=None)
        if continent is None:
            return "Unknown"
        north_global_continents = ["North America", "Europe", "Australia"]
        return "Sur Global" if continent not in north_global_continents else "Norte Global"

    df["global_south_status"] = df["Country"].apply(get_global_south_status)
    df["group"] = df["inferred_gender"] + " - " + df["global_south_status"]

    return df


def load_sample_file() -> BytesIO | None:
    """Devuelve un archivo de ejemplo incluido en el repositorio."""

    sample_path = Path(__file__).with_name("data").joinpath("demo_scopus.csv")
    if not sample_path.exists():
        return None

    sample_bytes = sample_path.read_bytes()
    buffer = BytesIO(sample_bytes)
    buffer.name = str(sample_path)
    return buffer


def build_group_weights(
    base_weight: float,
    female_boost: float,
    male_boost: float,
    south_boost: float,
    north_boost: float,
) -> Dict[str, float]:
    """Genera la tabla de pesos para los grupos interseccionales."""

    gender_modifiers = {
        "female": female_boost,
        "mostly_female": (female_boost + base_weight) / 2,
        "male": male_boost,
        "mostly_male": (male_boost + base_weight) / 2,
        "andy": base_weight,
        "unknown": base_weight,
    }

    region_modifiers = {
        "Sur Global": south_boost,
        "Norte Global": north_boost,
        "Unknown": base_weight,
    }

    weights: Dict[str, float] = {}
    for gender_label, gender_weight in gender_modifiers.items():
        for region_label, region_weight in region_modifiers.items():
            group_key = f"{gender_label} - {region_label}"
            weights[group_key] = round(base_weight * gender_weight * region_weight, 3)
    return weights


@st.cache_data(show_spinner=False)
def calculate_kcdi(
    df: pd.DataFrame, group_weights: Dict[str, float]
) -> tuple[float | None, float | None, float | None, pd.DataFrame | None]:
    """Calcula el KCDI y métricas asociadas."""

    total_contributions = len(df)
    if total_contributions == 0:
        return None, None, None, None

    df_calc = df.copy()
    group_counts = df_calc["group"].value_counts()
    pi = group_counts / total_contributions

    # Índice de Shannon
    H_shannon = -np.sum(pi * np.log(pi.replace(0, 1)))

    df_calc["Wi"] = df_calc["group"].apply(lambda x: group_weights.get(x, 1.0))
    W_bar = df_calc["Wi"].mean()

    kcdi = H_shannon * W_bar
    return kcdi, H_shannon, W_bar, df_calc


def get_dataset_overview(df: pd.DataFrame) -> Dict[str, str | float]:
    overview: Dict[str, str | float] = {
        "registros": float(len(df)),
        "paises": float(df["Country"].nunique()),
        "participacion_sur": float((df["global_south_status"] == "Sur Global").mean()),
    }

    if "Year" in df.columns:
        year_series = pd.to_numeric(df["Year"], errors="coerce").dropna()
        if not year_series.empty:
            overview["rango_temporal"] = f"{int(year_series.min())} - {int(year_series.max())}"
        else:
            overview["rango_temporal"] = "No disponible"
    else:
        overview["rango_temporal"] = "No disponible"

    return overview


def calculate_kratos_metrics(df: pd.DataFrame) -> Dict[str, float]:
    """Calcula el indicador KRATOS (balance, colaboración e impacto)."""

    if df.empty:
        return {}

    gender_series = df["inferred_gender"].astype(str)
    global_south_share = (df["global_south_status"] == "Sur Global").mean()
    female_share = gender_series.str.contains("female", case=False, na=False).mean()

    def balance_score(proportion: float) -> float:
        proportion = float(proportion) if proportion == proportion else 0.0
        return max(0.0, 1 - abs(0.5 - proportion) * 2)

    representation_score = (balance_score(global_south_share) + balance_score(female_share)) / 2

    # Colaboración
    if "Authors" in df.columns:
        author_counts = (
            df["Authors"].astype(str).apply(lambda x: len([a for a in x.split(";") if a.strip()]))
        )
        avg_authors = author_counts.mean()
        collaboration_score = min(avg_authors / 5, 1.0)
    else:
        avg_authors = np.nan
        collaboration_score = 0.5

    # Impacto
    if "Cited by" in df.columns:
        citations = pd.to_numeric(df["Cited by"], errors="coerce").fillna(0)
        if citations.max() > 0:
            normalized = np.log1p(citations) / np.log1p(citations.max())
            impact_score = float(normalized.mean())
        else:
            impact_score = 0.0
        avg_citations = float(citations.mean())
    else:
        impact_score = 0.5
        avg_citations = np.nan

    kratos_index = float(np.mean([representation_score, collaboration_score, impact_score]))

    return {
        "index": kratos_index,
        "representation_score": representation_score,
        "collaboration_score": collaboration_score,
        "impact_score": impact_score,
        "global_south_share": global_south_share,
        "female_share": female_share,
        "avg_authors": avg_authors,
        "avg_citations": avg_citations,
    }


def create_kcdi_compass_plot(kcdi_value: float):
    """Genera una visualización de tipo 'brújula' para el Índice KCDI."""

    warnings.filterwarnings("ignore", category=UserWarning)
    color_less_diverse = "#E34234"
    color_more_diverse = "#007FFF"
    label_font = {"fontweight": "bold", "fontsize": 10}
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"projection": "polar"})
    ax.set_theta_zero_location("W", offset=10)
    ax.set_theta_direction(-1)
    ax.set_yticklabels([])
    ax.set_xticks(np.deg2rad(np.arange(0, 181, 15)))
    ax.set_xticklabels([])
    ax.set_ylim(0, 1)
    ax.bar(
        np.deg2rad(np.arange(0, 91, 1)),
        height=1,
        width=np.deg2rad(1),
        bottom=0.8,
        color=color_less_diverse,
        alpha=0.8,
        label="Menos Diverso",
        zorder=1,
    )
    ax.bar(
        np.deg2rad(np.arange(90, 181, 1)),
        height=1,
        width=np.deg2rad(1),
        bottom=0.8,
        color=color_more_diverse,
        alpha=0.8,
        label="Más Diverso",
        zorder=1,
    )
    ax.text(np.deg2rad(180), 1.05, "0", ha="center", va="center", **label_font)
    ax.text(np.deg2rad(90), 1.05, "0.5", ha="center", va="center", **label_font)
    ax.text(np.deg2rad(0), 1.05, "1", ha="center", va="center", **label_font)
    kcdi_value = max(0.0, min(1.0, kcdi_value))
    theta = np.deg2rad(180 * (1 - kcdi_value))
    ax.plot([theta, theta], [0, 0.9], color="black", linewidth=3, solid_capstyle="round", zorder=2)
    ax.scatter(theta, 0.9, color="black", s=100, zorder=2)
    ax.set_title(f"Índice KCDI: {kcdi_value:.3f}", fontsize=14, pad=20, fontweight="bold")
    ax.text(np.deg2rad(135), 0.5, "Menos diverso", ha="center", va="center", **label_font, color="white")
    ax.text(np.deg2rad(45), 0.5, "Más diverso", ha="center", va="center", **label_font, color="white")
    ax.spines["polar"].set_visible(False)
    ax.grid(False)
    plt.tight_layout()
    return fig


def plot_intersectional_bar(df: pd.DataFrame):
    counts = df["group"].value_counts().reset_index()
    counts.columns = ["Grupo", "Cantidad"]
    fig = px.bar(
        counts,
        x="Grupo",
        y="Cantidad",
        color="Grupo",
        title="Contribuciones Interseccionales (Género x Región)",
    )
    fig.update_layout(showlegend=False)
    return fig


def plot_region_distribution(df: pd.DataFrame):
    region_counts = df["global_south_status"].value_counts().reset_index()
    region_counts.columns = ["Región", "Cantidad"]
    fig = px.pie(
        region_counts,
        names="Región",
        values="Cantidad",
        title="Distribución Regional",
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    return fig


def plot_gender_distribution(df: pd.DataFrame):
    gender_counts = df["inferred_gender"].value_counts().reset_index()
    gender_counts.columns = ["Género inferido", "Cantidad"]
    fig = px.bar(
        gender_counts,
        x="Género inferido",
        y="Cantidad",
        color="Género inferido",
        title="Distribución de género inferido",
    )
    fig.update_layout(showlegend=False)
    return fig


def plot_publication_trend(df: pd.DataFrame):
    if "Year" not in df.columns:
        return None
    year_series = pd.to_numeric(df["Year"], errors="coerce").dropna()
    if year_series.empty:
        return None
    annual_counts = year_series.value_counts().sort_index()
    fig = px.line(
        annual_counts,
        x=annual_counts.index,
        y=annual_counts.values,
        markers=True,
        labels={"x": "Año", "y": "Publicaciones"},
        title="Evolución temporal de publicaciones",
    )
    return fig


# ==============================================================================
# Interfaz de usuario
# ==============================================================================
st.sidebar.header("⚙️ Configuración del Análisis")
st.sidebar.markdown(
    "Ajusta los pesos con los que se calcula el **KCDI** para reflejar tu criterio de"
    " justicia epistémica."
)

if hasattr(st, "query_params"):
    qp_source = st.query_params.items()
    query_params = {
        key: (value if isinstance(value, list) else [value])
        for key, value in qp_source
    }
else:  # Compatibilidad con versiones anteriores
    query_params = st.experimental_get_query_params()
demo_param = (
    bool(query_params.get("demo"))
    and str(query_params.get("demo")[0]).lower() in {"1", "true", "yes"}
)

base_weight = st.sidebar.slider("Peso base", 0.5, 2.0, 1.0, 0.1)
female_boost = st.sidebar.slider("Multiplicador mujeres", 0.5, 2.0, 1.2, 0.1)
male_boost = st.sidebar.slider("Multiplicador hombres", 0.5, 2.0, 0.9, 0.1)
south_boost = st.sidebar.slider("Multiplicador Sur Global", 0.5, 2.0, 1.1, 0.1)
north_boost = st.sidebar.slider("Multiplicador Norte Global", 0.5, 2.0, 0.9, 0.1)

st.sidebar.markdown("---")
use_sample_data = st.sidebar.checkbox(
    "Usar dataset de ejemplo", value=demo_param, help="Carga el archivo demo incluido."
)

uploaded_file = st.file_uploader("Sube tu archivo de Scopus", type=["csv", "xlsx"])

sample_requested = use_sample_data or demo_param
if sample_requested and uploaded_file is None:
    sample_file = load_sample_file()
    if sample_file:
        uploaded_file = sample_file
        st.sidebar.success("Dataset de ejemplo listo para su análisis.")
    else:
        st.sidebar.error("No se encontró el archivo de ejemplo en `data/demo_scopus.csv`.")

if uploaded_file:
    with st.spinner("Procesando archivo y calculando métricas..."):
        df_processed = load_and_process_data(uploaded_file)

    if df_processed is not None:
        st.success("✅ Datos cargados y procesados correctamente.")
        overview = get_dataset_overview(df_processed)

        col_over_1, col_over_2, col_over_3 = st.columns(3)
        col_over_1.metric("Registros analizados", f"{int(overview['registros']):,}".replace(",", "."))
        col_over_2.metric("Países distintos", f"{int(overview['paises'])}")
        col_over_3.metric(
            "Participación Sur Global",
            f"{overview['participacion_sur'] * 100:.1f}%",
        )
        st.caption(f"Rango temporal disponible: {overview['rango_temporal']}")

        group_weights = build_group_weights(
            base_weight=base_weight,
            female_boost=female_boost,
            male_boost=male_boost,
            south_boost=south_boost,
            north_boost=north_boost,
        )

        kcdi, H_shannon, W_bar, df_final = calculate_kcdi(df_processed, group_weights)

        if kcdi is not None and df_final is not None:
            st.markdown("---")
            st.subheader("📊 Resultados del Análisis KCDI")

            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric(label="Índice KCDI", value=f"{kcdi:.4f}")
                st.info("El KCDI se calcula como: $H_{Shannon} \\times \\bar{W}$")
                st.metric(label="Índice de Shannon ($H_{Shannon}$)", value=f"{H_shannon:.4f}")
                st.metric(label="Factor de Ponderación ($\\bar{W}$)", value=f"{W_bar:.4f}")
            with col2:
                st.pyplot(create_kcdi_compass_plot(kcdi))

            with st.expander("Ver tabla de pesos aplicada"):
                weight_table = (
                    pd.DataFrame(
                        [
                            {"Grupo": group, "Peso": weight}
                            for group, weight in group_weights.items()
                        ]
                    )
                    .sort_values("Peso", ascending=False)
                    .reset_index(drop=True)
                )
                st.dataframe(weight_table, width="stretch")

            st.markdown("---")
            st.subheader("🛡️ Indicador KRATOS")
            kratos_metrics = calculate_kratos_metrics(df_final)
            if kratos_metrics:
                st.metric("KRATOS", f"{kratos_metrics['index']:.3f}")
                st.progress(float(max(0, min(1, kratos_metrics["index"]))))
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric(
                        "Representación equilibrada",
                        f"{kratos_metrics['representation_score'] * 100:.1f}%",
                        help="Se basa en la proximidad al 50% de representación por género y región",
                    )
                    st.caption(
                        f"Sur Global: {kratos_metrics['global_south_share'] * 100:.1f}%"
                        f" | Mujeres: {kratos_metrics['female_share'] * 100:.1f}%"
                    )
                with col_b:
                    st.metric(
                        "Colaboración",
                        f"{kratos_metrics['collaboration_score'] * 100:.1f}%",
                    )
                    if not np.isnan(kratos_metrics["avg_authors"]):
                        st.caption(
                            f"Autores promedio por registro: {kratos_metrics['avg_authors']:.1f}"
                        )
                    else:
                        st.caption("Autores promedio: no disponible en el archivo")
                with col_c:
                    st.metric(
                        "Impacto",
                        f"{kratos_metrics['impact_score'] * 100:.1f}%",
                    )
                    if not np.isnan(kratos_metrics["avg_citations"]):
                        st.caption(
                            f"Citas promedio (Scopus): {kratos_metrics['avg_citations']:.1f}"
                        )
                    else:
                        st.caption("Citas promedio: no disponible en el archivo")

                with st.expander("Metodología KRATOS"):
                    st.markdown(
                        """
                        - **Representación**: se calcula observando qué tan cerca están las
                          participaciones del 50% tanto para género como para región.
                        - **Colaboración**: se aproxima por el número promedio de autores por
                          publicación (mayor colaboración = mayor puntaje).
                        - **Impacto**: utiliza las citas reportadas en Scopus (columna `Cited by`).
                        
                        El índice final es el promedio de las tres dimensiones, lo que permite
                        identificar cuellos de botella para fortalecer la justicia epistémica.
                        """
                    )
            else:
                st.warning("No fue posible calcular KRATOS con los datos disponibles.")

            st.markdown("---")
            st.subheader("🔍 Análisis Interseccional y Visualizaciones")
            tab1, tab2, tab3, tab4 = st.tabs(
                ["Interseccional", "Regiones", "Género", "Tiempo"]
            )
            with tab1:
                st.plotly_chart(plot_intersectional_bar(df_final), width="stretch")
            with tab2:
                st.plotly_chart(plot_region_distribution(df_final), width="stretch")
            with tab3:
                st.plotly_chart(plot_gender_distribution(df_final), width="stretch")
            with tab4:
                timeline_fig = plot_publication_trend(df_final)
                if timeline_fig is not None:
                    st.plotly_chart(timeline_fig, width="stretch")
                else:
                    st.info(
                        "No se encontró una columna 'Year' con valores válidos para graficar la"
                        " evolución temporal."
                    )

            st.markdown("---")
            st.subheader("📦 Exportación de Resultados")
            csv_data = df_final.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Descargar datos procesados (CSV)",
                data=csv_data,
                file_name="scopus_data_processed.csv",
                mime="text/csv",
            )

            with st.expander("Vista previa de los datos procesados"):
                st.dataframe(df_final.head(200), width="stretch")
else:
    st.info("Carga un archivo para iniciar el análisis KCDI + KRATOS.")
