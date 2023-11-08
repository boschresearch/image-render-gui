from nicegui import ui, Tailwind
from catharsys.gui.web.widgets.cls_pos_range import CPosRange, EPosRangeStyle


def Func(uiEl: ui.element, fValMin: float, fValMax: float, bMinChanged: bool, bMaxChanged: bool):
    print(f"{fValMin}[{bMinChanged}] -> {fValMax}[{bMaxChanged}]")


# enddef


with ui.column().classes("w-full q-pa-md"):
    uiRange = CPosRange(
        _fMin=0.0,
        _fMax=20.0,
        _fStep=1.0,
        _fValueMin=3.0,
        _fValueMax=5.0,
        _fRangeMin=3.0,
        _fRangeMax=7.0,
        _eStyle=EPosRangeStyle.ROW,
        _sLabel="Frame",
    )
    uiRange = CPosRange(
        _fMin=0.0,
        _fMax=20.0,
        _fStep=1.0,
        _fValueMin=3.0,
        _fValueMax=5.0,
        _fRangeMin=3.0,
        _fRangeMax=7.0,
        _eStyle=EPosRangeStyle.STACKED,
        _sLabel="Frame",
    )
    uiRange = CPosRange(
        _fMin=0.0,
        _fMax=20.0,
        _fStep=1.0,
        _fValueMin=3.0,
        _fValueMax=5.0,
        _fRangeMin=3.0,
        _fRangeMax=7.0,
        _eStyle=EPosRangeStyle.INTEGRATED,
        _sLabel="Frame",
    )

# endwith

ui.run()
