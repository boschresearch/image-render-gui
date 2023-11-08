###
# Author: Christian Perwass (CR/ADI2.1)
# <LICENSE id="Apache-2.0">
#
#   Image-Render Automation Functions module
#   Copyright 2023 Robert Bosch GmbH and its subsidiaries
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# </LICENSE>
###

import os
import math
from pathlib import Path
from nicegui import ui, Tailwind, events
from catharsys.gui.web.widgets.cls_message import CMessage, EMessageType
import catharsys.plugins.std.util.imgproc as imgproc
import numpy as np

from .cls_ui_image import CUiImage

# need to enable OpenExr explicitly
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
import cv2


class CImageViewer:
    def __init__(self):
        self._iImgHeight: int = None
        self._iImgWidth: int = None

    # enddef

    def _OnScaleImage(self, _uiImage: ui.image, _xArgs: events.ValueChangeEventArguments):
        self.ScaleImage(_uiImage, float(_xArgs.value))

    # enddef

    def ScaleImage(self, _uiImage: ui.image, _fScalePower: float):
        fScale = math.exp(_fScalePower)
        iW = fScale * self._iImgWidth
        iH = fScale * self._iImgHeight
        _uiImage.style(f"width: {iW}px; height: {iH}px;")

    # enddef

    def GetImageDialog(self, _pathImage: Path):
        if _pathImage.exists():
            aImage: np.ndarray = cv2.imread(_pathImage.as_posix())
            self._iImgHeight, self._iImgWidth = aImage.shape[0:2]

        else:
            self._iImgWidth = None
            self._iImgHeight = None
        # endif

        # print(_pathImage)
        dlgImg = ui.dialog().props("maximized persistent")  # .style("width: 800px; max-width: 1200px;")
        with dlgImg:
            # with ui.card().tight():
            with ui.grid().style(
                "grid-template-columns: 1fr; "
                "grid-template-rows: auto 1fr auto;"
                "width: 100%; height: 100%;"
                "justify-items: stretch;"
                "background: white;"
            ):
                with ui.element("q-bar"):
                    ui.label("Image Viewer").tailwind.text_color("black")
                    ui.element("q-space")
                    ui.button(icon="close", on_click=lambda: dlgImg.close()).props("dense flat")
                # endwith
                with ui.scroll_area().style("height: 100%; width: 100%; padding: 5px;"):
                    if not _pathImage.exists():
                        # with ui.column():
                        ui.icon("report_problem", size="xl")
                        ui.label(f"Image path not found: {(_pathImage.as_posix())}")
                        # endwith
                    else:
                        if _pathImage.suffix not in [".png", ".jpg", ".jpeg"]:
                            # with ui.column():
                            ui.icon("report_problem", size="xl")
                            ui.label(f"Image file type '{_pathImage.suffix}' not supported")
                            # endwith
                        else:
                            uiImg = CUiImage(_pathImage).props('fit=cover position="0px 0px"')
                            # uiImg = ui.image(_pathImage).props(
                            #     'fit=cover position="0px 0px"'
                            # )  # .style("position: 50px 100px;")  # .style("max-width: 100%;")

                        # endif
                    # endif
                # endwith
                ui.slider(
                    min=-2.0, max=2.0, step=0.01, value=0.0, on_change=lambda xArgs: self._OnScaleImage(uiImg, xArgs)
                ).style("padding: 5px")
                # endwith
            # endwith card
        # endwith dialog

        return dlgImg

    # enddef

    def ShowImage(self, _pathImage: Path):
        self.GetImageDialog(_pathImage).open()

    # enddef

    async def AsyncShowImage(self, _pathImage: Path):
        await self.GetImageDialog(_pathImage)

    # enddef

    # def _OnMouse(self, _xArgs: events.MouseEventArguments):
    #     # print(_xArgs)

    #     self._labInfoImage.set_text(f"[{_xArgs.image_x:.1f}, {_xArgs.image_y:.1f}]")
    #     self._labInfoImage.update()

    # # enddef


# endclass
