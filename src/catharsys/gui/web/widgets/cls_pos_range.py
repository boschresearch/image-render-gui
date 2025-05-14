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

import enum
import math
from typing import Any, Callable, Optional

from nicegui.events import ValueChangeEventArguments
from nicegui.element import Element
from nicegui import ui

from .cls_range import CRange


class EPosRangeStyle(enum.Enum):
    ROW = enum.auto()
    STACKED = enum.auto()
    INTEGRATED = enum.auto()


# endclass


class CPosRange:
    def __init__(
        self,
        *,
        _fMin: float,
        _fMax: float,
        _fValueMin: float,
        _fValueMax: float,
        _fRangeMin: float,
        _fRangeMax: float,
        _fStep: float = 1.0,
        _eStyle: EPosRangeStyle = EPosRangeStyle.ROW,
        _sLabel: str = "Value",
        _funcOnChanged: Optional[Callable[[Element, float, float, bool], Any]] = None,
        _bUseRangeStep: bool = False,
    ) -> None:
        self._fMin: float = _fMin
        self._fMax: float = _fMax
        self._fValMin: float = _fValueMin
        self._fValMax: float = _fValueMax
        self._fStep: float = _fStep
        self._eStyle: EPosRangeStyle = _eStyle
        self._sLabel: str = _sLabel
        self._bUseRangeStep: bool = _bUseRangeStep

        if _fRangeMin is not None and _fRangeMax is not None and _fRangeMin > _fRangeMax:
            fVal = _fRangeMin
            _fRangeMin = _fRangeMax
            _fRangeMax = fVal
        # endif

        self._bHasIntStep: bool = math.remainder(self._fStep, 1.0) < 1e-12

        self._fRangeMin: float = _fRangeMin
        self._fRangeMax: float = _fRangeMax
        self._funcOnChange: Optional[Callable[[Element, float, float, bool], Any]] = _funcOnChanged
        self._bBlockOnChange: bool = False

        self._fPos: float = self._fValMin
        self._fRange: float = self._fValMax - self._fValMin
        if self._bHasIntStep is True:
            self._fRange += self._fStep
        # endif

        self._fRange = min(max(self._fRange, self._fRangeMin), self._fRangeMax)

        self._fValMax = self._fValMin + self._fRange
        if self._bHasIntStep is True:
            self._fValMax -= self._fStep
        # endif
        self._uiMain: ui.element

        if self._eStyle == EPosRangeStyle.STACKED:
            self._uiMain = ui.card().tight().props("flat bordered").classes("w-full q-pa-md q-pb-lg")
            with self._uiMain:
                self._CreateSliderPos()
                self._CreateSliderRange()
            # endwith column
        elif self._eStyle == EPosRangeStyle.ROW:
            self._uiMain = ui.grid(columns=2).classes("w-full q-pa-md q-pb-lg").style("gap: 20px;")
            with self._uiMain:
                with ui.element("div").classes("w-full"):
                    self._CreateSliderPos()
                # endwith

                with ui.element("div").classes("w-full"):
                    self._CreateSliderRange()
                # endwith
            # endwith stacked

        elif self._eStyle == EPosRangeStyle.INTEGRATED:
            ui.badge(_sLabel, color="secondary")
            self._uiMain = CRange(
                _fMin=self._fMin,
                _fMax=self._fMax,
                _fValueMin=self._fValMin,
                _fValueMax=self._fValMax,
                _fStep=self._fStep,
                _fRangeMin=self._fRangeMin,
                _fRangeMax=self._fRangeMax,
                _funcOnChanged=self._OnIntegratedPosRangeChange,
            )

        # endif

    # enddef

    @property
    def fValueMin(self) -> float:
        return self._fValMin

    # enddef

    @property
    def fValueMax(self) -> float:
        return self._fValMax

    # enddef

    @property
    def fPosition(self) -> float:
        return self._fPos

    # enddef

    @property
    def fRange(self) -> float:
        return self._fRange

    # enddef

    # ####################################################################################################
    def _GetPosText(self):
        if self._bHasIntStep is True:
            iMin = int(self._fValMin)
            iMax = int(self._fValMax)
            iTotalMin = int(self._fMin)
            iTotalMax = int(self._fMax)
            return f"{self._sLabel}: {iMin} to {iMax} from [{iTotalMin}, {iTotalMax}]"
        else:
            return f"{self._sLabel}: {self._fValMin} to {self._fValMax} from [{self._fMin}, {self._fMax}]"
        # endif

    # enddef

    # ####################################################################################################
    def _GetRangeText(self):
        if self._bHasIntStep is True:
            iRange = int(self._fRange)
            return f"{self._sLabel} Count: {iRange}"
        else:
            return f"{self._sLabel} Range: {self._fRange}"
        # endif

    # enddef

    # ####################################################################################################
    def _CreateSliderPos(self):
        self._uiBadgePos: ui.badge = ui.badge(self._GetPosText(), color="secondary")
        fMax = self._fMax - self._fRange
        if self._bHasIntStep is True:
            fMax += self._fStep
        # endif

        if self._bUseRangeStep:
            fStep = self._fRange
        else:
            fStep = self._fStep
        # endif

        self._uiSliderPos: ui.slider = (
            ui.slider(
                min=self._fMin,
                max=fMax,
                step=fStep,
                value=self._fValMin,
                on_change=self._OnChangePos,
            )
            .props("label dense color=light-green")
            .on("change", self._OnPosChanged, [None], throttle=0.05)
        )

    # enddef

    # ####################################################################################################
    def _CreateSliderRange(self):
        self._uiBadgeRange: ui.badge = ui.badge(self._GetRangeText(), color="secondary")
        self._uiSliderRange: ui.slider = (
            ui.slider(
                min=self._fRangeMin,
                max=self._fRangeMax,
                step=self._fStep,
                value=self._fRange,
                on_change=self._OnChangeRange,
            )
            .props("label dense color=red")
            .style("padding-top: 0px")
            .on("change", self._OnRangeChanged, [None], throttle=0.05)
        )

    # enddef

    # ####################################################################################################
    def SetValuesMinMax(self, _fMin: float, _fMax: float):
        fMin = max(_fMin, self._fMin)
        fMax = min(_fMax, self._fMax)

        fMin = math.trunc(fMin / self._fStep) * self._fStep
        fMax = math.trunc(fMax / self._fStep) * self._fStep

        if self._eStyle == EPosRangeStyle.INTEGRATED:
            uiRange: CRange = self._uiMain
            uiRange.SetValue(fMin, fMax)
        else:
            self._uiSliderPos.set_value(fMin)
            self._uiSliderRange.set_value(fMax - fMin)
        # endif

    # enddef

    # ####################################################################################################
    def _OnChangePos(self, _xArgs: ValueChangeEventArguments):
        self._fValMin = self._fPos = float(_xArgs.value)
        self._fValMax = self._fValMin + self._fRange
        if self._bHasIntStep is True:
            self._fValMax -= self._fStep
        # endif

        self._fValMax = min(self._fValMax, self._fMax)

        self._uiBadgePos.set_text(self._GetPosText())

    # enddef

    # ####################################################################################################
    def _OnChangeRange(self, _xArgs: ValueChangeEventArguments):
        self._fRange = float(_xArgs.value)
        self._fValMax: float = self._fValMin + self._fRange
        if self._bHasIntStep is True:
            self._fValMax -= self._fStep
        # endif

        if self._fValMax > self._fMax:
            self._fValMin = self._fValMax - self._fRange
            if self._bHasIntStep is True:
                self._fValMin += self._fStep
            # endif
        # endif

        self._uiBadgeRange.set_text(self._GetRangeText())

    # enddef

    # ####################################################################################################
    def _OnPosChanged(self, _xArgs: ValueChangeEventArguments):
        if self._funcOnChange is not None:
            self._funcOnChange(_xArgs.sender, self._fValMin, self._fValMax, False)
        # endif

    # enddef

    # ####################################################################################################
    def _OnRangeChanged(self, _xArgs: ValueChangeEventArguments):
        fPosMax: float = self._fMax - self._fRange

        if self._bUseRangeStep:
            fStep = self._fRange
            if self._bHasIntStep is True:
                fPosMax += 1
            # endif
        else:
            fStep = self._fStep
            if self._bHasIntStep is True:
                fPosMax += fStep
            # endif
        # endif


        fPosMax = min(fPosMax, self._fMax)

        self._uiSliderPos._props["max"] = fPosMax
        self._uiSliderPos._props["step"] = fStep
        self._fValMin = self._fPos = min(self._fValMin, fPosMax)
        self._uiSliderPos.set_value(self._fValMin)
        self._uiSliderPos.update()

        if self._funcOnChange is not None:
            self._funcOnChange(_xArgs.sender, self._fValMin, self._fValMax, True)
        # endif

    # enddef

    # ####################################################################################################
    def _OnIntegratedPosRangeChange(
        self,
        _uiElement: Element,
        _fValMin: float,
        _fValMax: float,
        _bValMinChanged: bool,
        _bValMaxChanged: bool,
    ):
        self._fValMin = _fValMin
        self._fValMax = _fValMax
        self._fRange = self._fValMax - self._fValMin
        if self._bHasIntStep is True:
            self._fRange += self._fStep
        # endif

        bRangeChanged: bool = self._fPos == self._fValMin
        self._fPos = self._fValMin

        if self._funcOnChange is not None:
            self._funcOnChange(_uiElement, self._fValMin, self._fValMax, bRangeChanged)
        # endif

    # enddef


# endclass
