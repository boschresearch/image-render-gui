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
import enum
import asyncio
import functools
import concurrent
from datetime import datetime
from pathlib import Path
from nicegui import ui, Tailwind, events
from typing import Callable, Optional, Any

import ison
from anybase import config
from anybase import file as anyfile

from catharsys.api.products.cls_variant_group_products import CVariantGroupProducts
from catharsys.config.cls_variant_group import CVariantGroup
from catharsys.api.products.cls_path_structure import CPathStructure
from catharsys.api.products.cls_group import CArtefactType
from catharsys.api.products.cls_view_dim import EViewDimType
from catharsys.api.products.cls_product_view import CProductView, CViewDimNode

from .cls_pos_range import CPosRange, EPosRangeStyle
from ..util.cls_thumbnails import CThumbnails
from .cls_message import CMessage, EMessageType
from .cls_image_viewer import CImageViewer


class ESpecialSelectIds(str, enum.Enum):
    ALL = "* All"


# enddef


class CVariantGroupProductView:
    def __init__(
        self,
        *,
        _uiRow: ui.row,
        _xVariantGroup: CVariantGroup,
        _funcOnClose: Optional[Callable[[None], None]] = None,
    ):
        self._uiRowMain: ui.row = _uiRow
        self._xVariantGroup: CVariantGroup = _xVariantGroup
        self._xProdView = CProductView(CVariantGroupProducts(_xVariantGroup=_xVariantGroup))

        self._funcOnClose: Optional[Callable[[None], None]] = _funcOnClose

        self._xMessage = CMessage()
        self._xMessage.uiMain = self._uiRowMain
        self._xImageViewer = CImageViewer()
        self._bIsValid: bool = False

        self._iBlockOnChangeSelectGroup: int = 0
        self._iBlockOnChangeSelectGroupVar: int = 0
        self._iBlockOnChangeSelectArtVar: int = 0
        self._iBlockOnCheckArtType: int = 0
        self._iBlockScanArtefacts: int = 0
        self._iBlockUpdateProductView: int = 0

        self._lGrpVarValueLists: list[list[str]] = None
        self._dicArtVarValueLists: dict[str, list[list[str]]] = None

        self._dicGrpVarSelectUi: dict[str, ui.select] = None
        self._dicArtVarSelectUi: dict[str, dict[str, ui.element]] = None

        self._bShowPixinMessage: bool = True

        self._lViewDimGridColors: list[str] = ["rgb(150, 150, 150)", "rgb(160,160,160)", "rgb(170,170,170)"]
        # self._lViewDimGridColors: list[str] = ["primary", "secondary", "primary"]
        # self._lViewDimGridColors: list[str] = ["rgb(224 242 254)", "rgb(186 230 253)", "rgb(125 211 252)"]

        self._dicVgGrpVarSel: dict = dict()
        self._dicVgArtTypeVarSel: dict = dict()
        self._dicVgViewDimNamesSel: dict[str, list[str]] = dict()
        self._dicVgArtTypeViewDimNamesSel: dict[str, dict[str, list[str]]] = dict()

        self._pathSettingsDir = self._xVariantGroup.pathGroup / ".gui"
        self._pathSettingsDir.mkdir(parents=True, exist_ok=True)

        self._pathSettings = self._pathSettingsDir / "product_view_settings.json"
        # print(self._pathSettings)
        if self._pathSettings.exists():
            self._dicSettings = anyfile.LoadJson(self._pathSettings)
            self._dicVgGrpVarSel = self._dicSettings.get("dicVgGrpVarSel", self._dicVgGrpVarSel)
            self._dicVgArtTypeVarSel = self._dicSettings.get("dicVgArtTypeVarSel", self._dicVgArtTypeVarSel)
            self._dicVgViewDimNamesSel = self._dicSettings.get("dicVgViewDimNamesSel", self._dicVgViewDimNamesSel)
            self._dicVgArtTypeViewDimNamesSel = self._dicSettings.get(
                "dicVgArtTypeViewDimNamesSel", self._dicVgArtTypeViewDimNamesSel
            )
            # print(self._dicSettings)
        else:
            self._dicSettings = dict()
        # enddef

        self._xParser = ison.Parser({})

        pathThumbnails: Path = _xVariantGroup.xProject.xConfig.pathOutput / "thumbnails" / _xVariantGroup.sGroup
        pathThumbnails.mkdir(parents=True, exist_ok=True)

        self._xThumbnails = CThumbnails(
            _pathThumbnails=pathThumbnails, _pathMain=_xVariantGroup.xProject.xConfig.pathMain
        )
        self._UpdateThumbImageStyle()
        self.OnCreate()

    # enddef

    # ##########################################################################################################
    def __del__(self):
        self.CleanUp()

    # enddef

    # ##########################################################################################################
    def SaveSettings(self):
        self._dicSettings["dicVgGrpVarSel"] = self._dicVgGrpVarSel
        self._dicSettings["dicVgArtTypeVarSel"] = self._dicVgArtTypeVarSel
        self._dicSettings["dicVgViewDimNamesSel"] = self._dicVgViewDimNamesSel
        self._dicSettings["dicVgArtTypeViewDimNamesSel"] = self._dicVgArtTypeViewDimNamesSel

        anyfile.SaveJson(self._pathSettings, self._dicSettings, iIndent=4)

    # enddef

    # ##########################################################################################################
    def CleanUp(self):
        self.SaveSettings()

    # enddef

    # ##########################################################################################################
    def OnClose(self):
        self.CleanUp()
        if self._funcOnClose is not None:
            self._funcOnClose()
        # endif

    # enddef

    # ##########################################################################################################
    def OnCreate(self):
        self._uiRowMain.clear()
        with self._uiRowMain:
            ui.label("Initializing product view...")
            ui.spinner("ball", size="xl")
            ui.timer(0.2, self.Create, once=True)
        # endwith

    # enddef

    # ##########################################################################################################
    def Create(self):
        try:
            pathProd: Path = self._xVariantGroup.xProject.xConfig.pathLaunch / "production.json5"
            if not pathProd.exists():
                self._uiRowMain.clear()
                with self._uiRowMain:
                    with ui.column():
                        ui.label("Production data definition file missing at path:")
                        ui.markdown(f"`{(pathProd.as_posix())}`")
                    # endwith

                    with ui.row().classes("w-full"):
                        ui.button("Retry", on_click=self.Create)

                        # Close Button if handler is available
                        if self._funcOnClose is not None:
                            self._butClose = ui.button(icon="close", on_click=self.OnClose).classes("ml-auto")
                        else:
                            self._butClose = None
                        # endif
                    # endwith
                # endwith
            else:
                self._xProdView.FromFile(pathProd)

                self._iBlockOnChangeSelectGroup += 1
                try:
                    self._uiRowMain.clear()
                    with self._uiRowMain:
                        with ui.element("q-list").props("padding").classes("w-full"):
                            # with ui.column().classes("w-full"):
                            # ui.label(f"Production View")
                            with ui.row().classes("w-full").style("padding-bottom: 0.5em"):
                                lGroups = self._xProdView.lGroups
                                self._uiSelGrp = self._CreateSelectUi(
                                    _lOptions=self._xProdView.dicGroupKeyNames,
                                    _sLabel="View Group",
                                    _xValue=lGroups[0],
                                    _funcOnChange=self._OnChangeSelectGroup,
                                )
                                Tailwind().min_width("100px").apply(self._uiSelGrp)
                                if self._xProdView.iGroupCount == 1:
                                    self._uiSelGrp.set_visibility(False)
                                # endif
                                self._uiButScan = ui.button(
                                    "Scan Filesystem", on_click=lambda: self.ScanArtefacts(_bForceRescan=True)
                                )
                                self._uiLabelScan = ui.label("")
                                self._UpdateScanCacheLabel()
                                self._uiSpinScan = ui.spinner("dots", size="xl", color="primary")
                                self._uiSpinScan.set_visibility(False)

                                # Close Button if handler is available
                                if self._funcOnClose is not None:
                                    self._butClose = ui.button(icon="close", on_click=lambda: self.OnClose()).classes(
                                        "ml-auto"
                                    )
                                else:
                                    self._butClose = None
                                # endif
                            # endwith

                            with ui.expansion("Product Selection", icon="description").props(
                                "switch-toggle-side default-opened expand-separator"
                            ).classes("w-full"):
                                self._uiRowGroup = ui.row().classes("w-full").style("padding-bottom: 0.5em")
                                with self._uiRowGroup:
                                    ui.label("Scanning for artefacts...")
                                # endwith
                                self._uiRowArtSel = ui.row().classes("w-full").style("padding-bottom: 0.5em")
                            # endwith expansion

                            # ui.separator()

                            with ui.expansion("View Settings", icon="description").props(
                                "switch-toggle-side default-opened expand-separator"
                            ).classes("w-full"):
                                self._uiRowViewDim = (
                                    ui.row().classes("w-full").style("padding-bottom: 0.5em;padding-top: 0.5em")
                                )

                            # endwith expansion

                            # ui.separator()

                            with ui.row().classes("w-full").style("padding-top: 0.5em; padding-bottom: 0.5em"):
                                self._uiButUpdateView = ui.button("Update View", on_click=self._OnUpdateProductView)
                                self._CreateSelectUi(
                                    _lOptions=["32", "64", "128", "256", "512"],
                                    _xValue=str(self._xThumbnails.iTargetWidth),
                                    _sLabel="Image Preview Size",
                                    _funcOnChange=self._OnChangeImagePreviewSize,
                                )
                                self._uiSelMaxColsPerRowTop = self._CreateSelectUi(
                                    _lOptions=[str(x) for x in range(2, 21)],
                                    _xValue="10",
                                    _sLabel="Max columns in top row",
                                )
                                self._uiSelMaxColsPerRow = self._CreateSelectUi(
                                    _lOptions=[str(x) for x in range(2, 21)],
                                    _xValue="10",
                                    _sLabel="Max columns per row",
                                )
                            # endwith
                            self._uiRowViewArt = ui.row().classes("w-full")

                        # endwith column
                    # endwith
                    ui.timer(0.1, self.ScanArtefacts, once=True)
                    self._bIsValid = True
                finally:
                    self._iBlockOnChangeSelectGroup -= 1
                # endtry

            # endif
        except Exception as xEx:
            self._uiRowMain.clear()
            with self._uiRowMain:
                with ui.column().classes("w-full") as colMain:
                    colMain.style("position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);")

                    sText: str = self._xMessage.GetExceptionText("Error initializing product viewer", xEx)
                    lLines: list[str] = sText.splitlines()

                    ui.icon("thunderstorm", size="xl").tailwind.align_self("center")

                    logX = ui.log().classes("h-80")
                    logX.tailwind.width("3/4").background_color("slate-400").align_self("center")
                    for sLine in lLines:
                        logX.push(sLine)
                    # endfor

                    with ui.row() as uiButRow:
                        uiButRow.tailwind.align_self("center")
                        ui.button("Retry", on_click=self.Create)
                        # Close Button if handler is available
                        if self._funcOnClose is not None:
                            self._butClose = ui.button("Close", on_click=lambda: self._funcOnClose())
                        # endif
                    # endwith
                # endwith
            # endwith
        # endtry

        self._uiRowMain.update()

    # enddef

    # #############################################################################################
    def _CloseMenuItemFromEvent(self, _xArgs: events.ClickEventArguments):
        # Async message handler for menu items only work properly, if the menu item
        # does not use the "auto_close" feature. So, we have to close the menu item
        # explicitly, here.
        if isinstance(_xArgs.sender, ui.menu_item):
            uiItem: ui.menu_item = _xArgs.sender
            uiItem.menu.close()
        # endif

    # enddef

    # ##########################################################################################################
    def _OnChangeImagePreviewSize(self, _xArgs: events.ValueChangeEventArguments):
        iSize: int = int(_xArgs.value)
        self._xThumbnails.iTargetWidth = iSize
        self._UpdateThumbImageStyle()
        self.UpdateProductView()

    # enddef

    # ##########################################################################################################
    def _CreateSelectUi(
        self,
        *,
        _lOptions: list,
        _sLabel: str,
        _xValue: Any,
        _bMultiple: bool = False,
        _funcOnChange: Callable[..., None] = None,
    ) -> ui.select:
        return (
            ui.select(options=_lOptions, label=_sLabel, value=_xValue, multiple=_bMultiple, on_change=_funcOnChange)
            .props("dense options-dense filled")
            .classes("w-auto")
            .style("min-width: 10rem")
        )

    # enddef

    # ##########################################################################################################
    def _GetScanCacheFilename(self, _sGroup: str) -> Path:
        return self._xVariantGroup.pathVariants / "_cache" / f"fs-scan-{_sGroup}.pickle"

    # enddef

    # ##########################################################################################################
    def _GetScanCacheFileDateTimeString(self, _sGroup: str) -> Optional[str]:
        pathScanCache: Path = self._GetScanCacheFilename(_sGroup)
        if not pathScanCache.exists():
            return None
        # endif

        fTime: float = os.path.getmtime(pathScanCache.as_posix())
        dtFile = datetime.utcfromtimestamp(fTime)

        return dtFile.strftime("%d.%m.%Y, %H:%M:%S")

    # enddef

    # ##########################################################################################################
    def _UpdateScanCacheLabel(self):
        sSelGrp = str(self._uiSelGrp.value)
        sDateTime = self._GetScanCacheFileDateTimeString(sSelGrp)
        self._uiLabelScan.set_text(f"Last scan: {sDateTime}")

    # enddef

    # ##########################################################################################################
    async def ScanArtefacts(self, *, _bForceRescan: bool = False):
        if self._iBlockScanArtefacts == 0:
            self._iBlockScanArtefacts += 1
            self._uiButScan.disable()
            self._uiButUpdateView.disable()
            # self._uiButScan.set_visibility(False)
            self._uiSpinScan.set_visibility(True)
            try:
                sSelGrp = str(self._uiSelGrp.value)
                pathScanCache: Path = self._GetScanCacheFilename(sSelGrp)
                if pathScanCache.exists() and _bForceRescan is False:
                    xLoop = asyncio.get_running_loop()
                    with concurrent.futures.ThreadPoolExecutor() as xPool:
                        await xLoop.run_in_executor(xPool, lambda: self._xProdView.DeserializeScan(pathScanCache))
                    # endwith
                else:
                    self._uiLabelScan.set_text("Scanning...")
                    pathScanCache.parent.mkdir(parents=True, exist_ok=True)

                    xLoop = asyncio.get_running_loop()
                    with concurrent.futures.ThreadPoolExecutor() as xPool:
                        await xLoop.run_in_executor(xPool, lambda: self._xProdView.ScanArtefacts(_sGroupId=sSelGrp))
                        await xLoop.run_in_executor(xPool, lambda: self._xProdView.SerializeScan(pathScanCache))
                    # endwith
                    self._UpdateScanCacheLabel()
                # endif
                self.UpdateGroup()
            except Exception as xEx:
                self._xMessage.ShowException("Error scanning artefacts", xEx)

            finally:
                self._uiSpinScan.set_visibility(False)
                # self._uiButScan.set_visibility(True)
                self._uiButUpdateView.enable()
                self._uiButScan.enable()
                self._iBlockScanArtefacts -= 1
            # endtry

        # endif

    # enddef

    # ##########################################################################################################
    def _OnChangeSelectGroup(self, _xArgs: events.ValueChangeEventArguments):
        if self._iBlockOnChangeSelectGroup == 0:
            self.UpdateGroup()
        # enddef

    # enddef

    # ##########################################################################################################
    def _CreateCallback_OnChangeGrpVarSelectUi(
        self, _sVarId: str, _funcOnChange: Callable[[str, events.ValueChangeEventArguments], None]
    ) -> Callable:
        def Callback(_xArgs: events.ValueChangeEventArguments):
            _funcOnChange(_sVarId, _xArgs)

        # enddef
        return Callback

    # enddef

    # ##########################################################################################################
    def _CreateCallback_OnChangeArtTypeSelectUi(
        self, _sArtTypeId: str, _funcOnChange: Callable[[str, str, events.ValueChangeEventArguments], None]
    ) -> Callable:
        def Callback(_sVarId: str, _xArgs: events.ValueChangeEventArguments):
            _funcOnChange(_sArtTypeId, _sVarId, _xArgs)

        # enddef
        return Callback

    # enddef

    # ##########################################################################################################
    def _CreatePathVarSelectUi(
        self,
        *,
        _xPathStruct: CPathStructure,
        _lVarValueLists: list[list[str]],
        _lVarLabelLists: list[list[str]],
        _dicVarSel: dict[str, list[str]],
        _funcOnChange: Optional[Callable[[str, events.ValueChangeEventArguments], None]] = None,
    ) -> dict[str, ui.select]:
        dicVarSelectUi: dict[str, ui.select] = dict()
        sVarId: str
        lValues: list[str]

        for sVarId, lValues, lLabels in zip(_xPathStruct.lPathVarIds, _lVarValueLists, _lVarLabelLists):
            if len(lValues) <= 1:
                continue
            # endif
            lSel: list[str] = _dicVarSel.get(sVarId)

            dicOptions = {ESpecialSelectIds.ALL: "All"}
            dicOptions.update({k: v for k, v in zip(lValues, lLabels)})

            if lSel is None:
                lSel = [ESpecialSelectIds.ALL]
            else:
                lSel = [x for x in lSel if x in dicOptions]
                if len(lSel) == 0:
                    lSel = [ESpecialSelectIds.ALL]
                # endif
            # endif
            _dicVarSel[sVarId] = lSel

            xPathVar = _xPathStruct.dicVars[sVarId]
            dicVarSelectUi[sVarId] = self._CreateSelectUi(
                _lOptions=dicOptions,
                _sLabel=xPathVar.sName,
                _bMultiple=True,
                _xValue=lSel,
                _funcOnChange=self._CreateCallback_OnChangeGrpVarSelectUi(sVarId, _funcOnChange),
            )
        # endfor

        return dicVarSelectUi

    # enddef

    # ##########################################################################################################
    def UpdateGroup(self):
        self._iBlockOnChangeSelectGroup += 1
        self._iBlockOnChangeSelectGroupVar += 1
        try:
            sSelGrp = str(self._uiSelGrp.value)
            self._xProdView.SelectGroup(sSelGrp)

            if sSelGrp not in self._dicVgGrpVarSel:
                self._dicVgGrpVarSel[sSelGrp] = dict()
                self._dicVgArtTypeVarSel[sSelGrp] = dict()
                self._dicVgViewDimNamesSel[sSelGrp] = []
                self._dicVgArtTypeViewDimNamesSel[sSelGrp] = dict()
            # endif

            if self._xProdView.bHasGroupData is False:
                self._uiRowGroup.clear()
                with self._uiRowGroup:
                    ui.label("No data found")
                # endwith
                self._xMessage.ShowMessage(
                    "No data found. Try scanning the filesystem again", _eType=EMessageType.WARNING, _bDialog=False
                )
            else:
                self._uiRowGroup.clear()
                with self._uiRowGroup:
                    self._dicGrpVarSelectUi = self._CreatePathVarSelectUi(
                        _xPathStruct=self._xProdView.xGrpPathStruct,
                        _lVarValueLists=self._xProdView.lGrpVarValueLists,
                        _lVarLabelLists=self._xProdView.lGrpVarLabelLists,
                        _dicVarSel=self._dicVgGrpVarSel[sSelGrp],
                        _funcOnChange=self._OnChangeSelectGroupVar,
                    )
                # endwith group row

                self.UpdateArtefactSelection()
            # endif
        except Exception as xEx:
            self._xMessage.ShowException("Error updating group", xEx)

        finally:
            self._iBlockOnChangeSelectGroup -= 1
            self._iBlockOnChangeSelectGroupVar -= 1
        # endtry

    # enddef

    # ##########################################################################################################
    def _CheckVarSelectUi(self, _xArgs: events.ValueChangeEventArguments, *, _xSel: Optional[ui.select] = None):
        xSel: ui.select = _xArgs.sender if _xSel is None else _xSel

        if len(_xArgs.value) == 0 or _xArgs.value[-1] == ESpecialSelectIds.ALL:
            xSel.set_value([ESpecialSelectIds.ALL])
        elif ESpecialSelectIds.ALL in _xArgs.value:
            xSel.set_value([_xArgs.value[-1]])
        # endif

    # enddef

    # ##########################################################################################################
    def _OnChangeSelectGroupVar(self, _sVarId: str, _xArgs: events.ValueChangeEventArguments):
        if self._iBlockOnChangeSelectGroupVar == 0:
            self._iBlockOnChangeSelectGroupVar += 1
            self._CheckVarSelectUi(_xArgs)

            sSelGrp = str(self._uiSelGrp.value)
            self._dicVgGrpVarSel[sSelGrp][_sVarId] = _xArgs.sender.value

            self._iBlockOnChangeSelectGroupVar -= 1

            self.UpdateArtefactSelection()
        # enddef

    # enddef

    # ##########################################################################################################
    def _GetSelectedUiValues(
        self,
        *,
        _dicVarSelectUi: dict[str, ui.element],
        _lVarValueLists: list[list[str]],
        _lVarIds: list[str],
    ) -> list[list[str]]:
        lVarSelValueLists: list[list[str]] = []
        # lVarSelLabelLists: list[list[str]] = []
        sVarId: str
        lVarValues: list[str]
        # lVarLabels: list[str]
        for sVarId, lVarValues in zip(_lVarIds, _lVarValueLists):
            uiSelVar: ui.select = _dicVarSelectUi.get(sVarId)
            if uiSelVar is None:
                lVarSelValueLists.append(lVarValues)
                continue
            # endif
            lSelValues: list[str] = uiSelVar.value
            if ESpecialSelectIds.ALL in lSelValues:
                lVarSelValueLists.append(lVarValues)
            else:
                lVarSelValueLists.append(lSelValues)
                # try:
                #     lLabelList = [uiSelVar.options[x] for x in lSelValues]
                # except Exception as xEx:
                #     sMsg = f"sVarId: {sVarId}\n lSelValue: {lSelValues}\n lVarValues: {lVarValues}\n lVarLabels: {lVarLabels}\n"
                #     self._xMessage.ShowException(sMsg, xEx)
                # # endtry
            # endif
        # endfor
        return lVarSelValueLists

    # enddef

    # ##########################################################################################################
    def UpdateArtefactSelection(self):
        self._iBlockOnChangeSelectArtVar += 1
        try:
            lSelGrpVarValueLists = self._GetSelectedUiValues(
                _dicVarSelectUi=self._dicGrpVarSelectUi,
                _lVarValueLists=self._xProdView.lGrpVarValueLists,
                _lVarIds=self._xProdView.lGrpPathVarIds,
            )

            self._xProdView.SetSelectedGroupVarValueLists(lSelGrpVarValueLists)

            # print(f"self._dicArtVarValueLists: {self._dicArtVarValueLists}")
            # print(f"self._dicArtVarTypeLists: {self._dicArtVarTypeLists}")

            self._dicArtVarSelectUi: dict[str, dict[str, ui.element]] = dict()

            sSelGrp = str(self._uiSelGrp.value)
            dicArtTypeVarSel: dict[str, dict[str, list[str]]] = self._dicVgArtTypeVarSel[sSelGrp]

            self._uiRowArtSel.clear()
            with self._uiRowArtSel:
                with ui.column().classes("w-full"):
                    uiRowArtTypeNoVars = ui.row().classes("w-full")
                    uiColArtType = ui.column().classes("w-full")

                    dicSelArtTypeVarId: dict[str, list[str]] = {}
                    xArtType: CArtefactType
                    for xArtType, lArtVarValueLists, lArtVarLabelLists in self._xProdView.ArtefactVarListsItems():
                        dicVarSel: dict[str, list[str]] = dicArtTypeVarSel.get(xArtType.sId)
                        if dicVarSel is None:
                            dicArtTypeVarSel[xArtType.sId] = dict()
                            dicVarSel = dicArtTypeVarSel[xArtType.sId]
                        # endif

                        self._dicArtVarSelectUi[xArtType.sId] = dict()
                        dicVarSelectUi = self._dicArtVarSelectUi[xArtType.sId]
                        iMaxValCnt: int = max([len(x) for x in lArtVarValueLists])
                        # print(f"{xArtType.sName} [{iMaxValCnt}]: {lArtVarValueLists}")

                        if iMaxValCnt <= 1:
                            # print(f"Single Value Var: {xArtType.sName}")
                            with uiRowArtTypeNoVars:
                                dicVarSelectUi["__checkbox"] = ui.checkbox(
                                    xArtType.sName, value=True, on_change=self._OnCheckArtType
                                )
                            # endwith
                        else:
                            with uiColArtType:
                                with ui.row():
                                    dicVarSelectUi["__checkbox"] = ui.checkbox(
                                        xArtType.sName, value=True, on_change=self._OnCheckArtType
                                    )
                                    dicPathVarSelUi = self._CreatePathVarSelectUi(
                                        _xPathStruct=xArtType.xPathStruct,
                                        _lVarValueLists=lArtVarValueLists,
                                        _lVarLabelLists=lArtVarLabelLists,
                                        _dicVarSel=dicVarSel,
                                        _funcOnChange=self._CreateCallback_OnChangeArtTypeSelectUi(
                                            xArtType.sId, self._OnChangeSelectArtVar
                                        ),
                                    )
                                    dicVarSelectUi.update(dicPathVarSelUi)

                                    dicSelArtTypeVarId[xArtType.sId] = list(dicPathVarSelUi.keys())
                                # endwith row
                            # endwith
                        # endif has more than one variable value
                    # endfor artefact types
                    # ui.separator()
                    # self._uiRowViewDim = ui.row().classes("w-full")

                # endwith column
            # endwith artefact selection row

            self._xProdView.SetSelectedArtefactVariableIds(dicSelArtTypeVarId)
            self.UpdateViewDims()
        except Exception as xEx:
            self._xMessage.ShowException("Error updating artefact selection", xEx)

        finally:
            self._iBlockOnChangeSelectArtVar -= 1
        # endtry

    # enddef

    # ##########################################################################################################
    def _OnCheckArtType(self, _xArgs: events.ValueChangeEventArguments):
        if self._iBlockOnCheckArtType == 0:
            self._iBlockOnCheckArtType += 1
            try:
                xCheck: ui.checkbox = _xArgs.sender
                if xCheck.value is False:
                    bHasSelected = False
                    for dicVarSelectUi in self._dicArtVarSelectUi.values():
                        uiEl: ui.checkbox = dicVarSelectUi["__checkbox"]
                        if uiEl.value is True:
                            bHasSelected = True
                            break
                        # endif
                    # endfor
                    if bHasSelected is False:
                        for dicVarSelectUi in self._dicArtVarSelectUi.values():
                            uiEl: ui.checkbox = dicVarSelectUi["__checkbox"]
                            if uiEl != xCheck:
                                uiEl.set_value(True)
                            # endif
                        # endfor
                    # endif
                # endif

                self.UpdateViewDims()
            except Exception as xEx:
                self._xMessage.ShowException("Error selecting artefact type", xEx)

            finally:
                self._iBlockOnCheckArtType -= 1
            # endtry
        # endif

    # enddef

    # ##########################################################################################################
    def _OnChangeSelectArtVar(self, _sArtTypeId: str, _sVarId: str, _xArgs: events.ValueChangeEventArguments):
        if self._iBlockOnChangeSelectArtVar == 0:
            self._iBlockOnChangeSelectArtVar += 1
            self._CheckVarSelectUi(_xArgs)

            # Ensure that common artefact variables are consistent over all artefacts
            # sSrcArtTypeId: str = None
            # sSrcArtVarId: str = None
            # uiEl: ui.element = None

            # # First we need to find the artefact type id and variable id of the sender
            # for sArtTypeId, dicSelArtVarUi in self._dicArtVarSelectUi.items():
            #     if sArtTypeId.startswith("__"):
            #         continue
            #     # endif
            #     for sArtVarId, uiEl in dicSelArtVarUi.items():
            #         if uiEl == _xArgs.sender:
            #             sSrcArtTypeId = sArtTypeId
            #             sSrcArtVarId = sArtVarId
            #             break
            #         # endif
            #     # endfor

            #     if sSrcArtTypeId is not None:
            #         break
            #     # endif
            # # endfor

            # Now we set the modified value at all other artefacts with the same variable

            sSelGrp = str(self._uiSelGrp.value)
            dicArtTypeVarSel = self._dicVgArtTypeVarSel[sSelGrp]

            lArtTypes = self._xProdView._dicSelCommonArtVarTypes.get(_sVarId)
            if lArtTypes is not None:
                for sArtTypeId in lArtTypes:
                    dicSelArtVarUi = self._dicArtVarSelectUi[sArtTypeId]
                    dicVarSel = dicArtTypeVarSel[sArtTypeId]

                    xEl = dicSelArtVarUi.get(_sVarId)
                    if xEl is None:
                        continue
                    # endif
                    xSel: ui.select = xEl
                    xSel.set_value(_xArgs.value)
                    self._CheckVarSelectUi(_xArgs, _xSel=xSel)
                    dicVarSel[_sVarId] = xSel.value
                # endfor
            # endif

            self._iBlockOnChangeSelectArtVar -= 1
            self.UpdateViewDims()
        # enddef

    # enddef

    # ##########################################################################################################
    def _CreateCallback_OnChangeViewDimSelectUi(self, _iDimIdx: int) -> Callable:
        def Callback(_xArgs: events.ValueChangeEventArguments):
            self._OnChangeViewDimSelectUi(_iDimIdx, _xArgs)

        # enddef
        return Callback

    # enddef

    # ##########################################################################################################
    def UpdateViewDims(self):
        self._xProdView.ClearArtefactVarSelection()

        # Find the artefact variables where more than one value is selected.
        for sArtTypeId, dicSelArtVarUi in self._dicArtVarSelectUi.items():
            uiCheck: ui.checkbox = dicSelArtVarUi["__checkbox"]
            if uiCheck.value is False:
                continue
            # endif

            # xArtType: CArtefactType = self._xProdGrp.dicArtTypes[sArtTypeId]
            lArtPathVarIds = self._xProdView.GetArtefactPathVarIds(sArtTypeId)
            lArtVarValueLists = self._xProdView.dicArtVarValueLists[sArtTypeId]

            lSelArtVarValueLists = self._GetSelectedUiValues(
                _dicVarSelectUi=dicSelArtVarUi,
                _lVarValueLists=lArtVarValueLists,
                _lVarIds=lArtPathVarIds,
            )
            self._xProdView.SetSelectedArtefactVarValueListsForType(sArtTypeId, lSelArtVarValueLists)
        # endfor

        self._xProdView.UpdateArtefactVarSelection()
        self._xProdView.UpdateViewDimNames()

        # Create the lists of view dimension selectors
        self._lViewDimTypeUi: list[ui.select] = []
        self._dicArtViewDimTypeUi: dict[str, list[ui.select]] = dict()

        sSelGrp = str(self._uiSelGrp.value)
        lViewDimNamesSel = self._dicVgViewDimNamesSel[sSelGrp]
        lNewViewDimNamesSel = []
        setViewDimNames = set(self._xProdView.dicViewDimNames.keys())

        dicArtTypeViewDimNamesSel = self._dicVgArtTypeViewDimNamesSel[sSelGrp]
        dicNewArtTypeViewDimNamesSel = dict()

        self._uiRowViewDim.clear()
        with self._uiRowViewDim:
            with ui.grid(columns=2).classes("w-full"):
                with ui.card():
                    with ui.column():
                        with ui.row().classes("w-full"):
                            bRow: bool = True
                            iDimSelCnt: int = len(lViewDimNamesSel)
                            iDimSelIdx: int = 0
                            for iDimIdx, sDimKey in enumerate(self._xProdView.dicViewDimNames.keys()):
                                # print(f"lViewDimNamesSel: {lViewDimNamesSel}")
                                # print(f"setViewDimNames: {setViewDimNames}")

                                while True:
                                    sDimSel: str = None
                                    if iDimSelIdx >= iDimSelCnt:
                                        break
                                    # endif
                                    sDimSel = lViewDimNamesSel[iDimSelIdx]
                                    iDimSelIdx += 1
                                    if sDimSel in setViewDimNames:
                                        break
                                    # endif
                                # endwhile
                                # print(f"Pre. sDimSel: {sDimSel}")
                                if sDimSel is not None:
                                    setViewDimNames.discard(sDimSel)
                                else:
                                    sDimSel = setViewDimNames.pop()
                                # endif
                                # print(f"Post sDimSel: {sDimSel}")

                                sName: str = "Row" if bRow is True else "Column"
                                self._lViewDimTypeUi.append(
                                    self._CreateSelectUi(
                                        _lOptions=self._xProdView.dicViewDimNames,
                                        _sLabel=f"Along {sName} {((iDimIdx//2)+1)}",
                                        _xValue=sDimSel,
                                        _funcOnChange=self._CreateCallback_OnChangeViewDimSelectUi(iDimIdx),
                                    )
                                )
                                lNewViewDimNamesSel.append(sDimSel)
                                bRow = not bRow
                            # endfor
                            self._dicVgViewDimNamesSel[sSelGrp] = lNewViewDimNamesSel
                        # endwith
                        with ui.column().classes("w-full"):
                            for sArtTypeId, dicViewDimNames in self._xProdView._dicArtViewDimNames.items():
                                lViewDimNamesSel: list[str] = dicArtTypeViewDimNamesSel.get(sArtTypeId)
                                if lViewDimNamesSel is None:
                                    dicArtTypeViewDimNamesSel[sArtTypeId] = []
                                    lViewDimNamesSel = []
                                # endif
                                lNewViewDimNamesSel = []
                                setViewDimNames = set(dicViewDimNames.keys())
                                iDimSelCnt: int = len(lViewDimNamesSel)
                                iDimSelIdx: int = 0

                                self._dicArtViewDimTypeUi[sArtTypeId] = []
                                lArtViewDimTypeUi: list[ui.select] = self._dicArtViewDimTypeUi[sArtTypeId]
                                with ui.row().classes("w-full"):
                                    ui.label(self._xProdView.GetArtefactTypeName(sArtTypeId))
                                    for iDimIdx, sDimKey in enumerate(dicViewDimNames.keys()):
                                        # print(f"lViewDimNamesSel: {lViewDimNamesSel}")
                                        # print(f"setViewDimNames: {setViewDimNames}")

                                        while True:
                                            sDimSel: str = None
                                            if iDimSelIdx >= iDimSelCnt:
                                                break
                                            # endif
                                            sDimSel = lViewDimNamesSel[iDimSelIdx]
                                            iDimSelIdx += 1
                                            if sDimSel in setViewDimNames:
                                                break
                                            # endif
                                        # endwhile
                                        # print(f"Pre. sDimSel: {sDimSel}")
                                        if sDimSel is not None:
                                            setViewDimNames.discard(sDimSel)
                                        else:
                                            sDimSel = setViewDimNames.pop()
                                        # endif
                                        # print(f"Post sDimSel: {sDimSel}")

                                        lArtViewDimTypeUi.append(
                                            self._CreateSelectUi(
                                                _lOptions=dicViewDimNames,
                                                _sLabel=f"Dim {(iDimIdx+1)}",
                                                _xValue=sDimSel,
                                                _funcOnChange=self._CreateCallback_OnChangeArtViewDimSelectUi(
                                                    sArtTypeId, iDimIdx
                                                ),
                                            )
                                        )
                                        lNewViewDimNamesSel.append(sDimSel)
                                    # endfor art var
                                # endwith row

                                dicNewArtTypeViewDimNamesSel[sArtTypeId] = lNewViewDimNamesSel

                            # endfor art type
                            self._dicVgArtTypeViewDimNamesSel[sSelGrp] = dicNewArtTypeViewDimNamesSel

                        # endwith
                    # endwith column
                # endwith
                with ui.card():
                    with ui.column().classes("w-full"):
                        self._dicViewDimRangeUi: dict[str, CPosRange] = dict()
                        for sDimKey, sDimName in self._xProdView.dicViewDimNames.items():
                            with ui.row().classes("w-full"):
                                sDimId, eDimType = self._xProdView.GetDimIdType(sDimKey)
                                if eDimType == EViewDimType.GROUP:
                                    sGrpVarId: str = sDimId
                                    iGrpVarCnt = self._xProdView.GetSelectedGroupVarValueCount(sGrpVarId)
                                    if iGrpVarCnt > 3:
                                        self._dicViewDimRangeUi[sDimKey] = CPosRange(
                                            _fMin=1,
                                            _fMax=iGrpVarCnt,
                                            _fValueMin=1,
                                            _fValueMax=min(6, iGrpVarCnt),
                                            _fRangeMin=1,
                                            _fRangeMax=min(100, iGrpVarCnt),
                                            _sLabel=sDimName,
                                            _eStyle=EPosRangeStyle.STACKED,
                                            _funcOnChanged=self._OnChangeViewRange,
                                        )
                                    # endif

                                elif eDimType == EViewDimType.ARTCOMVAR:
                                    sArtVarId: str = sDimId
                                    iVarCnt = self._xProdView.GetSelectedActiveCommonArtefactVarValueCount(sArtVarId)
                                    if iVarCnt > 3:
                                        self._dicViewDimRangeUi[sDimKey] = CPosRange(
                                            _fMin=1,
                                            _fMax=iVarCnt,
                                            _fValueMin=1,
                                            _fValueMax=min(6, iVarCnt),
                                            _fRangeMin=1,
                                            _fRangeMax=min(20, iVarCnt),
                                            _sLabel=sDimName,
                                            _eStyle=EPosRangeStyle.STACKED,
                                            _funcOnChanged=self._OnChangeViewRange,
                                        )
                                    # endif

                                # endif
                            # endwith
                        # endfor view dims

                        # Unique Artefact View Dims
                        self._dicArtViewDimRangeUi: dict[str, dict[str, CPosRange]] = dict()
                        for sArtTypeId, dicViewDimNames in self._xProdView.dicArtViewDimNames.items():
                            self._dicArtViewDimRangeUi[sArtTypeId] = dict()
                            dicArtViewDimRangeUi: dict[str, CPosRange] = dict()
                            for sDimKey, sArtVarName in dicViewDimNames.items():
                                sArtVarId, eDimType = self._xProdView.GetDimIdType(sDimKey)
                                if eDimType != EViewDimType.ARTVAR:
                                    continue
                                # endif
                                iVarCnt = self._xProdView.GetSelectedArtefactVarValueCount(sArtTypeId, sArtVarId)
                                if iVarCnt > 3:
                                    dicArtViewDimRangeUi[sArtVarId] = CPosRange(
                                        _fMin=1,
                                        _fMax=iVarCnt,
                                        _fValueMin=1,
                                        _fValueMax=min(6, iVarCnt),
                                        _fRangeMin=1,
                                        _fRangeMax=min(10, iVarCnt),
                                        _sLabel=sArtVarName,
                                        _eStyle=EPosRangeStyle.STACKED,
                                        _funcOnChanged=self._OnChangeViewRange,
                                    )
                                # endif
                            # endfor art vars
                        # endfor art types

                    # endwith column
                # endwith card
            # endwith grid
        # endwith Row

    # enddef

    # ##########################################################################################################
    def _CreateCallback_OnChangeArtViewDimSelectUi(self, _sArtTypeId: str, _iDimIdx: int) -> Callable:
        def Callback(_xArgs: events.ValueChangeEventArguments):
            self._OnChangeArtViewDimSelectUi(_sArtTypeId, _iDimIdx, _xArgs)

        # enddef
        return Callback

    # enddef

    # ##########################################################################################################
    def _OnChangeArtViewDimSelectUi(self, _sArtTypeId: str, _iDimIdx: int, _xArgs: events.ValueChangeEventArguments):
        uiSel: ui.select = _xArgs.sender
        uiUpdateSel: ui.select = None
        dicViewDimNames: dict[str, str] = self._xProdView.dicArtViewDimNames.get(_sArtTypeId)
        if dicViewDimNames is None:
            return
        # endif

        lViewDimTypeUi: list[ui.select] = self._dicArtViewDimTypeUi.get(_sArtTypeId)
        if lViewDimTypeUi is None:
            return
        # endif

        setDimKeys: set[str] = set(dicViewDimNames.keys())
        uiEl: ui.select
        for uiEl in lViewDimTypeUi:
            if uiEl.value == uiSel.value and uiEl != uiSel:
                uiUpdateSel = uiEl
            # endif
            setDimKeys.discard(uiEl.value)
        # endfor

        if uiUpdateSel is not None and len(setDimKeys) > 0:
            uiUpdateSel.set_value(setDimKeys.pop())
        # endif

    # enddef

    # ##########################################################################################################
    def _OnChangeViewRange(self, _xSender: ui.element, _fMin: float, _fMax: float, _bRangeChanged: bool):
        self._OnUpdateProductView(None)

    # enddef

    # ##########################################################################################################
    def _OnChangeViewDimSelectUi(self, _iDimIdx: int, _xArgs: events.ValueChangeEventArguments):
        uiSel: ui.select = _xArgs.sender
        uiUpdateSel: ui.select = None
        setDimKeys: set[str] = set(self._xProdView.dicViewDimNames.keys())
        uiEl: ui.select
        for uiEl in self._lViewDimTypeUi:
            if uiEl.value == uiSel.value and uiEl != uiSel:
                uiUpdateSel = uiEl
            # endif
            setDimKeys.discard(uiEl.value)
        # endfor

        if uiUpdateSel is not None and len(setDimKeys) > 0:
            sDimKey = setDimKeys.pop()
            uiUpdateSel.set_value(sDimKey)
        # endif

        sSelGrp = str(self._uiSelGrp.value)
        self._dicVgViewDimNamesSel[sSelGrp][_iDimIdx] = uiSel.value

    # enddef

    # ##########################################################################################################
    def _OnUpdateProductView(self, _xArgs: events.ValueChangeEventArguments):
        if self._iBlockUpdateProductView == 0:
            self._xMessage.ShowWait("Updating view...")
            ui.timer(0.2, self.UpdateProductView, once=True)
        # enddef

    # enddef

    # ##########################################################################################################
    def UpdateProductView(self):
        if self._iBlockUpdateProductView > 0:
            return
        # endif

        self._iBlockUpdateProductView += 1
        try:
            if self._xProdView.bHasGroupData is False:
                self._xMessage.ShowMessage(
                    "No data available. Try scanning the filesystem.", _eType=EMessageType.WARNING, _bDialog=False
                )
                return
            # endif

            # Create view dimensions iteration structure
            self._xProdView.ClearViewDims()
            iMin: int
            iMax: int
            xSel: ui.select = None
            for xSel in self._lViewDimTypeUi:
                sDimKey = str(xSel.value)
                xRange: CPosRange = self._dicViewDimRangeUi.get(sDimKey)
                if xRange is None:
                    iMin = None
                    iMax = None
                else:
                    iMin = int(xRange.fValueMin) - 1
                    iMax = int(xRange.fValueMax) - 1
                # endif
                self._xProdView.AddViewDim(_sDimKey=sDimKey, _iRangeMin=iMin, _iRangeMax=iMax)
            # endfor view dims

            # Create view dims for unique artefact vars
            lViewDimTypeUi: list[ui.select]
            for sArtTypeId, lViewDimTypeUi in self._dicArtViewDimTypeUi.items():
                dicViewDimRangeUi: dict[str, CPosRange] = self._dicArtViewDimRangeUi.get(sArtTypeId)
                for xSel in lViewDimTypeUi:
                    sDimKey = str(xSel.value)
                    xRange: CPosRange = None
                    iMin = None
                    iMax = None
                    if dicViewDimRangeUi is not None:
                        xRange = dicViewDimRangeUi.get(sDimKey)
                        if xRange is not None:
                            iMin = int(xRange.fValueMin) - 1
                            iMax = int(xRange.fValueMax) - 1
                        # endif
                    # endif

                    self._xProdView.AddViewDim(
                        _sDimKey=sDimKey, _iRangeMin=iMin, _iRangeMax=iMax, _sArtTypeId=sArtTypeId
                    )
                # endfor dim selection
            # endfor art type

            # self._lViewGrpPath = [x[0] for x in self._lSelGrpVarValueLists]
            # self._sViewArtTypeId = next((x for x in self._dicSelArtVarValueLists), None)

            xViewDimNode = self._xProdView.StartViewDimNodeIteration()
            iViewDimCnt: int = len(self._xProdView.lViewDims)
            iMaxColsPerRowTop: int = int(self._uiSelMaxColsPerRowTop.value)
            iMaxColsPerRow: int = int(self._uiSelMaxColsPerRow.value)
            self._lMaxColsPerBlock: list[int] = [iMaxColsPerRowTop] + [iMaxColsPerRow] * (iViewDimCnt - 1)

            # print("\nStart Update product view\n")
            # print(f"{self._lMaxColsPerBlock}")

            if xViewDimNode is None:
                self._xMessage.ShowMessage("No artefacts available", _eType=EMessageType.WARNING)
                self._uiRowViewArt.clear()
            else:
                self._uiRowViewArt.clear()
                with self._uiRowViewArt:
                    self._ShowViewDimRow(_xViewDimNode=xViewDimNode)
                # endwith
            # endif
        except Exception as xEx:
            self._xMessage.ShowException("Error updating view", xEx)
        finally:
            self._iBlockUpdateProductView -= 1
            self._xMessage.HideWait()
        # endtry

    # enddef

    # ##########################################################################################################
    def _ShowViewDimRow(self, *, _xViewDimNode: CViewDimNode):
        iBlockColCnt = _xViewDimNode.iRange

        iRowCnt = 1
        xViewDimNodeCol = _xViewDimNode.NextDim()
        if xViewDimNodeCol is not None and not xViewDimNodeCol.bIsUniqueArtVarStartNode:
            iRowCnt = xViewDimNodeCol.iRange
        # endif

        sBgColor: str = self._lViewDimGridColors[(_xViewDimNode.iDimIdx // 2) % len(self._lViewDimGridColors)]

        iMaxColsPerBlock = self._lMaxColsPerBlock[_xViewDimNode.iDimIdx]
        iGridBlockCnt: int = 1
        if iBlockColCnt > iMaxColsPerBlock:
            iGridBlockCnt = iBlockColCnt // iMaxColsPerBlock + (1 if (iBlockColCnt % iMaxColsPerBlock) > 0 else 0)
            iBlockColCnt = iMaxColsPerBlock
        # endif

        bShowRowLabel: bool = (iBlockColCnt > 1 or iRowCnt > 1) and xViewDimNodeCol is not None
        sRowLabelItem: str = "auto" if bShowRowLabel else ""

        sGridStyle: str = (
            f"grid-template-rows: auto repeat({iRowCnt}, minmax(0, 1fr));"
            f"grid-template-columns: {sRowLabelItem} repeat({iBlockColCnt}, minmax(0, 1fr));"
            f"grid-auto-flow: column;"
            "grid-gap: 10px;"
            f"background-color: {sBgColor};"
            "padding: 10px;"
            "justify-items: center;"
            # "align-items: center;"
            # "justify-items: center; align-items: center;"
        )

        if iGridBlockCnt > 1:
            sGridStyle += "border: 1px solid #fff; border-radius: 10px;"
        # endif

        bShowGridBlockTitle: bool = iGridBlockCnt > 1
        sBlockGridTitleRowStyle: str = "auto" if bShowGridBlockTitle else ""

        sBlockGridStyle: str = (
            f"grid-template-rows: repeat({iGridBlockCnt}, {sBlockGridTitleRowStyle} minmax(0, 1fr));"
            f"grid-auto-flow: column;"
            "grid-gap: 10px;"
            f"background-color: {sBgColor};"
            "padding: 10px;"
            "justify-items: center;"
            # "align-items: center;"
            # "justify-items: center; align-items: center;"
        )

        sStyleItem: str = "padding: 3px;justify-self: center;align-self: center;"

        lViewDimRowLabels: list[str] = None
        iViewDimRowLabelCnt: int = 0
        if xViewDimNodeCol is not None:
            lViewDimRowLabels = list(xViewDimNodeCol.lLabels)
            iViewDimRowLabelCnt = len(lViewDimRowLabels)
        # endif

        lViewDimColLabels: list[str] = list(_xViewDimNode.lLabels)
        iViewDimColLabelCnt = len(lViewDimColLabels)

        # print("---")
        # print(f"iDimIdx: {_xViewDimNode.iDimIdx}")
        # print(f"iRowCnt: {iRowCnt}")
        # print(f"iMaxColsPerBlock: {iMaxColsPerBlock}")
        # print(f"iGridBlockCnt: {iGridBlockCnt}")
        # print(f"iBlockColCnt: {iBlockColCnt}")
        # print(f"bShowGridBlockTitle: {bShowGridBlockTitle}")
        # if lViewDimRowLabels is not None:
        #     print(f"lViewDimRowLabels: {lViewDimRowLabels}")
        # # endif
        # print(f"lViewDimColLabels: {lViewDimColLabels}")

        _xViewDimNode.Reset()

        with ui.grid().classes("w-full").style(sBlockGridStyle):
            for iGridBlockIdx in range(iGridBlockCnt):
                iColStartIdx: int = iGridBlockIdx * iBlockColCnt
                if bShowGridBlockTitle is True:
                    ui.label(
                        f"{_xViewDimNode.sDimLabel}s {(_xViewDimNode.xViewDim.iIdx+1)} to {(_xViewDimNode.xViewDim.iIdx+iBlockColCnt)}"
                    ).style("justify-self: start;")
                # endif

                with ui.grid().classes("w-full").style(sGridStyle):
                    # Draw row labels
                    if bShowRowLabel is True:
                        ui.label(" ").style(sStyleItem)

                        if lViewDimRowLabels is not None:
                            for sLabel in lViewDimRowLabels:
                                sStyle = "writing-mode: vertical-lr" if len(sLabel) > 2 else ""
                                ui.label(sLabel).style(sStyle).style(sStyleItem)
                            # endfor
                        # endif
                    # endif

                    for iColIdx in range(iColStartIdx, iColStartIdx + iBlockColCnt):
                        if iColIdx >= iViewDimColLabelCnt:
                            ui.label(" ")
                            for iRowIdx in range(iViewDimRowLabelCnt):
                                ui.label(" ")
                            # endfor
                        else:
                            sLabel: str = lViewDimColLabels[iColIdx]
                            # print(f"[{iGridBlockIdx, iColIdx}]: {sLabel}")

                            ui.label(sLabel).style(sStyleItem)
                            xViewDimNodeCol = _xViewDimNode.NextDim()
                            # if xViewDimNodeCol is not None:
                            #     print(f"{sPre} In row [next]: {xViewDimNodeCol.sLabel}")
                            # else:
                            #     print(f"{sPre} Show Artefact")
                            # # endif

                            # Create row elements
                            if xViewDimNodeCol is None:
                                self._ShowViewDimArt()
                            elif xViewDimNodeCol.bIsUniqueArtVarStartNode is True:
                                self._ShowViewDimRow(_xViewDimNode=xViewDimNodeCol)
                            else:
                                self._ShowViewDimCol(_xViewDimNode=xViewDimNodeCol)
                            # endif

                            _xViewDimNode.Next()
                        # endif
                    # endfor
                # endwith grid block
            # endfor blocks
        # endwith column of grid blocks

    # enddef

    # ##########################################################################################################
    def _xxx_ShowViewDimRow(self, *, _xViewDimNode: CViewDimNode, _bRowMajor: bool = True):
        iColCnt = 1

        if _bRowMajor is True:
            xViewDimNodeCol = _xViewDimNode.NextDim()
            if xViewDimNodeCol is not None and not xViewDimNodeCol.bIsUniqueArtVarStartNode:
                iColCnt = xViewDimNodeCol.iRange
            # endif
        else:
            iColCnt = _xViewDimNode.iRange
        # endif

        # sPre = ">" * _xViewDimNode.iDimIdx
        # if _xViewDimNode.sArtTypeId is not None:
        #     sPre = f"{_xViewDimNode.sArtTypeId} -> " + sPre
        # # endif

        # if xViewDimNodeCol is not None:
        #     print(f"{sPre} Start In row [next]: {xViewDimNodeCol.sLabel}")
        # # endif

        # if _xViewDimNode.bIsUniqueArtVarStartNode:
        #     print(f"{sPre} Is unique art var start node")
        #     # iColCnt = _xViewDimNode.iRange
        # # endif

        sBgColor: str = self._lViewDimGridColors[(_xViewDimNode.iDimIdx // 2) % len(self._lViewDimGridColors)]
        sGridFlow: str = "row" if _bRowMajor is True else "column"

        bTopRow: bool = _xViewDimNode.iDimIdx == 0 and _xViewDimNode.sArtTypeId is None
        iGridBlockCnt: int = 1
        iTopColsPerBlock: int = 4
        if bTopRow is True and iColCnt > iTopColsPerBlock:
            iGridBlockCnt = iColCnt // iTopColsPerBlock + 1 if (iColCnt % iTopColsPerBlock) > 0 else 0
            iColCnt = iTopColsPerBlock
        # endif

        sStyle: str = (
            f"grid-template-columns: auto repeat({iColCnt}, minmax(0, 1fr));"
            f"grid-auto-flow: {sGridFlow};"
            "grid-gap: 10px;"
            f"background-color: {sBgColor};"
            "padding: 10px;"
            "justify-items: center;"
            # "align-items: center;"
            # "justify-items: center; align-items: center;"
        )
        sStyleItem: str = "padding: 3px;justify-self: center;align-self: center;"

        lViewDimColLabels = list(xViewDimNodeCol.lLabels)
        iViewDimColCnt = len(lViewDimColLabels)
        _xViewDimNode.Reset()

        with ui.column().classes("w-full"):
            for iGridBlockIdx in range(iGridBlockCnt):
                with ui.grid().classes("w-full").style(sStyle):
                    # ## DEBUG
                    # sValue = self._GetViewDimLabel(xViewDim)
                    # print(f"ROW> xViewDim: {sValue}")
                    # ##

                    # Create Column header row
                    if _bRowMajor is True:
                        if xViewDimNodeCol is not None:
                            xViewDimNodeCol.Reset()

                            ui.label(" ").style(sStyleItem)
                            if bTopRow is True:
                                iStart = iGridBlockIdx * iColCnt
                                for iIdx in range(iColCnt):
                                    iPos = iIdx + iStart
                                    if iPos < iViewDimColCnt:
                                        sValue = lViewDimColLabels[iPos]
                                    else:
                                        sValue = " "
                                    # endif
                                    ui.label(sValue).style(sStyleItem)
                                # endfor
                            else:
                                for sValue in lViewDimColLabels:
                                    ui.label(sValue).style(sStyleItem)
                                # endwhile
                            # endif
                        # endif
                    else:
                        _xViewDimNode.Reset()
                        ui.label(" ").style(sStyleItem)
                        if _xViewDimNode.iRange == 1:
                            ui.label(" ").style(sStyleItem)
                        else:
                            for sLabel in _xViewDimNode.lLabels:
                                sStyle = "writing-mode: vertical-lr" if len(sLabel) > 2 else ""
                                ui.label(sLabel).style(sStyle).style(sStyleItem)
                            # endfor
                        # endif

                    # endif

                    while True:
                        # Write row label
                        if _bRowMajor is True:
                            if _xViewDimNode.iRange > 1:
                                sValue = _xViewDimNode.sLabel
                                sStyle = "writing-mode: vertical-lr" if len(sValue) > 2 else ""
                                ui.label(sValue).style(sStyle).style(sStyleItem)
                            else:
                                ui.label(" ").style(sStyleItem)
                            # endif
                        # endif

                        # print(f"{sPre} In row:  {_xViewDimNode.xViewDim.iIdx}, {_xViewDimNode.sValue}")
                        xViewDimNodeCol = _xViewDimNode.NextDim()
                        # if xViewDimNodeCol is not None:
                        #     print(f"{sPre} In row [next]: {xViewDimNodeCol.sLabel}")
                        # else:
                        #     print(f"{sPre} Show Artefact")
                        # # endif

                        # Create row elements
                        if xViewDimNodeCol is None:
                            self._ShowViewDimArt()
                        elif xViewDimNodeCol.bIsUniqueArtVarStartNode is True:
                            self._ShowViewDimRow(_xViewDimNode=xViewDimNodeCol, _bRowMajor=_bRowMajor)
                        else:
                            self._ShowViewDimCol(_xViewDimNode=xViewDimNodeCol, _bRowMajor=_bRowMajor)
                        # endif

                        if _xViewDimNode.Next() is False:
                            break
                        # endif
                        if bTopRow is True and _xViewDimNode.xViewDim.iIdx % iTopColsPerBlock == 0:
                            break
                        # endif

                    # endwhile
                # endwith grid
                if iGridBlockIdx < iGridBlockCnt - 1:
                    ui.separator()
                # endif
            # endfor grid block
        # endwith column

    # enddef

    # ##########################################################################################################
    def _ShowViewDimCol(self, *, _xViewDimNode: CViewDimNode):
        xViewDimNodeCol = _xViewDimNode.NextDim()

        # sPre = ">" * _xViewDimNode.iDimIdx
        # if _xViewDimNode.sArtTypeId is not None:
        #     sPre = f"{_xViewDimNode.sArtTypeId} -> " + sPre
        # # endif

        # if xViewDimNodeCol is not None:
        #     print(f"{sPre} Start In col [next]: {xViewDimNodeCol.sValue}")
        # # endif

        sStyleItem: str = "padding: 3px;justify-self: center;align-self: center;"
        # sValue = self._GetViewDimLabel(xViewDim)

        while True:
            # print(f"{sPre} In col: {_xViewDimNode.xViewDim.iIdx}, {_xViewDimNode.sValue}")
            xViewDimNodeCol = _xViewDimNode.NextDim()
            # if xViewDimNodeCol is not None:
            #     print(f"{sPre} In col [next]: {xViewDimNodeCol.sLabel}")
            # else:
            #     print(f"{sPre} Show Artefact")
            # # endif

            if xViewDimNodeCol is None:
                self._ShowViewDimArt()
            else:
                self._ShowViewDimRow(_xViewDimNode=xViewDimNodeCol)
            # endif

            if _xViewDimNode.Next() is False:
                break
            # endif
        # endwhile

    # enddef

    # ##########################################################################################################
    def _UpdateThumbImageStyle(self):
        iMinWidth: int = self._xThumbnails.iTargetWidth // 2
        iMaxWidth: int = self._xThumbnails.iTargetWidth * 2
        # iMinHeight: int = self._xThumbnails.iTargetHeight // 2
        # iMaxHeight: int = self._xThumbnails.iTargetHeight * 2

        self._sThumbImageStyle = f"min-width: {iMinWidth}px; max-width: {iMaxWidth}px; height: 100%; width: 100%;"
        # f"min-height: {iMinHeight}px; max-height: {iMaxHeight}px"

    # enddef

    # ##########################################################################################################
    def _ShowViewDimArt(self):
        ndArt, xArtType = self._xProdView.GetViewDimNodeIterationValue()
        sStyleItem: str = "padding: 3px;justify-self: center;align-self: center;"

        if ndArt is None:
            ui.icon("report_problem", size="xl").style(sStyleItem)
        else:
            pathThumb: Path = None
            pathArt: Path = ndArt.pathFS
            sTooltip: str = None
            sBelow: str = None

            if xArtType.dicMeta is not None:
                for sMetaId, dicMetaData in xArtType.dicMeta.items():
                    dicDti = config.CheckConfigType(dicMetaData, "/catharsys/production/artefact/meta/*:*")
                    if dicDti["bOK"] is True:
                        lMetaType = dicDti["lCfgType"][4:]
                        if lMetaType[0] == "json":
                            dicPrint: dict = dicMetaData.get("mPrint")
                            if isinstance(dicPrint, dict):
                                dicVars = self._xProdView.dicVarValues
                                self._xParser.dicVarData.clear()
                                lResult = self._xParser.Process(
                                    dicMetaData, lProcessPaths=["sRelPath"], dicConstVars=dicVars
                                )
                                # print(lResult)
                                pathJson: Path = pathArt.parent / lResult[0]["sRelPath"]
                                # print(pathJson)
                                if pathJson.exists():
                                    dicData = anyfile.LoadJson(pathJson)
                                    # print(dicData)
                                    dicProcPrint = self._xParser.Process(dicPrint, dicConstVars={"meta_data": dicData})
                                    # print(dicProcPrint)
                                    if "tooltip" in dicProcPrint:
                                        sTooltip = "</br>".join(dicProcPrint["tooltip"]["lLines"])
                                        # print(sTooltip)
                                    # endif
                                    if "below" in dicProcPrint:
                                        sBelow = "</br>".join(dicProcPrint["below"]["lLines"])
                                        # print(sTooltip)
                                    # endif
                                # endif
                            # endif
                        # endif
                    # endif
                # endfor
            # endif

            if pathArt.suffix in [".png", ".jpg", ".exr"]:
                pathThumb = self._xThumbnails.ProvideThumbnailPath(pathArt)
                with ui.image(pathThumb).style("padding: 3px;") as uiImage:
                    uiImage.props("fit=contain").style(self._sThumbImageStyle)
                    if sTooltip is not None:
                        with ui.element("q-tooltip"):
                            ui.html(sTooltip)
                        # endwith
                    # endif

                    with ui.menu().props("context-menu touch-position"):
                        ui.menu_item(
                            "Copy full path to clipboard",
                            on_click=functools.partial(self._OnCopyImagePath, pathArt),
                            auto_close=False,
                        )
                        ui.menu_item(
                            "Image Viewer",
                            on_click=functools.partial(self._OnShowImageViewer, pathArt),
                            auto_close=False,
                        )
                        ui.menu_item(
                            "Pixel Inspector",
                            on_click=functools.partial(self._OnShowPixelInspector, pathArt),
                            auto_close=False,
                        )
                        ui.menu_item(
                            "Download",
                            on_click=functools.partial(self._OnDownloadImage, pathArt),
                            auto_close=False,
                        )
                    # endwith menu
                # endwith image
            else:
                with ui.column().style(sStyleItem):
                    ui.icon("contact_support", size="xl")
                    ui.label(f"Filetype '{pathArt.suffix}' not supported")
                # endwith
            # endif
            # ui.label(ndArt.pathFS.as_posix())
        # endif

    # enddef

    # ##########################################################################################################
    async def _OnCopyImagePath(self, _pathImage: Path, _xArgs: events.ClickEventArguments):
        try:
            await ui.run_javascript(f'navigator.clipboard.writeText("{(_pathImage.as_posix())}")', respond=False)

        except Exception as xEx:
            self._xMessage.ShowException("Error copying image path to clipboard", xEx)

        finally:
            self._CloseMenuItemFromEvent(_xArgs)
        # endtry

    # enddef

    # ##########################################################################################################
    async def _OnShowImageViewer(self, _pathImage: Path, _xArgs: events.ClickEventArguments):
        try:
            await self._xImageViewer.AsyncShowImage(_pathImage)

        except Exception as xEx:
            self._xMessage.ShowException("Error in image viewer", xEx)

        finally:
            self._CloseMenuItemFromEvent(_xArgs)
        # endtry

    # enddef

    # ##########################################################################################################
    def _DownloadImage(self, _pathImage: Path):
        iStartIdx: int = 0
        for iIdx, sPart in enumerate(_pathImage.parts):
            if sPart == "_render" or sPart == "_production":
                iStartIdx = iIdx + 1
                break
            # endif
        # endfor

        sFilename: str = "-".join(_pathImage.parts[iStartIdx:])

        ui.download(_pathImage, sFilename)

    # enddef

    # ##########################################################################################################
    async def _OnShowPixelInspector(self, _pathImage: Path, _xArgs: events.ClickEventArguments):
        try:
            self._DownloadImage(_pathImage)
            if self._bShowPixinMessage:
                await self._xMessage.AsyncShowMessage(
                    "After the file is downloaded open it in the 'pixin' tab by pressing F3",
                    _eType=EMessageType.INFO,
                    _bDialog=True,
                )
                self._bShowPixinMessage = False
            # endif
            await ui.run_javascript('window.open("https://pixin.app/", "_blank")', respond=False)
            # await ui.run_javascript('window.open("https://pixin.app/", "_blank").focus()', respond=False)

        except Exception as xEx:
            self._xMessage.ShowException("Error starting pixel inspector", xEx)

        finally:
            self._CloseMenuItemFromEvent(_xArgs)
        # endtry

    # enddef

    # ##########################################################################################################
    async def _OnDownloadImage(self, _pathImage: Path, _xArgs: events.ClickEventArguments):
        try:
            self._DownloadImage(_pathImage)

        except Exception as xEx:
            self._xMessage.ShowException("Error starting image download", xEx)

        finally:
            self._CloseMenuItemFromEvent(_xArgs)
        # endtry

    # enddef


# endclass
