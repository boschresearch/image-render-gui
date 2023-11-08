from nicegui import ui, Tailwind

miA = None

bSelected = False


def Select():
    global bSelected, miA

    bSelected = not bSelected
    if bSelected is True:
        miA.set_text("Selected")
    else:
        miA.set_text("Unselected")
    # endif


# enddef


with ui.row().classes("w-full items-center"):
    result = ui.label().classes("mr-auto")
    with ui.button(icon="menu").props("flat"):
        with ui.menu() as menu:
            # with ui.grid(columns=2).classes("w-full").style(
            #     replace="grid-template-columns: 30px auto;justify-content: center;"  # align-items: center;justify-content: center;"
            # ):
            #     ui.icon("rocket", size="30px").tailwind.background_color("blue-400")
            #     # .align_self("center").justify_self("center")
            #     ui.menu_item("Menu item 1", lambda: result.set_text("Selected item 1"))
            # # endwith
            miA = ui.menu_item("Unselected", lambda: Select())
            ui.menu_item("Menu item 2", lambda: result.set_text("Selected item 2"))
            ui.menu_item("Menu item 3 (keep open)", lambda: result.set_text("Selected item 3"), auto_close=False)
            ui.separator()
            ui.menu_item("Close", on_click=menu.close)
        # endwith
    # endwith

# endwith

ui.run()
