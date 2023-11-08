from nicegui import ui, Tailwind
from catharsys.gui.web.widgets.cls_tabs import CTabs


xTabs = CTabs()
with xTabs.Add(_sName="h", _sLabel="Home", _sIcon="home"):
    ui.label("Home")
# endwith

with xTabs.Add(_sName="a", _sLabel="About", _sIcon="info"):
    ui.label("About")
# endwith

# xTabs.Select("a")
# print(xTabs.sSelected)

ui.button("select a", on_click=lambda: xTabs.Select("a"))
ui.button("hide h", on_click=lambda: xTabs.SetVisibility("h", False))
ui.button("show h", on_click=lambda: xTabs.SetVisibility("h", True))
ui.button("set icon h to 1", on_click=lambda: xTabs.SetIcon("h", "rocket"))
ui.button("set icon h to 2", on_click=lambda: xTabs.SetIcon("h", "rocket_launch"))
ui.run()
