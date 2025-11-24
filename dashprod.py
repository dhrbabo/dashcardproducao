import streamlit as st
import pandas as pd
import random
from datetime import datetime
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh

# Configuração da página
st.set_page_config(page_title="Dashboard Produção", layout="wide")
st.title("🏭 Linhas de Produção - Status do Dia")

# CSS para auto-refresh
st.markdown("""
<style>
    .auto-refresh-indicator {
        position: fixed;
        top: 10px;
        right: 10px;
        background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
        color: white;
        padding: 8px 15px;
        border-radius: 20px;
        font-size: 14px;
        z-index: 9999;
        font-weight: bold;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

# SOLUÇÃO: Inicialização do session_state para manter o arquivo
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'uploaded_file_name' not in st.session_state:
    st.session_state.uploaded_file_name = None
if 'df_processado' not in st.session_state:
    st.session_state.df_processado = None
if 'produtos_por_linha' not in st.session_state:
    st.session_state.produtos_por_linha = None

if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False
if 'rotation_index' not in st.session_state:
    st.session_state.rotation_index = 0
if 'last_refresh_time' not in st.session_state:
    st.session_state.last_refresh_time = time.time()
if 'max_caracteres_linha' not in st.session_state:
    st.session_state.max_caracteres_linha = 25
if 'max_caracteres_produto' not in st.session_state:
    st.session_state.max_caracteres_produto = 30
if 'rotacao_por_linha' not in st.session_state:
    st.session_state.rotacao_por_linha = {}
if 'refresh_counter' not in st.session_state:
    st.session_state.refresh_counter = 0
if 'refresh_interval' not in st.session_state:
    st.session_state.refresh_interval = 30
if 'rotacao_ativa' not in st.session_state:
    st.session_state.rotacao_ativa = True

# Funções de negócio
def obter_dia_atual():
    dias_semana_ingles = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
    dias_semana_portugues = ['SEGUNDA', 'TERCA', 'QUARTA', 'QUINTA', 'SEXTA', 'SABADO', 'DOMINGO']
    dia_numero = datetime.now().weekday()
    return dias_semana_portugues[dia_numero]

def importar_excel(arquivo):
    try:
        df = pd.read_excel(arquivo)
        return df
    except Exception as e:
        st.error(f"Erro ao importar arquivo Excel: {e}")
        return None

def processar_dados_base_real(df):
    dia_atual = obter_dia_atual()
    dados_processados = []
    
    for _, row in df.iterrows():
        linha = row['LINHA']
        descrprod = row['DESCRPROD']
        meta_dia_atual = row[dia_atual]
        qtd_apontada = row['QTDAPONTADA']
        total_semana = row['TOTALSEMANA']
        saldo_semana = row['SALDOSEMANA']
        
        if total_semana > 0:
            percentual = (qtd_apontada / total_semana) * 100
        else:
            percentual = 0
            
        dados_processados.append({
            'LINHA': linha,
            'DESCRPROD': descrprod,
            'SEQ': row.get('SEQ', 0),
            'META_DIA': meta_dia_atual,
            'QTDAPONTADA': qtd_apontada,
            'TOTALSEMANA': total_semana,
            'PERC': round(percentual, 1),
            'SALDOSEMANA': saldo_semana,
            'DIA_ATUAL': dia_atual
        })
    
    return pd.DataFrame(dados_processados)

def obter_produtos_por_linha(df):
    produtos_por_linha = {}
    for linha in df['LINHA'].unique():
        produtos = df[df['LINHA'] == linha][['DESCRPROD', 'QTDAPONTADA', 'SEQ']].to_dict('records')
        produtos.sort(key=lambda x: x.get('SEQ', 0))
        produtos_por_linha[linha] = produtos
    return produtos_por_linha

def limitar_texto(texto, max_caracteres=20):
    if len(str(texto)) > max_caracteres:
        return str(texto)[:max_caracteres-3] + "..."
    return str(texto)

def create_gauge_chart(percentual, height=120):
    if percentual >= 85:
        color = "#2878a7"
    elif percentual >= 70:
        color = "#28a745"
    elif percentual >= 50:
        color = "#ffc107"
    else:
        color = "#dc3545"
    
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
                {'range': [50, 70], 'color': '#e9ecef'},
                {'range': [70, 100], 'color': '#dee2e6'}],
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

def create_compact_card(linha_nome, linha_data, produtos_por_linha, product_rotation_index=0):
    dados_linha = linha_data[linha_data['LINHA'] == linha_nome]
    
    total_produzido_linha = dados_linha['QTDAPONTADA'].sum()
    total_objetivo_linha = dados_linha['TOTALSEMANA'].sum()
    percentual_conclusao_linha = (total_produzido_linha / total_objetivo_linha * 100) if total_objetivo_linha > 0 else 0
    
    produtos_da_linha = produtos_por_linha.get(linha_nome, [])
    
    if not produtos_da_linha:
        st.error(f"❌ Nenhum produto encontrado para a linha {linha_nome}")
        return
    
    produto_index = product_rotation_index % len(produtos_da_linha)
    produto_atual = produtos_da_linha[produto_index]
    
    descrprod = produto_atual['DESCRPROD']
    qtd_produzida_produto = produto_atual['QTDAPONTADA']
    
    meta_dia_produto = 0
    for _, row in dados_linha.iterrows():
        if row['DESCRPROD'] == descrprod:
            meta_dia_produto = row['META_DIA']
            break
    
    if percentual_conclusao_linha >= 85:
        cor_borda = "#2878a7"
        status = "✅"
        status_text = "Meta Atingida"
    elif percentual_conclusao_linha >= 70:
        cor_borda = "#28a745"
        status = "✅"
        status_text = "Próximo da Meta"
    elif percentual_conclusao_linha >= 50:
        cor_borda = "#c29201"
        status = "🟡"
        status_text = "Em Andamento"
    else:
        cor_borda = "#dc3545"
        status = "🔴"
        status_text = "Atenção"
    
    max_caracteres_linha = st.session_state.get('max_caracteres_linha', 25)
    max_caracteres_produto = st.session_state.get('max_caracteres_produto', 30)
    
    linha_nome_limitado = limitar_texto(linha_nome, max_caracteres_linha)
    descrprod_limitado = limitar_texto(descrprod, max_caracteres_produto)
    
    with st.container():
        st.markdown(f"""
        <div style="border: 3px solid {cor_borda}; border-radius: 12px; padding: 12px; margin: 8px; background: {cor_borda}20; box-shadow: 0 2px 4px rgba(0,0,0,0.1); height: 80px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <h4 style="color: white; margin: 0; font-size: 24px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 280px;" title="{linha_nome}">{linha_nome_limitado}</h4>
                    <span style="font-size: 12px; background: {cor_borda}20; margin: 8px; border-radius: 12px; color: {cor_borda}; font-weight: bold;">
                        {status} {status_text}
                    </span>
                </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"<div style='font-size: 20px; color: #666; margin-bottom: 8px; line-height: 1.3; margin: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;' title='{descrprod}'>{descrprod_limitado}</div>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="background: #e9ecef; border-radius: 10px; height: 30px; margin: 8px 0; position: relative;">
            <div style="background: {cor_borda}; border-radius: 10px; height: 100%; width: {min(percentual_conclusao_linha, 100)}%; transition: width 0.3s ease;"></div>
            <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; font-size: 26px; font-weight: bold; color: {'white' if percentual_conclusao_linha > 50 else 'black'};">
                {total_produzido_linha:,} / {total_objetivo_linha:,}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            fig = create_gauge_chart(percentual_conclusao_linha)
            st.plotly_chart(fig, use_container_width=True, key=f"gauge_{linha_nome}_{product_rotation_index}")
        with col2:
            st.metric(
                "Produto Atual", 
                f"{qtd_produzida_produto:,}",
                help=f"Produzido: {descrprod}",
                label_visibility="visible"
            )
            st.caption(f"📦 {produto_index + 1}/{len(produtos_da_linha)} produtos")
        
    st.markdown("---")

# Interface principal
st.sidebar.header("📤 Importar Dados")

# SOLUÇÃO CRÍTICA: File uploader que mantém o estado
arquivo = st.sidebar.file_uploader(
    "Carregar planilha Excel",
    type=['xlsx', 'xls'],
    help="Faça upload da planilha com os dados de produção",
    key="file_uploader"
)

# SOLUÇÃO: Quando um novo arquivo é carregado, salvar no session_state
if arquivo is not None:
    if (st.session_state.uploaded_file_name != arquivo.name or 
        st.session_state.uploaded_file is None):
        
        st.session_state.uploaded_file = arquivo
        st.session_state.uploaded_file_name = arquivo.name
        
        # Processar o novo arquivo
        df_importado = importar_excel(arquivo)
        if df_importado is not None:
            st.session_state.df_processado = processar_dados_base_real(df_importado)
            st.session_state.produtos_por_linha = obter_produtos_por_linha(st.session_state.df_processado)
            st.sidebar.success(f"✅ {arquivo.name} carregado com sucesso!")
        else:
            st.sidebar.error("❌ Erro ao importar a planilha")
            st.session_state.df_processado = None
            st.session_state.produtos_por_linha = None

# SOLUÇÃO: Botão para limpar arquivo carregado
if st.session_state.uploaded_file is not None:
    if st.sidebar.button("🗑️ Remover Arquivo Atual"):
        st.session_state.uploaded_file = None
        st.session_state.uploaded_file_name = None
        st.session_state.df_processado = None
        st.session_state.produtos_por_linha = None
        st.rerun()

# Exibir dia atual na sidebar
dia_atual = obter_dia_atual()
st.sidebar.markdown(f"**📅 Dia de Hoje: {dia_atual}**")

# Configurações de caracteres
st.sidebar.header("⚙️ Configurações de Texto")
novo_max_linha = st.sidebar.slider(
    "Máx. caracteres - Nome da Linha",
    min_value=10,
    max_value=50,
    value=st.session_state.max_caracteres_linha
)

novo_max_produto = st.sidebar.slider(
    "Máx. caracteres - Nome do Produto", 
    min_value=10,
    max_value=50,
    value=st.session_state.max_caracteres_produto
)

# Atualizar session_state
st.session_state.max_caracteres_linha = novo_max_linha
st.session_state.max_caracteres_produto = novo_max_produto

# Configuração de rotação e auto-refresh
st.sidebar.header("🔄 Auto-Refresh & Rotação")

auto_refresh = st.sidebar.checkbox("Ativar Auto-Refresh", 
                                  value=st.session_state.auto_refresh,
                                  key="auto_refresh_checkbox")

refresh_interval = st.sidebar.slider("Intervalo (segundos)", 
                                    min_value=5, 
                                    max_value=120, 
                                    value=st.session_state.refresh_interval,
                                    key="refresh_slider")

rotacao_ativa = st.sidebar.checkbox("Ativar rotação de produtos", 
                                   value=st.session_state.rotacao_ativa,
                                   key="rotacao_checkbox")

# Atualizar session_state
st.session_state.auto_refresh = auto_refresh
st.session_state.refresh_interval = refresh_interval
st.session_state.rotacao_ativa = rotacao_ativa

# SOLUÇÃO: Aplicar o auto-refresh apenas se estiver ativado
if st.session_state.auto_refresh:
    # Usar streamlit-autorefresh
    refresh_count = st_autorefresh(interval=st.session_state.refresh_interval * 1000, 
                                  limit=100, 
                                  key="auto_refresh_component")
    
    # Quando o auto-refresh acontecer, atualizar a rotação
    if refresh_count > 0 and st.session_state.rotacao_ativa:
        for linha in st.session_state.get('linhas_filtradas', []):
            if linha not in st.session_state.rotacao_por_linha:
                st.session_state.rotacao_por_linha[linha] = 0
            st.session_state.rotacao_por_linha[linha] += 1

# Botão manual para forçar atualização
if st.sidebar.button("🔄 Forçar Refresh Manual", type="primary"):
    st.session_state.refresh_counter += 1
    if st.session_state.rotacao_ativa:
        for linha in st.session_state.get('linhas_filtradas', []):
            if linha not in st.session_state.rotacao_por_linha:
                st.session_state.rotacao_por_linha[linha] = 0
            st.session_state.rotacao_por_linha[linha] += 1
    st.session_state.last_refresh_time = time.time()
    st.rerun()

# SOLUÇÃO: Carregar dados - Prioridade para arquivo salvo no session_state
if st.session_state.df_processado is not None:
    # Usar dados do arquivo carregado (mantido no session_state)
    df_processado = st.session_state.df_processado
    produtos_por_linha = st.session_state.produtos_por_linha
    
    # Mostrar info do arquivo atual
    st.sidebar.info(f"📊 **Arquivo Atual:** {st.session_state.uploaded_file_name}")
    
else:
    # Dados de exemplo (apenas se não há arquivo carregado)
    @st.cache_data(ttl=60)  # Cache mais longo para dados de exemplo
    def load_data():
        data = []
        linhas_produtos = {
            "VINAGRE 500 1": ["8 - VINAGRE DE ALCOOL 500ML SADIO"],
            "TEMPERO SECO SACHE 1": ["3343 - ALECRIM PC 7G SADIO", "9961 - TEMPERO DO CHEF PC 30G SADIO"],
            "TEMPERO SECO MANUAL 1": ["7488 - PIMENTA PRETA REFIL 40G MR MAKER", "9704 - TEMPERO DO CHEF POTE 130G MR MAKER"]
        }
        
        for linha, produtos in linhas_produtos.items():
            for i, produto in enumerate(produtos):
                total_semana = random.randint(1000, 7000)
                qtd_apontada = random.randint(0, total_semana)
                percentual = (qtd_apontada / total_semana) * 100
                saldo_semana = total_semana - qtd_apontada
                
                data.append({
                    'LINHA': linha,
                    'DESCRPROD': produto,
                    'SEQ': i + 1,
                    'META_DIA': random.randint(100, 1000),
                    'QTDAPONTADA': qtd_apontada,
                    'TOTALSEMANA': total_semana,
                    'PERC': round(percentual, 1),
                    'SALDOSEMANA': saldo_semana,
                    'DIA_ATUAL': dia_atual
                })
        
        return pd.DataFrame(data)
    
    df_processado = load_data()
    produtos_por_linha = obter_produtos_por_linha(df_processado)
    
    st.sidebar.info("📝 **Usando dados de exemplo**")

# Filtros
st.sidebar.header("🔍 Filtros")
status_todos = st.sidebar.checkbox("Todos", value=True, key="todos")
status_target = st.sidebar.checkbox("No Target (≥90%)", value=True, key="target")
status_andamento = st.sidebar.checkbox("Em Andamento (75-89%)", value=True, key="andamento")
status_atencao = st.sidebar.checkbox("Atenção (<75%)", value=True, key="atencao")
buscar_linha = st.sidebar.text_input("🔎 Buscar Linha:")

# Filtrar linhas
linhas_disponiveis = df_processado['LINHA'].unique()
linhas_filtradas = []

for linha in linhas_disponiveis:
    dados_linha = df_processado[df_processado['LINHA'] == linha]
    total_produzido = dados_linha['QTDAPONTADA'].sum()
    total_objetivo = dados_linha['TOTALSEMANA'].sum()
    percentual_linha = (total_produzido / total_objetivo * 100) if total_objetivo > 0 else 0
    
    status_ok = False
    if percentual_linha >= 90 and status_target:
        status_ok = True
    elif 75 <= percentual_linha < 90 and status_andamento:
        status_ok = True
    elif percentual_linha < 75 and status_atencao:
        status_ok = True
    
    if buscar_linha and buscar_linha.lower() not in linha.lower():
        status_ok = False
    
    if status_ok:
        linhas_filtradas.append(linha)

st.session_state.linhas_filtradas = linhas_filtradas

# Indicador visual de auto-refresh
if st.session_state.auto_refresh:
    current_time = time.time()
    time_since_last_refresh = current_time - st.session_state.last_refresh_time
    tempo_restante = max(0, st.session_state.refresh_interval - time_since_last_refresh)
    
    st.markdown(f"""
    <div class="auto-refresh-indicator" title="Auto-Refresh Ativo">
        🔄 {int(tempo_restante)}s
    </div>
    """, unsafe_allow_html=True)

# Organizar em grid
if len(linhas_filtradas) > 0:
    cols = st.columns(4)
    
    for idx, linha in enumerate(sorted(linhas_filtradas)):
        col_idx = idx % 4
        with cols[col_idx]:
            rotation_idx = st.session_state.rotacao_por_linha.get(linha, 0)
            create_compact_card(linha, df_processado, produtos_por_linha, rotation_idx)
else:
    st.warning("ℹ️ Nenhuma linha encontrada com os filtros aplicados.")

# Resumo geral
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Resumo Geral")

total_geral_produzido = df_processado['QTDAPONTADA'].sum()
total_geral_objetivo = df_processado['TOTALSEMANA'].sum()
perc_geral = (total_geral_produzido / total_geral_objetivo * 100) if total_geral_objetivo > 0 else 0

# Estatísticas
linhas_target = 0
linhas_andamento = 0
linhas_atencao = 0

for linha in linhas_disponiveis:
    dados_linha = df_processado[df_processado['LINHA'] == linha]
    total_produzido = dados_linha['QTDAPONTADA'].sum()
    total_objetivo = dados_linha['TOTALSEMANA'].sum()
    percentual_linha = (total_produzido / total_objetivo * 100) if total_objetivo > 0 else 0
    
    if percentual_linha >= 90:
        linhas_target += 1
    elif percentual_linha >= 75:
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

# Informações de sistema
st.sidebar.markdown("---")
st.sidebar.subheader("🔄 Status do Sistema")

if st.session_state.auto_refresh:
    current_time = time.time()
    time_since_last_refresh = current_time - st.session_state.last_refresh_time
    tempo_restante = max(0, st.session_state.refresh_interval - time_since_last_refresh)
    st.sidebar.info(f"**⏱️ Próximo refresh em: {int(tempo_restante)}s**")
else:
    st.sidebar.info("**⏸️ Auto-refresh desativado**")

st.sidebar.metric("Total de produtos", sum(len(prods) for prods in produtos_por_linha.values()))
st.sidebar.metric("Refresh count", st.session_state.refresh_counter)

# Informação sobre o arquivo atual
st.sidebar.markdown("---")
st.sidebar.subheader("💾 Dados Atuais")

if st.session_state.uploaded_file_name:
    st.sidebar.success(f"**Arquivo:** {st.session_state.uploaded_file_name}")
    st.sidebar.info(f"**Linhas carregadas:** {len(df_processado)}")
else:
    st.sidebar.info("**Usando dados de exemplo**")
