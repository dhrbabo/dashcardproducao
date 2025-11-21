import streamlit as st
import pandas as pd
import random
from datetime import datetime
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Dashboard Produção", layout="wide")
st.title("🏭 Linhas de Produção - Status do Dia")

# Gerar dados realistas para 10 linhas
@st.cache_data
def load_data():
    # Produtos disponíveis
    produtos = [
        "Smartphone Galaxy X", "Tablet Pro 12", "Laptop Elite", "Smartwatch Fit", 
        "Fones Bluetooth", "Monitor 4K", "Teclado Mecânico", "Mouse Gamer", 
        "Webcam HD", "Caixa de Som", "Carregador Wireless", "HD Externo SSD",
        "Placa de Vídeo RTX", "Processador i9", "Memória RAM 32GB"
    ]
    
    # Linhas de produção
    linhas = [f"LINHA {i:02d}" for i in range(1, 13)]
    
    data = []
    
    for linha in linhas:
        # Cada linha tem entre 1-3 produtos
        num_produtos = random.randint(1, 3)
        produtos_linha = random.sample(produtos, num_produtos)
        
        for produto in produtos_linha:
            # Gerar dados realistas
            total_semana = random.randint(800, 2500)
            qtd_apontada = random.randint(int(total_semana * 0.6), int(total_semana * 1))
            perc = (qtd_apontada / total_semana) * 100
            saldo_semana = total_semana - qtd_apontada
            
            # Produção por dia (distribuída)
            dias = ['SEGUNDA', 'TERCA', 'QUARTA', 'QUINTA', 'SEXTA', 'SABADO', 'DOMINGO']
            producao_dias = {}
            total_distribuido = 0
            
            for i, dia in enumerate(dias):
                if i < len(dias) - 1:
                    prod_dia = random.randint(int(qtd_apontada * 0.1), int(qtd_apontada * 0.25))
                    producao_dias[dia] = prod_dia
                    total_distribuido += prod_dia
                else:
                    # Último dia recebe o que falta
                    producao_dias[dia] = qtd_apontada - total_distribuido
            
            data.append({
                'CODWCP': f"P{random.randint(1000, 9999)}",
                'DESCRPROD': produto,
                'LINHA': linha,
                'SEGUNDA': producao_dias['SEGUNDA'],
                'TERCA': producao_dias['TERCA'],
                'QUARTA': producao_dias['QUARTA'],
                'QUINTA': producao_dias['QUINTA'],
                'SEXTA': producao_dias['SEXTA'],
                'SABADO': producao_dias['SABADO'],
                'DOMINGO': producao_dias['DOMINGO'],
                'QTDAPONTADA': qtd_apontada,
                'TOTALSEMANA': total_semana,
                'PERC': round(perc, 1),
                'SALDOSEMANA': saldo_semana
            })
    
    return pd.DataFrame(data)

df = load_data()

# Função para criar gauge chart
def create_gauge_chart(percentual, height=120):
    # Definir cores baseadas no percentual
    if percentual >= 80:
        color = "#28a745"  # Verde
    elif percentual >= 70:
        color = "#ffc107"  # Amarelo
    else:
        color = "#dc3545"  # Vermelho
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = percentual,
        number = {'suffix': '%', 'font': {'size': 38}},
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': color, 'thickness': 1},
            'bgcolor': "white",
            'borderwidth': 0,
            'bordercolor': "black",
            'steps': [
                {'range': [0, 50], 'color': '#f8f9fa'},
                {'range': [50, 80], 'color': '#e9ecef'},
                {'range': [80, 100], 'color': '#dee2e6'}],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.85,
                'value': 90}}))
    
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        font={'family': "Arial"},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

# Função para criar card compacto otimizado
def create_compact_card(linha_nome, linha_data):
    produtos_linha = linha_data[linha_data['LINHA'] == linha_nome]
    total_produzido = produtos_linha['QTDAPONTADA'].sum()
    total_objetivo = produtos_linha['TOTALSEMANA'].sum()
    percentual_conclusao = (total_produzido / total_objetivo * 100) if total_objetivo > 0 else 0
    saldo_semana = produtos_linha['SALDOSEMANA'].sum()
    
    # Definir cor baseada no percentual
    if percentual_conclusao >= 80:
        cor_borda = "#28a745"  # Verde
        status = "✅"
        status_text = "Próximo da Meta"
    elif percentual_conclusao >= 70:
        cor_borda = "#c29201"  # Amarelo
        status = "🟡"
        status_text = "Em Andamento"
    else:
        cor_borda = "#dc3545"  # Vermelho
        status = "🔴"
        status_text = "Atenção"
    
    with st.container():
        # Card compacto
        st.markdown(f"""
        <div style="border: 3px solid {cor_borda}; border-radius: 12px; padding: 12px; margin: 8px; background: {cor_borda}20; box-shadow: 0 2px 4px rgba(0,0,0,0.1); height: 80px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <h4 style="color: white; margin: 0; font-size: 26px;">{linha_nome}</h4>
                    <span style="font-size: 14px; background: {cor_borda}20; padding: 2px 8px; border-radius: 12px; color: {cor_borda}; font-weight: bold;">
                        {status} {status_text}
                    </span>
                </div>
        """, unsafe_allow_html=True)
        
        # Lista compacta de produtos
        produtos_lista = [f"{produto['DESCRPROD']}" for _, produto in produtos_linha.iterrows()]
        produtos_texto = " | ".join(produtos_lista)
        st.markdown(f"<div style='font-size: 20px; color: #666; margin-bottom: 8px; line-height: 1.3; margin: 8px;'>{produtos_texto}</div>", unsafe_allow_html=True)
        
        # Barra de progresso com valores NOMINAIS (apontado/meta)
        st.markdown(f"""
        <div style="background: #e9ecef; border-radius: 10px; height: 30px; margin: 8px 0; position: relative;">
            <div style="background: {cor_borda}; border-radius: 10px; height: 100%; width: {min(percentual_conclusao, 100)}%; transition: width 0.3s ease;"></div>
            <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; font-size: 26px; font-weight: bold; color: {'white' if percentual_conclusao > 50 else 'black'};">
                {total_produzido:,} / {total_objetivo:,}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Métricas em grid compacto
        col1, col2 = st.columns(2)
        with col1:
            # Gráfico de indicador (gauge) com a porcentagem
            fig = create_gauge_chart(percentual_conclusao)
            st.plotly_chart(fig, use_container_width=True, key=f"gauge_{linha_nome}")
        with col2:
            st.metric(
                "Produzido", 
                f"{total_produzido:,}",
                help="Quantidade total apontada",
                label_visibility="visible"
            )
        
    st.markdown("---")

# Filtros na sidebar
st.sidebar.header("🔍 Filtros")
st.sidebar.markdown("**Filtrar por Status:**")

# Filtros de status
status_todos = st.sidebar.checkbox("Todos", value=True, key="todos")
status_target = st.sidebar.checkbox("No Target (≥90%)", value=True, key="target")
status_andamento = st.sidebar.checkbox("Em Andamento (75-89%)", value=True, key="andamento")
status_atencao = st.sidebar.checkbox("Atenção (<75%)", value=True, key="atencao")

# Buscar linha específica
buscar_linha = st.sidebar.text_input("🔎 Buscar Linha:")

# Filtrar linhas
linhas_disponiveis = df['LINHA'].unique()
linhas_filtradas = []

for linha in linhas_disponiveis:
    produtos_linha = df[df['LINHA'] == linha]
    total_produzido = produtos_linha['QTDAPONTADA'].sum()
    total_objetivo = produtos_linha['TOTALSEMANA'].sum()
    percentual = (total_produzido / total_objetivo * 100) if total_objetivo > 0 else 0
    
    # Aplicar filtros de status
    status_ok = False
    if percentual >= 90 and status_target:
        status_ok = True
    elif 75 <= percentual < 90 and status_andamento:
        status_ok = True
    elif percentual < 75 and status_atencao:
        status_ok = True
    
    # Aplicar filtro de busca
    if buscar_linha and buscar_linha.lower() not in linha.lower():
        status_ok = False
    
    if status_ok:
        linhas_filtradas.append(linha)

# Organizar em grid 4 colunas
if len(linhas_filtradas) > 0:
    cols = st.columns(4)
    
    # Distribuir cards pelas colunas
    for idx, linha in enumerate(sorted(linhas_filtradas)):
        col_idx = idx % 4
        with cols[col_idx]:
            create_compact_card(linha, df)
else:
    st.warning("ℹ️ Nenhuma linha encontrada com os filtros aplicados.")

# Resumo geral na sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Resumo Geral")

total_geral_produzido = df['QTDAPONTADA'].sum()
total_geral_objetivo = df['TOTALSEMANA'].sum()
perc_geral = (total_geral_produzido / total_geral_objetivo * 100) if total_geral_objetivo > 0 else 0

# Estatísticas por status
linhas_target = 0
linhas_andamento = 0
linhas_atencao = 0

for linha in linhas_disponiveis:
    produtos_linha = df[df['LINHA'] == linha]
    total_produzido = produtos_linha['QTDAPONTADA'].sum()
    total_objetivo = produtos_linha['TOTALSEMANA'].sum()
    percentual = (total_produzido / total_objetivo * 100) if total_objetivo > 0 else 0
    
    if percentual >= 90:
        linhas_target += 1
    elif percentual >= 75:
        linhas_andamento += 1
    else:
        linhas_atencao += 1

st.sidebar.metric("Total Produzido", f"{total_geral_produzido:,}")
st.sidebar.metric("Meta Total", f"{total_geral_objetivo:,}")
st.sidebar.metric("Eficiência Geral", f"{perc_geral:.1f}%")

st.sidebar.markdown("### 🎯 Distribuição por Status")
st.sidebar.success(f"**No Target:** {linhas_target} linhas")
st.sidebar.warning(f"**Em Andamento:** {linhas_andamento} linhas")
st.sidebar.error(f"**Atenção:** {linhas_atencao} linhas")

