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


class CValueControlInput(CValueControl):
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

        if len(self._lType) == 0 or self._lType[0] != "input":
            raise RuntimeError(f"Input control initialized with invalid dictionary of type: {self._sDti}")
        # endif

        if isinstance(_dicData, dict):
            sValue = convert.DictElementToString(_dicData, _sName, sDefault="")
        else:
            sValue = str(_xValue)
        # endif

        bIsPassword: bool = convert.DictElementToBool(_dicCtrl, "bIsPassword", bDefault=False)
        bTogglePwView: bool = convert.DictElementToBool(_dicCtrl, "bTogglePasswordView", bDefault=False)

        self._uiCtrl: ui.input = ui.input(
            label=self._sLabel, 
            placeholder="start typing", 
            value=sValue, 
            password=bIsPassword,
            password_toggle_button=bTogglePwView,
            on_change=lambda xArgs: self.OnChange(xArgs)
        )

        if self._sTooltip is not None:
            self._uiCtrl.tooltip(self._sTooltip)
        # endif

    # enddef

    # ###################################################################################
    def OnChange(self, _xArgs: events.ValueChangeEventArguments):
        if isinstance(self._dicData, dict):
            try:
                sValue: str = str(_xArgs.value)
            except Exception:
                sValue = ""
            # endtry

            bDoChange: bool = True
            if self._funcOnChange is not None:
                bDoChange = self._funcOnChange(_xArgs, self._dicData, self._sName, sValue)
            # endif

            if bDoChange is True:
                self._dicData[self._sName] = sValue
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
