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

from nicegui.element import Element
from nicegui.events import ClickEventArguments
from nicegui import ui

from typing import Any, Callable, Optional

from catharsys.api.products.cls_category import CCategoryTypeBoolGroup


class CUiBoolGroup(Element):
    def __init__(
        self,
        _xCatBoolGrp: CCategoryTypeBoolGroup,
        *,
        _iValue: int = None,
        _bVertical: bool = False,
        _funcOnChange: Optional[Callable[[int], Any]] = None,
    ):
        super().__init__("div")
        self._classes.append("nicegui-grid")

        iValue: int = _iValue if _iValue is not None else _xCatBoolGrp.GetDefaultValue()
        iChoiceCnt = len(_xCatBoolGrp.lChoices)
        iValue = min(max(iValue, 0), iChoiceCnt - 1)

        self._style["gap"] = "1px"
        if _bVertical is True:
            self._style["grid-template-rows"] = f"repeat({iChoiceCnt}, minmax(min-content, max-content))"
            self._style["grid-template-columns"] = "1fr"
        else:
            self._style["grid-template-columns"] = f"repeat({iChoiceCnt}, minmax(min-content, max-content))"
            self._style["grid-template-rows"] = "1fr"
        # endif

        self._xCatBoolGrp: CCategoryTypeBoolGroup = _xCatBoolGrp
        self._funcOnChange = _funcOnChange
        self._lButtons: list[ui.button] = []

        with self:
            for iIdx, xChoice in enumerate(_xCatBoolGrp.lChoices):
                uiBut = ui.button(icon=xChoice.sIcon, on_click=self._CreateHandler_OnClick(iIdx)).props("dense")
                if iIdx == iValue:
                    sColor: str = xChoice.sColor
                    if len(sColor) == 0:
                        sColor = "primary"
                    # endif
                    uiBut.props(f"color={sColor}")
                else:
                    uiBut.props(remove="color")
                # endif

                self._lButtons.append(uiBut)
                if len(xChoice.sDescription) > 0:
                    with uiBut:
                        ui.tooltip(xChoice.sDescription)
                    # endwith
                # endif
            # endfor
        # endwith

    # enddef

    def SelectChoice(self, _iIdx: int):
        for iIdx, uiBut in enumerate(self._lButtons):
            if iIdx == _iIdx:
                sColor: str = self._xCatBoolGrp.lChoices[_iIdx].sColor
                if len(sColor) == 0:
                    sColor = "primary"
                # endif
                uiBut.props(f"color={sColor}")
            else:
                uiBut.props(remove="color")
            # endif
        # endfor

        if self._funcOnChange is not None:
            self._funcOnChange(_iIdx)
        # endif

    # enddef

    def _CreateHandler_OnClick(self, _iIdx: int):
        def _OnClick(_xArgs: ClickEventArguments):
            self.SelectChoice(_iIdx)

        # enddef
        return _OnClick

    # enddef


# endclass
