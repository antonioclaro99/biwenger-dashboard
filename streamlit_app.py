import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="📊 Jugadores Biwenger", layout="wide")

st.title("📊 Jugadores Biwenger")

# URL de Dropbox
dropbox_url = "https://www.dropbox.com/scl/fi/33v549k09ypevy7re3fbj/jugadores_biwenger.csv?rlkey=hafbwd6i04yloigclnnv1oe0f&st=3aq68ntm&dl=1"

@st.cache_data
def load_data(url):
    df = pd.read_csv(url)
    df["Valor Actual"] = df["Valor Actual"].replace({r"[^\d]": ""}, regex=True).astype(float)
    df["Fecha de Desbloqueo"] = pd.to_datetime(df["Fecha de Desbloqueo"], errors="coerce")
    df["Horas"] = df["Horas"].astype(float)
    df["Minutos"] = df["Minutos"].astype(float)
    df["Tiempo restante (h)"] = df["Horas"] + df["Minutos"] / 60
    return df

df = load_data(dropbox_url)

# Pestañas
tab1, tab2 = st.tabs(["⏳ Cláusulas", "📊 Estadísticas"])

# --- TAB 1: Clausulas ---
with tab1:
    st.subheader("Filtros de cláusulas")

    col1, col2, col3 = st.columns(3)
    propietarios = ["Todos"] + sorted(df["Propietario"].unique())
    propietario_sel = col1.selectbox("Filtrar por propietario", propietarios)
    tiempo_max = col2.slider("Tiempo máximo restante (horas)", 0, 48, 48)
    posiciones = ["Todas"] + sorted(df["Posición"].unique())
    posicion_sel = col3.selectbox("Filtrar por posición", posiciones)

    df_filtrado = df[df["Tiempo restante (h)"] <= tiempo_max]
    if propietario_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Propietario"] == propietario_sel]
    if posicion_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Posición"] == posicion_sel]

    # Columna HTML para imágenes
    image_width = 60
    df_filtrado["Foto"] = df_filtrado["Enlace_imagen"].apply(
        lambda url: f'<img src="{url}" width="{image_width}">'
    )

    cols_mostrar = [
        "Foto", "Nombre", "Equipo", "Posición", "Propietario",
        "Valor Actual", "Puntos", "Horas", "Minutos", "Fecha de Desbloqueo"
    ]
    df_tabla = df_filtrado[cols_mostrar]

    st.subheader(f"📋 Jugadores con cláusula <{tiempo_max}h")
    st.write(df_tabla.to_html(escape=False, index=False), unsafe_allow_html=True)

# --- TAB 2: Estadísticas ---
with tab2:
    st.subheader("💰 Valor total de jugadores por propietario (en millones)")

    # Gráfica 1: Valor total en millones (ordenada)
    valor_por_propietario = (
        df.groupby("Propietario")["Valor Actual"]
        .sum()
        .reset_index()
    )
    valor_por_propietario["Valor (M)"] = valor_por_propietario["Valor Actual"] / 1_000_000
    valor_por_propietario = valor_por_propietario.sort_values("Valor (M)", ascending=False)

    fig_valor = px.bar(
        valor_por_propietario,
        x="Propietario",
        y="Valor (M)",
        text=valor_por_propietario["Valor (M)"].map(lambda x: f"{x:.1f}M"),
        color="Propietario",
        title="💰 Valor total de jugadores por propietario (en millones)"
    )
    fig_valor.update_traces(textposition="outside")
    fig_valor.update_layout(
        xaxis={'categoryorder':'array', 'categoryarray':valor_por_propietario["Propietario"]},
        margin=dict(t=100),
        yaxis=dict(range=[0, valor_por_propietario["Valor (M)"].max() * 1.15])
    )
    st.plotly_chart(fig_valor, use_container_width=True)

    # Gráfica 2: Incremento diario en millones (ordenada y con negativos)
    st.subheader("📈 Incremento diario del valor del equipo (en millones)")

    incremento_por_propietario = (
        df.groupby("Propietario")["Variacion_diaria"]
        .sum()
        .reset_index()
    )
    incremento_por_propietario["Incremento (M)"] = incremento_por_propietario["Variacion_diaria"] / 1_000_000
    incremento_por_propietario = incremento_por_propietario.sort_values("Incremento (M)", ascending=False)

    fig_incremento = px.bar(
        incremento_por_propietario,
        x="Propietario",
        y="Incremento (M)",
        text=incremento_por_propietario["Incremento (M)"].map(lambda x: f"{x:.1f}M"),
        color="Propietario",
        title="📈 Incremento diario del valor del equipo (en millones)"
    )
    fig_incremento.update_traces(textposition="outside")
    fig_incremento.update_layout(
        xaxis={'categoryorder':'array', 'categoryarray':incremento_por_propietario["Propietario"]},
        margin=dict(t=100),
        yaxis=dict(
            range=[
                incremento_por_propietario["Incremento (M)"].min() * 1.55,
                incremento_por_propietario["Incremento (M)"].max() * 1.25
            ]
        )
    )
    st.plotly_chart(fig_incremento, use_container_width=True)
