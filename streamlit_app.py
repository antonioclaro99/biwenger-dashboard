import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="📊 Jugadores Biwenger", layout="wide")
st.title("📊 Jugadores Biwenger")

# --- URLs de Dropbox ---
url_liga = "https://www.dropbox.com/scl/fi/dy5rnly5qmjw8o5vbprvu/liga.csv?rlkey=dcnb8vjdzadcleukoqu3r4yx2&st=w3fhqlup&dl=1"
url_usuarios = "https://www.dropbox.com/scl/fi/7i5j3n3semnp6js8zy678/usuarios.csv?rlkey=u0gir8jctlr6w8trxdfavmq8d&st=cgenm5zl&dl=1"
url_jugadores = "https://www.dropbox.com/scl/fi/e965d1089v7umaw57yifq/jugadores_final.csv?rlkey=cgssxqhipl782c0qc4coytdnc&st=43zelkr6&dl=1"
url_clausulas = "https://www.dropbox.com/scl/fi/gedow86lz673fgm8ximom/clausulas.csv?rlkey=1alc7fdqg3ecdwkw5kwlheo1i&st=zqbaa81m&dl=1"


@st.cache_data
def load_csv(url):
    return pd.read_csv(url)

df_liga = load_csv(url_liga)
df_usuarios = load_csv(url_usuarios)
df_jugadores = load_csv(url_jugadores)
df_clausulas = load_csv(url_clausulas)


# --- Preprocesamiento jugadores ---
df_jugadores["valor_actual"] = df_jugadores["valor_actual"].replace({r"[^\d]": ""}, regex=True).astype(float)
df_jugadores["fecha_desbloqueo"] = pd.to_datetime(df_jugadores["fecha_desbloqueo"], errors="coerce")
df_jugadores["variacion_diaria"] = df_jugadores["variacion_diaria"].astype(float)

# Unimos icono de propietario
df_jugadores = df_jugadores.merge(df_usuarios[["id","imagen"]], left_on="propietario_id", right_on="id", how="left")
df_jugadores = df_jugadores.rename(columns={"imagen":"icono_propietario"})

# --- Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⏳ Cláusulas próximas",
    "📊 Estadísticas por propietario",
    "📝 Cláusulas desbloqueadas",
    "📈 Gráficas adicionales",
    "🔨 Clausulazos recibidos en los últimos 7 días"
])

# --- TAB 1: Cláusulas próximas ---
with tab1:
    st.subheader("Filtros de cláusulas próximas")
    col1, col2, col3 = st.columns(3)

    propietarios = ["Todos"] + sorted(df_usuarios["nombre"].unique())
    propietario_sel = col1.selectbox("Filtrar por propietario", propietarios)
    tiempo_max = col2.slider("Tiempo máximo restante (horas)", 0, 48, 48)
    posiciones = ["Todas"] + sorted(df_jugadores["posicion"].dropna().unique())
    posicion_sel = col3.selectbox("Filtrar por posición", posiciones)

    df_tab1 = df_jugadores.copy()
    # Calculamos horas restantes
    df_tab1["Horas_restantes"] = (df_tab1["fecha_desbloqueo"] - pd.Timestamp.now()).dt.total_seconds()/3600
    df_tab1 = df_tab1[df_tab1["Horas_restantes"] <= tiempo_max]
    if propietario_sel != "Todos":
        df_tab1 = df_tab1[df_tab1["nombre_usuario"] == propietario_sel]
    if posicion_sel != "Todas":
        df_tab1 = df_tab1[df_tab1["posicion"] == posicion_sel]

    # Formateamos valores numéricos
    df_tab1["Valor Cláusula"] = df_tab1["valor_clausula"].apply(lambda x: f"{int(x):,}".replace(",", "."))
    df_tab1["Valor Actual"] = df_tab1["valor_actual"].apply(lambda x: f"{int(x):,}".replace(",", "."))
    df_tab1["Puntos"] = df_tab1["puntos"].apply(lambda x: f"{int(x):,}".replace(",", "."))
    df_tab1["Horas Restantes"] = df_tab1["Horas_restantes"].apply(lambda x: f"{int(x)}h")  # redondeamos hacia abajo

    # Imagenes HTML centradas
    df_tab1["Foto Jugador"] = df_tab1["enlace_imagen"].apply(
        lambda x: f'<div style="text-align:center"><img src="{x}" height="50"></div>'
    )
    df_tab1["Icono Propietario"] = df_tab1["icono_propietario"].apply(
        lambda x: f'<div style="text-align:center"><img src="{x}" height="50"></div>'
    )

    # Seleccionamos y renombramos columnas en formato humano
    cols_mostrar = [
        "Foto Jugador", "nombre", "equipo", "posicion", "nombre_usuario",
        "Icono Propietario", "Valor Cláusula", "Valor Actual", "Puntos",
        "Horas Restantes", "fecha_desbloqueo"
    ]
    cols_renombrar = {
        "Foto Jugador": "Foto Jugador",
        "nombre": "Nombre",
        "equipo": "Equipo",
        "posicion": "Posición",
        "nombre_usuario": "Propietario",
        "Icono Propietario": "Icono Propietario",
        "Valor Cláusula": "Valor Cláusula",
        "Valor Actual": "Valor Actual",
        "Puntos": "Puntos",
        "Horas Restantes": "Horas Restantes",
        "fecha_desbloqueo": "Fecha Desbloqueo"
    }

    st.write(df_tab1[cols_mostrar].rename(columns=cols_renombrar).to_html(escape=False, index=False), unsafe_allow_html=True)


# --- TAB 2: Estadísticas por propietario ---
import plotly.express as px

# Paleta manual de colores bien diferenciados
colores_manual = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]

# Diccionario consistente por ID de propietario
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
        dragmode=False  # <- deshabilita el arrastre/zoom
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
        dragmode=False  # <- deshabilita interacciones
    )
    st.plotly_chart(fig_incremento, use_container_width=True, config={"displayModeBar": False})


# --- TAB 3: Cláusulas desbloqueadas ---
with tab3:
    st.subheader("Jugadores con cláusula desbloqueada recientemente")

    # Filtramos solo las filas cuya fecha_desbloqueo es anterior a ahora
    df_tab3 = df_jugadores[df_jugadores["fecha_desbloqueo"] < pd.Timestamp.now()].copy()

    # Formateamos valores numéricos igual que tab1
    df_tab3["Valor Cláusula"] = df_tab3["valor_clausula"].apply(lambda x: f"{int(x):,}".replace(",", "."))
    df_tab3["Valor Actual"] = df_tab3["valor_actual"].apply(lambda x: f"{int(x):,}".replace(",", "."))
    df_tab3["Puntos"] = df_tab3["puntos"].apply(lambda x: f"{int(x):,}".replace(",", "."))

    # Imagenes HTML centradas
    df_tab3["Foto Jugador"] = df_tab3["enlace_imagen"].apply(
        lambda x: f'<div style="text-align:center"><img src="{x}" height="50"></div>'
    )
    df_tab3["Icono Propietario"] = df_tab3["icono_propietario"].apply(
        lambda x: f'<div style="text-align:center"><img src="{x}" height="50"></div>'
    )

    # Columnas y renombrado igual que tab1
    cols_mostrar = [
        "Foto Jugador", "nombre", "equipo", "posicion", "nombre_usuario",
        "Icono Propietario", "Valor Cláusula", "Valor Actual", "Puntos",
        "fecha_desbloqueo"
    ]
    cols_renombrar = {
        "Foto Jugador": "Foto Jugador",
        "nombre": "Nombre",
        "equipo": "Equipo",
        "posicion": "Posición",
        "nombre_usuario": "Propietario",
        "Icono Propietario": "Icono Propietario",
        "Valor Cláusula": "Valor Cláusula",
        "Valor Actual": "Valor Actual",
        "Puntos": "Puntos",
        "fecha_desbloqueo": "Fecha Desbloqueo"
    }

    # Formateamos fecha de manera legible como en tab1
    df_tab3["fecha_desbloqueo"] = df_tab3["fecha_desbloqueo"].dt.strftime("%d/%m/%Y %H:%M")

    st.write(df_tab3[cols_mostrar].rename(columns=cols_renombrar).to_html(escape=False, index=False), unsafe_allow_html=True)

# --- TAB 4: Gráficas adicionales ---
with tab4:
    st.subheader("🏆 Top 10 jugadores por valor")
    top_jugadores = df_jugadores.sort_values("valor_actual", ascending=False).head(10)
    st.dataframe(top_jugadores[["nombre","equipo","nombre_usuario","valor_actual","puntos"]])

    st.subheader("📊 Valor medio por posición")
    valor_pos = df_jugadores.groupby("posicion")["valor_actual"].mean().reset_index()
    valor_pos["Valor (M)"] = valor_pos["valor_actual"]/1_000_000
    fig_pos = px.bar(valor_pos, x="posicion", y="Valor (M)", text=valor_pos["Valor (M)"].map(lambda x: f"{x:.2f}M"))
    fig_pos.update_traces(textposition="outside")
    st.plotly_chart(fig_pos, use_container_width=True)


# --- TAB 5: Cláusulazos recibidos ---
with tab5:
    st.subheader("Clausulazos recibidos por propietario en los últimos 7 días")

    # Convertimos fecha
    df_clausulas["entry_date"] = pd.to_datetime(df_clausulas["entry_date"], errors="coerce")

    # Filtramos últimos 7 días
    fecha_limite = pd.Timestamp.now() - pd.Timedelta(days=7, hours=2)
    df_recientes = df_clausulas[df_clausulas["entry_date"] >= fecha_limite]

    # Contamos clausulazos por emisor (from_id)
    clausulas_recibidas = df_recientes.groupby("from_id").size().reset_index(name="clausulazos_recibidos")

    # Limitamos a máximo 3
    clausulas_recibidas["clausulazos_recibidos"] = clausulas_recibidas["clausulazos_recibidos"].clip(upper=3)

    # Cruzamos con df_usuarios por id para que aparezcan todos los usuarios
    df_tab5 = df_usuarios[["id", "nombre"]].merge(
        clausulas_recibidas, left_on="id", right_on="from_id", how="left"
    ).fillna(0)

    df_tab5["clausulazos_recibidos"] = df_tab5["clausulazos_recibidos"].astype(int)
    df_tab5 = df_tab5.drop(columns=["from_id","id"])  # Eliminamos columnas innecesarias
    df_tab5 = df_tab5.reset_index(drop=True)  # Esto elimina la columna index

    # Función para color semáforo
    def color_semáforo(val):
        color = {0:"#2ca02c", 1:"#ffdd57", 2:"#ff8c00", 3:"#d62728"}.get(val, "#cccccc")
        return f'background-color: {color}; color: black; text-align:center; font-weight:bold;'

    st.write("Cada celda indica cuántos clausulazos ha recibido el propietario en los últimos 7 días (máx 3).")
    st.dataframe(df_tab5.style.applymap(color_semáforo, subset=["clausulazos_recibidos"]))


