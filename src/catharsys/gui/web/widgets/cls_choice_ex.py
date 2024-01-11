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
from nicegui.events import ClickEventArguments, GenericEventArguments
from nicegui.elements.mixins.value_element import ValueElement
from nicegui.elements.mixins.disableable_element import DisableableElement
from nicegui import ui

from typing import Any, Callable, Dict, List, Optional, Union

from catharsys.api.products.cls_category import CCategoryTypeBoolGroup

# ##################################################################################################
# This file is work in progress!
#
# This is an extension of the original nicegui ChoiceElement class.
# It adds slot ids, so that every choice can be styled in a correpsponding slot.
# The last, commented out class in this file, gives an example of how to use this class.
# ##################################################################################################


class ChoiceElementEx(ValueElement):
    def __init__(
        self,
        *,
        tag: Optional[str] = None,
        options: Union[List, Dict],
        value: Any,
        on_change: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.options = options
        self._values: List[str] = []
        self._labels: List[str] = []
        self._update_values_and_labels()
        super().__init__(tag=tag, value=value, on_value_change=on_change)
        self._update_options()

    def _update_values_and_labels(self) -> None:
        self._values = self.options if isinstance(self.options, list) else list(self.options.keys())
        self._labels = self.options if isinstance(self.options, list) else list(self.options.values())

    def _update_options(self) -> None:
        before_value = self.value
        self._props["options"] = [
            {"value": index, "slot": str(index)}
            for index, option in enumerate(self._labels)
            # {"value": index, "label": option, "slot": str(index)} for index, option in enumerate(self._labels)
        ]
        if not isinstance(before_value, list):  # NOTE: no need to update value in case of multi-select
            self._props[self.VALUE_PROP] = self._value_to_model_value(before_value)
            self.value = before_value if before_value in self._values else None

    def update(self) -> None:
        self._update_values_and_labels()
        self._update_options()
        super().update()

    def set_options(self, options: Union[List, Dict], *, value: Any = None) -> None:
        """Set the options of this choice element.

        :param options: The new options.
        :param value: The new value. If not given, the current value is kept.
        """
        self.options = options
        if value is not None:
            self.value = value
        self.update()


class ToggleEx(ChoiceElementEx, DisableableElement):
    def __init__(
        self,
        options: Union[List, Dict],
        *,
        value: Any = None,
        on_change: Optional[Callable[..., Any]] = None,
        clearable: bool = False,
    ) -> None:
        """Toggle

        This element is based on Quasar's `QBtnToggle <https://quasar.dev/vue-components/button-toggle>`_ component.

        The options can be specified as a list of values, or as a dictionary mapping values to labels.
        After manipulating the options, call `update()` to update the options in the UI.

        :param options: a list ['value1', ...] or dictionary `{'value1':'label1', ...}` specifying the options
        :param value: the initial value
        :param on_change: callback to execute when selection changes
        :param clearable: whether the toggle can be cleared by clicking the selected option
        """
        super().__init__(tag="q-btn-toggle", options=options, value=value, on_change=on_change)
        self._props["clearable"] = clearable

    def _event_args_to_value(self, e: GenericEventArguments) -> Any:
        return self._values[e.args] if e.args is not None else None

    def _value_to_model_value(self, value: Any) -> Any:
        return self._values.index(value) if value in self._values else None


##############################################################################################


# class CUiBoolGroup(ToggleEx):
#     def __init__(
#         self,
#         _xCatBoolGrp: CCategoryTypeBoolGroup,
#         *,
#         _iValue: int = None,
#         _bVertical: bool = False,
#         _funcOnChange: Optional[Callable[[int], Any]] = None,
#     ):
#         super().__init__(list(range(len(_xCatBoolGrp.lChoices))), value=_iValue, on_change=_funcOnChange)
#         sProps = "dense"
#         if _bVertical is True:
#             sProps += " stack"
#         # endif
#         self.props(sProps)
#         with self:
#             for iIdx, xChoice in enumerate(_xCatBoolGrp.lChoices):
#                 with self.add_slot(str(iIdx)):
#                     sProps: str = f"name={xChoice.sIcon}"
#                     if len(xChoice.sColor) > 0:
#                         sProps += f" color={xChoice.sColor}"
#                     # endif

#                     ui.element("q-icon").props(sProps).style("font-size: 1rem; margin: 1px; padding: 1px;")
#                     ui.tooltip(xChoice.sDescription)
#                     # endwith
#                 # endwith
#             # endfor
#         # endwith

#     # enddef


# # endclass
