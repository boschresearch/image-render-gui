from nicegui import ui, Tailwind

with ui.row().classes("w-full"):
    uiSel = (
        ui.select(options=["a", "b", "c"], label="My Selection")
        .classes("w-auto")
        .style("min-width: 10rem")
        .props("dense options-dense filled bottom-slots")
    )
    with uiSel.add_slot("append"):
        ui.button(icon="add").props("round dense flat")
    # endwith
    with uiSel.add_slot("hint"):
        ui.label("this is nice")
    # endwith
    # Tailwind().min_width("40").width("auto").apply(uiSel)
# endwith

ui.run(dark=True)
