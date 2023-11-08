from nicegui import ui, Tailwind
from catharsys.gui.web.widgets.cls_range import CRange


def Func(uiEl: ui.element, fValMin: float, fValMax: float, bMinChanged: bool, bMaxChanged: bool):
    print(f"{fValMin}[{bMinChanged}] -> {fValMax}[{bMaxChanged}]")


# enddef


with ui.row().classes("w-full"):
    uiRange = CRange(
        _fMin=0.0,
        _fMax=5.1,
        _fStep=1.0,
        _fValueMin=0.0,
        _fValueMax=4.0,
        _fRangeMin=0.0,
        _fRangeMax=10.0,
        _funcOnChanged=Func,
    )
# endwith

ui.run()
