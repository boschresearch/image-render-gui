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


class CValueControlSelect(CValueControl):
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
        self._sClassLabel = "text-xs font-light pb-0"
        self._sSelectStyle = "min-width: 8rem"
        self._sSelectProps = "stack-label dense options-dense filled"

        if len(self._lType) == 0 or self._lType[0] != "select":
            raise RuntimeError(f"Select control initialized with invalid dictionary of type: {self._sDti}")
        # endif

        if len(self._lType) == 1:
            self._lType.append("str")
        # endif

        self._lRawOptions = _dicCtrl.get("lOptions")
        if self._lRawOptions is None:
            raise RuntimeError("Select control definition misses 'lOptions' argument")
        # endif

        self._bMultiple: bool = convert.DictElementToBool(_dicCtrl, "bMultiple", bDefault=False)

        self._uiCtrl: ui.select = None

        sDataType = self._lType[1]
        if sDataType == "int":
            if isinstance(_dicData, dict):
                iValue = convert.DictElementToInt(_dicData, _sName, iDefault=0)
            elif isinstance(_xValue, int) or isinstance(_xValue, float):
                iValue = int(_xValue)
            else:
                iValue = 0
            # endif

            self._lOptions = [convert.ToInt(x, iDefault=0) for x in self._lRawOptions]

            with ui.row():
                # ui.label(self._sLabel).classes(self._sClassLabel)
                self._uiCtrl = (
                    ui.select(
                        options=self._lOptions,
                        value=iValue,
                        multiple=self._bMultiple,
                        on_change=lambda xArgs: self.OnChangeInt(xArgs),
                    )
                    .props(f'label="{self._sLabel}" {self._sSelectProps}')
                    .style(self._sSelectStyle)
                )
            # endwith

        elif sDataType == "float":
            if isinstance(_dicData, dict):
                fValue = convert.DictElementToFloat(_dicData, _sName, fDefault=0.0)
            elif isinstance(_xValue, int) or isinstance(_xValue, float):
                fValue = float(_xValue)
            else:
                fValue = 0.0
            # endif

            self._lOptions = {
                convert.ToFloat(x, fDefault=0.0): convert.ToString(x, sDefault="") for x in self._lRawOptions
            }

            with ui.row():
                # ui.label(self._sLabel).classes(self._sClassLabel)
                self._uiCtrl = (
                    ui.select(
                        options=self._lOptions,
                        value=fValue,
                        multiple=self._bMultiple,
                        on_change=lambda xArgs: self.OnChangeFloat(xArgs),
                    )
                    .props(f'label="{self._sLabel}" {self._sSelectProps}')
                    .style(self._sSelectStyle)
                )
            # endwith

        elif sDataType == "str":
            if self._bMultiple is True:
                if isinstance(_dicData, dict):
                    xValue = convert.DictElementToStringList(_dicData, _sName, lDefault=[""])
                else:
                    xValue = _xValue
                # endif
            else:
                if isinstance(_dicData, dict):
                    xValue = convert.DictElementToString(_dicData, _sName, sDefault="")
                else:
                    xValue = str(_xValue)
                # endif
            # endif

            self._lOptions = [convert.ToString(x, sDefault="") for x in self._lRawOptions]

            # with ui.column():
            #     ui.label(self._sLabel).classes(self._sClassLabel)
            #     ui.select(options=self._lOptions, value=sValue, on_change=lambda xArgs: self.OnChangeString(xArgs))
            # # endwith
            self._uiCtrl = (
                ui.select(
                    options=self._lOptions,
                    value=xValue,
                    multiple=self._bMultiple,
                    on_change=lambda xArgs: self.OnChangeString(xArgs),
                )
                .props(f'label="{self._sLabel}" {self._sSelectProps}')
                .style(self._sSelectStyle)
            )

        else:
            raise RuntimeError(f"Unsupported control number type '{sDataType}")
        # endif

        if self._sTooltip is not None:
            self._uiCtrl.tooltip(self._sTooltip)
        # endif

    # enddef

    # ###################################################################################
    def OnChangeInt(self, _xArgs: events.ValueChangeEventArguments):
        if isinstance(self._dicData, dict):
            if self._bMultiple is True:
                xValue = _xArgs.value
            else:
                try:
                    xValue: int = int(_xArgs.value)
                except Exception:
                    xValue = 0
                # endtry
            # endif

            bDoChange: bool = True
            if self._funcOnChange is not None:
                bDoChange = self._funcOnChange(_xArgs, self._dicData, self._sName, xValue)
            # endif

            if bDoChange is True:
                self._dicData[self._sName] = xValue
                # print(self._dicData)
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
            if self._bMultiple is True:
                xValue = _xArgs.value
            else:
                try:
                    xValue: float = float(_xArgs.value)
                except Exception:
                    xValue = 0.0
                # endtry
            # endtry

            bDoChange: bool = True
            if self._funcOnChange is not None:
                bDoChange = self._funcOnChange(_xArgs, self._dicData, self._sName, xValue)
            # endif

            if bDoChange is True:
                self._dicData[self._sName] = xValue
                # print(self._dicData)
            else:
                self._uiCtrl.disable()
                self._uiCtrl.value = self._dicData[self._sName]
                self._uiCtrl.update()
                self._uiCtrl.enable()
            # endif
        # endif

    # enddef

    # ###################################################################################
    def OnChangeString(self, _xArgs: events.ValueChangeEventArguments):
        if isinstance(self._dicData, dict):
            if self._bMultiple is True:
                xValue = _xArgs.value
            else:
                try:
                    xValue = str(_xArgs.value)
                except Exception:
                    xValue = ""
                # endtry
            # endif

            bDoChange: bool = True
            if self._funcOnChange is not None:
                bDoChange = self._funcOnChange(_xArgs, self._dicData, self._sName, xValue)
            # endif

            if bDoChange is True:
                self._dicData[self._sName] = xValue
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
