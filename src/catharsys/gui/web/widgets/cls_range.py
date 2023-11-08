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

from typing import Any, Callable, Optional

from nicegui.events import ValueChangeEventArguments
from nicegui.elements.mixins.disableable_element import DisableableElement
from nicegui.elements.mixins.value_element import ValueElement
from nicegui.element import Element
from nicegui import ui


class CRange(ValueElement, DisableableElement):
    def __init__(
        self,
        *,
        _fMin: float,
        _fMax: float,
        _fValueMin: float,
        _fValueMax: float,
        _fStep: float = 1.0,
        _fRangeMin: float = None,
        _fRangeMax: float = None,
        _funcOnChanged: Optional[Callable[[Element, float, float, bool, bool], Any]] = None,
    ) -> None:
        super().__init__(
            tag="q-range", value={"min": _fValueMin, "max": _fValueMax}, on_value_change=None, throttle=0.05
        )
        self.classes("w-full q-pa-md q-pb-lg")
        # self._style["padding-top"] = "1.0em"
        self._props["min"] = _fMin
        self._props["max"] = _fMax
        self._props["step"] = _fStep
        self._props["drag-range"] = True
        self._props["label-always"] = True

        self._fMin: float = _fMin
        self._fMax: float = _fMax
        self._fValMin: float = _fValueMin
        self._fValMax: float = _fValueMax

        if _fRangeMin is not None and _fRangeMax is not None and _fRangeMin > _fRangeMax:
            fVal = _fRangeMin
            _fRangeMin = _fRangeMax
            _fRangeMax = fVal
        # endif

        self._fMinRange: float = _fRangeMin
        self._fMaxRange: float = _fRangeMax
        self._funcOnChange: Callable[[Element, float, float, bool, bool], Any] = _funcOnChanged
        self._bBlockOnChange: bool = False

        self.on("change", self._OnChanged, [None], throttle=0.05)

        # print("\nCRange:")
        # print(f"_fMinRange: {self._fMinRange}")
        # print(f"_fMaxRange: {self._fMaxRange}")
        # print(f"fStep: {_fStep}")

    # enddef

    @property
    def fValueMin(self) -> float:
        return self._fValMin

    # enddef

    @property
    def fValueMax(self) -> float:
        return self._fValMax

    # enddef

    # #######################################################################################################
    def SetValue(self, fValMin: float, fValMax: float):
        self.set_value({"min": fValMin, "max": fValMax})

    # enddef

    # #######################################################################################################
    def _OnSetValue(self):
        self._bBlockOnChange = True
        self.SetValue(self._fValMin, self._fValMax)
        self.update()
        self._bBlockOnChange = False

    # enddef

    # #######################################################################################################
    def _OnChanged(self, _xArgs: ValueChangeEventArguments):
        if self._bBlockOnChange is False:
            try:
                self._bBlockOnChange = True
                dicValues: dict[str, float] = _xArgs.args
                fValMin: float = dicValues["min"]
                fValMax: float = dicValues["max"]

                bValMinChanged: bool = fValMin != self._fValMin
                bValMaxChanged: bool = fValMax != self._fValMax

                bDoUpdate: bool = False
                fRange = fValMax - fValMin
                if self._fMinRange is not None and self._fMinRange > fRange:
                    if bValMinChanged is True:
                        fValMax = fValMin + self._fMinRange
                        if fValMax > self._fMax:
                            fValMax = self._fMax
                            fValMin = self._fMax - self._fMinRange
                        # endif
                    else:
                        fValMin = fValMax - self._fMinRange
                        if fValMin < self._fMin:
                            fValMin = self._fMin
                            fValMax = self._fMin + self._fMinRange
                        # endif
                    # endif
                    bDoUpdate = True
                elif self._fMaxRange is not None and self._fMaxRange < fRange:
                    if bValMinChanged is True:
                        fValMax = fValMin + self._fMaxRange
                        if fValMax > self._fMax:
                            fValMax = self._fMax
                            fValMin = self._fMax - self._fMaxRange
                        # endif
                    else:
                        fValMin = fValMax - self._fMaxRange
                        if fValMin < self._fMin:
                            fValMin = self._fMin
                            fValMax = self._fMin + self._fMaxRange
                        # endif
                    # endif
                    bDoUpdate = True
                # endif

                self._fValMin = fValMin
                self._fValMax = fValMax

                if self._funcOnChange is not None:
                    self._funcOnChange(_xArgs.sender, fValMin, fValMax, bValMinChanged, bValMaxChanged)
                # endif

                if bDoUpdate is True:
                    # Need to adapt the values of the range object
                    # after it finished updating. This only reliably
                    # works by creating a timer that changes the ui
                    # at a later time.
                    ui.timer(0.2, self._OnSetValue, once=True)
                # endif

            finally:
                self._bBlockOnChange = False
            # endtry
        # endif

    # enddef


# endclass
