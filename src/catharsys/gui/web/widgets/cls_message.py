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

import functools
import traceback
import enum
from nicegui import ui, Tailwind, events
from dataclasses import dataclass


class EMessageType(enum.Enum):
    INFO = enum.auto()
    WARNING = enum.auto()
    ERROR = enum.auto()
    EXCEPTION = enum.auto()


# endclass


@dataclass
class CMessageDialogSettings:
    sTitle: str = None
    sIcon: str = None
    sBgColor: str = None
    sNotifyType: str = None


# endclass


class CMessage:
    def __init__(self, _uiMain: ui.element = None):
        self.dicMessageTypeDlgCfg: dict[EMessageType, CMessageDialogSettings] = {
            EMessageType.INFO: CMessageDialogSettings(
                sTitle="Info", sIcon="info", sBgColor="primary", sNotifyType="info"
            ),
            EMessageType.WARNING: CMessageDialogSettings(
                sTitle="Warning", sIcon="report_problem", sBgColor="amber-500", sNotifyType="warning"
            ),
            EMessageType.ERROR: CMessageDialogSettings(
                sTitle="Error", sIcon="report_problem", sBgColor="red-500", sNotifyType="negative"
            ),
            EMessageType.EXCEPTION: CMessageDialogSettings(
                sTitle="Exception", sIcon="thunderstorm", sBgColor="fuchsia-600", sNotifyType="negative"
            ),
        }

        self.dlgMain: ui.dialog = ui.dialog()
        self.bWaitShown: bool = False
        # self.dlgWait: ui.dialog = ui.dialog().props("persistent")
        self.uiMain: ui.element = _uiMain

    # enddef

    # #############################################################################################
    def _CreateCallback_SubmitDialogResult(self, _dlgX: ui.dialog, _sResult: str):
        def Submit():
            _dlgX.submit(_sResult)

        # enddef
        return Submit

    # enddef

    # #############################################################################################
    def _ProvideDialog(self) -> ui.dialog:
        self.dlgMain.close()
        self.dlgMain.clear()
        self.bWaitShown = False

        self.dlgMain.props(remove="persistent maximized fullWidth")
        return self.dlgMain
    # enddef

    # #############################################################################################
    def _CloseDialog(self):
        self.dlgMain.close()
    # enddef

    # #############################################################################################
    async def AskOptions(self, _sText: str, _lOptions: list[str]):

        dlgQuestion = self._ProvideDialog()
        with dlgQuestion:
            with ui.card():
                with ui.row().classes("w-full"):
                    with ui.column().classes("items-center"):
                        with ui.row():
                            ui.icon("question_mark", size="xl")
                        # endwith
                    # endwith

                    with ui.column().classes("items-center"):
                        with ui.row():
                            ui.label(_sText)
                        # endwith
                        with ui.row():
                            for sOption in _lOptions:
                                ui.button(
                                    sOption, on_click=self._CreateCallback_SubmitDialogResult(dlgQuestion, sOption)
                                )
                            # endfor
                        # endwith row
                    # endwith column
                # endwith main row
            # wndwith card
        # endwith dialog

        sResult = await dlgQuestion
        return sResult

    # enddef

    # #############################################################################################
    async def AskYesNo(self, _sText: str, *, _bShowCancelOption: bool = False):
        lOptions: list[str] = ["Yes", "No"]
        if _bShowCancelOption is True:
            lOptions.append("Cancel")
        # endif
        return await self.AskOptions(_sText, lOptions)

    # enddef

    # #############################################################################################
    def ShowMessageScreen(self, *, _sText: str, _sIcon: str):
        dlgMsg = self._ProvideDialog().props("persistent maximized")
        # Tailwind().background_color("white").apply(dlgMsg)
        with dlgMsg:
            with ui.card().classes("bg-primary text-white"):
                with ui.column().classes("w-full") as colMain:
                    colMain.style("position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);")
                    ui.icon(_sIcon, size="xl").tailwind.align_self("center")
                    ui.label(_sText).tailwind.font_size("xl").align_self("center")
                # endwith
            # endwith
        # endwith dialog
        dlgMsg.open()

    # enddef

    # #############################################################################################
    def _CreateMessageDialog(self, _sText: str, *, _eType: EMessageType = EMessageType.INFO) -> ui.dialog:
        xDlgCfg = self.dicMessageTypeDlgCfg.get(_eType)
        if xDlgCfg is None:
            xDlgCfg = self.dicMessageTypeDlgCfg[EMessageType.EXCEPTION]
            _eType = EMessageType.EXCEPTION
        # endif

        # if _eType == EMessageType.EXCEPTION:
        #     sWidth = "3/4"
        # else:
        #     sWidth = "1/2"
        # # endif

        lLines: list[str] = _sText.splitlines()
        # with self.uiMain:
        dlgMsg = self._ProvideDialog().props("persistent")
        if _eType == EMessageType.EXCEPTION:
            dlgMsg.props("fullWidth")
        # endif

        with dlgMsg:
            cardDlg = ui.card().tight().classes("w-full")
            Tailwind().background_color(xDlgCfg.sBgColor).apply(cardDlg)
            with cardDlg:
                with ui.card_section().classes("row items-center"):
                    ui.label(xDlgCfg.sTitle).classes("text-h6")
                    ui.element("q-space")
                    ui.icon(xDlgCfg.sIcon, size="lg").props("flat round dense")
                # endwith
                with ui.card_section().classes("w-full"):
                    logX = ui.log().classes("w-full h-80")
                    for sLine in lLines:
                        logX.push(sLine)
                    # endfor
                # endwith
                with ui.card_actions().props("align=right").classes(f"{xDlgCfg.sBgColor} text-teal"):
                    ui.button("Close", on_click=dlgMsg.close).props("flat")
                # endwith
            # endwith
        # endwith
        # endwith

        return dlgMsg

    # enddef

    # #############################################################################################
    async def _OnCopyText(self, _sText: str, _xArgs: events.ClickEventArguments = None):
        sCmd = f'navigator.clipboard.writeText("{_sText}")'
        # print(f">>> Command:\n {sCmd}")
        await ui.run_javascript(sCmd)
        await self.AsyncShowMessage("Dialog box text copied to clipboard", _eType=EMessageType.INFO, _bDialog=False)

    # enddef

    # #############################################################################################
    def _CreateMessageNotify(self, _sText: str, *, _eType: EMessageType = EMessageType.INFO) -> ui.dialog:
        xDlgCfg = self.dicMessageTypeDlgCfg.get(_eType)
        if xDlgCfg is None:
            xDlgCfg = self.dicMessageTypeDlgCfg[EMessageType.EXCEPTION]
        # endif

        return ui.notify(_sText, type=xDlgCfg.sNotifyType, color=xDlgCfg.sBgColor)

    # enddef

    # #############################################################################################
    def ShowMessage(self, _sText: str, *, _eType: EMessageType = EMessageType.INFO, _bDialog: bool = True):
        if _bDialog is True:
            dlgMsg = self._CreateMessageDialog(_sText, _eType=_eType)
            dlgMsg.open()
        else:
            self._CreateMessageNotify(_sText, _eType=_eType)
        # endif

    # enddef

    # #############################################################################################
    async def AsyncShowMessage(self, _sText: str, *, _eType: EMessageType = EMessageType.INFO, _bDialog: bool = True):
        if _bDialog is True:
            dlgMsg = self._CreateMessageDialog(_sText, _eType=_eType)
            await dlgMsg
        else:
            self._CreateMessageNotify(_sText, _eType=_eType)
        # endif

    # enddef

    # #############################################################################################
    def GetExceptionText(self, _sText: str, _xEx: Exception) -> str:
        sMsg = "> ".join(traceback.format_exception(_xEx))
        return f"EXCEPTION {_sText}\n{(str(_xEx))}\n======================================\n\n{sMsg}\n"

    # enddef

    # #############################################################################################
    def ShowException(self, _sText: str, _xEx: Exception):
        self.ShowMessage(self.GetExceptionText(_sText, _xEx), _eType=EMessageType.EXCEPTION)
        # if self.uiMain is not None:
        #     with self.uiMain:
        #         ui.timer(0.1, functools.partial(self._OnCopyText, _sText), once=True)
        #     # endwith
        # # endif

    # endif

    # #############################################################################################
    async def AsyncShowException(self, _sText: str, _xEx: Exception):
        sMsg = self.GetExceptionText(_sText, _xEx)
        await self.AsyncShowMessage(sMsg, _eType=EMessageType.EXCEPTION)
        # if self.uiMain is not None:
        #     with self.uiMain:
        #         ui.timer(0.1, functools.partial(self._OnCopyText, sMsg), once=True)
        #     # endwith
        # # endif

    # endif

    # #############################################################################################
    def ShowWait(self, _sText: str = None):
        dlgWait = self._ProvideDialog().props("persistent")
        with dlgWait:
            with ui.card().classes("w-64"):
                with ui.column().classes("w-full items-center"):
                    with ui.row():
                        ui.spinner("dots", size="xl", color="primary")
                    # endwith
                    if isinstance(_sText, str):
                        with ui.row():
                            ui.label(_sText)
                        # endwith
                    # endif
                # endwith column
            # endwith card
        # endwith dialog
        self.bWaitShown = True
        dlgWait.open()


    # enddef

    # #############################################################################################
    def HideWait(self):
        if self.bWaitShown is True:
            self._CloseDialog()
            self.bWaitShown = False
        # endif
        
    # enddef


# endclass
