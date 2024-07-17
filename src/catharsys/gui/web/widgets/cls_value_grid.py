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
import copy

from nicegui import ui, events
from anybase import config

from anybase import convert

from .cls_factory_value_control import CFactoryValueControl
from .cls_value_control import CValueControl


class CValueGrid:
    """Administers a grid of value controls.

    Args:
        _gridData (ui.grid): The grid to which the controls are added.
        _dicValues (dict): The dictionary of values.
        _xCtrlFactory (CFactoryValueControl): The factory for creating value controls.
        _lExcludeRegEx (list, optional): List of regular expressions for excluding values. Defaults to [].
        _dicGuiArgs (dict, optional): Dictionary of GUI arguments. Defaults to None.
        _dicDefaultGuiArgs (dict, optional): Dictionary of default GUI arguments. Defaults to dict().
        _sDataId (str, optional): The data ID. Defaults to None.
        _lValueSubDict (dict[str, dict], optional): Dictionary of keys into value dictionary with value of gui args. Defaults to None.
        _funcOnChange (Callable[[events.ValueChangeEventArguments, dict, str, Any], bool], optional): Function to call when a value changes. Defaults to None.

    """
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
        _dicValueSubDict: dict[str, dict] | None = None,
        _funcOnChange: Optional[Callable[[events.ValueChangeEventArguments, dict, str, Any], bool]] = None,
    ):
        self._dicValues: dict = _dicValues
        self._dicValueSubDict: dict[str, dict] | None = _dicValueSubDict
        if self._dicValueSubDict is not None:
            for sKey in self._dicValueSubDict:
                if sKey not in self._dicValues:
                    raise RuntimeError(f"Key '{sKey}' not found in values dictionary")
                # endif
            # endfor
        # endif

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

        # self._dicGuiVarDef: dict = self._dicGuiArgs.get("mVars", dict())
        # self._dicGuiCtrlDefaults: dict[str, dict[str, Any]] = self._dicGuiArgs.get("mControlDefaults", dict())

        # # if true: all vars are shown apart from those listed in lExcludeVars
        # # if false: only vars are shown that have a gui definition or are listed in lIncludeVars
        # #              and are not listed in lExcludeVars.
        # self._bShowAllVars = convert.DictElementToBool(self._dicGuiArgs, "bShowAllVars", bDefault=True)
        # self._lIncludeVars = convert.DictElementToStringList(self._dicGuiArgs, "lIncludeVars", lDefault=[])
        # self._lExcludeVars = convert.DictElementToStringList(self._dicGuiArgs, "lExcludeVars", lDefault=[])

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
                if self._dicValueSubDict is None:
                    for sValName in self._dicValues:
                        xCtrl = self.GetControl(sValName, self._dicValues, self._dicGuiArgs)
                        if xCtrl is not None:
                            self._dicCtrl[sValName] = xCtrl
                        # endif
                    # endfor
                else:
                    for sSubDictId, dicSubGuiArgs in self._dicValueSubDict.items():
                        dicSubValues: dict = self._dicValues[sSubDictId]
                        if isinstance(dicSubGuiArgs, dict):
                            dicEffGuiArgs = copy.deepcopy(self._dicGuiArgs)
                            dicEffGuiArgs.update(dicSubGuiArgs)
                        else:
                            dicEffGuiArgs = self._dicGuiArgs
                        # endif

                        for sValName in dicSubValues:
                            xCtrl = self.GetControl(sValName, dicSubValues, dicEffGuiArgs)
                            if xCtrl is not None:
                                self._dicCtrl[sValName] = xCtrl
                            # endif
                        # endfor
                       
                    # endfor
                # endif 
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
                            with ui.row().classes("bg-teal text-white w-full px-2"):
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
                                            dicValues: dict = self._dicValues
                                            dicEffGuiArgs: dict = self._dicGuiArgs
                                            if isinstance(self._dicValueSubDict, dict):
                                                for sSubDictId, dicSubGuiArgs in self._dicValueSubDict.items():
                                                    if sValName in self._dicValues[sSubDictId]:
                                                        dicValues = self._dicValues[sSubDictId]
                                                        if isinstance(dicSubGuiArgs, dict):
                                                            dicEffGuiArgs = copy.deepcopy(self._dicGuiArgs)
                                                            dicEffGuiArgs.update(dicSubGuiArgs)
                                                        # endif
                                                        break
                                                    # endif
                                                # endfor
                                            # endif

                                            if sValName not in dicValues:
                                                raise RuntimeError(
                                                    f"Variable '{sValName}' in row layout for data type '{_sDataId}' not available"
                                                )
                                            # endif
                                            xCtrl = self.GetControl(sValName, dicValues, dicEffGuiArgs)
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
    def GetControl(self, 
                   _sValName: str, 
                   _dicValues: dict, 
                   _dicGuiArgs: dict) -> Optional[CValueControl]:
        xCtrl: CValueControl = None

        if len(_sValName) < 2 or "/" in _sValName:
            return None
        # endif

        dicGuiVarDef: dict = _dicGuiArgs.get("mVars", dict())
        dicGuiCtrlDefaults: dict[str, dict[str, Any]] = _dicGuiArgs.get("mControlDefaults", dict())

        # if true: all vars are shown apart from those listed in lExcludeVars
        # if false: only vars are shown that have a gui definition or are listed in lIncludeVars
        #              and are not listed in lExcludeVars.
        bShowAllVars = convert.DictElementToBool(_dicGuiArgs, "bShowAllVars", bDefault=True)
        lIncludeVars = convert.DictElementToStringList(_dicGuiArgs, "lIncludeVars", lDefault=[])
        lExcludeVars = convert.DictElementToStringList(_dicGuiArgs, "lExcludeVars", lDefault=[])

        xMatch = None
        for reExclude in self._lReExclude:
            xMatch = reExclude.fullmatch(_sValName)
            if xMatch is not None:
                break
            # endif
        # endfor
        if xMatch is not None:
            return None
        # endif

        if _sValName in lExcludeVars:
            return None
        # endif

        try:
            sNameTypeDef = f"{_sValName}/gui"
            dicTypeDef = _dicValues.get(sNameTypeDef)
            if not isinstance(dicTypeDef, dict):
                dicTypeDef = dicGuiVarDef.get(_sValName)
            # endif
            # print(f"dicGuiVarDef[{sValName}]: {dicTypeDef}")

            if bShowAllVars is False and dicTypeDef is None and _sValName not in lIncludeVars:
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
                    dicDefTypeCfg = self._xCtrlFactory.GetControlConfigFromName(_sValName)
                    dicDefTypeCfg.update(dicTypeDef)
                    dicTypeDef = dicDefTypeCfg
                # endif

                if dicTypeDef is not None:
                    for sCtrlDti, dicCtrlArgs in dicGuiCtrlDefaults.items():
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
                    _sValName,
                    _dicCtrl=dicTypeDef,
                    _dicData=_dicValues,
                    _funcOnChange=self._funcOnChange,
                )
            else:  # if bEmptyGuiDict is True:
                xCtrl = self._xCtrlFactory.FromName(
                    _sValName, _dicData=_dicValues, _funcOnChange=self._funcOnChange
                )
            # endif
        except Exception as xEx:
            ui.notify(
                f"Error creating control for value '{_sValName}'\n{(str(xEx))}",
                multiLine=True,
                classes="multi-line-notification",
            )
        # endtry

        return xCtrl

    # enddef
