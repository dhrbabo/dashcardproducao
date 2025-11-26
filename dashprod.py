import streamlit as st
import pandas as pd
import random
from datetime import datetime
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
import requests
import io

# Configuração da página
st.set_page_config(page_title="Dashboard - Linhas de Produção", layout="wide")
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

# SOLUÇÃO: Inicialização do session_state para manter os dados
if 'df_processado' not in st.session_state:
    st.session_state.df_processado = None
if 'produtos_por_linha' not in st.session_state:
    st.session_state.produtos_por_linha = None

if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = True  # ✅ AGORA ATIVADO POR PADRÃO
if 'rotation_index' not in st.session_state:
    st.session_state.rotation_index = 0
if 'last_refresh_time' not in st.session_state:
    st.session_state.last_refresh_time = time.time()
if 'max_caracteres_linha' not in st.session_state:
    st.session_state.max_caracteres_linha = 50
if 'max_caracteres_produto' not in st.session_state:
    st.session_state.max_caracteres_produto = 50
if 'rotacao_por_linha' not in st.session_state:
    st.session_state.rotacao_por_linha = {}
if 'refresh_counter' not in st.session_state:
    st.session_state.refresh_counter = 0
if 'refresh_interval' not in st.session_state:
    st.session_state.refresh_interval = 60  # ✅ 60 SEGUNDOS POR PADRÃO
if 'rotacao_ativa' not in st.session_state:
    st.session_state.rotacao_ativa = True
if 'github_url' not in st.session_state:
    st.session_state.github_url = "https://github.com/ALN84/produ/blob/main/backups/dash_prod.csv"
if 'data_source' not in st.session_state:
    st.session_state.data_source = "github"
if 'data_last_updated' not in st.session_state:
    st.session_state.data_last_updated = None
if 'last_github_hash' not in st.session_state:  # ✅ NOVO: Para detectar mudanças no GitHub
    st.session_state.last_github_hash = None

# Funções de negócio
def obter_dia_atual():
    """Retorna o dia da semana atual em português MAIÚSCULO para compatibilidade"""
    dias_semana_ingles = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
    dias_semana_portugues = ['SEGUNDA', 'TERCA', 'QUARTA', 'QUINTA', 'SEXTA', 'SABADO', 'DOMINGO']
    dia_numero = datetime.now().weekday()
    return dias_semana_portugues[dia_numero]

def detectar_coluna_dia(df):
    """Detecta automaticamente qual coluna corresponde ao dia atual"""
    dia_atual = obter_dia_atual()
    
    if dia_atual in df.columns:
        return dia_atual
    
    variacoes = {
        'SEGUNDA': ['SEGUNDA', 'SEG', 'SEGUNDA-FEIRA', 'MONDAY', 'MON'],
        'TERCA': ['TERCA', 'TER', 'TERÇA', 'TERCA-FEIRA', 'TUESDAY', 'TUE'],
        'QUARTA': ['QUARTA', 'QUA', 'QUARTA-FEIRA', 'WEDNESDAY', 'WED'],
        'QUINTA': ['QUINTA', 'QUI', 'QUINTA-FEIRA', 'THURSDAY', 'THU'],
        'SEXTA': ['SEXTA', 'SEX', 'SEXTA-FEIRA', 'FRIDAY', 'FRI'],
        'SABADO': ['SABADO', 'SAB', 'SÁBADO', 'SATURDAY', 'SAT'],
        'DOMINGO': ['DOMINGO', 'DOM', 'SUNDAY', 'SUN']
    }
    
    for coluna in df.columns:
        coluna_upper = str(coluna).upper().strip()
        if dia_atual in variacoes:
            if coluna_upper in variacoes[dia_atual]:
                return coluna
    
    return dia_atual

def importar_csv_github(url):
    """Importa dados de um arquivo CSV no GitHub"""
    try:
        # Para URLs raw do GitHub
        if 'raw.githubusercontent.com' not in url and 'github.com' in url:
            url = url.replace('github.com', 'raw.githubusercontent.com')
            url = url.replace('/blob/', '/')
        
        # Fazer requisição para o arquivo
        response = requests.get(url)
        response.raise_for_status()
        
        # ✅ CALCULAR HASH para detectar mudanças
        current_hash = hash(response.text)
        
        # Ler CSV com ponto e vírgula como separador
        df = pd.read_csv(io.StringIO(response.text), sep=';')
        
        # ✅ ATUALIZADO: Verificar se as colunas necessárias existem (DHAPO é opcional)
        colunas_necessarias = ['LINHA', 'DESCRPROD', 'QTDAPONTADA', 'TOTALSEMANA', 'SALDOSEMANA']
        colunas_faltantes = [col for col in colunas_necessarias if col not in df.columns]
        
        if colunas_faltantes:
            st.error(f"❌ Colunas faltantes no CSV: {colunas_faltantes}")
            return None
        
        # ✅ NOVO: Verificar se a coluna DHAPO existe e avisar se não
        if 'DHAPO' not in df.columns:
            st.warning("⚠️ Coluna DHAPO não encontrada no CSV. Os dados de último apontamento não serão exibidos.")
        
        # Atualizar timestamp e hash
        st.session_state.data_last_updated = time.time()
        st.session_state.last_github_hash = current_hash
        
        return df
        
    except Exception as e:
        st.error(f"Erro ao importar arquivo CSV do GitHub: {e}")
        return None

def verificar_atualizacao_github():
    """Verifica se o arquivo no GitHub foi atualizado"""
    if not st.session_state.auto_refresh or st.session_state.data_source != "github":
        return False
    
    if not st.session_state.github_url:
        return False
    
    try:
        # Converter para raw URL
        url = st.session_state.github_url
        if 'raw.githubusercontent.com' not in url and 'github.com' in url:
            url = url.replace('github.com', 'raw.githubusercontent.com')
            url = url.replace('/blob/', '/')
        
        # Fazer requisição para verificar mudanças
        response = requests.get(url)
        response.raise_for_status()
        
        current_hash = hash(response.text)
        
        # Se é a primeira vez ou se o hash mudou
        if st.session_state.last_github_hash is None or st.session_state.last_github_hash != current_hash:
            return True
            
    except Exception:
        pass
    
    return False

def importar_excel(arquivo):
    try:
        df = pd.read_excel(arquivo)
        st.session_state.data_last_updated = time.time()
        return df
    except Exception as e:
        st.error(f"Erro ao importar arquivo Excel: {e}")
        return None

def processar_dados_base_real(df):
    """Processa os dados usando a coluna correspondente ao dia atual"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    coluna_dia_atual = detectar_coluna_dia(df)
    dia_atual_nome = obter_dia_atual()
    
    dados_processados = []
    
    # ✅ NOVO: Calcular o último DHAPO por linha
    dh_apontamento_por_linha = {}
    if 'DHAPO' in df.columns:
        for linha in df['LINHA'].unique():
            dh_linha = df[df['LINHA'] == linha]['DHAPO']
            # Encontrar o maior DHAPO (mais recente) para a linha
            dh_validos = [dh for dh in dh_linha if pd.notna(dh)]
            if dh_validos:
                try:
                    # Converter para datetime e pegar o mais recente
                    dh_dates = [pd.to_datetime(dh) for dh in dh_validos]
                    dh_apontamento_por_linha[linha] = max(dh_dates)
                except:
                    # Se não conseguir converter, usar o último não-nulo
                    dh_apontamento_por_linha[linha] = dh_validos[-1]
    
    for index, row in df.iterrows():
        try:
            if pd.isna(row['LINHA']) or row['LINHA'] == '':
                continue
                
            linha = str(row['LINHA']).strip()
            descrprod = str(row['DESCRPROD']).strip()
            
            try:
                meta_dia_atual = float(row[coluna_dia_atual]) if pd.notna(row[coluna_dia_atual]) else 0
            except KeyError:
                meta_dia_atual = 0
            
            try:
                qtd_apontada = float(row['QTDAPONTADA']) if pd.notna(row['QTDAPONTADA']) else 0
                total_semana = float(row['TOTALSEMANA']) if pd.notna(row['TOTALSEMANA']) else 0
                saldo_semana = float(row['SALDOSEMANA']) if pd.notna(row['SALDOSEMANA']) else 0
            except ValueError:
                continue
            
            if total_semana > 0:
                percentual = (qtd_apontada / total_semana) * 100
            else:
                percentual = 0
                
            dados_processados.append({
                'LINHA': linha,
                'DESCRPROD': descrprod,
                'SEQ': int(row.get('SEQ', 0)) if pd.notna(row.get('SEQ')) else 0,
                'META_DIA': int(meta_dia_atual),
                'QTDAPONTADA': qtd_apontada,
                'TOTALSEMANA': total_semana,
                'PERC': round(percentual, 1),
                'SALDOSEMANA': saldo_semana,
                'DIA_ATUAL': dia_atual_nome,
                'COLUNA_USADA': coluna_dia_atual,
                'DHAPO_LINHA': dh_apontamento_por_linha.get(linha)  # ✅ NOVO: DHAPO da linha
            })
            
        except Exception:
            continue
    
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
        number = {
            'suffix': '%', 
            'font': {'size': 38},
            'valueformat': '.0f'
        },
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

def obter_cor_status(percentual):
    """Retorna a cor e informações do status baseado no percentual"""
    if percentual >= 85:
        return "#2878a7", "✅", "Meta Atingida", 1
    elif percentual >= 70:
        return "#28a745", "✅", "Próximo da Meta", 2
    elif percentual >= 50:
        return "#ffc107", "🟡", "Em Andamento", 3
    else:
        return "#dc3545", "🔴", "Atenção", 4

def create_compact_card(linha_nome, linha_data, produtos_por_linha, product_rotation_index=0):
    dados_linha = linha_data[linha_data['LINHA'] == linha_nome]
    
    if dados_linha.empty:
        return
    
    total_produzido_linha = dados_linha['QTDAPONTADA'].sum()
    total_objetivo_linha = dados_linha['TOTALSEMANA'].sum()
    percentual_conclusao_linha = (total_produzido_linha / total_objetivo_linha * 100) if total_objetivo_linha > 0 else 0
    
    produtos_da_linha = produtos_por_linha.get(linha_nome, [])
    
    if not produtos_da_linha:
        return
    
    produto_index = product_rotation_index % len(produtos_da_linha)
    produto_atual = produtos_da_linha[produto_index]
    
    descrprod = produto_atual['DESCRPROD']
    qtd_produzida_produto = produto_atual['QTDAPONTADA']
    qtd_objetivo_produto = dados_linha['META_DIA'][dados_linha['DESCRPROD'] == descrprod].sum()
    percentual_produto = qtd_produzida_produto / qtd_objetivo_produto * 100 if qtd_objetivo_produto > 0 else 0
    
    meta_dia_produto = 0
    dia_atual = ""
    
    for _, row in dados_linha.iterrows():
        if row['DESCRPROD'] == descrprod:
            meta_dia_produto = row['META_DIA']
            dia_atual = row['DIA_ATUAL']
            break
    
    # ✅ NOVO: Capturar DHAPO da linha (não do produto)
    dh_apontamento_linha = dados_linha.iloc[0]['DHAPO_LINHA'] if 'DHAPO_LINHA' in dados_linha.columns else None
    
    cor_borda, status, status_text, _ = obter_cor_status(percentual_conclusao_linha)
    
    max_caracteres_linha = st.session_state.get('max_caracteres_linha', 50)
    max_caracteres_produto = st.session_state.get('max_caracteres_produto', 50)
    
    linha_nome_limitado = limitar_texto(linha_nome, max_caracteres_linha)
    descrprod_limitado = limitar_texto(descrprod, max_caracteres_produto)
    
    # ✅ NOVO: Formatar a data/hora do apontamento DA LINHA
    dh_apontamento_formatado = ""
    if dh_apontamento_linha and pd.notna(dh_apontamento_linha):
        try:
            if isinstance(dh_apontamento_linha, str):
                # Tentar converter string para datetime
                dh_apontamento_dt = pd.to_datetime(dh_apontamento_linha)
            else:
                dh_apontamento_dt = dh_apontamento_linha
                
            dh_apontamento_formatado = dh_apontamento_dt.strftime("%d/%m/%Y %H:%M")
        except:
            dh_apontamento_formatado = str(dh_apontamento_linha)
    
    with st.container():
        st.markdown(f"""
        <div style="border: 3px solid {cor_borda}; border-radius: 12px; padding: 12px; margin: 8px; background: {cor_borda}20; box-shadow: 0 2px 4px rgba(0,0,0,0.1); height: 80px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <h4 style="color: white; margin: 0; font-size: 24px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 300px;" title="{linha_nome}">{linha_nome_limitado}</h4>
                    <span style="font-size: 12px; background: {cor_borda}20; margin: 8px; border-radius: 12px; color: {cor_borda}; font-weight: bold;">
                        {status}
                    </span>
                </div>
        """, unsafe_allow_html=True)
        
        
        st.markdown(f"<div style='font-size: 20px; color: #666; margin-bottom: 8px; line-height: 1.0; margin: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;' title='{descrprod}'>{descrprod_limitado}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size: 20px; color: #666; margin-bottom: 8px; line-height: 1.0; margin: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;' title='{descrprod}'>| 🏭: {produto_index + 1}º | ✅: {qtd_produzida_produto:,.0f} | 🎯: {qtd_objetivo_produto:,.0f} | 📊: {percentual_produto:.0f}% |</div>".replace(",", "."), unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: #e9ecef; border-radius: 10px; height: 30px; margin: 8px 0; position: relative;">
            <div style="background: {cor_borda}; border-radius: 10px; height: 100%; width: {min(percentual_conclusao_linha, 100)}%; transition: width 0.3s ease;"></div>
            <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; font-size: 26px; font-weight: bold; color: {'white' if percentual_conclusao_linha > 70 else 'black'};">
                {total_produzido_linha:,.0f} / {total_objetivo_linha:,.0f}
            </div>
        </div>
        """.replace(",", "."), unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            fig = create_gauge_chart(percentual_conclusao_linha)
            st.plotly_chart(fig, use_container_width=True, key=f"gauge_{linha_nome}_{product_rotation_index}")
            st.markdown("""
            <style>
            div[data-testid="stMetricValue"] {
                font-size: 24px !important;
            }
            </style>
            """, unsafe_allow_html=True)

            with col2:            
                if dh_apontamento_formatado:
                    st.metric(
                        "Último Apontamento",
                        dh_apontamento_formatado,
                        label_visibility="visible"
                    )
                else:
                    st.metric(
                        "Último Apontamento",
                        "N/A",
                        label_visibility="visible"
                    )
                st.caption(f"📦 {produto_index + 1}/{len(produtos_da_linha)} produtos")

# ✅ CARREGAMENTO AUTOMÁTICO AO INICIAR
if st.session_state.df_processado is None and st.session_state.github_url:
    with st.spinner("Carregando dados do GitHub..."):
        df_importado = importar_csv_github(st.session_state.github_url)
        if df_importado is not None:
            st.session_state.df_processado = processar_dados_base_real(df_importado)
            st.session_state.produtos_por_linha = obter_produtos_por_linha(st.session_state.df_processado)
            st.session_state.data_last_updated = time.time()

# ✅ VERIFICAÇÃO DE ATUALIZAÇÃO DO GITHUB
if verificar_atualizacao_github():
    df_importado = importar_csv_github(st.session_state.github_url)
    if df_importado is not None:
            st.session_state.df_processado = processar_dados_base_real(df_importado)
            st.session_state.produtos_por_linha = obter_produtos_por_linha(st.session_state.df_processado)
            st.session_state.refresh_counter += 1
            st.session_state.data_last_updated = time.time()
            st.sidebar.success(f"✅ Dados atualizados automaticamente! ({datetime.now().strftime('%H:%M:%S')})")

# Interface principal
st.sidebar.header("📤 Fonte de Dados")

# Seleção da fonte de dados
data_source = st.sidebar.radio(
    "Selecione a fonte de dados:",
    ["GitHub CSV", "Upload Excel"],
    index=0,
    key="data_source_radio"
)

if data_source == "GitHub CSV":
    st.session_state.data_source = "github"
    
    github_url = st.sidebar.text_input(
        "🔗 URL do arquivo CSV no GitHub:",
        value=st.session_state.github_url,
        placeholder="https://github.com/usuario/repositorio/arquivo.csv",
        help="Cole a URL direta do arquivo CSV no GitHub"
    )
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("📥 Carregar do GitHub", type="primary"):
            if github_url:
                with st.spinner("Carregando dados do GitHub..."):
                    df_importado = importar_csv_github(github_url)
                    if df_importado is not None:
                        st.session_state.df_processado = processar_dados_base_real(df_importado)
                        st.session_state.produtos_por_linha = obter_produtos_por_linha(st.session_state.df_processado)
                        st.session_state.github_url = github_url
                        st.session_state.data_last_updated = time.time()
                        st.sidebar.success("✅ Dados carregados do GitHub com sucesso!")
                    else:
                        st.sidebar.error("❌ Erro ao carregar dados do GitHub")
            else:
                st.sidebar.warning("⚠️ Por favor, insira uma URL do GitHub")
    
    with col2:
        if st.session_state.github_url and st.session_state.df_processado is not None:
            if st.button("🔄 Atualizar Dados"):
                with st.spinner("Atualizando dados do GitHub..."):
                    df_importado = importar_csv_github(st.session_state.github_url)
                    if df_importado is not None:
                        st.session_state.df_processado = processar_dados_base_real(df_importado)
                        st.session_state.produtos_por_linha = obter_produtos_por_linha(st.session_state.df_processado)
                        st.session_state.refresh_counter += 1
                        st.session_state.data_last_updated = time.time()
                        st.sidebar.success("✅ Dados atualizados do GitHub!")
                        st.rerun()

else:
    st.session_state.data_source = "upload"
    
    arquivo = st.sidebar.file_uploader(
        "📤 Carregar planilha Excel",
        type=['xlsx', 'xls'],
        help="Faça upload da planilha com os dados de produção"
    )
    
    if arquivo is not None:
        with st.spinner("Processando arquivo Excel..."):
            df_importado = importar_excel(arquivo)
            if df_importado is not None:
                st.session_state.df_processado = processar_dados_base_real(df_importado)
                st.session_state.produtos_por_linha = obter_produtos_por_linha(st.session_state.df_processado)
                st.session_state.data_last_updated = time.time()
                st.sidebar.success(f"✅ {arquivo.name} carregado com sucesso!")

# Botão para limpar dados carregados
if st.session_state.df_processado is not None:
    if st.sidebar.button("🗑️ Limpar Dados Atuais"):
        st.session_state.df_processado = None
        st.session_state.produtos_por_linha = None
        st.session_state.github_url = "https://github.com/ALN84/produ/blob/main/backups/dash_prod.csv"
        st.session_state.data_last_updated = None
        st.session_state.last_github_hash = None
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

st.session_state.max_caracteres_linha = novo_max_linha
st.session_state.max_caracteres_produto = novo_max_produto

# ✅ CONFIGURAÇÃO DE AUTO-REFRESH MELHORADA
st.sidebar.header("🔄 Auto-Refresh & Rotação")

auto_refresh = st.sidebar.checkbox(
    "Ativar Auto-Refresh com atualização de dados", 
    value=st.session_state.auto_refresh,
    help="Atualiza automaticamente os dados do GitHub quando houver mudanças"
)

refresh_interval = st.sidebar.slider(
    "Intervalo de verificação (segundos)", 
    min_value=10, 
    max_value=300, 
    value=st.session_state.refresh_interval,
    help="Intervalo para verificar se o arquivo no GitHub foi atualizado"
)

rotacao_ativa = st.sidebar.checkbox(
    "Ativar rotação de produtos", 
    value=st.session_state.rotacao_ativa
)

st.session_state.auto_refresh = auto_refresh
st.session_state.refresh_interval = refresh_interval
st.session_state.rotacao_ativa = rotacao_ativa

# ✅ AUTO-REFRESH COM ATUALIZAÇÃO GARANTIDA
if st.session_state.auto_refresh:
    refresh_count = st_autorefresh(
        interval=st.session_state.refresh_interval * 1000, 
        limit=100, 
        key="auto_refresh_component"
    )
    
    # ✅ SEMPRE RECARREGAR DADOS DO GITHUB A CADA CICLO
    if refresh_count > 0 and st.session_state.data_source == "github" and st.session_state.github_url:
        # Removido o spinner aqui
        df_importado = importar_csv_github(st.session_state.github_url)
        if df_importado is not None:
            st.session_state.df_processado = processar_dados_base_real(df_importado)
            st.session_state.produtos_por_linha = obter_produtos_por_linha(st.session_state.df_processado)
            st.session_state.last_refresh_time = time.time()
            st.session_state.refresh_counter += 1
            st.session_state.data_last_updated = time.time()
            st.sidebar.success(f"✅ Dados atualizados! ({datetime.now().strftime('%H:%M:%S')})")
    
    # Atualizar rotação de produtos
    if st.session_state.rotacao_ativa:
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

# Carregar dados - Prioridade para dados carregados
if st.session_state.df_processado is not None:
    df_processado = st.session_state.df_processado
    produtos_por_linha = st.session_state.produtos_por_linha
    
    if st.session_state.data_source == "github":
        st.sidebar.info("📊 **Fonte:** GitHub CSV")
        if st.session_state.github_url:
            st.sidebar.caption(f"URL: {st.session_state.github_url[:50]}...")
    else:
        st.sidebar.info("📊 **Fonte:** Arquivo Excel")
    
else:
    @st.cache_data(ttl=60)
    def load_data():
        data = []
        linhas_produtos = {
            "VINAGRE 500 1": ["8 - VINAGRE DE ALCOOL 500ML SADIO"],
            "TEMPERO SECO SACHE 1": ["3343 - ALECRIM PC 7G SADIO", "9961 - TEMPERO DO CHEF PC 30G SADIO"],
            "TEMPERO SECO MANUAL 1": ["7488 - PIMENTA PRETA REFIL 40G MR MAKER", "9704 - TEMPERO DO CHEF POTE 130G MR MAKER"]
        }
        
        dia_atual = obter_dia_atual()
        
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
                    'DIA_ATUAL': dia_atual,
                    'COLUNA_USADA': dia_atual
                })
        
        return pd.DataFrame(data)
    
    df_processado = load_data()
    produtos_por_linha = obter_produtos_por_linha(df_processado)
    
    st.sidebar.info("📝 **Usando dados de exemplo**")

# Restante do código (filtros, grid, resumo) permanece igual...
# [O restante do código permanece exatamente igual...]

# Filtros
st.sidebar.header("🔍 Filtros")
status_todos = st.sidebar.checkbox("Todos", value=True, key="todos")
status_target = st.sidebar.checkbox("No Target (≥90%)", value=True, key="target")
status_andamento = st.sidebar.checkbox("Em Andamento (75-89%)", value=True, key="andamento")
status_atencao = st.sidebar.checkbox("Atenção (<75%)", value=True, key="atencao")
buscar_linha = st.sidebar.text_input("🔎 Buscar Linha:")

# Filtrar e ORDENAR linhas por status (do melhor para o pior)
linhas_disponiveis = df_processado['LINHA'].unique()
linhas_com_status = []

for linha in linhas_disponiveis:
    dados_linha = df_processado[df_processado['LINHA'] == linha]
    total_produzido = dados_linha['QTDAPONTADA'].sum()
    total_objetivo = dados_linha['TOTALSEMANA'].sum()
    percentual_linha = (total_produzido / total_objetivo * 100) if total_objetivo > 0 else 0
    
    # Obter cor e prioridade do status
    _, _, _, prioridade = obter_cor_status(percentual_linha)
    
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
        linhas_com_status.append({
            'nome': linha,
            'percentual': percentual_linha,
            'prioridade': prioridade,
            'cor': obter_cor_status(percentual_linha)[0]
        })

# SOLUÇÃO: Ordenar linhas por status (do melhor para o pior)
# Prioridade: 1 (Azul) > 2 (Verde) > 3 (Amarelo) > 4 (Vermelho)
linhas_ordenadas = sorted(linhas_com_status, key=lambda x: x['prioridade'])

# Extrair apenas os nomes das linhas ordenadas
linhas_filtradas = [linha['nome'] for linha in linhas_ordenadas]

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

# Organizar em grid - AGORA ORDENADO POR STATUS
if len(linhas_filtradas) > 0:
    cols = st.columns(2)
    
    for idx, linha_info in enumerate(linhas_ordenadas):
        linha = linha_info['nome']
        col_idx = idx % 2
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
    
    # ✅ MOSTRAR SE HÁ ATUALIZAÇÕES DETECTADAS
def verificar_atualizacao_github():
    if not st.session_state.auto_refresh or st.session_state.data_source != "github":
        return False
    
    if not st.session_state.github_url:
        return False
    
    try:
        # ✅ SEMPRE RECARREGAR - abordagem mais simples
        current_time = time.time()
        
        # Verificar se passou tempo suficiente desde a última atualização
        if hasattr(st.session_state, 'last_github_check'):
            time_since_last_check = current_time - st.session_state.last_github_check
            if time_since_last_check < st.session_state.refresh_interval:
                return False
        
        st.session_state.last_github_check = current_time
        
        # ✅ SEMPRE RETORNAR TRUE para forçar atualização a cada ciclo
        # Isso garante que sempre vamos verificar mudanças
        st.sidebar.info("🔍 Verificando GitHub...")
        return True
            
    except Exception as e:
        st.sidebar.error(f"Erro ao verificar GitHub: {e}")
    
    return False

# Legenda das cores
st.sidebar.markdown("---")
st.sidebar.subheader("🎨 Legenda de Status")
st.sidebar.markdown("""
- **🔵 Azul**: Meta Atingida (≥85%)
- **🟢 Verde**: Próximo da Meta (70-84%)
- **🟡 Amarelo**: Em Andamento (50-69%)
- **🔴 Vermelho**: Atenção (<50%)
""")
