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


import functools
from nicegui import ui, Tailwind, events
from typing import Callable, Optional

from catharsys.api.action.cls_action_handler import CActionHandler, EJobStatus
from catharsys.config.cls_exec_job import CConfigExecJob

from anybase.cls_process_group_handler import EProcessStatus
from anybase.cls_process_output import CProcessOutput

from .cls_message import CMessage, EMessageType


class CJobInfo:
    def __init__(
        self,
        *,
        _uiGrid: ui.grid,
        _xActHandler: CActionHandler,
        _funcOnClose: Optional[Callable[[None], None]] = None,
        _funcOnStart: Optional[Callable[[None], None]] = None,
        _funcOnEnd: Optional[Callable[[None], None]] = None,
    ):
        self._uiGridMain: ui.grid = _uiGrid
        self._xActHandler: CActionHandler = _xActHandler
        self._funcOnClose: Callable[[None], None] = _funcOnClose
        self._funcOnStart: Callable[[None], None] = _funcOnStart
        self._funcOnEnd: Callable[[None], None] = _funcOnEnd

        self._dicJobOutputTypeText: dict[str, list[str]] = dict()
        self._iDisplayJobIdx: int = 0
        self._bEnableJobOutputAutoScroll: bool = True

        self._dicJobStatusIconName: dict[EProcessStatus, str] = {
            EJobStatus.NOT_STARTED: "schedule",
            EJobStatus.STARTING: "trending_up",
            EJobStatus.RUNNING: "mediation",
            EJobStatus.ENDED: "done",
            EJobStatus.TERMINATED: "close",
        }

        self._xMessage = CMessage()

        self._iJobUpdateIndex: int = 0

        # Create UI Elements
        self._uiTimerJobUpdate = ui.timer(1.0, lambda: self._JobsUpdate(), active=False)
        self._lbutJobStatus: list[ui.button] = []
        with self._uiGridMain:
            ui.label(f"Action: {self._xActHandler.xAction.sAction}")
            with ui.grid(columns=3):
                self._butLaunch = ui.button("Launch", on_click=self.Launch)
                self._butTerminate = ui.button("Terminate", on_click=self.TerminateAll)
                if self._funcOnClose is not None:
                    self._butClose = ui.button("Close", on_click=self._funcOnClose)
                else:
                    self._butClose = None
                # endif
            # endwith
            twCtrlButStyle = Tailwind().width("40")
            twCtrlButStyle.apply(self._butLaunch)
            twCtrlButStyle.apply(self._butTerminate)
            if self._butClose is not None:
                twCtrlButStyle.apply(self._butClose)
            # endif
            self._butTerminate.disable()

            self._uiBadgeAlive = ui.element("q-badge").props("color=red rounded").classes("q-mr-sm")
            with self._uiBadgeAlive:
                self._labStatus = ui.label("Status: n/a")
            # endwith
            self._rowJobStatus = ui.row()
            ui.separator()
            self._labJobSectionTitle = ui.label("Selected Job")
            self._rowJobInfo = ui.row()
            self._labJobOutput = ui.label("Job Output")
            self._rowJobOutput = ui.row()

        # endwith

    # enddef

    # #####################################################################################################
    def _CreateJobOutput(self):
        self._dicJobOutputTypeText.clear()
        lOutTypes = self._xActHandler.GetJobOutputTypes()
        iJobCnt = self._xActHandler.iJobCount
        self._dicScrlJobOutput: dict[str, ui.scroll_area] = dict()
        self._dicHtmlJobOutput: dict[str, ui.html] = dict()

        self._rowJobOutput.clear()
        with self._rowJobOutput:
            sOutType: str = None
            for sOutType in lOutTypes:
                self._dicJobOutputTypeText[sOutType] = [""] * iJobCnt
                with ui.expansion(sOutType, icon="description").props("switch-toggle-side").classes("w-full"):
                    uiCard = ui.card()
                    Tailwind().width("full").height("100").apply(uiCard)

                    with uiCard:
                        self._dicScrlJobOutput[sOutType] = ui.scroll_area(
                            on_scroll=lambda xArgs: self._OnScrollJobOutput(xArgs)
                        )
                        with self._dicScrlJobOutput[sOutType]:
                            self._dicHtmlJobOutput[sOutType] = ui.html("<pre><code>n/a</code></pre>")
                        # endwith scroll area
                    # endwith card
                # endwith expansion
            # endfor output type
        # endwith row

    # enddef

    # #####################################################################################################
    def _JobsUpdate(self):
        # print("> Job Update: START")
        self._iJobUpdateIndex += 1
        sColor: str = "green" if (self._iJobUpdateIndex % 2) == 0 else "blue"
        self._uiBadgeAlive.props(f"color={sColor}")
        self._uiBadgeAlive.update()

        self._xActHandler.UpdateJobOutput(_iMaxTime_ms=100)

        setJobsStatusChanged = self._xActHandler.GetJobStatusChanged()
        setJobOutChanged = self._xActHandler.GetJobOutputChanged()

        for iJobIdx in setJobsStatusChanged:
            eJobStatus: EJobStatus = self._xActHandler.GetJobStatus(iJobIdx)
            sIconName = self._dicJobStatusIconName[eJobStatus]
            self._lbutJobStatus[iJobIdx].props(f"icon={sIconName}")
            # print(f"[{iJobIdx}]: {eJobStatus}, {sIconName}")
            if eJobStatus == EJobStatus.TERMINATED:
                sEndMsg = self._xActHandler.GetJobEndMessage(iJobIdx)
                sMsg = "\n--- Job TERMINATED ---\n\n" + sEndMsg
                for sOutType in self._dicJobOutputTypeText:
                    self._dicJobOutputTypeText[sOutType][iJobIdx] += sMsg
                # endfor
                setJobOutChanged.add(iJobIdx)
            # endif
            if iJobIdx == self._iDisplayJobIdx:
                self._DisplayJobInfo()
            # endif
        # endfor

        # print(f"> Job Update: setJobOutChanged: {setJobOutChanged}")

        for iJobIdx in setJobOutChanged:
            for sOutType in self._dicJobOutputTypeText:
                xJobOut: CProcessOutput = self._xActHandler.GetJobOutput(iJobIdx, _sType=sOutType)
                lOutput = self._dicJobOutputTypeText[sOutType]
                sLine: str = None
                for sLine in xJobOut:
                    lOutput[iJobIdx] += sLine
                # endfor
            # endfor output type
        # endfor job index

        # print(f"> Job Update: self._iDisplayJobIdx: {self._iDisplayJobIdx}")
        if self._iDisplayJobIdx in setJobOutChanged:
            # print("> Job Update: Display Job Output")
            self._DisplayJobOutput()
        # endif
        # print("> Job Update: END")

    # enddef

    # #####################################################################################################
    def _DisplayJobOutput(self):
        sOutType: str = None
        for sOutType in self._dicJobOutputTypeText:
            htmlJobOutput = self._dicHtmlJobOutput[sOutType]
            scrlJobOutput = self._dicScrlJobOutput[sOutType]

            sText: str = self._dicJobOutputTypeText[sOutType][self._iDisplayJobIdx]
            if len(sText) == 0:
                sText = "--- no output ---"
            # endif
            htmlJobOutput.set_content("<pre><code>\n" + sText + "\n</code></pre>\n")
            htmlJobOutput.update()

            if self._bEnableJobOutputAutoScroll is True:
                scrlJobOutput.update()
                scrlJobOutput.scroll_to(percent=100.0)
                scrlJobOutput.update()
            # endif
        # endfor output type

    # enddef

    # #####################################################################################################
    def _DisplayJobInfo(self):
        xJobCfg: CConfigExecJob = self._xActHandler.GetJobConfig(self._iDisplayJobIdx)
        self._labJobSectionTitle.set_text(f"Selected Job: {xJobCfg.iIdx}: {xJobCfg.sName}")
        eJobStatus: EJobStatus = self._xActHandler.GetJobStatus(self._iDisplayJobIdx)

        dicJobInfo = self._xActHandler.GetJobInfo(self._iDisplayJobIdx)
        self._rowJobInfo.clear()
        with self._rowJobInfo:
            lCols = []
            dicRow = dict()
            for sTitle in dicJobInfo:
                lCols.append({"name": sTitle, "label": sTitle, "field": sTitle})
                dicRow[sTitle] = dicJobInfo[sTitle]
            # endfor
            ui.table(columns=lCols, rows=[dicRow], row_key="name")

            twButStyle = Tailwind().width("1").height("1")
            self._butDisplayJobTerminate = ui.button(
                icon="close", color="red", on_click=lambda: self._xActHandler.TerminateJob(self._iDisplayJobIdx)
            )
            if eJobStatus == EJobStatus.ENDED or eJobStatus == EJobStatus.TERMINATED:
                self._butDisplayJobTerminate.disable()
            else:
                self._butDisplayJobTerminate.enable()
            # endif

            twButStyle.apply(self._butDisplayJobTerminate)
        # endwith

    # enddef

    # #####################################################################################################
    def _OnScrollJobOutput(self, xArgs: events.ScrollEventArguments):
        # print(f"Vertical percentage: {xArgs.vertical_percentage}")
        self._bEnableJobOutputAutoScroll = xArgs.vertical_percentage >= 0.9
        # pass

    # enddef

    # #####################################################################################################
    def _JobsCreateStatus(self, iIdx: int, iCnt: int):
        self._labStatus.set_text(f"Status: creating configurations {iIdx}-{(iIdx+9)} of {iCnt}")

    # enddef

    # #####################################################################################################
    def _JobsExecStart(self):
        self._iJobUpdateIndex = 0
        self._uiBadgeAlive.props("color=yellow")

        iJobCnt = self._xActHandler.iJobCount
        self._labStatus.set_text(f"Status: processing {iJobCnt} jobs")
        self._iDisplayJobIdx = 0
        # iColumns: int = 10
        # self._rowJobStatus.style(replace=f"grid-template-columns:repeat({iColumns}, minmax(0, 1fr))")
        # self._rowJobStatus.update()
        twButStyle = Tailwind().width("1").height("1")

        with self._rowJobStatus:
            for iJobIdx in range(iJobCnt):
                butX = ui.button(
                    icon=self._dicJobStatusIconName[self._xActHandler.GetJobStatus(iJobIdx)],
                    on_click=self._CreateCallback_JobShowOutput(iJobIdx),
                )
                twButStyle.apply(butX)
                xJobCfg: CConfigExecJob = self._xActHandler.GetJobConfig(iJobIdx)
                butX.tooltip(f"{xJobCfg.iIdx}: {xJobCfg.sName}")
                self._lbutJobStatus.append(butX)
            # endfor
        # endwith

        self._CreateJobOutput()

        self._lbutJobStatus[self._iDisplayJobIdx].disable()
        self._bEnableJobOutputAutoScroll = True
        self._DisplayJobOutput()
        self._uiTimerJobUpdate.activate()

        if self._funcOnStart is not None:
            self._funcOnStart()
        # endif

    # enddef

    # #####################################################################################################
    def _JobsExecEnd(self):
        iJobCnt = self._xActHandler.iJobCount
        self._labStatus.set_text(f"Status: finished processing {iJobCnt} jobs")

        self._uiTimerJobUpdate.deactivate()
        self._JobsUpdate()

        if self._funcOnEnd is not None:
            self._funcOnEnd()
        # endif

        self._uiBadgeAlive.props("color=red")

    # enddef

    # #####################################################################################################
    def _CreateCallback_JobShowOutput(self, iJobIdx: int):
        def Callback():
            self._JobShowOutput(iJobIdx)

        # enddef
        return Callback

    # enddef

    # #####################################################################################################
    def _JobShowOutput(self, iJobIdx: int):
        if iJobIdx == self._iDisplayJobIdx:
            return
        # endif

        self._lbutJobStatus[self._iDisplayJobIdx].enable()
        self._iDisplayJobIdx = iJobIdx
        self._lbutJobStatus[self._iDisplayJobIdx].disable()

        xJobCfg: CConfigExecJob = self._xActHandler.GetJobConfig(self._iDisplayJobIdx)
        self._labJobOutput.set_text(f"Job {xJobCfg.iIdx}: {xJobCfg.sName} [{xJobCfg.sLabel}]")
        self._bEnableJobOutputAutoScroll = True

        self._DisplayJobInfo()
        self._DisplayJobOutput()

    # enddef

    # #####################################################################################################
    @staticmethod
    async def CallLaunch(_self: "CJobInfo"):
        await _self.Launch()

    # enddef

    async def Launch(self):
        self._butLaunch.disable()
        if self._butClose is not None:
            self._butClose.disable()
        # endif
        self._butTerminate.enable()
        self._rowJobStatus.clear()
        self._lbutJobStatus.clear()
        self._dicJobOutputTypeText.clear()

        try:
            await self._xActHandler.Launch(
                _funcCreateJobsStatus=lambda iIdx, iCnt: self._JobsCreateStatus(iIdx, iCnt),
                _funcJobExecStart=lambda: self._JobsExecStart(),
                _funcJobExecEnd=lambda: self._JobsExecEnd(),
            )
        except Exception as xEx:
            self._xMessage.ShowMessage(str(xEx), _eType=EMessageType.EXCEPTION)
        finally:
            self._butLaunch.enable()
            self._butTerminate.disable()
            if self._butClose is not None:
                self._butClose.enable()
            # endif
        # endtry

    # enddef

    # #####################################################################################################
    def TerminateAll(self):
        self._xActHandler.TerminateAll()

    # enddef


# endclass
