import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

# Título da página Streamlit
st.set_page_config(layout="wide")
st.title('Diagramas de Risco de Incêndio')
st.markdown("---")

# === LÓGICA DE GERAÇÃO DO DIAGRAMA ===

# Definições de risco e cores
mapa_de_cores = {
    'Baixo': '#4CAF50',
    'Moderado': '#FFC107',
    'Alto': '#FFA500',
    'Crítico': '#D32F2F',
}
limites_risco = [0, 0.25, 0.50, 0.75, 1.20]
nomes_risco = ['Baixo', 'Moderado', 'Alto', 'Crítico']

def ultimo_valor_valido(lista):
    for v in reversed(lista):
        if not (isinstance(v, float) and np.isnan(v)):
            return v
    return np.nan

def calc_ttr(df):
    ttr_values = []
    drop_streak_values = []
    
    # Adicionando uma verificação para evitar erro com dados vazios
    if df.empty:
        df['ICTR14'] = np.nan
        return df

    for i in range(len(df)):
        vr7 = df['VR7']
        rf = df['risco_fogo']
        
        if np.isnan(vr7.iloc[i]):
            ttr_values.append(np.nan)
            drop_streak_values.append(0)
            continue
        
        rf_t = rf.iloc[i]
        mm7_t = vr7.iloc[i]
        
        if len(ttr_values) == 0 or np.all(pd.isna(ttr_values)):
            ttr_values.append(mm7_t)
            drop_streak_values.append(0)
            continue
            
        ttr_prev = ultimo_valor_valido(ttr_values)
        if isinstance(ttr_prev, float) and np.isnan(ttr_prev):
            ttr_values.append(mm7_t)
            drop_streak_values.append(0)
            continue

        rf_prev = rf.iloc[i - 1] if i - 1 >= 0 else rf_t
        delta = rf_t - rf_prev
        last_drop_streak = drop_streak_values[-1] if len(drop_streak_values) > 0 else 0
        
        if delta < 0:
            drop_streak = last_drop_streak + 1
        else:
            drop_streak = 0
            
        if delta > 0:
            inc = 0.3 * delta + 0.01
            ttr_t = max(mm7_t, ttr_prev + inc)
        elif delta == 0:
            ttr_t = ttr_prev
        else:
            if drop_streak == 1:
                ttr_t = max(mm7_t, ttr_prev)
            else:
                ttr_t = mm7_t
        
        ttr_values.append(ttr_t)
        drop_streak_values.append(drop_streak)
    
    df['ICTR14'] = ttr_values
    return df

# === GERAÇÃO DO GRÁFICO PLOTLY PARA CADA ARQUIVO ===

# Lista dos arquivos a serem processados
caminho_pasta = r"D:\Documentos\ufrpe\IPECTI\Projeto Raffael\incendio_florestal\riskdiagrams-incendios"
arquivos_excel = [
    "Risco_Ubatuba.xlsx",
    "Risco_Palmeiras.xlsx",
    "Risco_Cotriguaçu.xlsx",
]

for nome_arquivo in arquivos_excel:
    caminho_completo = os.path.join(caminho_pasta, nome_arquivo)
    nome_local = nome_arquivo.replace("Risco_", "").replace(".xlsx", "").replace("Risco.xlsx", "Cidade")

    st.subheader(f'Diagrama de Risco de Incêndio para {nome_local.capitalize()}')
    
    if not os.path.exists(caminho_completo):
        st.error(f"Arquivo **{nome_arquivo}** não encontrado em: `{caminho_pasta}`.")
        continue

    # Lê os dados
    df = pd.read_excel(caminho_completo, sheet_name='Cidade')
    df.columns = ['data', 'risco_fogo']
    df['data'] = pd.to_datetime(df['data'])
    df = df.sort_values('data')

    # Calcula VR7 e TTR
    df['VR7'] = df['risco_fogo'].rolling(window=7, min_periods=7).mean().clip(lower=0)
    df = calc_ttr(df)
    
    df_plot = df.dropna(subset=['risco_fogo', 'ICTR14']).copy()
    if df_plot.empty:
        st.warning(f"O arquivo {nome_arquivo} não contém dados suficientes para gerar o diagrama.")
        continue
    
    df_plot['data'] = df_plot['data'].dt.strftime('%d-%m-%Y')
    df_plot['Nivel_Risco'] = pd.cut(df_plot['risco_fogo'], bins=limites_risco, labels=nomes_risco, right=False)

    
# Gera o gráfico Plotly
    fig = go.Figure()

    # Fundo do gráfico (Mapa de calor)
    xx = np.linspace(0, 1.20, 500)
    yy = np.linspace(0, 1.60, 500)
    X, Y = np.meshgrid(xx, yy)
    EPG_grid = Y * X + (X * 0.3)
    EPG_norm = np.clip(EPG_grid / 1, 0, 1)
    paleta = [(0.00, '#4CAF50'), (0.30, '#FFA500'), (1.00, '#D32F2F')]
    plotly_colorscale = [(p, c) for p, c in paleta]
    fig.add_trace(go.Heatmap(x=xx, y=yy, z=EPG_norm, colorscale=plotly_colorscale, showscale=False, opacity=0.68, hoverinfo='none'))

    # Linha de trajetória (sem pontos)
    fig.add_trace(go.Scatter(
        x=df_plot['risco_fogo'],
        y=df_plot['ICTR14'],
        mode='lines',
        line=dict(color='black', width=1.5, dash='dash'),
        hoverinfo='none',
        showlegend=False
    ))

    # Adiciona os pontos com cores baseadas no nível de risco
    for nivel in nomes_risco:
        df_nivel = df_plot[df_plot['Nivel_Risco'] == nivel]
        if not df_nivel.empty:
            fig.add_trace(go.Scatter(
                x=df_nivel['risco_fogo'],
                y=df_nivel['ICTR14'],
                mode='markers',
                marker=dict(color=mapa_de_cores[nivel], size=10, line=dict(width=1, color='black')),
                name=f'Nível {nivel}',
                hoverinfo='text',
                hovertext=[
                    f"<b>Data:</b> {data}<br><b>Risco de Fogo:</b> {rf}<br><b>TTR:</b> {ttr}<br><b>Nível:</b> {nivel}"
                    for data, rf, ttr in zip(df_nivel['data'], df_nivel['risco_fogo'], df_nivel['ICTR14'])
                ],
                showlegend=False  # Não mostra a legenda para os pontos plotados
            ))

    # Cria as entradas de legenda separadamente para que sejam fixas
    for nivel in nomes_risco:
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(color=mapa_de_cores[nivel], size=10, line=dict(width=1, color='black')),
            name=f'Nível {nivel}',
        ))
    
    # Layout e títulos
    fig.update_layout(
        title=dict(text=f'<b>{nome_local.capitalize()}</b>', x=0.5, font=dict(size=18)),
        xaxis=dict(title='Risco de fogo observado (RF)', range=[0, 1.20], showgrid=False, zeroline=False, showline=False,),
        yaxis=dict(title='Tendência temporal de risco (TTR)', range=[0, 1.60], showgrid=False, zeroline=False, showline=False,),
        plot_bgcolor='white',
        width=800, height=500,
        legend_title_text='<b>Níveis de Risco</b>',
        legend=dict(font=dict(color="black")),
    )
    
    # Exibe o gráfico no Streamlit
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("---")