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

from typing import Optional, Any, Callable
from nicegui import ui, events
from anybase import convert

from .cls_value_control import CValueControl


class CValueControlNumber(CValueControl):
    def __init__(
        self,
        _sName: str,
        _dicCtrl: dict,
        _xValue: Any = None,
        _dicData: Optional[dict] = None,
        _funcOnChange: Optional[Callable[[events.ValueChangeEventArguments, dict, str, Any], bool]] = None,
    ):
        super().__init__(_sName, _dicCtrl)
        self._dicData = _dicData
        self._funcOnChange: Callable[[events.ValueChangeEventArguments, dict, str, Any], bool] = _funcOnChange

        if len(self._lType) == 0 or self._lType[0] != "number":
            raise RuntimeError(f"Number control initialized with invalid dictionary of type: {self._sDti}")
        # endif

        if len(self._lType) == 1:
            self._lType.append("float")
        # endif

        self._uiCtrl: ui.number = None

        sDataType = self._lType[1]
        if sDataType == "int":
            if isinstance(_dicData, dict):
                iValue = convert.DictElementToInt(_dicData, _sName, iDefault=0)
            elif isinstance(_xValue, int) or isinstance(_xValue, float):
                iValue = int(_xValue)
            else:
                iValue = 0
            # endif

            self._uiCtrl = ui.number(
                label=self._sLabel, value=iValue, format="%d", on_change=lambda xArgs: self.OnChangeInt(xArgs)
            )

        elif sDataType == "float":
            if isinstance(_dicData, dict):
                fValue = convert.DictElementToFloat(_dicData, _sName, fDefault=0.0)
            elif isinstance(_xValue, int) or isinstance(_xValue, float):
                fValue = float(_xValue)
            else:
                fValue = 0.0
            # endif

            self._uiCtrl = ui.number(
                label=self._sLabel, value=fValue, format="%f", on_change=lambda xArgs: self.OnChangeFloat(xArgs)
            )

        else:
            raise RuntimeError(f"Unsupported control number type '{sDataType}")
        # endif

    # enddef

    # ###################################################################################
    def OnChangeInt(self, _xArgs: events.ValueChangeEventArguments):
        if isinstance(self._dicData, dict):
            try:
                iValue: int = int(_xArgs.value)
            except Exception:
                iValue = 0
            # endtry

            bDoChange: bool = True
            if self._funcOnChange is not None:
                bDoChange = self._funcOnChange(_xArgs, self._dicData, self._sName, iValue)
            # endif

            if bDoChange is True:
                # print(f"write '{iValue}' to '{self._sName}' of {(id(self._dicData))}")
                self._dicData[self._sName] = iValue
            else:
                self._uiCtrl.disable()
                self._uiCtrl.value = self._dicData[self._sName]
                self._uiCtrl.update()
                self._uiCtrl.enable()
            # endif
        # endif

    # enddef

    # ###################################################################################
    def OnChangeFloat(self, _xArgs: events.ValueChangeEventArguments):
        if isinstance(self._dicData, dict):
            try:
                fValue: float = float(_xArgs.value)
            except Exception:
                fValue = 0.0
            # endtry

            bDoChange: bool = True
            if self._funcOnChange is not None:
                bDoChange = self._funcOnChange(_xArgs, self._dicData, self._sName, fValue)
            # endif

            if bDoChange is True:
                self._dicData[self._sName] = fValue
                # print(self._dicData)
            else:
                self._uiCtrl.disable()
                self._uiCtrl.value = self._dicData[self._sName]
                self._uiCtrl.update()
                self._uiCtrl.enable()
            # endif
        # endif

    # enddef


# endclass
