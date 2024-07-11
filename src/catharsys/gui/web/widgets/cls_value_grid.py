###
# Author: Christian Perwass (CR/AEC5)
# <LICENSE id="Apache-2.0">
#
#   Image-Render Automation Functions module
#   Copyright 2022 Robert Bosch GmbH and its subsidiaries
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

import re
from typing import Optional, Callable, Any

from nicegui import ui, events
from anybase import config

from anybase import convert

from .cls_factory_value_control import CFactoryValueControl
from .cls_value_control import CValueControl


class CValueGrid:
    def __init__(
        self,
        *,
        _gridData: ui.grid,
        _dicValues: dict,
        _xCtrlFactory: CFactoryValueControl,
        _lExcludeRegEx: Optional[list] = [],
        _dicGuiArgs: Optional[dict] = None,
        _dicDefaultGuiArgs: Optional[dict] = dict(),
        _sDataId: str = None,
        _funcOnChange: Optional[Callable[[events.ValueChangeEventArguments, dict, str, Any], bool]] = None,
    ):
        self._dicValues: dict = _dicValues
        self._gridData: ui.grid = _gridData
        self._xCtrlFactory: CFactoryValueControl = _xCtrlFactory
        self._dicCtrl: dict[str, CValueControl] = {}
        self._lReExclude: list = [re.compile(x) for x in _lExcludeRegEx]
        self._funcOnChange: Callable[[events.ValueChangeEventArguments, dict, str, Any], bool] = _funcOnChange

        self._bShowAllVars: bool = True
        self._lIncludeVars: list[str] = []
        self._lExcludeVars: list[str] = []

        self._dicGuiArgs: dict = dict()

        if isinstance(_dicDefaultGuiArgs, dict):
            self._dicGuiArgs.update(_dicDefaultGuiArgs)
        # endif

        if isinstance(_dicGuiArgs, dict):
            self._dicGuiArgs.update(_dicGuiArgs)
        # endif

        # print(f"dicGuiArgs: {self._dicGuiArgs}")

        self._dicGuiVarDef: dict = self._dicGuiArgs.get("mVars", dict())
        self._dicGuiCtrlDefaults: dict[str, dict[str, Any]] = self._dicGuiArgs.get("mControlDefaults", dict())

        # if true: all vars are shown apart from those listed in lExcludeVars
        # if false: only vars are shown that have a gui definition or are listed in lIncludeVars
        #              and are not listed in lExcludeVars.
        self._bShowAllVars = convert.DictElementToBool(self._dicGuiArgs, "bShowAllVars", bDefault=True)
        self._lIncludeVars = convert.DictElementToStringList(self._dicGuiArgs, "lIncludeVars", lDefault=[])
        self._lExcludeVars = convert.DictElementToStringList(self._dicGuiArgs, "lExcludeVars", lDefault=[])

        iColumnCount: int = 4

        dicDataGridLayout: dict = self._dicGuiArgs.get("mGridLayout", dict())
        dicGridLayout: dict = None
        self._lLayoutGroups: list[dict] = None

        if _sDataId is not None:
            dicGridLayout = dicDataGridLayout.get(_sDataId)
            if isinstance(dicGridLayout, dict):
                iColumnCount = convert.DictElementToInt(dicGridLayout, "iColumnCount", iDefault=1)
                self._lLayoutGroups = dicGridLayout.get("lGroups")
                if self._lLayoutGroups is None:
                    raise RuntimeError(f"No element 'lGroups' found in 'mGridLayout' for data type '{_sDataId}'")
                # endif
            # endif
        # endif
        # print(f"self._bShowAllVars: {self._bShowAllVars}")

        # print(f"dicGuiVarDef: {dicGuiVarDef}")
        xCtrl: CValueControl = None

        if self._lLayoutGroups is None:
            _gridData.clear()
            _gridData.style(f"grid-template-columns: repeat({iColumnCount}, minmax(0, 1fr))")
            self._gridData.set_visibility(True)
            with _gridData:
                sValName: str = None
                for sValName in self._dicValues:
                    xCtrl = self.GetControl(sValName)
                    if xCtrl is not None:
                        self._dicCtrl[sValName] = xCtrl
                    # endif
                # endfor
            # endwith

        else:
            # iColumnCount = len(self._lLayoutGroups)
            _gridData.clear()
            _gridData.style(f"grid-template-columns: repeat({iColumnCount}, minmax(0, 1fr))")
            self._gridData.set_visibility(True)
            with _gridData:
                sValName: str
                dicGroup: dict
                for dicGroup in self._lLayoutGroups:
                    sTitle: str = dicGroup.get("sTitle", "")
                    uiCard = ui.card().tight().props("flat bordered").classes("w-full")
                    with uiCard:
                        if len(sTitle) > 0:
                            with ui.card_section().classes("bg-teal text-white w-full"):
                                ui.label(sTitle).classes("text-subtitle2")
                            # endwith
                            # ui.separator().props("inset")
                        # endif
                        with ui.card_section():
                            with ui.element("q-list").props("padding").classes("w-full"):
                                lRows: list[list[str]] = dicGroup.get("lRows", [])
                                lRow: list[str]
                                for lRow in lRows:
                                    with ui.row().classes("w-full"):
                                        for sValName in lRow:
                                            if sValName not in self._dicValues:
                                                raise RuntimeError(
                                                    f"Variable '{sValName}' in row layout for data type '{_sDataId}' not available"
                                                )
                                            # endif
                                            xCtrl = self.GetControl(sValName)
                                            if xCtrl is not None:
                                                if sValName in self._dicCtrl:
                                                    raise RuntimeError(
                                                        f"Variable '{sValName}' is referenced more than once in grid layout: {(list(self._dicCtrl.keys()))}"
                                                    )
                                                # endif
                                                self._dicCtrl[sValName] = xCtrl
                                            # endif
                                        # endfor row elements
                                    # endwith
                                # endfor layout rows
                            # endwith q-list
                        # endwith card section
                    # endwith card
                # endfor group
            # endwith gridData
        # endif

        if len(self._dicCtrl) == 0:
            self._gridData.set_visibility(False)
        # endif

    # enddef

    # ##########################################################################################################
    def GetControl(self, sValName: str) -> Optional[CValueControl]:
        xCtrl: CValueControl = None

        if len(sValName) < 2 or "/" in sValName:
            return None
        # endif

        xMatch = None
        for reExclude in self._lReExclude:
            xMatch = reExclude.fullmatch(sValName)
            if xMatch is not None:
                break
            # endif
        # endfor
        if xMatch is not None:
            return None
        # endif

        if sValName in self._lExcludeVars:
            return None
        # endif

        try:
            sNameTypeDef = f"{sValName}/gui"
            dicTypeDef: dict = self._dicValues.get(sNameTypeDef)
            if not isinstance(dicTypeDef, dict):
                dicTypeDef = self._dicGuiVarDef.get(sValName)
            # endif
            # print(f"dicGuiVarDef[{sValName}]: {dicTypeDef}")

            if self._bShowAllVars is False and dicTypeDef is None and sValName not in self._lIncludeVars:
                return None
            # endif

            # bEmptyGuiDict: bool = False
            if isinstance(dicTypeDef, dict):
                bUseCfgFromName: bool = False
                try:
                    dicDti = config.CheckConfigType(dicTypeDef, "/catharsys/gui/control/*:*")
                    if dicDti["bOK"] is False:
                        bUseCfgFromName = True
                    # endif
                except Exception:
                    bUseCfgFromName = True
                    # bEmptyGuiDict = True
                # endtry

                if bUseCfgFromName is True:
                    dicDefTypeCfg = self._xCtrlFactory.GetControlConfigFromName(sValName)
                    dicDefTypeCfg.update(dicTypeDef)
                    dicTypeDef = dicDefTypeCfg
                # endif

                if dicTypeDef is not None:
                    for sCtrlDti, dicCtrlArgs in self._dicGuiCtrlDefaults.items():
                        dicCtrlDti = config.CheckConfigType(dicTypeDef, sCtrlDti)
                        if dicCtrlDti["bOK"] is True:
                            dicTypeDef.update(dicCtrlArgs)
                        # endif
                    # endfor
                # endif
            else:
                dicTypeDef = None
            # endif

            # xValue = _dicValues[sValName]
            if dicTypeDef is not None:
                xCtrl = self._xCtrlFactory.FromDict(
                    sValName,
                    _dicCtrl=dicTypeDef,
                    _dicData=self._dicValues,
                    _funcOnChange=self._funcOnChange,
                )
            else:  # if bEmptyGuiDict is True:
                xCtrl = self._xCtrlFactory.FromName(
                    sValName, _dicData=self._dicValues, _funcOnChange=self._funcOnChange
                )
            # endif
        except Exception as xEx:
            ui.notify(
                f"Error creating control for value '{sValName}'\n{(str(xEx))}",
                multiLine=True,
                classes="multi-line-notification",
            )
        # endtry

        return xCtrl

    # enddef
