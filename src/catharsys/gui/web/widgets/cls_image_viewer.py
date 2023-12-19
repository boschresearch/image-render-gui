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
from typing import Callable, Optional, Any

from .cls_ui_image import CUiImage

# need to enable OpenExr explicitly
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
import cv2


class CImageViewer:
    def __init__(self):
        self._iImgHeight: int = None
        self._iImgWidth: int = None
        self._uiImage: CUiImage = None
        self._bIsDrawn: bool = False
        self._fScalePower: float = 1.0
        self._uiLabelTitle: ui.label = None
        self._pathImage: Path = None
        self._sTitle: str = None

    # enddef

    @property
    def bIsDrawn(self) -> bool:
        return self._bIsDrawn

    # enddef

    def _OnScaleImage(self, _uiImage: ui.image, _xArgs: events.ValueChangeEventArguments):
        self.ScaleImage(_uiImage, float(_xArgs.value))

    # enddef

    def ScaleImage(self, _uiImage: ui.image, _fScalePower: float):
        self._fScalePower = _fScalePower
        fScale = math.exp(self._fScalePower)
        iW = fScale * self._iImgWidth
        iH = fScale * self._iImgHeight
        _uiImage.style(f"width: {iW}px; height: {iH}px;")

    # enddef

    def UpdateScale(self):
        self.ScaleImage(self._uiImage, self._fScalePower)

    # enddef

    def UpdateImage(
        self,
        _pathImage: Path,
        *,
        _sTitle: Optional[str] = None,
    ):
        self._pathImage = _pathImage
        if _sTitle is not None:
            self._sTitle = _sTitle
        # endif

        if self._uiImage is not None:
            if _pathImage.exists():
                aImage: np.ndarray = cv2.imread(_pathImage.as_posix())
                self._iImgHeight, self._iImgWidth = aImage.shape[0:2]

            else:
                raise RuntimeError(f"Image does not exist: {(_pathImage.as_posix())}")
            # endif

            if _sTitle is not None:
                self._uiLabelTitle.set_text(_sTitle)
            # endif
            self._uiImage.UpdateImage(_pathImage)
            self.UpdateScale()
        # endif

    # enddef

    def DrawImage(
        self,
        _pathImage: Path,
        *,
        _sHeight: str = "80vh",
        _bShowFullscreen: bool = True,
        _sTitle: Optional[str] = "Image Viewer",
        _funcOnClose: Optional[Callable[[None], None]] = None,
    ):
        self._pathImage = _pathImage
        if _sTitle is not None:
            self._sTitle = _sTitle
        # endif

        if _pathImage.exists():
            aImage: np.ndarray = cv2.imread(_pathImage.as_posix())
            self._iImgHeight, self._iImgWidth = aImage.shape[0:2]

        else:
            self._iImgWidth = None
            self._iImgHeight = None
        # endif

        # with ui.card().tight():
        with ui.grid().style(
            "grid-template-columns: 1fr; "
            "grid-template-rows: 30px auto 30px;"
            f"width: 100%; height: {_sHeight};"
            "justify-items: stretch;"
            "background: white;"
            "opacity: 1"
        ):
            with ui.element("q-bar"):
                self._uiLabelTitle = ui.label(_sTitle)
                self._uiLabelTitle.tailwind.text_color("black")
                ui.element("q-space")
                if _bShowFullscreen is True:
                    ui.button(icon="fullscreen", on_click=self._OnFullscreen).props("dense flat")
                # endif
                ui.button(icon="close", on_click=_funcOnClose).props("dense flat")
            # endwith

            self._uiScrollArea = ui.scroll_area()
            self._uiScrollArea.style(
                "height: 100%; width: 100%;"
                # "padding: 5px;"
                "background-color: #8f8f8f;"
                # "opacity: 0.8;"
                "background-image:  repeating-linear-gradient(45deg, #a4a4a4 25%, transparent 25%, transparent 75%, #a4a4a4 75%, #a4a4a4), repeating-linear-gradient(45deg, #a4a4a4 25%, #8f8f8f 25%, #8f8f8f 75%, #a4a4a4 75%, #a4a4a4);"
                "background-position: 0 0, 10px 10px;"
                "background-size: 20px 20px;"
            )
            with self._uiScrollArea:
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
                        self._uiImage = CUiImage(_pathImage).props('fit=cover position="0px 0px"')
                        # uiImg = ui.image(_pathImage).props(
                        #     'fit=cover position="0px 0px"'
                        # )  # .style("position: 50px 100px;")  # .style("max-width: 100%;")

                    # endif
                # endif
            # endwith
            ui.slider(
                min=-2.0,
                max=2.0,
                step=0.01,
                value=0.0,
                on_change=lambda xArgs: self._OnScaleImage(self._uiImage, xArgs),
            ).style("")
            # endwith
        # endwith card
        self._bIsDrawn = True
        self.UpdateScale()

    # enddef

    def GetImageDialog(self, _pathImage: Path, _sTitle: str):
        # print(_pathImage)
        dlgImg = ui.dialog().props("maximized persistent")  # .style("width: 800px; max-width: 1200px;")
        with dlgImg:
            self.DrawImage(
                _pathImage,
                _sTitle=_sTitle,
                _sHeight="100vh",
                _bShowFullscreen=False,
                _funcOnClose=lambda: dlgImg.close(),
            )
        # endwith dialog

        return dlgImg

    # enddef

    def ShowImage(self, _pathImage: Path):
        self.GetImageDialog(_pathImage).open()

    # enddef

    async def AsyncShowImage(self, _pathImage: Path, _sTitle: str):
        await self.GetImageDialog(_pathImage, _sTitle)

    # enddef

    async def _OnFullscreen(self):
        xImgViewer = CImageViewer()
        await xImgViewer.AsyncShowImage(self._pathImage, self._sTitle)
        del xImgViewer

    # enddef

    # def _OnMouse(self, _xArgs: events.MouseEventArguments):
    #     # print(_xArgs)

    #     self._labInfoImage.set_text(f"[{_xArgs.image_x:.1f}, {_xArgs.image_y:.1f}]")
    #     self._labInfoImage.update()

    # # enddef


# endclass
