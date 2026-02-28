import flet as ft
import sqlite3
import re
from datetime import datetime
from notificador import Notificador  # Importa a classe real do notificador

# ====================== CORES UNIMED ======================
UNIMED_GREEN = "#007A33"
UNIMED_LIGHT = "#00A651"
UNIMED_DARK = "#004d1f"
UNIMED_BG = "#0f1a14"

# ====================== FORMATAÇÃO AUTOMÁTICA DE DATA ======================
def formatar_data_entrada(texto: str) -> str | None:
    """Aceita: 27022026, 2702/2026, 27/02/2026, 27-02-2026, 1/3/2026 etc."""
    if not texto or not texto.strip():
        return None
    texto = texto.strip().replace("-", "/").replace(" ", "")

    padroes = [
        r"^(\d{2})(\d{2})(\d{4})$",        # 27022026
        r"^(\d{2})(\d{2})/(\d{4})$",       # 2702/2026
        r"^(\d{1,2})/(\d{1,2})/(\d{4})$",  # 27/02/2026 ou 1/3/2026
        r"^(\d{1,2})/(\d{1,2})/(\d{2})$",  # 27/02/26 (assume 20xx)
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

# ====================== BANCO DE DADOS ======================
def init_db():
    conn = sqlite3.connect("prestadores.db")
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS prestadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE,
        nome TEXT,
        email TEXT,
        data_cadastro DATE DEFAULT CURRENT_DATE,
        tipo_prestador TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS datas_envio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_prestador TEXT,
        referencia TEXT,
        faturamento_inicio DATE,
        faturamento_fim DATE,
        recurso_inicio DATE,
        recurso_fim DATE,
        status TEXT DEFAULT 'Ativo'
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS log_envios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_envio DATETIME DEFAULT CURRENT_TIMESTAMP,
        prestador_id INTEGER,
        prestador_nome TEXT,
        referencia TEXT,
        tipo_conta TEXT,
        tipo_notificacao TEXT,
        sucesso INTEGER DEFAULT 1,
        mensagem TEXT,
        FOREIGN KEY (prestador_id) REFERENCES prestadores(id)
    )''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect("prestadores.db")

# ====================== APLICAÇÃO PRINCIPAL ======================
def main(page: ft.Page):
    page.title = "Unimed RV - Gestão de Prestadores Credenciados"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = UNIMED_BG
    page.padding = 30
    page.scroll = ft.ScrollMode.AUTO
    page.window_min_width = 1280
    page.window_min_height = 820
    page.window_width = 1380
    page.window_height = 900

    # Inicializa banco e notificador
    init_db()
    notificador = Notificador()

    # Variáveis de estado
    editando_prestador_id: int | None = None
    editando_data_id: int | None = None

    # ====================== CAMPOS PRESTADORES ======================
    txt_codigo = ft.TextField(
        label="Código", 
        width=180, 
        border_color=UNIMED_GREEN,
        icon=ft.Icons.BADGE
    )
    
    txt_nome = ft.TextField(
        label="Nome do Prestador", 
        width=360, 
        border_color=UNIMED_GREEN,
        icon=ft.Icons.PERSON
    )
    
    txt_email = ft.TextField(
        label="E-mail", 
        width=360, 
        border_color=UNIMED_GREEN,
        icon=ft.Icons.EMAIL
    )
    
    dd_tipo_prestador = ft.Dropdown(
        label="Tipo de Prestador",
        width=340,
        border_color=UNIMED_GREEN,
        icon=ft.Icons.CATEGORY,
        options=[
            ft.dropdown.Option("Prestadores de Terapias"),
            ft.dropdown.Option("Prestadores Credenciados"),
            ft.dropdown.Option("Demais Prestadores"),
        ]
    )

    # ====================== CAMPOS DATAS ======================
    dd_tipo_envio = ft.Dropdown(
        label="Tipo de Prestador",
        width=340,
        border_color=UNIMED_GREEN,
        icon=ft.Icons.CALENDAR_MONTH,
        options=[
            ft.dropdown.Option("Prestadores de Terapias"),
            ft.dropdown.Option("Prestadores Credenciados"),
            ft.dropdown.Option("Demais Prestadores"),
        ]
    )
    
    txt_referencia = ft.TextField(
        label="Referência (ex: Fevereiro/2026)", 
        width=260, 
        border_color=UNIMED_GREEN,
        icon=ft.Icons.CALENDAR_MONTH
    )
    
    dd_status = ft.Dropdown(
        label="Status", 
        width=160, 
        value="Ativo",
        border_color=UNIMED_GREEN,
        icon=ft.Icons.CIRCLE,
        options=[
            ft.dropdown.Option("Ativo"),
            ft.dropdown.Option("Inativo")
        ]
    )

    txt_fat_ini = ft.TextField(
        label="Faturamento Início", 
        width=170, 
        hint_text="26/01/2026", 
        border_color=UNIMED_GREEN,
        icon=ft.Icons.PLAY_ARROW
    )
    
    txt_fat_fim = ft.TextField(
        label="Faturamento Fim", 
        width=170, 
        hint_text="25/02/2026", 
        border_color=UNIMED_GREEN,
        icon=ft.Icons.STOP
    )
    
    txt_rec_ini = ft.TextField(
        label="Recurso Início", 
        width=170, 
        hint_text="07/02/2026", 
        border_color=UNIMED_GREEN,
        icon=ft.Icons.PLAY_ARROW
    )
    
    txt_rec_fim = ft.TextField(
        label="Recurso Fim", 
        width=170, 
        hint_text="25/02/2026", 
        border_color=UNIMED_GREEN,
        icon=ft.Icons.STOP
    )

    # Formatação automática ao sair do campo
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
        columns=[
            ft.DataColumn(ft.Text("Código")),
            ft.DataColumn(ft.Text("Nome")),
            ft.DataColumn(ft.Text("E-mail")),
            ft.DataColumn(ft.Text("Tipo")),
            ft.DataColumn(ft.Text("Data Cad.")),
            ft.DataColumn(ft.Text("Ações")),
        ],
        rows=[],
        width=1200,
    )

    tabela_datas = ft.DataTable(
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
        width=1200,
    )

    tabela_log = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Data/Hora")),
            ft.DataColumn(ft.Text("Prestador")),
            ft.DataColumn(ft.Text("Referência")),
            ft.DataColumn(ft.Text("Tipo Conta")),
            ft.DataColumn(ft.Text("Notificação")),
            ft.DataColumn(ft.Text("Status")),
        ],
        rows=[],
        width=1200,
    )

    # ====================== FUNÇÕES CRUD ======================
    def limpar_campos_prestador():
        nonlocal editando_prestador_id
        txt_codigo.value = ""
        txt_nome.value = ""
        txt_email.value = ""
        dd_tipo_prestador.value = None
        btn_salvar_prestador.text = "Salvar Prestador"
        editando_prestador_id = None
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
        btn_salvar_data.text = "Salvar Datas"
        editando_data_id = None
        page.update()

    def editar_prestador(id: int):
        nonlocal editando_prestador_id
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT codigo, nome, email, tipo_prestador FROM prestadores WHERE id = ?", (id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            editando_prestador_id = id
            txt_codigo.value = row[0]
            txt_nome.value = row[1]
            txt_email.value = row[2]
            dd_tipo_prestador.value = row[3]
            btn_salvar_prestador.text = "Atualizar Prestador"
            page.update()

    def excluir_prestador(id: int):
        def confirmar(e):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM prestadores WHERE id = ?", (id,))
            conn.commit()
            conn.close()
            page.dialog.open = False
            atualizar_tabela_prestadores()
            page.snack_bar = ft.SnackBar(ft.Text("Prestador excluído!", color="green"))
            page.snack_bar.open = True
            page.update()

        page.dialog = ft.AlertDialog(
            title=ft.Text("Confirmar exclusão"),
            content=ft.Text("Tem certeza que deseja excluir este prestador?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(page.dialog, 'open', False) or page.update()),
                ft.TextButton("Excluir", on_click=confirmar),
            ],
        )
        page.dialog.open = True
        page.update()

    def editar_data(id: int):
        nonlocal editando_data_id
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""SELECT tipo_prestador, referencia, faturamento_inicio, 
                                faturamento_fim, recurso_inicio, recurso_fim, status 
                         FROM datas_envio WHERE id = ?""", (id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            editando_data_id = id
            dd_tipo_envio.value = row[0]
            txt_referencia.value = row[1]
            
            # Formata datas se existirem
            if row[2]:
                d = datetime.strptime(row[2], "%Y-%m-%d").date()
                txt_fat_ini.value = d.strftime("%d/%m/%Y")
            if row[3]:
                d = datetime.strptime(row[3], "%Y-%m-%d").date()
                txt_fat_fim.value = d.strftime("%d/%m/%Y")
            if row[4]:
                d = datetime.strptime(row[4], "%Y-%m-%d").date()
                txt_rec_ini.value = d.strftime("%d/%m/%Y")
            if row[5]:
                d = datetime.strptime(row[5], "%Y-%m-%d").date()
                txt_rec_fim.value = d.strftime("%d/%m/%Y")
            
            dd_status.value = row[6]
            btn_salvar_data.text = "Atualizar Datas"
            page.update()

    def excluir_data(id: int):
        def confirmar(e):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM datas_envio WHERE id = ?", (id,))
            conn.commit()
            conn.close()
            page.dialog.open = False
            atualizar_tabela_datas()
            page.snack_bar = ft.SnackBar(ft.Text("Período excluído!", color="green"))
            page.snack_bar.open = True
            page.update()

        page.dialog = ft.AlertDialog(
            title=ft.Text("Confirmar exclusão"),
            content=ft.Text("Tem certeza que deseja excluir este período?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(page.dialog, 'open', False) or page.update()),
                ft.TextButton("Excluir", on_click=confirmar),
            ],
        )
        page.dialog.open = True
        page.update()

    def salvar_prestador(e):
        nonlocal editando_prestador_id
        if not all([txt_codigo.value, txt_nome.value, txt_email.value, dd_tipo_prestador.value]):
            page.snack_bar = ft.SnackBar(ft.Text("Preencha todos os campos!"))
            page.snack_bar.open = True
            page.update()
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if editando_prestador_id:
                cursor.execute("""
                    UPDATE prestadores SET codigo=?, nome=?, email=?, tipo_prestador=?
                    WHERE id=?
                """, (txt_codigo.value, txt_nome.value, txt_email.value, 
                      dd_tipo_prestador.value, editando_prestador_id))
                msg = "Prestador atualizado com sucesso!"
                editando_prestador_id = None
                btn_salvar_prestador.text = "Salvar Prestador"
            else:
                cursor.execute("""
                    INSERT INTO prestadores (codigo, nome, email, tipo_prestador)
                    VALUES (?, ?, ?, ?)
                """, (txt_codigo.value, txt_nome.value, txt_email.value, dd_tipo_prestador.value))
                msg = "Prestador cadastrado com sucesso!"
            
            conn.commit()
            page.snack_bar = ft.SnackBar(ft.Text(msg, color="green"))
            page.snack_bar.open = True
            limpar_campos_prestador()
            atualizar_tabela_prestadores()
            
        except sqlite3.IntegrityError:
            page.snack_bar = ft.SnackBar(ft.Text("Código já existe!"))
            page.snack_bar.open = True
        finally:
            conn.close()
            page.update()

    def salvar_data_envio(e):
        nonlocal editando_data_id
        if not all([dd_tipo_envio.value, txt_referencia.value]):
            page.snack_bar = ft.SnackBar(ft.Text("Preencha tipo e referência!"))
            page.snack_bar.open = True
            page.update()
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Converte datas se fornecidas
            fat_ini = None
            fat_fim = None
            rec_ini = None
            rec_fim = None

            if txt_fat_ini.value:
                try:
                    d = datetime.strptime(txt_fat_ini.value, "%d/%m/%Y").date()
                    fat_ini = d.strftime("%Y-%m-%d")
                except:
                    pass

            if txt_fat_fim.value:
                try:
                    d = datetime.strptime(txt_fat_fim.value, "%d/%m/%Y").date()
                    fat_fim = d.strftime("%Y-%m-%d")
                except:
                    pass

            if txt_rec_ini.value:
                try:
                    d = datetime.strptime(txt_rec_ini.value, "%d/%m/%Y").date()
                    rec_ini = d.strftime("%Y-%m-%d")
                except:
                    pass

            if txt_rec_fim.value:
                try:
                    d = datetime.strptime(txt_rec_fim.value, "%d/%m/%Y").date()
                    rec_fim = d.strftime("%Y-%m-%d")
                except:
                    pass

            if editando_data_id:
                cursor.execute("""
                    UPDATE datas_envio SET 
                        tipo_prestador=?, 
                        referencia=?, 
                        faturamento_inicio=?, 
                        faturamento_fim=?, 
                        recurso_inicio=?, 
                        recurso_fim=?, 
                        status=? 
                    WHERE id=?
                """, (dd_tipo_envio.value, txt_referencia.value, 
                      fat_ini, fat_fim, rec_ini, rec_fim, 
                      dd_status.value, editando_data_id))
                msg = "Datas atualizadas com sucesso!"
                editando_data_id = None
                btn_salvar_data.text = "Salvar Datas"
            else:
                cursor.execute("""
                    INSERT INTO datas_envio 
                    (tipo_prestador, referencia, faturamento_inicio, faturamento_fim,
                     recurso_inicio, recurso_fim, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (dd_tipo_envio.value, txt_referencia.value, 
                      fat_ini, fat_fim, rec_ini, rec_fim, dd_status.value))
                msg = "Datas cadastradas com sucesso!"
            
            conn.commit()
            page.snack_bar = ft.SnackBar(ft.Text(msg, color="green"))
            page.snack_bar.open = True
            limpar_campos_data()
            atualizar_tabela_datas()
            
        except sqlite3.IntegrityError:
            page.snack_bar = ft.SnackBar(ft.Text("Referência já existe para este tipo!"))
            page.snack_bar.open = True
        finally:
            conn.close()
            page.update()

    def testar_notificacoes(e):
        """Executa o notificador real e mostra resultado"""
        try:
            # Mostra loading
            page.snack_bar = ft.SnackBar(ft.Text("Verificando notificações..."), open=True)
            page.update()
            
            # Executa notificador
            notificacoes = notificador.verificar_e_notificar()
            
            # Atualiza tabela de log
            atualizar_tabela_log()
            
            if notificacoes:
                msg = f"✅ {len(notificacoes)} notificação(ões) enviada(s)!"
            else:
                msg = "ℹ️ Nenhuma notificação necessária hoje."
            
            page.snack_bar = ft.SnackBar(ft.Text(msg))
            page.snack_bar.open = True
            
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"❌ Erro: {str(ex)}"))
            page.snack_bar.open = True
        finally:
            page.update()

    def testar_email_direto(e):
        """Teste direto de envio de e-mail"""
        if not txt_email.value:
            page.snack_bar = ft.SnackBar(ft.Text("Digite um e-mail para teste!"))
            page.snack_bar.open = True
            page.update()
            return
        
        try:
            # Cria uma notificação de teste
            html = notificador.criar_card_email(
                titulo="🔧 TESTE DO SISTEMA",
                mensagem=(
                    "Esta é uma mensagem de teste do sistema de notificações da Unimed RV.\n\n"
                    "Se você recebeu este e-mail, o sistema está configurado corretamente!"
                ),
                prestador=txt_nome.value or "Prestador Teste",
                referencia="Teste Sistema",
                tipo_conta="Teste"
            )
            
            sucesso = notificador.enviar_email(
                destinatario=txt_email.value,
                assunto="🔧 Teste do Sistema de Notificações - Unimed RV",
                html_content=html
            )
            
            if sucesso:
                page.snack_bar = ft.SnackBar(ft.Text(f"✅ E-mail enviado para {txt_email.value}!"))
            else:
                page.snack_bar = ft.SnackBar(ft.Text("❌ Falha no envio. Verifique .env"))
            
            page.snack_bar.open = True
            page.update()
            
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {str(ex)}"))
            page.snack_bar.open = True
            page.update()

    # ====================== ATUALIZAÇÃO DAS TABELAS ======================
    def atualizar_tabela_prestadores():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, codigo, nome, email, tipo_prestador, data_cadastro FROM prestadores ORDER BY nome")
        rows = cursor.fetchall()
        conn.close()

        tabela_prestadores.rows.clear()
        for row in rows:
            tabela_prestadores.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(row[1])),
                    ft.DataCell(ft.Text(row[2])),
                    ft.DataCell(ft.Text(row[3])),
                    ft.DataCell(ft.Text(row[4])),
                    ft.DataCell(ft.Text(str(row[5]))),
                    ft.DataCell(ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.EDIT, 
                            icon_color=ft.Colors.BLUE, 
                            tooltip="Editar",
                            on_click=lambda e, rid=row[0]: editar_prestador(rid)
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE, 
                            icon_color=ft.Colors.RED, 
                            tooltip="Excluir",
                            on_click=lambda e, rid=row[0]: excluir_prestador(rid)
                        ),
                    ]))
                ])
            )
        page.update()

    def atualizar_tabela_datas():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""SELECT id, tipo_prestador, referencia, 
                                faturamento_inicio, faturamento_fim, 
                                recurso_inicio, recurso_fim, status 
                         FROM datas_envio 
                         ORDER BY tipo_prestador, referencia""")
        rows = cursor.fetchall()
        conn.close()

        tabela_datas.rows.clear()
        for row in rows:
            # Formata datas para exibição
            fat_ini = datetime.strptime(row[3], "%Y-%m-%d").strftime("%d/%m/%Y") if row[3] else "-"
            fat_fim = datetime.strptime(row[4], "%Y-%m-%d").strftime("%d/%m/%Y") if row[4] else "-"
            rec_ini = datetime.strptime(row[5], "%Y-%m-%d").strftime("%d/%m/%Y") if row[5] else "-"
            rec_fim = datetime.strptime(row[6], "%Y-%m-%d").strftime("%d/%m/%Y") if row[6] else "-"

            # Cor do status
            status_color = ft.Colors.GREEN if row[7] == "Ativo" else ft.Colors.RED
            
            tabela_datas.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(row[1])),
                    ft.DataCell(ft.Text(row[2])),
                    ft.DataCell(ft.Text(fat_ini)),
                    ft.DataCell(ft.Text(fat_fim)),
                    ft.DataCell(ft.Text(rec_ini)),
                    ft.DataCell(ft.Text(rec_fim)),
                    ft.DataCell(ft.Text(row[7], color=status_color)),
                    ft.DataCell(ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.EDIT, 
                            icon_color=ft.Colors.BLUE, 
                            tooltip="Editar",
                            on_click=lambda e, rid=row[0]: editar_data(rid)
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE, 
                            icon_color=ft.Colors.RED, 
                            tooltip="Excluir",
                            on_click=lambda e, rid=row[0]: excluir_data(rid)
                        ),
                    ]))
                ])
            )
        page.update()

    def atualizar_tabela_log():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT data_envio, prestador_nome, referencia, tipo_conta, 
                   tipo_notificacao, sucesso 
            FROM log_envios 
            ORDER BY data_envio DESC LIMIT 50
        """)
        rows = cursor.fetchall()
        conn.close()

        tabela_log.rows.clear()
        for row in rows:
            status_icon = ft.Icons.CHECK_CIRCLE if row[5] else ft.Icons.ERROR
            status_color = ft.Colors.GREEN if row[5] else ft.Colors.RED
            
            tabela_log.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(row[0])[:16] if row[0] else "-")),
                    ft.DataCell(ft.Text(row[1] or "-")),
                    ft.DataCell(ft.Text(row[2] or "-")),
                    ft.DataCell(ft.Text(row[3] or "-")),
                    ft.DataCell(ft.Text(row[4] or "-")),
                    ft.DataCell(
                        ft.Icon(
                            name=status_icon, 
                            color=status_color,
                            size=20
                        )
                    ),
                ])
            )
        page.update()

    # ====================== BOTÕES ======================
    btn_salvar_prestador = ft.ElevatedButton(
        text="Salvar Prestador", 
        icon=ft.Icons.SAVE,
        bgcolor=UNIMED_GREEN, 
        color="white", 
        on_click=salvar_prestador,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
    )
    
    btn_salvar_data = ft.ElevatedButton(
        text="Salvar Datas", 
        icon=ft.Icons.SAVE,
        bgcolor=UNIMED_GREEN, 
        color="white", 
        on_click=salvar_data_envio,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
    )
    
    btn_novo_prestador = ft.TextButton(
        "Novo Prestador", 
        icon=ft.Icons.ADD, 
        on_click=lambda e: limpar_campos_prestador()
    )
    
    btn_nova_data = ft.TextButton(
        "Nova Data", 
        icon=ft.Icons.ADD, 
        on_click=lambda e: limpar_campos_data()
    )
    
    btn_testar_email = ft.ElevatedButton(
        text="Testar E-mail",
        icon=ft.Icons.EMAIL,
        on_click=testar_email_direto,
        bgcolor=ft.Colors.ORANGE,
        color="white",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
    )

    # ====================== ABAS ======================
    aba_prestadores = ft.Column([
        ft.Text("Cadastro de Prestadores", size=24, weight=ft.FontWeight.BOLD, color=UNIMED_LIGHT),
        ft.Container(
            content=ft.Column([
                ft.Row([txt_codigo, txt_nome, txt_email]),
                ft.Row([dd_tipo_prestador]),
                ft.Row([btn_salvar_prestador, btn_novo_prestador, btn_testar_email]),
            ]),
            padding=20,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
            border_radius=12,
        ),
        ft.Divider(color=UNIMED_GREEN, height=30),
        ft.Text("Prestadores Cadastrados", size=18, weight=ft.FontWeight.BOLD),
        ft.Container(
            content=ft.Column([tabela_prestadores], scroll=ft.ScrollMode.AUTO),
            height=420,
            border=ft.border.all(1, UNIMED_GREEN),
            border_radius=12,
            padding=10,
            bgcolor=ft.Colors.with_opacity(0.02, ft.Colors.WHITE),
        )
    ], scroll=ft.ScrollMode.AUTO, spacing=20)

    aba_datas = ft.Column([
        ft.Text("Configuração de Datas de Envio", size=24, weight=ft.FontWeight.BOLD, color=UNIMED_LIGHT),
        ft.Container(
            content=ft.Column([
                ft.Row([dd_tipo_envio, txt_referencia, dd_status]),
                ft.Text("Faturamento de Contas", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([txt_fat_ini, txt_fat_fim]),
                ft.Text("Recurso de Glosas", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([txt_rec_ini, txt_rec_fim]),
                ft.Row([btn_salvar_data, btn_nova_data]),
            ]),
            padding=20,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
            border_radius=12,
        ),
        ft.Divider(color=UNIMED_GREEN, height=30),
        ft.Text("Períodos Cadastrados", size=18, weight=ft.FontWeight.BOLD),
        ft.Container(
            content=ft.Column([tabela_datas], scroll=ft.ScrollMode.AUTO),
            height=420,
            border=ft.border.all(1, UNIMED_GREEN),
            border_radius=12,
            padding=10,
            bgcolor=ft.Colors.with_opacity(0.02, ft.Colors.WHITE),
        )
    ], scroll=ft.ScrollMode.AUTO, spacing=20)

    aba_log = ft.Column([
        ft.Row([
            ft.Text("Log de Notificações", size=24, weight=ft.FontWeight.BOLD, color=UNIMED_LIGHT),
            ft.ElevatedButton(
                text="Testar Notificações Agora", 
                icon=ft.Icons.SEND, 
                on_click=testar_notificacoes, 
                bgcolor=UNIMED_LIGHT,
                color="white",
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
            ),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Container(
            content=ft.Column([tabela_log], scroll=ft.ScrollMode.AUTO),
            height=620,
            border=ft.border.all(1, UNIMED_GREEN),
            border_radius=12,
            padding=10,
            bgcolor=ft.Colors.with_opacity(0.02, ft.Colors.WHITE),
        )
    ], scroll=ft.ScrollMode.AUTO, spacing=20)

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(
                text="Prestadores", 
                icon=ft.Icons.PEOPLE, 
                content=aba_prestadores
            ),
            ft.Tab(
                text="Datas de Envio", 
                icon=ft.Icons.CALENDAR_MONTH, 
                content=aba_datas
            ),
            ft.Tab(
                text="Log", 
                icon=ft.Icons.HISTORY, 
                content=aba_log
            ),
        ],
        divider_color=UNIMED_GREEN,
        indicator_color=UNIMED_LIGHT,
    )

    # AppBar com identidade Unimed
    page.appbar = ft.AppBar(
        title=ft.Text("Unimed RV - Gestão de Prestadores", size=22),
        leading=ft.Icon(ft.Icons.LOCAL_HOSPITAL, color=UNIMED_LIGHT, size=36),
        bgcolor=UNIMED_DARK,
        color="white",
        center_title=False,
        actions=[
            ft.IconButton(ft.Icons.REFRESH, on_click=lambda e: [
                atualizar_tabela_prestadores(),
                atualizar_tabela_datas(),
                atualizar_tabela_log()
            ]),
        ]
    )

    page.add(tabs)

    # Carrega dados iniciais
    atualizar_tabela_prestadores()
    atualizar_tabela_datas()
    atualizar_tabela_log()


if __name__ == "__main__":
    ft.app(target=main)