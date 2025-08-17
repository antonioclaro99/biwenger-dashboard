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

@st.cache_data
def load_csv(url):
    return pd.read_csv(url)

df_liga = load_csv(url_liga)
df_usuarios = load_csv(url_usuarios)
df_jugadores = load_csv(url_jugadores)

# --- Preprocesamiento jugadores ---
df_jugadores["valor_actual"] = df_jugadores["valor_actual"].replace({r"[^\d]": ""}, regex=True).astype(float)
df_jugadores["fecha_desbloqueo"] = pd.to_datetime(df_jugadores["fecha_desbloqueo"], errors="coerce")
df_jugadores["variacion_diaria"] = df_jugadores["variacion_diaria"].astype(float)

# Unimos icono de propietario
df_jugadores = df_jugadores.merge(df_usuarios[["id","imagen"]], left_on="propietario_id", right_on="id", how="left")
df_jugadores = df_jugadores.rename(columns={"imagen":"icono_propietario"})

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs([
    "⏳ Cláusulas próximas",
    "📊 Estadísticas por propietario",
    "📝 Cláusulas desbloqueadas",
    "📈 Gráficas adicionales"
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
with tab2:
    st.subheader("💰 Valor total de jugadores por propietario (millones)")
    valor_por_propietario = df_jugadores.groupby("nombre_usuario")["valor_actual"].sum().reset_index()
    valor_por_propietario["Valor (M)"] = valor_por_propietario["valor_actual"]/1_000_000
    valor_por_propietario = valor_por_propietario.sort_values("Valor (M)", ascending=False)

    fig_valor = px.bar(
        valor_por_propietario,
        x="nombre_usuario",
        y="Valor (M)",
        text=valor_por_propietario["Valor (M)"].map(lambda x: f"{x:.1f}M"),
        color="nombre_usuario"
    )
    fig_valor.update_traces(textposition="outside")
    fig_valor.update_layout(margin=dict(t=100), yaxis=dict(range=[0, valor_por_propietario["Valor (M)"].max()*1.15]))
    st.plotly_chart(fig_valor, use_container_width=True)

    st.subheader("📈 Incremento diario del valor del equipo (millones)")
    incremento_por_propietario = df_jugadores.groupby("nombre_usuario")["variacion_diaria"].sum().reset_index()
    incremento_por_propietario["Incremento (M)"] = incremento_por_propietario["variacion_diaria"]/1_000_000
    incremento_por_propietario = incremento_por_propietario.sort_values("Incremento (M)", ascending=False)

    fig_incremento = px.bar(
        incremento_por_propietario,
        x="nombre_usuario",
        y="Incremento (M)",
        text=incremento_por_propietario["Incremento (M)"].map(lambda x: f"{x:.2f}M"),
        color="nombre_usuario"
    )
    fig_incremento.update_traces(textposition="outside")
    fig_incremento.update_layout(
        margin=dict(t=100),
        yaxis=dict(
            range=[
                incremento_por_propietario["Incremento (M)"].min()*1.15,
                incremento_por_propietario["Incremento (M)"].max()*1.15
            ]
        )
    )
    st.plotly_chart(fig_incremento, use_container_width=True)

# --- TAB 3: Cláusulas desbloqueadas ---
with tab3:
    st.subheader("Jugadores con cláusula desbloqueada recientemente")
    df_tab3 = df_jugadores[df_jugadores["fecha_desbloqueo"] < pd.Timestamp.now()]
    df_tab3["Foto"] = df_tab3["enlace_imagen"].apply(lambda x: f'<img src="{x}" width="60">')
    df_tab3["Icono"] = df_tab3["icono_propietario"].apply(lambda x: f'<img src="{x}" width="40">')
    cols_mostrar = ["Foto","nombre","equipo","posicion","nombre_usuario","Icono","valor_clausula","valor_actual","puntos","fecha_desbloqueo"]
    st.write(df_tab3[cols_mostrar].to_html(escape=False,index=False), unsafe_allow_html=True)

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
