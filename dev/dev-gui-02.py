from nicegui import ui, Tailwind
import catharsys.api as capi
from catharsys.gui.web.util.cls_action_handler import CActionHandler
from catharsys.gui.web.widgets.cls_job_info import CJobInfo


wsX = capi.CWorkspace()
wsX.PrintInfo()
# prjX = wsX.Project("gui/dev-01")
prjX = wsX.Project("anytruth/test-01")
prjX.PrintActions()
actX = prjX.Action("render/std")

xActHandler = CActionHandler(_xAction=actX)

uiGrid = ui.grid()
Tailwind().width("full").apply(uiGrid)
xJobInfo = CJobInfo(_uiGrid=uiGrid, _xActHandler=xActHandler)

# uiLabelTime = ui.label()
# uiLabelStatus = ui.label()
# uiTimer = ui.timer(1.0, lambda: uiLabelTime.set_text(f"{datetime.now():%X}"))

# ui.button("Activate", on_click=lambda: uiTimer.activate())
# ui.button("Deactivate", on_click=lambda: uiTimer.deactivate())
# ui.button("Create Config", on_click=functools.partial(Launch, xActHandler, uiLabelStatus))

ui.run()
