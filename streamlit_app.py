import streamlit as st 
import pandas as pd
import plotly.express as px
from datetime import datetime, time, timedelta

from data_loader import (
    get_biwenger_token,
    get_league_data,
    get_public_players,
    get_user_players,
    obtener_clausulas_ejecutadas,
)

# ==============================
# CONFIG STREAMLIT
# ==============================
st.set_page_config(page_title="📊 Jugadores Biwenger", layout="wide")
st.title("📊 Jugadores Biwenger")

# ==============================
# VARIABLES SECRETAS
# ==============================
EMAIL = st.secrets["EMAIL"]
PASSWORD = st.secrets["PASSWORD"]
LEAGUE_ID = st.secrets["LEAGUE_ID"]
USER_ID = st.secrets["USER_ID"]

# ==============================
# FUNCIONES DE REFRESCO
# ==============================
def next_refresh_key() -> str:
    """Devuelve una clave distinta cuando toca refrescar los datos."""
    now = datetime.now()

    # Viernes → refresco a las horas y media (7:30, 8:30, ..., 21:30)
    if now.weekday() == 4:  # 0=lunes ... 4=viernes
        refresh_times = [time(h, 30) for h in range(7, 22)]  # 7:30 a 21:30
        today_times = [datetime.combine(now.date(), t) for t in refresh_times]
        last_refresh = max([dt for dt in today_times if dt <= now], default=None)
        if last_refresh is None:
            last_refresh = datetime.combine(now.date() - timedelta(days=1), refresh_times[-1])
        return last_refresh.strftime("%Y%m%d%H%M")

    # Resto de días → 3 veces al día
    refresh_times = [time(7, 10), time(12, 30), time(21, 10)]
    today_times = [datetime.combine(now.date(), t) for t in refresh_times]
    last_refresh = max([dt for dt in today_times if dt <= now], default=None)
    if last_refresh is None:
        last_refresh = datetime.combine(now.date() - timedelta(days=1), refresh_times[-1])
    return last_refresh.strftime("%Y%m%d%H%M")

def daily_refresh_key() -> str:
    """Clave que cambia solo una vez al día a las 7:10."""
    now = datetime.now()
    ref_time = datetime.combine(now.date(), time(7, 10))
    if now < ref_time:
        # Si aún no son las 7:10, usar el día anterior
        ref_time -= timedelta(days=1)
    return ref_time.strftime("%Y%m%d")

# ==============================
# CARGA DE DATOS
# ==============================
@st.cache_data
def load_data(dummy_key: str):
    token = get_biwenger_token(EMAIL, PASSWORD)

    # Liga y usuarios
    df_liga, df_usuarios = get_league_data(LEAGUE_ID, token, USER_ID)

    # Jugadores públicos
    df_players_public = get_public_players()

    # Jugadores de cada usuario
    df_all_owned = pd.DataFrame()
    for _, user in df_usuarios.iterrows():
        df_user_players = get_user_players(USER_ID, user["id"], LEAGUE_ID, token)
        df_all_owned = pd.concat([df_all_owned, df_user_players], ignore_index=True)

    # Join: unir jugadores públicos con propietarios
    df_jugadores = df_players_public.merge(df_all_owned, on="id", how="left")
    df_jugadores = df_jugadores.merge(
        df_usuarios[["id", "nombre", "imagen"]],
        left_on="propietario_id",
        right_on="id",
        how="left",
        suffixes=("", "_usuario")
    )
    df_jugadores.drop(columns=["id_usuario"], inplace=True)

    # Clausulas ejecutadas
    df_clausulas = obtener_clausulas_ejecutadas(LEAGUE_ID, USER_ID, token, limit=50)

    return df_liga, df_usuarios, df_jugadores, df_clausulas

# 🟢 Cargar datos
df_liga, df_usuarios, df_jugadores, df_clausulas = load_data(next_refresh_key())

# --- Preprocesamiento jugadores ---
df_jugadores["valor_actual"] = pd.to_numeric(df_jugadores["valor_actual"], errors="coerce")
df_jugadores["fecha_desbloqueo"] = pd.to_datetime(df_jugadores["fecha_desbloqueo"], errors="coerce")
df_jugadores["variacion_diaria"] = pd.to_numeric(df_jugadores["variacion_diaria"], errors="coerce")

# ==============================
# FUNCIONES EXTRA
# ==============================
@st.cache_data
def clausulas_abiertas_hoy(df_jugadores: pd.DataFrame, clave_dia: str):
    """Jugadores cuya cláusula se abre o está abierta en el día actual."""
    ahora = pd.Timestamp.now()
    hoy = ahora.normalize()
    df_hoy = df_jugadores[
        (df_jugadores["fecha_desbloqueo"].dt.date == hoy.date())
    ].copy()
    return df_hoy

# --- Tabs ---
tab1, tab5, tab3, tab2, tab4, tab6 = st.tabs([
    "⏳ Cláusulas próximas",
    "🔨 Clausulazos recibidos < 7 días",
    "📝 Cláusulas desbloqueadas",
    "📊 Estadísticas por propietario",
    "📈 Gráficas adicionales",
    "📅 Cláusulas de hoy"
])
# -----------------------------------------------------------------
# TAB 1: Cláusulas próximas
# -----------------------------------------------------------------
with tab1:
    st.subheader("Filtros de cláusulas próximas")
    col1, col2, col3 = st.columns(3)

    propietarios = ["Todos"] + sorted(df_usuarios["nombre"].unique())
    propietario_sel = col1.selectbox("Filtrar por propietario", propietarios)
    tiempo_max = col2.slider("Tiempo máximo restante (horas)", 0, 48, 48)
    posiciones = ["Todas"] + sorted(df_jugadores["posicion"].dropna().unique())
    posicion_sel = col3.selectbox("Filtrar por posición", posiciones)

    df_tab1 = df_jugadores.copy()
    df_tab1["Horas_restantes"] = (df_tab1["fecha_desbloqueo"] - pd.Timestamp.now()).dt.total_seconds()/3600
    df_tab1 = df_tab1[df_tab1["Horas_restantes"] <= tiempo_max]
    if propietario_sel != "Todos":
        df_tab1 = df_tab1[df_tab1["nombre"] == propietario_sel]
    if posicion_sel != "Todas":
        df_tab1 = df_tab1[df_tab1["posicion"] == posicion_sel]

    df_tab1["Valor Cláusula"] = df_tab1["valor_clausula"].apply(lambda x: f"{int(x):,}".replace(",", ".")) if "valor_clausula" in df_tab1 else "-"
    df_tab1["Valor Actual"] = df_tab1["valor_actual"].apply(lambda x: f"{int(x):,}".replace(",", "."))
    df_tab1["Puntos"] = df_tab1["puntos"].apply(lambda x: f"{int(x):,}".replace(",", "."))
    df_tab1["Horas Restantes"] = df_tab1["Horas_restantes"].apply(lambda x: f"{int(x)}h")

    df_tab1["Foto Jugador"] = df_tab1["enlace_imagen"].apply(lambda x: f'<div style="text-align:center"><img src="{x}" height="50"></div>')
    df_tab1["Icono Propietario"] = df_tab1["imagen"].apply(lambda x: f'<div style="text-align:center"><img src="{x}" height="50"></div>')

    cols_mostrar = ["Foto Jugador", "nombre", "equipo", "posicion", "nombre", "Icono Propietario", "Valor Cláusula", "Valor Actual", "Puntos", "Horas Restantes", "fecha_desbloqueo"]
    cols_renombrar = {"nombre": "Propietario", "equipo": "Equipo", "posicion": "Posición", "fecha_desbloqueo": "Fecha Desbloqueo"}

    st.write(df_tab1[cols_mostrar].rename(columns=cols_renombrar).to_html(escape=False, index=False), unsafe_allow_html=True)

# -----------------------------------------------------------------
# TAB 2: Estadísticas por propietario
# -----------------------------------------------------------------
colores_manual = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]
usuarios_ids = sorted(df_usuarios["id"].unique())
color_map_id = {str(uid): colores_manual[i % len(colores_manual)] for i, uid in enumerate(usuarios_ids)}

with tab2:
    st.subheader("💰 Valor total de jugadores por propietario (millones)")
    valor_por_propietario = df_jugadores.groupby(["nombre_usuario", "propietario_id"])["valor_actual"].sum().reset_index()
    valor_por_propietario["Valor (M)"] = valor_por_propietario["valor_actual"] / 1_000_000
    valor_por_propietario = valor_por_propietario.sort_values("Valor (M)", ascending=False)
    valor_por_propietario["propietario_id"] = valor_por_propietario["propietario_id"].astype(str)

    fig_valor = px.bar(
        valor_por_propietario,
        x="nombre_usuario",
        y="Valor (M)",
        text=valor_por_propietario["Valor (M)"].map(lambda x: f"{x:.1f}M"),
        color="propietario_id",
        color_discrete_map=color_map_id,
        labels={"nombre_usuario": "Propietario", "Valor (M)": "Valor total (millones)"}
    )
    fig_valor.update_traces(textposition="outside")
    fig_valor.update_layout(
        margin=dict(t=100),
        yaxis=dict(range=[0, valor_por_propietario["Valor (M)"].max() * 1.15]),
        showlegend=False,
        dragmode=False
    )
    st.plotly_chart(fig_valor, use_container_width=True, config={"displayModeBar": False})

    st.subheader("📈 Incremento diario del valor del equipo (millones)")
    incremento_por_propietario = df_jugadores.groupby(["nombre_usuario", "propietario_id"])["variacion_diaria"].sum().reset_index()
    incremento_por_propietario["Incremento (M)"] = incremento_por_propietario["variacion_diaria"] / 1_000_000
    incremento_por_propietario = incremento_por_propietario.sort_values("Incremento (M)", ascending=False)
    incremento_por_propietario["propietario_id"] = incremento_por_propietario["propietario_id"].astype(str)

    fig_incremento = px.bar(
        incremento_por_propietario,
        x="nombre_usuario",
        y="Incremento (M)",
        text=incremento_por_propietario["Incremento (M)"].map(lambda x: f"{x:.2f}M"),
        color="propietario_id",
        color_discrete_map=color_map_id,
        labels={"nombre_usuario": "Propietario", "Incremento (M)": "Incremento diario (millones)"}
    )
    fig_incremento.update_traces(textposition="outside")
    fig_incremento.update_layout(
        margin=dict(t=100),
        yaxis=dict(
            range=[
                incremento_por_propietario["Incremento (M)"].min() * 1.15,
                incremento_por_propietario["Incremento (M)"].max() * 1.15
            ]
        ),
        showlegend=False,
        dragmode=False
    )
    st.plotly_chart(fig_incremento, use_container_width=True, config={"displayModeBar": False})

# -----------------------------------------------------------------
# TAB 3: Cláusulas desbloqueadas
# -----------------------------------------------------------------
with tab3:
    st.subheader("Jugadores con cláusula desbloqueada recientemente")
    df_tab3 = df_jugadores[df_jugadores["fecha_desbloqueo"] < pd.Timestamp.now()].copy()
    df_tab3["Valor Cláusula"] = df_tab3["valor_clausula"].apply(lambda x: f"{int(x):,}".replace(",", "."))
    df_tab3["Valor Actual"] = df_tab3["valor_actual"].apply(lambda x: f"{int(x):,}".replace(",", "."))
    df_tab3["Puntos"] = df_tab3["puntos"].apply(lambda x: f"{int(x):,}".replace(",", "."))
    df_tab3["Foto Jugador"] = df_tab3["enlace_imagen"].apply(lambda x: f'<div style="text-align:center"><img src="{x}" height="50"></div>')
    df_tab3["Icono Propietario"] = df_tab3["imagen"].apply(lambda x: f'<div style="text-align:center"><img src="{x}" height="50"></div>')
    df_tab3["fecha_desbloqueo"] = df_tab3["fecha_desbloqueo"].dt.strftime("%d/%m/%Y %H:%M")
    cols_mostrar = ["Foto Jugador", "nombre", "equipo", "posicion", "nombre", "Icono Propietario", "Valor Cláusula", "Valor Actual", "Puntos", "fecha_desbloqueo"]
    cols_renombrar = {"nombre": "Propietario", "equipo": "Equipo", "posicion": "Posición", "fecha_desbloqueo": "Fecha Desbloqueo"}
    st.write(df_tab3[cols_mostrar].rename(columns=cols_renombrar).to_html(escape=False, index=False), unsafe_allow_html=True)

# -----------------------------------------------------------------
# TAB 4: Gráficas adicionales
# -----------------------------------------------------------------
with tab4:
    st.subheader("🏆 Top 10 jugadores por valor")
    top_jugadores = df_jugadores.sort_values("valor_actual", ascending=False).head(10)
    st.dataframe(top_jugadores[["nombre", "equipo", "valor_actual", "puntos"]])

    st.subheader("📊 Valor medio por posición")
    valor_pos = df_jugadores.groupby("posicion")["valor_actual"].mean().reset_index()
    valor_pos["Valor (M)"] = valor_pos["valor_actual"]/1_000_000
    fig_pos = px.bar(valor_pos, x="posicion", y="Valor (M)", text=valor_pos["Valor (M)"].map(lambda x: f"{x:.2f}M"))
    fig_pos.update_traces(textposition="outside")
    st.plotly_chart(fig_pos, use_container_width=True)

# -----------------------------------------------------------------
# TAB 5: Clausulazos recibidos
# -----------------------------------------------------------------
with tab5:
    st.subheader("Clausulazos recibidos por propietario en los últimos 7 días")
    fecha_limite = pd.Timestamp.now() - pd.Timedelta(days=7, hours=2)
    df_recientes = df_clausulas[df_clausulas["entry_date"] >= fecha_limite]
    clausulas_recibidas = df_recientes.groupby("from_id").size().reset_index(name="Recibidos")
    clausulas_recibidas["Recibidos"] = clausulas_recibidas["Recibidos"].clip(upper=3)
    df_tab5 = df_usuarios[["id", "nombre"]].merge(clausulas_recibidas, left_on="id", right_on="from_id", how="left").fillna(0)
    df_tab5["Recibidos"] = df_tab5["Recibidos"].astype(int)
    df_tab5["Restantes"] = 3 - df_tab5["Recibidos"]
    df_tab5 = df_tab5.drop(columns=["from_id", "id"]).reset_index(drop=True)
    df_tab5 = df_tab5.rename(columns={"nombre": "Nombre"})

    def color_fila(row):
        pastel = {0: "#a8ddb5", 1: "#ffe699", 2: "#ffb366", 3: "#f77f7f"}
        color = pastel.get(row["Recibidos"], "#cccccc")
        return [f'background-color: {color}; color: black; text-align:center; font-weight:bold;' for _ in row]

    styled_df = df_tab5.style.apply(color_fila, axis=1)
    html_table = styled_df.to_html().replace("</div>", "")
    st.markdown(f"<div style='overflow-x:auto;'>{html_table}", unsafe_allow_html=True)

# -----------------------------------------------------------------
# TAB 6: Cláusulas de hoy
# -----------------------------------------------------------------
with tab6:
    st.subheader("📅 Jugadores con cláusula abierta o desbloqueada hoy")

    # 👇 Pasamos la clave diaria
    df_hoy = clausulas_abiertas_hoy(df_jugadores, daily_refresh_key())

    if df_hoy.empty:
        st.info("No hay cláusulas que se hayan abierto hoy")
    else:
        df_hoy["Valor Cláusula"] = df_hoy["valor_clausula"].apply(lambda x: f"{int(x):,}".replace(",", "."))
        df_hoy["Valor Actual"] = df_hoy["valor_actual"].apply(lambda x: f"{int(x):,}".replace(",", "."))
        df_hoy["Puntos"] = df_hoy["puntos"].apply(lambda x: f"{int(x):,}".replace(",", "."))
        df_hoy["Foto Jugador"] = df_hoy["enlace_imagen"].apply(lambda x: f'<div style="text-align:center"><img src="{x}" height="50"></div>')
        df_hoy["Icono Propietario"] = df_hoy["imagen"].apply(lambda x: f'<div style="text-align:center"><img src="{x}" height="50"></div>')
        df_hoy["fecha_desbloqueo"] = df_hoy["fecha_desbloqueo"].dt.strftime("%d/%m/%Y %H:%M")
        cols_mostrar = ["Foto Jugador", "nombre", "equipo", "posicion", "nombre", "Icono Propietario", "Valor Cláusula", "Valor Actual", "Puntos", "fecha_desbloqueo"]
        cols_renombrar = {"nombre": "Propietario", "equipo": "Equipo", "posicion": "Posición", "fecha_desbloqueo": "Fecha Desbloqueo"}
        st.write(df_hoy[cols_mostrar].rename(columns=cols_renombrar).to_html(escape=False, index=False), unsafe_allow_html=True)