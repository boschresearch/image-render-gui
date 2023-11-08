import os
import math
from pathlib import Path
from nicegui import ui, Tailwind, events
from catharsys.gui.web.widgets.cls_message import CMessage, EMessageType
import catharsys.plugins.std.util.imgproc as imgproc
import numpy as np

# need to enable OpenExr explicitly
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
import cv2

pathImage = Path(r"[PATH TO IMAGE]")

aImage: np.ndarray = cv2.imread(pathImage.as_posix())
iImgHeight, iImgWidth = aImage.shape[0:2]


def OnScaleImage(_uiImage: ui.image, _xArgs: events.ValueChangeEventArguments):
    ScaleImage(_uiImage, float(_xArgs.value))


# enddef


def ScaleImage(_uiImage: ui.image, _fScalePower: float):
    fScale = math.exp(_fScalePower)
    iW = fScale * iImgWidth
    iH = fScale * iImgHeight
    _uiImage.style(f"width: {iW}px; height: {iH}px;")


# enddef


dlgMsg = ui.dialog().props("maximized persistent")  # .style("width: 800px; max-width: 1200px;")
with dlgMsg:
    # with ui.card().tight():
    with ui.grid().style(
        "grid-template-columns: 1fr; "
        "grid-template-rows: auto 1fr auto;"
        "width: 100%; height: 100%;"
        "justify-items: stretch;"
    ):
        with ui.element("q-bar"):
            ui.label("Image Viewer")
            ui.element("q-space")
            ui.button(icon="close", on_click=lambda: dlgMsg.close()).props("dense flat")
        # endwith
        with ui.scroll_area().style("height: 100%; width: 100%; padding: 5px;"):
            uiImg = ui.image(pathImage).props(
                'fit=cover position="0px 0px"'
            )  # .style("position: 50px 100px;")  # .style("max-width: 100%;")
        # endwith
        # with ui.card_section().props("row items-center"):
        ui.slider(min=-2.0, max=2.0, step=0.01, value=0.0, on_change=lambda xArgs: OnScaleImage(uiImg, xArgs)).style(
            "padding: 5px"
        )
        # endwith
    # endwith
# endwith
ScaleImage(uiImg, 0.0)
dlgMsg.open()

ui.run()
