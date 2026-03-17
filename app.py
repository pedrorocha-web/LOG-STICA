import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
from datetime import datetime
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema Logística", layout="centered")

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- IDs DE ACESSO ---
ID_DONO = "62322332399"
ID_MOTORISTA = "76565874204"

# --- FUNÇÃO PARA GERAR PDF ---
def gerar_pdf(dados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Relatório de Viagem", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    for key, value in dados.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

# --- TELA 1: LOGIN ---
if not st.session_state.logado:
    st.title("🚚 Login - Sistema de Logística")
    user_input = st.text_input("Digite seu ID de Acesso", type="password")
    if st.button("Entrar"):
        if user_input == ID_DONO or user_input == ID_MOTORISTA:
            st.session_state.logado = True
            st.session_state.user_id = user_input
            st.rerun()
        else:
            st.error("ID Inválido!")

# --- TELA 2: APLICATIVO ---
else:
    user_id = st.session_state.user_id
    
    # Barra Lateral
    st.sidebar.title("Opções")
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- VISÃO DO DONO ---
    if user_id == ID_DONO:
        st.title("📊 Painel do Proprietário")
        
        try:
            # Lê os dados forçando a atualização (ttl=0)
            df = conn.read(ttl=0)
            
            if df.empty:
                st.info("A planilha está vazia ou ainda não recebeu dados.")
            else:
                st.write("### Relatórios Recebidos")
                st.dataframe(df)

                # Exportar para Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                st.download_button("📥 Baixar Planilha Excel", data=buffer.getvalue(), file_name="relatorio_logistica.xlsx")
        except Exception as e:
            st.error(f"Erro ao ler a planilha: {e}")
            st.info("Verifique se o link nos Secrets e as permissões da planilha estão corretos.")

    # --- VISÃO DO MOTORISTA ---
    else:
        st.title("🚛 Área do Motorista")
        
        with st.form("form_motorista", clear_on_submit=True):
            st.subheader("Preencha as informações do dia")
            
            col1, col2 = st.columns(2)
            with col1:
                rota = st.text_input("Origem / Destino")
                cliente = st.text_input("Cliente")
                km = st.text_input("KM Inicial / Final")
            with col2:
                frete = st.number_input("Frete Bruto (R$)", min_value=0.0)
                posto = st.text_input("Posto")
                litros = st.number_input("Litros Abastecidos", min_value=0.0)
            
            obs = st.text_area("Manutenção / Despesas / Alimentação")
            
            st.warning("Confira os dados antes de enviar. O envio definitivo será feito agora.")
            enviar = st.form_submit_button("🚀 ENVIAR RELATÓRIO AGORA")

            if enviar:
                try:
                    # 1. Cria o registro
                    novo_relatorio = pd.DataFrame([{
                        "Data/Hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Rota": rota,
                        "Cliente": cliente,
                        "KM": km,
                        "Frete": str(frete),
                        "Posto": posto,
                        "Litros": str(litros),
                        "Observações": obs
                    }])
                    
                    # 2. Força a leitura atual da planilha (sem cache)
                    df_atual = conn.read(ttl=0)
                    
                    # 3. Junta os dados (Garante que mesmo que a planilha esteja vazia, funcione)
                    if df_atual is not None:
                        df_final = pd.concat([df_atual, novo_relatorio], ignore_index=True)
                    else:
                        df_final = novo_relatorio
                        
                    # 4. Grava de volta e LIMPA o cache
                    conn.update(data=df_final)
                    st.cache_data.clear() # Esta linha é vital para os dados não "sumirem"
                    
                    st.balloons()
                    st.success("✅ RELATÓRIO SALVO NA PLANILHA!")
                except Exception as e:
                    st.error(f"ERRO DE CONEXÃO: {e}")
                    st.info("Verifique se a planilha está como 'Editor' para 'Qualquer pessoa com o link'.")
