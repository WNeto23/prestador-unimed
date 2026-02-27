import flet as ft

def main(page: ft.Page):
    page.title = "Teste Simples"
    page.add(
        ft.Text("Olá mundo!"),
        ft.ElevatedButton("Clique aqui")
    )

ft.app(target=main)