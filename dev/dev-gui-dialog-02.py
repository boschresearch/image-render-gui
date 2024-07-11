from nicegui import ui, Tailwind
from catharsys.gui.web.widgets.cls_message import CMessage, EMessageType

dlgMsg = ui.dialog().props("fullWidth")  # .style("width: 800px; max-width: 1200px;")
with dlgMsg:
    with ui.card().style("width: 700px; max-width: 80vw"):
        ui.label(
            "th poefk awepfok awe pfakwep foka+pewfo a+epfo kawüef küefkpaowekf+paowekf awpefko +apefok a+pewfok a+pefo ka+epfoka+powfekapewokf aewf awef awenfjanwef jkawef"
        )
    # endwith
# endwith
dlgMsg.open()


ui.run()
