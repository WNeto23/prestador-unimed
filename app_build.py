# ====================== CONFIGURAÇÃO PARA BUILD ======================
import os
import sys

# Força o Flet a não tentar baixar nada
os.environ['FLET_FORCE_LOCAL'] = '1'
os.environ['FLET_CLI_NO_RICH_OUTPUT'] = '1'

# Resto dos imports
import flet as ft
import re
from datetime import datetime, date, timedelta
from pathlib import Path
import asyncio

# ====================== IMPORTAÇÕES DO NEONDB ======================
try:
    from database_neon import neon_db, USAR_NEON
    from psycopg2.extras import RealDictCursor
    print("✅ Módulo NeonDB carregado com sucesso!")
    USAR_NEON = True
except ImportError as e:
    print(f"❌ ERRO CRÍTICO: NeonDB não disponível - {e}")
    print("O sistema precisa do NeonDB para funcionar.")
    sys.exit(1)

# ====================== CORES UNIMED ======================
UNIMED_GREEN = "#007A33"
UNIMED_LIGHT = "#00A651"
UNIMED_DARK = "#004d1f"
UNIMED_BG = "#0f1a14"
UNIMED_GRAY = "#2a3a33"
UNIMED_CARD_BG = "#1e2a24"

# ====================== FUNÇÕES AUXILIARES ======================
def formatar_data_entrada(texto: str) -> str | None:
    if not texto or not texto.strip():
        return None
    texto = texto.strip().replace("-", "/").replace(" ", "")

    padroes = [
        r"^(\d{2})(\d{2})(\d{4})$",
        r"^(\d{2})(\d{2})/(\d{4})$",
        r"^(\d{1,2})/(\d{1,2})/(\d{4})$",
        r"^(\d{1,2})/(\d{1,2})/(\d{2})$",
    ]

    for padrao in padroes:
        match = re.match(padrao, texto)
        if match:
            try:
                g = match.groups()
                dia = g[0].zfill(2)
                mes = g[1].zfill(2)
                ano = g[2]
                if len(ano) == 2:
                    ano = "20" + ano
                dt = datetime(int(ano), int(mes), int(dia))
                return dt.strftime("%d/%m/%Y")
            except ValueError:
                continue
    return None

def get_db_connection():
    """Retorna conexão com o banco (APENAS NeonDB)"""
    return neon_db.get_connection()

def return_db_connection(conn):
    """Devolve conexão ao pool (NeonDB)"""
    if conn:
        neon_db.return_connection(conn)

def init_app_db():
    """Inicializa o banco de dados - NeonDB já cria as tabelas"""
    print("✅ Usando NeonDB - tabelas já verificadas pelo notificador")
    return

# ====================== FUNÇÕES ESPECÍFICAS DO BANCO ======================
def listar_prestadores(filtro=""):
    """Lista prestadores com filtro opcional"""
    query = """
        SELECT id, codigo, nome, email, tipo_prestador, data_cadastro 
        FROM prestadores
    """
    params = []
    
    if filtro:
        query += " WHERE LOWER(codigo) LIKE %s OR LOWER(nome) LIKE %s OR LOWER(email) LIKE %s"
        termo = f"%{filtro}%"
        params = [termo, termo, termo]
    
    query += " ORDER BY nome"
    
    conn = neon_db.get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(query, params)
    results = cursor.fetchall()
    neon_db.return_connection(conn)
    return [(r['id'], r['codigo'], r['nome'], r['email'], r['tipo_prestador'], r['data_cadastro']) for r in results]

def listar_datas_envio(filtro=""):
    """Lista períodos com filtro opcional"""
    query = """
        SELECT id, tipo_prestador, referencia, 
               faturamento_inicio, faturamento_fim, 
               recurso_inicio, recurso_fim, status 
        FROM datas_envio
    """
    params = []
    
    if filtro:
        query += " WHERE LOWER(tipo_prestador) LIKE %s OR LOWER(referencia) LIKE %s"
        termo = f"%{filtro}%"
        params = [termo, termo]
    
    query += " ORDER BY tipo_prestador, referencia DESC"
    
    conn = neon_db.get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(query, params)
    results = cursor.fetchall()
    neon_db.return_connection(conn)
    return [(r['id'], r['tipo_prestador'], r['referencia'], 
            r['faturamento_inicio'], r['faturamento_fim'],
            r['recurso_inicio'], r['recurso_fim'], r['status']) for r in results]

def listar_log_envios(limite=100):
    """Lista logs dos últimos envios"""
    query = """
        SELECT data_envio, prestador_nome, referencia, tipo_conta, 
               tipo_notificacao, sucesso 
        FROM log_envios 
        ORDER BY data_envio DESC LIMIT %s
    """
    conn = neon_db.get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(query, (limite,))
    results = cursor.fetchall()
    neon_db.return_connection(conn)
    return [(r['data_envio'], r['prestador_nome'], r['referencia'], 
            r['tipo_conta'], r['tipo_notificacao'], 1 if r['sucesso'] else 0) for r in results]

def contar_prestadores():
    """Retorna total de prestadores"""
    conn = neon_db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM prestadores")
    result = cursor.fetchone()[0]
    neon_db.return_connection(conn)
    return result

def contar_datas_ativas():
    """Retorna total de períodos ativos"""
    conn = neon_db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM datas_envio WHERE status = 'Ativo'")
    result = cursor.fetchone()[0]
    neon_db.return_connection(conn)
    return result

def contar_falhas_7dias():
    """Retorna falhas nos últimos 7 dias"""
    conn = neon_db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM log_envios 
        WHERE sucesso = FALSE AND data_envio >= CURRENT_DATE - INTERVAL '7 days'
    """)
    result = cursor.fetchone()[0]
    neon_db.return_connection(conn)
    return result

# ====================== FUNÇÕES AUXILIARES DE UI ======================
def criar_badge_status(status):
    """Cria badge colorido para status"""
    if status == "Ativo":
        return ft.Container(
            content=ft.Text("ATIVO", color="white", size=11, weight="bold"),
            bgcolor=UNIMED_GREEN,
            padding=ft.padding.symmetric(vertical=4, horizontal=12),
            border_radius=20,
        )
    else:
        return ft.Container(
            content=ft.Text("INATIVO", color="white", size=11, weight="bold"),
            bgcolor=ft.Colors.RED_700,
            padding=ft.padding.symmetric(vertical=4, horizontal=12),
            border_radius=20,
        )

def criar_badge_notificacao(tipo, sucesso):
    """Cria badge para tipo de notificação"""
    if sucesso:
        return ft.Container(
            content=ft.Text("✅ ENVIADO", color="white", size=11, weight="bold"),
            bgcolor=UNIMED_GREEN,
            padding=ft.padding.symmetric(vertical=4, horizontal=12),
            border_radius=20,
        )
    else:
        return ft.Container(
            content=ft.Text("❌ FALHA", color="white", size=11, weight="bold"),
            bgcolor=ft.Colors.RED_700,
            padding=ft.padding.symmetric(vertical=4, horizontal=12),
            border_radius=20,
        )

def criar_card_metrica(titulo, valor, cor_borda, icone):
    """Cria cards de métricas para dashboard"""
    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(icone, color=cor_borda, size=24),
                ft.Text(titulo, size=14, color=ft.Colors.GREY_400),
            ]),
            ft.Text(str(valor), size=32, weight="bold", color=cor_borda),
        ]),
        bgcolor=UNIMED_CARD_BG,
        border=ft.border.only(left=ft.BorderSide(6, cor_borda)),
        padding=20,
        border_radius=12,
        expand=True,
    )

def criar_quadro_tabela(tabela):
    return ft.Container(
        content=ft.Column(
            [
                ft.ListView(
                    controls=[tabela],
                    expand=True,
                )
            ],
            expand=True,
        ),
        expand=True, 
        border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.WHITE)),
        border_radius=10,
        padding=10,
        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLACK),
    )

# ====================== APLICAÇÃO PRINCIPAL ======================
def main(page: ft.Page):
    page.title = "Unimed RV - Gestão de Prestadores"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = UNIMED_BG
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO
    page.window.min_width = 1000
    page.window.min_height = 700
    page.window.width = 1400
    page.window.height = 900
    page.expand = True

    # Mostra qual banco está sendo usado
    snack_bar = ft.SnackBar(
        content=ft.Text("📦 Conectado ao NeonDB (PostgreSQL)"),
        bgcolor=UNIMED_GREEN
    )
    page.overlay.append(snack_bar)
    snack_bar.open = True
    
    # Inicializa banco
    init_app_db()

    # Importa notificador
    try:
        from notificador import Notificador
        notificador = Notificador()
        print("✅ Notificador carregado com sucesso!")
    except ImportError as e:
        notificador = None
        print(f"⚠️ Notificador não encontrado: {e}")
    except Exception as e:
        notificador = None
        print(f"⚠️ Erro ao carregar notificador: {e}")

    # Variáveis de estado
    editando_prestador_id: int | None = None
    editando_data_id: int | None = None
    filtro_prestadores = ""
    filtro_datas = ""

    # ====================== CAMPOS PRESTADORES ======================
    txt_codigo = ft.TextField(
        label="Código", 
        border_color=UNIMED_GREEN,
        dense=True
    )
    txt_nome = ft.TextField(
        label="Nome do Prestador", 
        border_color=UNIMED_GREEN,
        dense=True
    )
    txt_email = ft.TextField(
        label="E-mail", 
        border_color=UNIMED_GREEN,
        dense=True
    )
    
    dd_tipo_prestador = ft.Dropdown(
        label="Tipo de Prestador",
        border_color=UNIMED_GREEN,
        dense=True,
        options=[
            ft.dropdown.Option("Prestadores de Terapias"),
            ft.dropdown.Option("Prestadores Credenciados"),
            ft.dropdown.Option("Demais Prestadores"),
        ]
    )

    # ====================== CAMPOS DATAS ======================
    dd_tipo_envio = ft.Dropdown(
        label="Tipo de Prestador",
        border_color=UNIMED_GREEN,
        dense=True,
        options=dd_tipo_prestador.options[:]
    )
    
    txt_referencia = ft.TextField(
        label="Referência (ex: Fevereiro/2026)", 
        border_color=UNIMED_GREEN,
        dense=True
    )
    
    dd_status = ft.Dropdown(
        label="Status", 
        value="Ativo",
        border_color=UNIMED_GREEN,
        dense=True,
        options=[
            ft.dropdown.Option("Ativo"),
            ft.dropdown.Option("Inativo")
        ]
    )

    txt_fat_ini = ft.TextField(
        label="Faturamento Início", 
        hint_text="26/01/2026", 
        border_color=UNIMED_GREEN,
        dense=True
    )
    txt_fat_fim = ft.TextField(
        label="Faturamento Fim", 
        hint_text="25/02/2026", 
        border_color=UNIMED_GREEN,
        dense=True
    )
    txt_rec_ini = ft.TextField(
        label="Recurso Início", 
        hint_text="07/02/2026", 
        border_color=UNIMED_GREEN,
        dense=True
    )
    txt_rec_fim = ft.TextField(
        label="Recurso Fim", 
        hint_text="25/02/2026", 
        border_color=UNIMED_GREEN,
        dense=True
    )

    # ====================== CAMPOS DE FILTRO ======================
    txt_filtro_prestadores = ft.TextField(
        label="Filtrar prestadores...",
        hint_text="Nome ou código",
        prefix_icon=ft.Icons.SEARCH,
        border_color=UNIMED_GREEN,
        dense=True,
        expand=True,
        on_change=lambda e: filtrar_tabela_prestadores(e.control.value)
    )
    
    txt_filtro_datas = ft.TextField(
        label="Filtrar períodos...",
        hint_text="Referência ou tipo",
        prefix_icon=ft.Icons.SEARCH,
        border_color=UNIMED_GREEN,
        dense=True,
        expand=True,
        on_change=lambda e: filtrar_tabela_datas(e.control.value)
    )

    # ====================== FORMATAÇÃO DE DATAS ======================
    def on_blur_data(e):
        campo = e.control
        if valor := formatar_data_entrada(campo.value):
            campo.value = valor
            campo.error_text = None
        elif campo.value.strip():
            campo.error_text = "Formato inválido (ex: 27022026)"
        else:
            campo.error_text = None
        campo.update()

    for campo in [txt_fat_ini, txt_fat_fim, txt_rec_ini, txt_rec_fim]:
        campo.on_blur = on_blur_data

    # ====================== TABELAS ======================
    tabela_prestadores = ft.DataTable(
        expand=True,
        columns=[
            ft.DataColumn(ft.Text("Código")),
            ft.DataColumn(ft.Text("Nome")),
            ft.DataColumn(ft.Text("E-mail")),
            ft.DataColumn(ft.Text("Tipo")),
            ft.DataColumn(ft.Text("Data Cad.")),
            ft.DataColumn(ft.Text("Ações")),
        ],
        rows=[],
        heading_row_color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
    )

    tabela_datas = ft.DataTable(
        expand=True,
        columns=[
            ft.DataColumn(ft.Text("Tipo")),
            ft.DataColumn(ft.Text("Referência")),
            ft.DataColumn(ft.Text("Fat. Início")),
            ft.DataColumn(ft.Text("Fat. Fim")),
            ft.DataColumn(ft.Text("Rec. Início")),
            ft.DataColumn(ft.Text("Rec. Fim")),
            ft.DataColumn(ft.Text("Status")),
            ft.DataColumn(ft.Text("Ações")),
        ],
        rows=[],
    )

    tabela_log = ft.DataTable(
        expand=True,
        columns=[
            ft.DataColumn(ft.Text("Data/Hora")),
            ft.DataColumn(ft.Text("Prestador")),
            ft.DataColumn(ft.Text("Referência")),
            ft.DataColumn(ft.Text("Tipo Conta")),
            ft.DataColumn(ft.Text("Notificação")),
            ft.DataColumn(ft.Text("Status")),
        ],
        rows=[],
    )

    # ====================== FUNÇÕES CRUD ======================
    def limpar_campos_prestador():
        nonlocal editando_prestador_id
        txt_codigo.value = ""
        txt_nome.value = ""
        txt_email.value = ""
        dd_tipo_prestador.value = None
        editando_prestador_id = None
        btn_salvar_prestador.text = "Salvar Prestador"
        btn_salvar_prestador.bgcolor = UNIMED_GREEN
        btn_salvar_prestador.update()
        page.update()

    def limpar_campos_data():
        nonlocal editando_data_id
        dd_tipo_envio.value = None
        txt_referencia.value = ""
        txt_fat_ini.value = ""
        txt_fat_fim.value = ""
        txt_rec_ini.value = ""
        txt_rec_fim.value = ""
        dd_status.value = "Ativo"
        editando_data_id = None
        btn_salvar_data.text = "Salvar Datas"
        btn_salvar_data.bgcolor = UNIMED_GREEN
        btn_salvar_data.update()
        page.update()

    async def salvar_prestador_com_feedback(e):
        nonlocal editando_prestador_id
        
        if not all([txt_codigo.value, txt_nome.value, txt_email.value, dd_tipo_prestador.value]):
            snack = ft.SnackBar(content=ft.Text("Preencha todos os campos!"))
            page.overlay.append(snack)
            snack.open = True
            page.update()
            return

        try:
            conn = neon_db.get_connection()
            cursor = conn.cursor()
            
            if editando_prestador_id:
                cursor.execute("""
                    UPDATE prestadores SET codigo=%s, nome=%s, email=%s, tipo_prestador=%s
                    WHERE id=%s
                """, (txt_codigo.value, txt_nome.value, txt_email.value, 
                      dd_tipo_prestador.value, editando_prestador_id))
            else:
                cursor.execute("""
                    INSERT INTO prestadores (codigo, nome, email, tipo_prestador)
                    VALUES (%s, %s, %s, %s)
                """, (txt_codigo.value, txt_nome.value, txt_email.value, dd_tipo_prestador.value))
            
            conn.commit()
            neon_db.return_connection(conn)
            
            msg = "Prestador atualizado!" if editando_prestador_id else "Prestador cadastrado!"
            btn_salvar_prestador.text = "✓ Sucesso!"
            btn_salvar_prestador.bgcolor = ft.Colors.GREEN_700
            btn_salvar_prestador.update()
            
            await asyncio.sleep(1.5)
            
            snack = ft.SnackBar(content=ft.Text(msg))
            page.overlay.append(snack)
            snack.open = True
            limpar_campos_prestador()
            atualizar_tabela_prestadores()
            atualizar_metricas()
            
        except Exception as ex:
            snack = ft.SnackBar(content=ft.Text(f"Erro: {str(ex)}"))
            page.overlay.append(snack)
            snack.open = True
        finally:
            page.update()

    async def salvar_data_com_feedback(e):
        nonlocal editando_data_id
        
        if not all([dd_tipo_envio.value, txt_referencia.value]):
            snack = ft.SnackBar(content=ft.Text("Preencha tipo e referência!"))
            page.overlay.append(snack)
            snack.open = True
            page.update()
            return

        try:
            fat_ini = None; fat_fim = None; rec_ini = None; rec_fim = None

            if txt_fat_ini.value:
                try:
                    d = datetime.strptime(txt_fat_ini.value, "%d/%m/%Y").date()
                    fat_ini = d.strftime("%Y-%m-%d")
                except: pass

            if txt_fat_fim.value:
                try:
                    d = datetime.strptime(txt_fat_fim.value, "%d/%m/%Y").date()
                    fat_fim = d.strftime("%Y-%m-%d")
                except: pass

            if txt_rec_ini.value:
                try:
                    d = datetime.strptime(txt_rec_ini.value, "%d/%m/%Y").date()
                    rec_ini = d.strftime("%Y-%m-%d")
                except: pass

            if txt_rec_fim.value:
                try:
                    d = datetime.strptime(txt_rec_fim.value, "%d/%m/%Y").date()
                    rec_fim = d.strftime("%Y-%m-%d")
                except: pass

            conn = neon_db.get_connection()
            cursor = conn.cursor()
            
            if editando_data_id:
                cursor.execute("""
                    UPDATE datas_envio SET 
                        tipo_prestador=%s, referencia=%s, 
                        faturamento_inicio=%s, faturamento_fim=%s, 
                        recurso_inicio=%s, recurso_fim=%s, status=%s 
                    WHERE id=%s
                """, (dd_tipo_envio.value, txt_referencia.value, 
                      fat_ini, fat_fim, rec_ini, rec_fim, 
                      dd_status.value, editando_data_id))
            else:
                cursor.execute("""
                    INSERT INTO datas_envio 
                    (tipo_prestador, referencia, faturamento_inicio, faturamento_fim,
                     recurso_inicio, recurso_fim, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (dd_tipo_envio.value, txt_referencia.value, 
                      fat_ini, fat_fim, rec_ini, rec_fim, dd_status.value))
            
            conn.commit()
            neon_db.return_connection(conn)
            
            msg = "Datas atualizadas!" if editando_data_id else "Datas cadastradas!"
            btn_salvar_data.text = "✓ Sucesso!"
            btn_salvar_data.bgcolor = ft.Colors.GREEN_700
            btn_salvar_data.update()
            
            await asyncio.sleep(1.5)
            
            snack = ft.SnackBar(content=ft.Text(msg))
            page.overlay.append(snack)
            snack.open = True
            limpar_campos_data()
            atualizar_tabela_datas()
            atualizar_metricas()
            
        except Exception as ex:
            snack = ft.SnackBar(content=ft.Text(f"Erro: {str(ex)}"))
            page.overlay.append(snack)
            snack.open = True
        finally:
            page.update()

    def editar_prestador(id: int):
        nonlocal editando_prestador_id
        
        conn = neon_db.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT codigo, nome, email, tipo_prestador FROM prestadores WHERE id = %s", (id,))
        row = cursor.fetchone()
        neon_db.return_connection(conn)
        
        if row:
            editando_prestador_id = id
            txt_codigo.value = row['codigo']
            txt_nome.value = row['nome']
            txt_email.value = row['email']
            dd_tipo_prestador.value = row['tipo_prestador']
            btn_salvar_prestador.text = "Atualizar Prestador"
            page.update()

    def excluir_prestador(id: int):
        def confirmar(e):
            conn = neon_db.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM prestadores WHERE id = %s", (id,))
            conn.commit()
            neon_db.return_connection(conn)
            
            page.dialog.open = False
            atualizar_tabela_prestadores()
            atualizar_metricas()
            snack = ft.SnackBar(content=ft.Text("Prestador excluído!"))
            page.overlay.append(snack)
            snack.open = True
            page.update()

        page.dialog = ft.AlertDialog(
            title=ft.Text("Confirmar exclusão"),
            content=ft.Text("Tem certeza que deseja excluir este prestador?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(page.dialog, 'open', False) or page.update()),
                ft.ElevatedButton("Excluir", on_click=confirmar, bgcolor=ft.Colors.RED_700, color="white"),
            ],
        )
        page.dialog.open = True
        page.update()

    def editar_data(id: int):
        nonlocal editando_data_id
        
        conn = neon_db.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""SELECT tipo_prestador, referencia, faturamento_inicio, 
                                faturamento_fim, recurso_inicio, recurso_fim, status 
                         FROM datas_envio WHERE id = %s""", (id,))
        row = cursor.fetchone()
        neon_db.return_connection(conn)
        
        if row:
            editando_data_id = id
            dd_tipo_envio.value = row['tipo_prestador']
            txt_referencia.value = row['referencia']
            
            if row['faturamento_inicio']:
                d = datetime.strptime(str(row['faturamento_inicio']), "%Y-%m-%d").date()
                txt_fat_ini.value = d.strftime("%d/%m/%Y")
            if row['faturamento_fim']:
                d = datetime.strptime(str(row['faturamento_fim']), "%Y-%m-%d").date()
                txt_fat_fim.value = d.strftime("%d/%m/%Y")
            if row['recurso_inicio']:
                d = datetime.strptime(str(row['recurso_inicio']), "%Y-%m-%d").date()
                txt_rec_ini.value = d.strftime("%d/%m/%Y")
            if row['recurso_fim']:
                d = datetime.strptime(str(row['recurso_fim']), "%Y-%m-%d").date()
                txt_rec_fim.value = d.strftime("%d/%m/%Y")
            
            dd_status.value = row['status']
            btn_salvar_data.text = "Atualizar Datas"
            page.update()

    def excluir_data(id: int):
        def confirmar(e):
            conn = neon_db.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM datas_envio WHERE id = %s", (id,))
            conn.commit()
            neon_db.return_connection(conn)
            
            page.dialog.open = False
            atualizar_tabela_datas()
            atualizar_metricas()
            snack = ft.SnackBar(content=ft.Text("Período excluído!"))
            page.overlay.append(snack)
            snack.open = True
            page.update()

        page.dialog = ft.AlertDialog(
            title=ft.Text("Confirmar exclusão"),
            content=ft.Text("Tem certeza que deseja excluir este período?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(page.dialog, 'open', False) or page.update()),
                ft.ElevatedButton("Excluir", on_click=confirmar, bgcolor=ft.Colors.RED_700, color="white"),
            ],
        )
        page.dialog.open = True
        page.update()

    # ====================== FUNÇÃO DE TESTE DE E-MAIL ======================
    def testar_email(e):
        if notificador is None:
            snack = ft.SnackBar(content=ft.Text("❌ Notificador não disponível!"))
            page.overlay.append(snack)
            snack.open = True
            page.update()
            return
        
        email_teste = txt_email.value if txt_email.value else None
        nome_teste = txt_nome.value if txt_nome.value else "Prestador Teste"
        
        if not email_teste:
            conn = neon_db.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT email, nome FROM prestadores WHERE email IS NOT NULL AND email != '' LIMIT 1")
            result = cursor.fetchone()
            neon_db.return_connection(conn)
            
            if result:
                email_teste = result['email']
                nome_teste = result['nome']
            else:
                snack = ft.SnackBar(content=ft.Text("❌ Nenhum e-mail disponível para teste!"))
                page.overlay.append(snack)
                snack.open = True
                page.update()
                return
        
        try:
            snack = ft.SnackBar(content=ft.Text("⏳ Enviando e-mail de teste..."))
            page.overlay.append(snack)
            snack.open = True
            page.update()
            
            html = notificador.criar_card_email(
                titulo="🔧 TESTE DO SISTEMA",
                mensagem="Esta é uma mensagem de teste do sistema de notificações da Unimed RV.",
                prestador=nome_teste,
                referencia="Teste Manual",
                tipo_conta="Faturamento Contas",
                data_fim=date.today() + timedelta(days=5),
                dias_restantes=5
            )
            
            sucesso = notificador.enviar_email(
                destinatario=email_teste,
                assunto="🔧 Teste do Sistema - Unimed RV",
                html_content=html
            )
            
            if sucesso:
                snack = ft.SnackBar(content=ft.Text(f"✅ E-mail enviado para {email_teste}!"))
                
                conn = neon_db.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO log_envios 
                    (prestador_id, prestador_nome, referencia, tipo_conta, tipo_notificacao, sucesso, mensagem)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (None, nome_teste, "Teste Manual", "Teste", "Teste_Manual", True, "Teste manual de e-mail"))
                conn.commit()
                neon_db.return_connection(conn)
                
                atualizar_tabela_log()
            else:
                snack = ft.SnackBar(content=ft.Text("❌ Falha no envio. Verifique configurações."))
            
            page.overlay.append(snack)
            snack.open = True
            page.update()
            
        except Exception as ex:
            snack = ft.SnackBar(content=ft.Text(f"❌ Erro: {str(ex)}"))
            page.overlay.append(snack)
            snack.open = True
            page.update()

    # ====================== FUNÇÕES DE FILTRO ======================
    def filtrar_tabela_prestadores(termo: str):
        nonlocal filtro_prestadores
        filtro_prestadores = termo.lower()
        atualizar_tabela_prestadores()

    def filtrar_tabela_datas(termo: str):
        nonlocal filtro_datas
        filtro_datas = termo.lower()
        atualizar_tabela_datas()

    # ====================== FUNÇÕES DE ATUALIZAÇÃO ======================
    def calcular_metricas():
        total_prestadores = contar_prestadores()
        datas_ativas = contar_datas_ativas()
        falhas_7dias = contar_falhas_7dias()
        
        return total_prestadores, datas_ativas, falhas_7dias

    def atualizar_tabela_prestadores():
        results = listar_prestadores(filtro_prestadores)
        
        tabela_prestadores.rows.clear()
        for row in results:
            id_, codigo, nome, email, tipo, data_cad = row
            
            tabela_prestadores.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(codigo, weight="bold")),
                    ft.DataCell(ft.Text(nome)),
                    ft.DataCell(ft.Text(email)),
                    ft.DataCell(ft.Text(tipo)),
                    ft.DataCell(ft.Text(str(data_cad))),
                    ft.DataCell(ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.EDIT, 
                            icon_color=ft.Colors.BLUE_300,
                            tooltip="Editar",
                            on_click=lambda e, rid=id_: editar_prestador(rid)
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE, 
                            icon_color=ft.Colors.RED_300,
                            tooltip="Excluir",
                            on_click=lambda e, rid=id_: excluir_prestador(rid)
                        ),
                    ], spacing=5))
                ])
            )
        
        page.update()

    def atualizar_tabela_datas():
        results = listar_datas_envio(filtro_datas)
        
        tabela_datas.rows.clear()
        hoje = date.today()
        
        for row in results:
            id_, tipo, ref, fat_ini, fat_fim, rec_ini, rec_fim, status = row
            
            fat_ini_str = datetime.strptime(str(fat_ini), "%Y-%m-%d").strftime("%d/%m/%Y") if fat_ini else "-"
            fat_fim_str = datetime.strptime(str(fat_fim), "%Y-%m-%d").strftime("%d/%m/%Y") if fat_fim else "-"
            rec_ini_str = datetime.strptime(str(rec_ini), "%Y-%m-%d").strftime("%d/%m/%Y") if rec_ini else "-"
            rec_fim_str = datetime.strptime(str(rec_fim), "%Y-%m-%d").strftime("%d/%m/%Y") if rec_fim else "-"
            
            if fat_fim and datetime.strptime(str(fat_fim), "%Y-%m-%d").date() > hoje:
                dias_restantes = (datetime.strptime(str(fat_fim), "%Y-%m-%d").date() - hoje).days
                if dias_restantes <= 5:
                    fat_fim_str = f"⚠️ {fat_fim_str}"
            
            tabela_datas.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(tipo)),
                    ft.DataCell(ft.Text(ref, weight="bold")),
                    ft.DataCell(ft.Text(fat_ini_str)),
                    ft.DataCell(ft.Text(fat_fim_str, color=ft.Colors.RED_400 if "⚠️" in fat_fim_str else None)),
                    ft.DataCell(ft.Text(rec_ini_str)),
                    ft.DataCell(ft.Text(rec_fim_str)),
                    ft.DataCell(criar_badge_status(status)),
                    ft.DataCell(ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.EDIT, 
                            icon_color=ft.Colors.BLUE_300,
                            tooltip="Editar",
                            on_click=lambda e, rid=id_: editar_data(rid)
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE, 
                            icon_color=ft.Colors.RED_300,
                            tooltip="Excluir",
                            on_click=lambda e, rid=id_: excluir_data(rid)
                        ),
                    ], spacing=5))
                ])
            )
        
        page.update()

    def atualizar_tabela_log():
        results = listar_log_envios(100)
        
        tabela_log.rows.clear()
        for row in results:
            data, prestador, ref, tipo_conta, notif, sucesso = row
            
            tabela_log.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(data)[:16] if data else "-")),
                    ft.DataCell(ft.Text(prestador or "-")),
                    ft.DataCell(ft.Text(ref or "-", weight="bold")),
                    ft.DataCell(ft.Text(tipo_conta or "-")),
                    ft.DataCell(criar_badge_notificacao(notif, sucesso)),
                    ft.DataCell(
                        ft.Icon(
                            name=ft.Icons.CHECK_CIRCLE if sucesso else ft.Icons.ERROR,
                            color=ft.Colors.GREEN_400 if sucesso else ft.Colors.RED_400,
                            size=20
                        )
                    ),
                ])
            )
        page.update()

    def atualizar_metricas():
        total_prest, datas_ativas, falhas = calcular_metricas()
        
        metricas_row.controls.clear()
        metricas_row.controls.extend([
            criar_card_metrica("Prestadores", total_prest, ft.Colors.BLUE_400, ft.Icons.PEOPLE),
            criar_card_metrica("Períodos Ativos", datas_ativas, UNIMED_GREEN, ft.Icons.CALENDAR_MONTH),
            criar_card_metrica("Falhas (7d)", falhas, ft.Colors.RED_400, ft.Icons.ERROR),
        ])
        page.update()

    # ====================== BOTÕES ======================
    btn_salvar_prestador = ft.ElevatedButton(
        text="Salvar Prestador",
        icon=ft.Icons.SAVE,
        bgcolor=UNIMED_GREEN,
        color="white",
        on_click=salvar_prestador_com_feedback,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
    )
    
    btn_salvar_data = ft.ElevatedButton(
        text="Salvar Datas",
        icon=ft.Icons.SAVE,
        bgcolor=UNIMED_GREEN,
        color="white",
        on_click=salvar_data_com_feedback,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
    )
    
    btn_novo_prestador = ft.ElevatedButton(
        text="Novo Prestador",
        icon=ft.Icons.ADD,
        on_click=lambda e: limpar_campos_prestador()
    )
    
    btn_nova_data = ft.ElevatedButton(
        text="Nova Data",
        icon=ft.Icons.ADD,
        on_click=lambda e: limpar_campos_data()
    )
    
    btn_testar_email = ft.ElevatedButton(
        text="Testar E-mail",
        icon=ft.Icons.EMAIL,
        bgcolor=ft.Colors.ORANGE_400,
        color="white",
        on_click=testar_email,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
    )

    # ====================== CARDS DE MÉTRICAS ======================
    metricas_row = ft.ResponsiveRow([])
    
    total_prest, datas_ativas, falhas = calcular_metricas()
    metricas_row.controls.extend([
        criar_card_metrica("Prestadores", total_prest, ft.Colors.BLUE_400, ft.Icons.PEOPLE),
        criar_card_metrica("Períodos Ativos", datas_ativas, UNIMED_GREEN, ft.Icons.CALENDAR_MONTH),
        criar_card_metrica("Falhas (7d)", falhas, ft.Colors.RED_400, ft.Icons.ERROR),
    ])

    # ====================== ABAS ======================
    aba_prestadores = ft.Column([
        ft.Text("Cadastro de Prestadores", size=24, weight=ft.FontWeight.BOLD, color=UNIMED_LIGHT),
        ft.Container(
            content=ft.Column([
                ft.ResponsiveRow([
                    ft.Column([txt_codigo], col={"sm": 12, "md": 3}),
                    ft.Column([txt_nome], col={"sm": 12, "md": 5}),
                    ft.Column([txt_email], col={"sm": 12, "md": 4}),
                ]),
                ft.ResponsiveRow([
                    ft.Column([dd_tipo_prestador], col={"sm": 12, "md": 6}),
                    ft.Column([btn_salvar_prestador], col={"sm": 6, "md": 2}),
                    ft.Column([btn_novo_prestador], col={"sm": 3, "md": 1}),
                    ft.Column([btn_testar_email], col={"sm": 3, "md": 2}),
                ]),
            ]),
            padding=20,
            bgcolor=UNIMED_CARD_BG,
            border_radius=12,
        ),
        ft.Divider(color=UNIMED_GREEN, height=20),
        ft.ResponsiveRow([
            ft.Column([txt_filtro_prestadores], col={"sm": 12, "md": 12}),
        ]),
        criar_quadro_tabela(tabela_prestadores),
    ], expand=True, spacing=20)

    aba_datas = ft.Column([
        ft.Text("Configuração de Datas de Envio", size=24, weight=ft.FontWeight.BOLD, color=UNIMED_LIGHT),
        ft.Container(
            content=ft.Column([
                ft.ResponsiveRow([
                    ft.Column([dd_tipo_envio], col={"sm": 12, "md": 4}),
                    ft.Column([txt_referencia], col={"sm": 12, "md": 4}),
                    ft.Column([dd_status], col={"sm": 12, "md": 4}),
                ]),
                ft.Text("Faturamento de Contas", size=16, weight=ft.FontWeight.BOLD),
                ft.ResponsiveRow([
                    ft.Column([txt_fat_ini], col={"sm": 6, "md": 3}),
                    ft.Column([txt_fat_fim], col={"sm": 6, "md": 3}),
                ]),
                ft.Text("Recurso de Glosas", size=16, weight=ft.FontWeight.BOLD),
                ft.ResponsiveRow([
                    ft.Column([txt_rec_ini], col={"sm": 6, "md": 3}),
                    ft.Column([txt_rec_fim], col={"sm": 6, "md": 3}),
                ]),
                ft.ResponsiveRow([
                    ft.Column([btn_salvar_data], col={"sm": 6, "md": 3}),
                    ft.Column([btn_nova_data], col={"sm": 6, "md": 3}),
                ]),
            ]),
            padding=20,
            bgcolor=UNIMED_CARD_BG,
            border_radius=12,
        ),
        ft.Divider(color=UNIMED_GREEN, height=20),
        ft.ResponsiveRow([
            ft.Column([txt_filtro_datas], col={"sm": 12, "md": 12}),
        ]),
        criar_quadro_tabela(tabela_datas),
    ], expand=True, spacing=20)

    aba_log = ft.Column([
        ft.Row([
            ft.Text("Log de Notificações", size=24, weight=ft.FontWeight.BOLD, color=UNIMED_LIGHT),
            ft.Row([
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    icon_color=UNIMED_GREEN,
                    tooltip="Atualizar",
                    on_click=lambda e: atualizar_tabela_log()
                ),
                btn_testar_email,
            ]),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        criar_quadro_tabela(tabela_log),
    ], expand=True, spacing=20)

    aba_dashboard = ft.Column([
        ft.Text("Dashboard", size=24, weight=ft.FontWeight.BOLD, color=UNIMED_LIGHT),
        metricas_row,
        ft.Divider(color=UNIMED_GREEN, height=20),
        ft.Text("Últimas Notificações", size=18, weight=ft.FontWeight.BOLD),
        ft.Container(
            content=ft.ListView(
                controls=[tabela_log],
                expand=True,
            ),
            border=ft.border.all(1, UNIMED_GREEN),
            border_radius=12,
            padding=10,
            expand=True,
        ),
    ], expand=True, spacing=20)

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        expand=True,
        tabs=[
            ft.Tab(text="Dashboard", icon=ft.Icons.DASHBOARD, content=aba_dashboard),
            ft.Tab(text="Prestadores", icon=ft.Icons.PEOPLE, content=aba_prestadores),
            ft.Tab(text="Datas de Envio", icon=ft.Icons.CALENDAR_MONTH, content=aba_datas),
            ft.Tab(text="Log", icon=ft.Icons.HISTORY, content=aba_log),
        ],
        divider_color=UNIMED_GREEN,
        indicator_color=UNIMED_LIGHT,
    )

    page.appbar = ft.AppBar(
        title=ft.Text("Unimed RV - Gestão de Prestadores", size=20),
        leading=ft.Icon(ft.Icons.LOCAL_HOSPITAL, color=UNIMED_LIGHT, size=32),
        bgcolor=UNIMED_DARK,
        color="white",
        center_title=False,
        actions=[
            ft.IconButton(
                icon=ft.Icons.REFRESH,
                icon_color=UNIMED_LIGHT,
                tooltip="Atualizar tudo",
                on_click=lambda e: [
                    atualizar_metricas(),
                    atualizar_tabela_prestadores(),
                    atualizar_tabela_datas(),
                    atualizar_tabela_log()
                ]
            ),
        ]
    )

    page.add(tabs)

    # Carrega dados iniciais
    atualizar_metricas()
    atualizar_tabela_prestadores()
    atualizar_tabela_datas()
    atualizar_tabela_log()

if __name__ == "__main__":
    ft.app(main)