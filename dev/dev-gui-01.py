from nicegui import ui
from datetime import datetime

# with ui.grid():
#     ui.label("Hello World Again")
#     xSel = ui.select(options=[1, 2, 3, 4], value=2)
#     xSel.props('label="Hello World" stack-label dense options-dense')
# # endwith

label = ui.label()
xTimer = ui.timer(1.0, lambda: label.set_text(f"{datetime.now():%X}"))
ui.button("Activate", on_click=lambda: xTimer.activate())
ui.button("Deactivate", on_click=lambda: xTimer.deactivate())
ui.icon("schedule")
ui.icon("trending_up")
ui.icon("mediation")
ui.icon("done")
ui.run()
