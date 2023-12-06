#!/usr/bin/env python3
# -*- coding:utf-8 -*-
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

import os
import re
import asyncio
from typing import Union, Optional
from nicegui import ui, events, app, Client, Tailwind

try:
    from nicegui.welcome import get_all_ips as GetAllIps
except Exception:
    from nicegui.welcome import _get_all_ips as GetAllIps
# endtry

from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta

from dataclasses import dataclass
from timeit import default_timer as timer
import functools

from anybase.cls_any_error import CAnyError_Message

import catharsys.api as capi
from catharsys.config.cls_variant_group import CVariantGroup
from catharsys.config.cls_variant_project import CVariantProject
from catharsys.config.cls_variant_trial import CVariantTrial
from catharsys.config.cls_variant_instance import CVariantInstance

from catharsys.api.action.cls_action_handler import CActionHandler
from catharsys.gui.web.widgets.cls_job_info import CJobInfo

from anybase import convert, config

from .login import CLogin

from ..widgets.cls_factory_value_control import CFactoryValueControl
from ..widgets.cls_value_grid import CValueGrid
from ..widgets.cls_tabs import CTabs
from ..widgets.cls_message import CMessage, EMessageType
from ..widgets.cls_variant_group_product_view import CVariantGroupProductView


@dataclass
class CLaunchInstance:
    sId: str = None
    sLabel: str = None
    xInstance: CVariantInstance = None
    xActHandler: CActionHandler = None
    xJobInfo: CJobInfo = None


# endclass


class CPageWorkspace:
    dicClients: dict[str, "CPageWorkspace"] = {}
    bIsRegistered: bool = False
    xLogin: CLogin = None

    def __init__(self, _wsX: capi.CWorkspace, _xClient: Client):
        self.selProject: ui.select = None
        self.selAction: ui.select = None
        self.labPrjInfo: ui.label = None
        self.labActInfo: ui.label = None
        self.gridGlobalLaunchArgs: ui.grid = None
        self.gridActionLaunchArgs: ui.grid = None

        self.vgGlobLaunchArgs: CValueGrid = None
        self.vgActLaunchArgs: CValueGrid = None
        self.dicLaunchGuiArgs: dict = None

        self.gridTrialLocals: ui.grid = None
        self.gridTrialGlobals: ui.grid = None
        self.gridTrialConfigs: ui.grid = None

        self.xWorkspace: capi.CWorkspace = _wsX
        self.xProject: capi.CProject = None
        self.xAction: capi.CAction = None
        self.xVariants: capi.CVariants = None
        self.xVariantGroup: CVariantGroup = None
        self.xVariantProject: CVariantProject = None
        self.xVariantTrial: CVariantTrial = None
        self.bVariantInfoChanged: bool = False
        self.bLaunchDataChanged: bool = False
        self.bTrialDataChanged: bool = False
        self.setBackgroundTasks: set[asyncio.Task] = set()

        self.iBlockOnChangeProjectVariant: int = 0
        self.iBlockOnChangeLaunchFileVariant: int = 0
        self.iBlockOnChangeTrialVariant: int = 0
        self.iBlockOnChangeTrial: int = 0
        self.iBlockOnChangeAction: int = 0

        self.dicProjectLaunchInstances: dict[str, dict[str, CLaunchInstance]] = dict()
        self.dicProjectProductViewer: dict[str, CVariantGroupProductView] = dict()

        self.sStyleTextTitle = "text-lg font-medium"
        self.sStyleTextDescSmall = "text-sm italic"
        self.sStyleSelect = "min-width: 11rem;"

        self.xCtrlFactory = CFactoryValueControl()
        self.lExcludeLAValRegEx = ["sDTI", "sTrialFile", "lTrialFileOptions", "sExecFile", "sInfo"]

        self.xClientId: str = _xClient.id
        CPageWorkspace.dicClients[self.xClientId] = self

        self.xMessage = CMessage()

    # enddef

    # #############################################################################################
    @staticmethod
    def OnDisconnect(xClient: Client):
        # print("on_disconnect")
        CPageWorkspace.RemoveClient(xClient)
        # print(f"Disconnecting: {xClient.id}")
        # print(CPageWorkspace.dicClients)

    # enddef

    # #############################################################################################
    @staticmethod
    def Register(_wsX: capi.CWorkspace, _xLogin: CLogin):
        if CPageWorkspace.bIsRegistered is True:
            raise RuntimeError("Workspace page already registered")
        # endif
        CPageWorkspace.bIsRegistered = True
        CPageWorkspace.xLogin = _xLogin

        app.on_disconnect(CPageWorkspace.OnDisconnect)

        @ui.page("/")
        # The argument MUST be called 'client'. If nicegui finds this parameter name in the
        # function interface it strips it and passes in the client object.
        # Arguments with other names are passed on to FastAPI.
        def page_main(client: Client) -> Optional[RedirectResponse]:
            xRedirect = CPageWorkspace.xLogin.TestAuthRedirect()
            if xRedirect is not None:
                return xRedirect
            # endif

            xPageWs = CPageWorkspace.dicClients.get(client.id)
            if xPageWs is None:
                xPageWs = CPageWorkspace(_wsX, client)
                xPageWs.Create()
            # endif

        # enddef

    # enddef

    # #############################################################################################
    @classmethod
    def RemoveClient(cls, xClient: Union[Client, str]):
        # print("Remove client")
        sClientId: str = None
        if isinstance(xClient, Client):
            sClientId = xClient.id
        elif isinstance(xClient, str):
            sClientId = xClient
        else:
            return
        # endif

        xPageWs = CPageWorkspace.dicClients.get(sClientId)
        if xPageWs is not None:
            xPageWs.OnRemove()
            xPageWs.xClientId = None
            del CPageWorkspace.dicClients[sClientId]
        # endif

    # enddef

    # #############################################################################################
    def __del__(self):
        # print("Destructor")
        CPageWorkspace.RemoveClient(self.xClientId)

    # enddef

    # #############################################################################################
    def OnLogout(self):
        if self.xLogin.Logout() is True:
            ui.open("/login")
        # endif

    # enddef

    # #############################################################################################
    def _GetProjectLaunchInstances(self) -> dict[str, CLaunchInstance]:
        sProjectName: str = str(self.selProject.value)
        dicLaunchInstances: dict[str, CLaunchInstance] = self.dicProjectLaunchInstances.get(sProjectName)
        if dicLaunchInstances is None:
            self.dicProjectLaunchInstances[sProjectName] = dict()
            dicLaunchInstances = self.dicProjectLaunchInstances[sProjectName]
        # endif
        return dicLaunchInstances

    # enddef

    # #############################################################################################
    def _CloseMenuItemFromEvent(self, _xArgs: events.ClickEventArguments):
        # Async message handler for menu items only work properly, if the menu item
        # does not use the "auto_close" feature. So, we have to close the menu item
        # explicitly, here.
        if isinstance(_xArgs.sender, ui.menu_item):
            uiItem: ui.menu_item = _xArgs.sender
            uiItem.menu.close()
        # endif

    # enddef

    # #############################################################################################
    async def _OnReload(self, _xArgs: events.ClickEventArguments, *, _bAll: bool, _bOverwrite: bool = False):
        try:
            sAll: str = "ALL" if _bAll else ""
            sOverwrite: str = "Overwriting" if _bOverwrite else "Updating"
            sResult = await self.xMessage.AskYesNo(f"{sOverwrite} {sAll} variant settings with original?")
            if sResult == "No":
                return
            # endif

            self.xMessage.ShowWait("Reloading Configurations")
            ui.timer(0.1, functools.partial(self._OnTimerReload, _bAll=_bAll, _bOverwrite=_bOverwrite), once=True)

        finally:
            self._CloseMenuItemFromEvent(_xArgs)
        # enddef

    # enddef

    # #############################################################################################
    async def _OnTimerReload(self, *, _bAll: bool, _bOverwrite: bool = False):
        try:
            self.Reload(_bAll=_bAll, _bOverwrite=_bOverwrite)
            self.xMessage.HideWait()
        except Exception as xEx:
            self.xMessage.HideWait()
            await self.xMessage.AsyncShowException("reloading configurations", xEx)
        # endtry

    # enddef

    # #############################################################################################
    def Reload(self, *, _bAll: bool, _bOverwrite: bool = False):
        sProjectName: str = str(self.selProject.value)
        iProjectVarId: int = int(self.selProjectVariant.value)
        iTrialVarId: int = int(self.selTrialVariant.value)
        sTrialName: str = str(self.selTrial.value)
        sActionPath: str = str(self.selAction.value)

        self.xWorkspace = capi.CWorkspace(xWorkspace=self.xWorkspace.pathWorkspace)
        self.Create.refresh()

        # Dummy loop to implement breaking
        while True:
            if sProjectName not in self.xWorkspace.lProjectNames:
                break
            # endif

            self.selProject.set_value(sProjectName)
            self.UpdateProject()

            if _bAll is True:
                self.xVariants.UpdateFromSource(_bOverwrite=_bOverwrite)
                self.xVariants.Serialize()
            # endif

            xVariantLaunch = self.xVariantGroup.GetProjectVariant(iProjectVarId)
            if xVariantLaunch is None:
                break
            # endif

            self.selProjectVariant.set_value(iProjectVarId)
            self.UpdateProjectVariant()

            xVariantTrial = self.xVariantProject.GetTrialVariant(iTrialVarId)
            if xVariantTrial is None:
                break
            # endif

            self.selTrialVariant.set_value(iTrialVarId)
            self.UpdateTrialVariant()

            if sTrialName not in self.xVariantTrial.xTrialActions.lTrialFiles:
                break
            # endif

            self.selTrial.set_value(sTrialName)
            self.UpdateTrial()

            xActData = self.xVariantTrial.xTrialActions.GetResolvedAction(sActionPath)
            if xActData is None:
                break
            # endif

            self.selAction.set_value(sActionPath)
            self.UpdateAction()
            break
        # endwhile dummy

        if _bAll is False:
            self.xVariantProject.UpdateFromSource(_bOverwrite=_bOverwrite)
            self.xVariants.Serialize()
            self.UpdateProject()
        # endif

    # enddef

    # #############################################################################################
    def ToggleDarkMode(self):
        if self._darkMode.value is True:
            self._darkMode.disable()
            self._mitDarkMode.set_text("Enable Dark Mode")
        else:
            self._darkMode.enable()
            self._mitDarkMode.set_text("Disable Dark Mode")
        # endif

    # enddef

    # #############################################################################################
    @ui.refreshable
    def Create(self):
        self._darkMode = ui.dark_mode()
        self._darkMode.enable()

        bIsAdmin: bool = self.xLogin.bIsAdmin
        sUsername: str = self.xLogin.sUsername
        if sUsername is None:
            sUsername = "INVALID"
        # endif

        # ui.label(f"User: {sUsername} - Client ID: {self.xClientId}").classes("text-xs")

        with ui.header(elevated=True):
            with ui.element("q-toolbar"):
                with ui.button(icon="menu", color="slate-400").props("flat round dense").classes("q-mr-sm"):
                    self._menuMain = ui.menu()
                    Tailwind().width("auto").apply(self._menuMain)
                    with self._menuMain:
                        self._mitDarkMode = ui.menu_item("Disable Dark Mode", on_click=lambda: self.ToggleDarkMode())
                        ui.separator()
                        ui.menu_item(
                            "Reload original configurations for all variants",
                            on_click=functools.partial(self._OnReload, _bAll=True),
                            auto_close=False,
                        )
                    # endwith
                # endwith
                with ui.element("q-toolbar-title"):
                    ui.html(f"Catharsys Workspace: {self.xWorkspace.sName} v{self.xWorkspace.sVersion}")
                # endwith
                with ui.button(icon="account_circle", color="slate-400").props("flat round dense"):
                    self._menuMain = ui.menu()
                    Tailwind().width("auto").apply(self._menuMain)
                    with self._menuMain:
                        ui.label(sUsername).classes("text-h6").style("padding: 4px")
                        ui.menu_item("Logout", on_click=self.OnLogout, auto_close=True)

                        if bIsAdmin is True:
                            ui.menu_item("Add User", on_click=self.OnAddUser, auto_close=True)
                        # endif
                        ui.separator()
                        ui.label(f"Client ID: {self.xClientId}").classes("text-xs").style("padding: 4px")
                    # endwith
                # endwith

            # endwith toolbar
            # ui.label(f"Workspace: {self.xWorkspace.sName} v{self.xWorkspace.sVersion}").classes("text-h4")
            # ui.markdown(
            #     f"""<br>Requires Catharsys v{self.xWorkspace.sRequiredCatharsysVersion},
            #             Active Catharsys v{self.xWorkspace.sCatharsysVersion}
            # """
            # ).classes(self.sStyleTextDescSmall + " mr-auto")
        # endwith

        # with ui.left_drawer(top_corner=False, bottom_corner=False):
        # # endwith left drawer
        self._uiRowMain = ui.row().classes("w-full")
        self.xMessage.uiMain = self._uiRowMain
        with self._uiRowMain:
            self._tabsMain = CTabs(_funcOnChange=self._OnSelectMainTab)
            self._tabsMain.uiTabs.classes("w-full").props("align=left")
            self._tabsMain.uiPanels.classes("w-full")

            lProjectNames = list(self.xWorkspace.lProjectNames)
            lProjectNames.sort()
            sActProjName = lProjectNames[0]

            self._sMainTabId: str = "main"
            with self._tabsMain.Add(_sName=self._sMainTabId, _sLabel="Workspace", _sIcon="home"):
                # ############################################################
                # Main page
                # with ui.grid(columns=1):
                #     with ui.column():
                #         ui.markdown(f"""Requires Catharsys v{self.wsX.sRequiredCatharsysVersion}<br>
                #                     Active Catharsys v{self.wsX.sCatharsysVersion}
                #         """).classes(self.sStyleTextDescSmall)
                #     # endwith
                # # endwith
                # with ui.grid(columns=1).classes("w-full"):
                with ui.element("q-list").props("padding").classes("w-full"):
                    with ui.card().classes("w-full"):
                        with ui.row().classes("w-full"):
                            with ui.button(icon="menu", color="slate-400").props("flat"):
                                with ui.menu():
                                    ui.menu_item("Save All", on_click=lambda: self.SaveProjectVariant())
                                    ui.menu_item(
                                        "Copy link to product view",
                                        on_click=self.OnCopyTempLinkToProductView,
                                        auto_close=True,
                                    )
                                    ui.separator()
                                    ui.menu_item("Add Project Variant", on_click=lambda: self.OnAddProjectVariant())
                                    ui.menu_item(
                                        "Remove Project Variant", on_click=self.OnRemoveProjectVariant, auto_close=False
                                    )
                                    ui.separator()
                                    ui.menu_item(
                                        "Update from original",
                                        on_click=functools.partial(self._OnReload, _bAll=False, _bOverwrite=False),
                                        auto_close=False,
                                    )
                                    ui.menu_item(
                                        "Overwrite with original",
                                        on_click=functools.partial(self._OnReload, _bAll=False, _bOverwrite=True),
                                        auto_close=False,
                                    )
                                # endwith
                            # endwith
                            ui.button(icon="visibility", on_click=self.ShowProducts)
                            self.selProject = (
                                ui.select(
                                    options=lProjectNames,
                                    value=sActProjName,
                                    on_change=lambda xArgs: self.OnChangeProject(xArgs),
                                )
                                .props("label=Configurations stack-label dense options-dense filled")
                                .style(self.sStyleSelect)
                            )
                            # Tailwind().width(self.sSelectWidth).apply(self.selProject)

                            self.selProjectVariant = (
                                ui.select(options=[], on_change=lambda xArgs: self.OnChangeProjectVariant(xArgs))
                                .props('label="Configuration Variant" stack-label dense options-dense filled')
                                .style(self.sStyleSelect)
                            )

                            self.uiInputPrjVarInfo = (
                                ui.input(
                                    label="Project variant info",
                                    placeholder="enter info text, use : to separate name from longer description",
                                    on_change=self._OnProjectVariantInfoChanged,
                                )
                                .props("stack-label dense")
                                .style("flex-grow: 100;")
                                .on("blur", self._OnUpdateProjectVariantNames)
                            )

                        # endwith
                        self._uiRowProjectInfo = ui.row().classes("w-full")
                        with self._uiRowProjectInfo:
                            ui.label("Project Info:")
                            self.labPrjInfo = ui.label("").classes(self.sStyleTextDescSmall)
                        # endwith
                    # endwith

                    ui.separator()

                    # ##################################################################################
                    # Launch file variant and global launch arguments
                    with ui.card():
                        with ui.row().classes("w-full"):
                            with ui.button(icon="menu", color="slate-400").props("flat"):
                                with ui.menu():
                                    ui.menu_item("Add Launch Variant", on_click=lambda: self.OnAddLaunchFileVariant())
                                    ui.menu_item(
                                        "Remove Launch Variant",
                                        on_click=self.OnRemoveLaunchFileVariant,
                                        auto_close=False,
                                    )
                                # endwith
                            # endwith

                            self.selLaunchFileVariant = (
                                ui.select(options=[], on_change=lambda xArgs: self.OnChangeLaunchFileVariant(xArgs))
                                .props('label="Launch Variant" stack-label dense options-dense filled')
                                .style(self.sStyleSelect)
                            )
                            with self.selLaunchFileVariant.add_slot("append"):
                                ui.button(icon="add", on_click=self.OnAddLaunchFileVariant).props("round dense flat")
                            # endwith

                            self.uiInputLfvInfo = (
                                ui.input(
                                    label="Launch variant info",
                                    placeholder="enter info text, use : to separate name from longer description",
                                    on_change=self._OnLaunchVariantInfoChanged,
                                )
                                .props("stack-label dense")
                                .style("flex-grow: 100;")
                                .on("blur", self._OnUpdateLfvNames)
                            )
                        # endwith

                        with ui.expansion("Global Launch Arguments", icon="description").props(
                            "switch-toggle-side"
                        ).classes("w-full"):
                            with ui.card():
                                # ui.label("Global Launch Arguments").classes(self.sStyleTextTitle)
                                # with ui.card_section():
                                self.gridGlobalLaunchArgs = ui.grid(columns=4)
                                # endwith section
                            # endwith card
                        # endwith expansion
                    # endwith

                    ui.separator()

                    # ##################################################################################
                    # Action selection and action arguments
                    with ui.card():
                        with ui.row().classes("w-full"):
                            # ui.label("Actions").classes(self.sStyleTextTitle)
                            self.selAction = (
                                ui.select(options=[], on_change=lambda xArgs: self.OnChangeAction(xArgs))
                                .props("label=Actions stack-label dense options-dense filled")
                                .style(self.sStyleSelect)
                            )
                            # Tailwind().width(self.sSelectWidth).apply(self.selAction)

                            self.butInstantiateVariant = ui.button(
                                "Prepare Launch", on_click=lambda: self.InstantiateVariant()
                            )
                        # endwith

                        self._uiRowActionInfo = ui.row().classes("w-full")
                        with self._uiRowActionInfo:
                            ui.label("Action Info:")
                            self.labActInfo = ui.label("").classes(self.sStyleTextDescSmall)
                        # endwith

                        with ui.expansion("Action Launch Arguments", icon="description").props(
                            "switch-toggle-side"
                        ).classes("w-full"):
                            with ui.card():
                                # ui.label("Action Launch Arguments").classes(self.sStyleTextTitle)
                                # with ui.card_section():
                                self.gridActionLaunchArgs = ui.grid(columns=4)
                                # endwith section
                            # endwith card
                        # endwith expansion
                    # endwith launch arguments card

                    ui.separator()

                    # ##################################################################################
                    # Trial Variant and Trial selection
                    with ui.card():
                        with ui.row().classes("w-full"):
                            with ui.button(icon="menu", color="slate-400").props("flat"):
                                with ui.menu():
                                    ui.menu_item("Add Trial Variant", on_click=lambda: self.OnAddTrialVariant())
                                    ui.menu_item(
                                        "Remove Trial Variant", on_click=self.OnRemoveTrialVariant, auto_close=False
                                    )
                                # endwith
                            # endwith

                            self.selTrialVariant = (
                                ui.select(options=[], on_change=lambda xArgs: self.OnChangeTrialVariant(xArgs))
                                .props('label="Trial Variant" stack-label dense options-dense filled')
                                .style(self.sStyleSelect)
                            )
                            # Tailwind().width(self.sSelectWidth).apply(self.selTrialVariant)
                            with self.selTrialVariant.add_slot("append"):
                                ui.button(icon="add", on_click=self.OnAddTrialVariant).props("round dense flat")
                            # endwith
                            # with self.selTrialVariant.add_slot("hint"):
                            #     ui.label("Select a trial variation")
                            # # endwith

                            self.selTrial = (
                                ui.select(options=[], on_change=lambda xArgs: self.OnChangeTrial(xArgs))
                                .props("label=Trials stack-label dense options-dense filled")
                                .style(self.sStyleSelect)
                            )

                            self.uiInputTrialVarInfo = (
                                ui.input(
                                    label="Trial variant info",
                                    placeholder="enter info text, use : to separate name from longer description",
                                    on_change=self._OnTrialVariantInfoChanged,
                                )
                                .props("stack-label dense")
                                .style("flex-grow: 100;")
                                .on("blur", self._OnUpdateTrialVariantNames)
                            )

                        # endwith row

                        self._uiRowTrialInfo = ui.row().classes("w-full")
                        with self._uiRowTrialInfo:
                            ui.label("Trial Info:")
                            self.labTrialInfo = ui.label("").classes(self.sStyleTextDescSmall)
                        # endwith row
                        self._uiRowTrialInfo.set_visibility(False)

                        with ui.expansion("Trial Arguments", icon="description").props("switch-toggle-side").classes(
                            "w-full"
                        ):
                            with ui.card():
                                with ui.element("q-list").props("padding").classes("w-full"):
                                    self.gridTrialLocals = ui.grid(columns=4).style("padding-top: 10px")
                                    self.gridTrialGlobals = ui.grid(columns=4).style("padding-top: 10px")
                                    self.gridTrialConfigs = ui.grid(columns=4).style("padding-top: 10px")
                                # endwith

                            # endwith card
                        # endwith expansion
                    # endwith

                # endwith main
            # endwith main tab
        # endwith row main

        # with ui.footer():
        #     sUsername = self.xLogin.sUsername
        #     if sUsername is None:
        #         sUsername = "INVALID"
        #     # endif

        #     ui.label(f"User: {sUsername} - Client ID: {self.xClientId}").classes("text-xs")
        # # endwith

        self.UpdateProject()

    # enddef

    # #############################################################################################
    def _OnUpdateProjectVariantNames(self, _xArgs: events.ValueChangeEventArguments):
        self.iBlockOnChangeProjectVariant += 1
        try:
            self._UpdateProjectVariantSelection(_xSel=self.selProjectVariant.value)
        finally:
            self.iBlockOnChangeProjectVariant -= 1
        # endtry

    # enddef

    # #############################################################################################
    def _OnUpdateLfvNames(self, _xArgs: events.ValueChangeEventArguments):
        self.iBlockOnChangeLaunchFileVariant += 1
        try:
            self._UpdateLaunchFileVariantSelection(_xSel=self.selLaunchFileVariant.value)
        finally:
            self.iBlockOnChangeLaunchFileVariant -= 1
        # endtry

    # enddef

    # #############################################################################################
    def _OnUpdateTrialVariantNames(self, _xArgs: events.ValueChangeEventArguments):
        self.iBlockOnChangeTrialVariant += 1
        try:
            self._UpdateTrialVariantSelection(_xSel=self.selTrialVariant.value)
        finally:
            self.iBlockOnChangeTrialVariant -= 1
        # endtry

    # enddef

    # #############################################################################################
    def _OnLaunchVariantInfoChanged(self, _xArgs: events.ValueChangeEventArguments):
        if self.iBlockOnChangeLaunchFileVariant == 0:
            iLaunchVarId = self.selLaunchFileVariant.value
            self.xVariantProject.dicLaunchFileInfo[iLaunchVarId] = str(self.uiInputLfvInfo.value)
            self.bVariantInfoChanged = True
        # endif

    # enddef

    # #############################################################################################
    def _OnProjectVariantInfoChanged(self, _xArgs: events.ValueChangeEventArguments):
        if self.iBlockOnChangeLaunchFileVariant == 0:
            self.xVariantProject.sInfo = str(self.uiInputPrjVarInfo.value)
            self.bVariantInfoChanged = True
        # endif

    # enddef

    # #############################################################################################
    def _OnTrialVariantInfoChanged(self, _xArgs: events.ValueChangeEventArguments):
        if self.iBlockOnChangeTrialVariant == 0:
            self.xVariantTrial.sInfo = str(self.uiInputTrialVarInfo.value)
            self.bVariantInfoChanged = True
        # endif

    # enddef

    # #############################################################################################
    def OnRemove(self):
        # print("On Remove")
        self.SaveProjectVariant()
        self.xVariants.Serialize()

        lProdViewIds = list(self.dicProjectProductViewer.keys())
        for sProdViewId in lProdViewIds:
            self.dicProjectProductViewer[sProdViewId].CleanUp()
        # endfor

    # enddef

    # #############################################################################################
    def OnAddUser(self, _xArgs: events.ClickEventArguments):
        with self._uiRowMain:
            ui.timer(0.2, self.DoAddUser, once=True)
        # endwith

    # enddef

    # #############################################################################################
    async def DoAddUser(self):
        try:
            sUrl = await ui.run_javascript("window.location.href")
            # print(sUrl)

            xMatch = re.match(r"^(http|https):\/\/(?P<ip>\d+\.\d+\.\d+\.\d+)(:(?P<port>\d+))*.*", sUrl)
            if xMatch is None:
                await self.xMessage.AsyncShowMessage("Error creating link", _eType=EMessageType.ERROR)
                return
            # endif

            sUrlType: str = xMatch.group(1)

            sHost: str = os.environ["NICEGUI_HOST"]
            sPort: str = os.environ["NICEGUI_PORT"]
            lIps: set[str] = set(GetAllIps() if sHost == "0.0.0.0" else [])
            # lIps.discard("127.0.0.1")
            lUrls: list[str] = []
            for sIp in lIps:
                lUrls.append(f"{sUrlType}://{sIp}:{sPort}/")
            # endfor

            dlgLink = ui.dialog().props("persistent")
            with dlgLink:
                with ui.card().style("width: 300px"):
                    with ui.card_section():
                        ui.label("Add User").classes("text-h6")
                    # endwith
                    with ui.input("Expiry data") as uiDate:
                        with uiDate.add_slot("append"):
                            ui.icon("edit_calendar").on("click", lambda: uiMenu.open()).classes("cursor-pointer")
                        # endwith
                        with ui.menu() as uiMenu:
                            dtInit = datetime.now() + timedelta(days=30)
                            sDataInit = dtInit.strftime("%Y-%m-%d")
                            uiDate.set_value(sDataInit)
                            ui.date(value=sDataInit).bind_value(uiDate)
                        # endwith
                    # endwith
                    uiSelUrl = ui.select(options=lUrls, label="URL Base", value=lUrls[0])
                    inUser = ui.input("Username")
                    with ui.row().classes("w-full"):
                        ui.button("Add User", on_click=lambda: dlgLink.submit("ok"))
                        ui.button("Cancel", on_click=lambda: dlgLink.submit("cancel"))
                    # endwith
                # endwith
            # endwith dialog
            sResult = await dlgLink

            if sResult == "ok":
                sLink = uiSelUrl.value
                # print(f"Link start: {sLink}")
                dtLinkExpire: datetime = datetime.now() + timedelta(minutes=10)

                # print(f"Date: {uiDate.value}")
                dateSel = datetime.strptime(uiDate.value, "%Y-%m-%d").date()
                dtExpire = datetime.combine(dateSel, datetime.utcnow().time())
                # print(f"Expire: {dtExpire}")
                sUsername: str = str(inUser.value)
                sBaseLink: str = f"resetpw/{sUsername}"
                sLinkId: str = self.xLogin.ProvidePublicLinkId(sBaseLink, dtLinkExpire)

                self.xLogin.AddUserTempPassword(sUsername, _dtExpire=dtExpire, _lRights=["default"])

                sLink += f"{sBaseLink}/{sLinkId}"
                await ui.run_javascript(f'navigator.clipboard.writeText("{sLink}")', respond=False)
                await self.xMessage.AsyncShowMessage(
                    "Link to user initial login copied to clipboard", _eType=EMessageType.INFO, _bDialog=False
                )
            else:
                await self.xMessage.AsyncShowMessage(
                    "Cancelled adding user", _eType=EMessageType.WARNING, _bDialog=False
                )
            # endif
        except Exception as xEx:
            await self.xMessage.AsyncShowException("adding user", xEx)
        # endtry

    # enddef

    # #############################################################################################
    def OnCopyTempLinkToProductView(self, _xArgs: events.ClickEventArguments):
        # self._CloseMenuItemFromEvent(_xArgs)
        with self._uiRowMain:
            ui.timer(0.2, self.DoCopyTempLinkToProductView, once=True)
        # endwith

    # enddef

    # #############################################################################################
    async def DoCopyTempLinkToProductView(self):
        try:
            sUrl = await ui.run_javascript("window.location.href")
            # print(sUrl)

            xMatch = re.match(r"^(http|https):\/\/(?P<ip>\d+\.\d+\.\d+\.\d+)(:(?P<port>\d+))*.*", sUrl)
            if xMatch is None:
                await self.xMessage.AsyncShowMessage("Error creating link", _eType=EMessageType.ERROR)
                return
            # endif

            sUrlType: str = xMatch.group(1)

            sHost: str = os.environ["NICEGUI_HOST"]
            sPort: str = os.environ["NICEGUI_PORT"]
            lIps: set[str] = set(GetAllIps() if sHost == "0.0.0.0" else [])
            # lIps.discard("127.0.0.1")
            lUrls: list[str] = []
            for sIp in lIps:
                lUrls.append(f"{sUrlType}://{sIp}:{sPort}/")
            # endfor

            dlgLink = ui.dialog().props("persistent")
            with dlgLink:
                with ui.card().style("width: 300px"):
                    with ui.card_section():
                        ui.label("Link Settings").classes("text-h6")
                    # endwith
                    with ui.input("Expiry data") as uiDate:
                        with uiDate.add_slot("append"):
                            ui.icon("edit_calendar").on("click", lambda: uiMenu.open()).classes("cursor-pointer")
                        # endwith
                        with ui.menu() as uiMenu:
                            dtInit = datetime.now() + timedelta(days=1)
                            sDataInit = dtInit.strftime("%Y-%m-%d")
                            uiDate.set_value(sDataInit)
                            ui.date(value=sDataInit).bind_value(uiDate)
                        # endwith
                    # endwith
                    uiSelUrl = ui.select(options=lUrls, label="URL Base", value=lUrls[0])
                    with ui.row().classes("w-full"):
                        ui.button("Create Link", on_click=lambda: dlgLink.submit("ok"))
                        ui.button("Cancel", on_click=lambda: dlgLink.submit("cancel"))
                    # endwith
                # endwith
            # endwith dialog
            sResult = await dlgLink

            if sResult == "ok":
                sLink = uiSelUrl.value
                # print(f"Link start: {sLink}")

                # print(f"Date: {uiDate.value}")
                dateSel = datetime.strptime(uiDate.value, "%Y-%m-%d").date()
                dtExpire = datetime.combine(dateSel, datetime.utcnow().time())
                # print(f"Expire: {dtExpire}")

                sProjectId: str = self.xVariants.xProject.sId.replace("/", "+")
                sGroupId: str = self.xVariantGroup.sGroup.replace("/", "+")
                sBaseLink: str = f"productview/{sProjectId}/{sGroupId}"
                sLinkId: str = self.xLogin.ProvidePublicLinkId(sBaseLink, dtExpire)

                sLink += f"{sBaseLink}/{sLinkId}"
                await ui.run_javascript(f'navigator.clipboard.writeText("{sLink}")', respond=False)
                await self.xMessage.AsyncShowMessage(
                    "Link to product view copied to clipboard", _eType=EMessageType.INFO, _bDialog=False
                )
            else:
                await self.xMessage.AsyncShowMessage(
                    "Cancelled link creation", _eType=EMessageType.WARNING, _bDialog=False
                )
            # endif
        except Exception as xEx:
            await self.xMessage.AsyncShowException("creating link", xEx)
        # endtry

    # enddef

    # #############################################################################################
    def OnChangeProject(self, _xArgs: events.ValueChangeEventArguments):
        # print(_xArgs)
        # print("OnChangeProject")

        self.UpdateProject()

    # enddef

    # #############################################################################################
    def UpdateProject(self):
        # Save any changes to current project before changing the project.
        # Only saves parts that need saving.
        self.SaveProjectVariant()

        self.iBlockOnChangeProjectVariant += 1
        try:
            sProjectName = self.selProject.value
            self.xProject = self.xWorkspace.Project(sProjectName)
            if len(self.xProject.sInfo) > 0:
                self._uiRowProjectInfo.set_visibility(True)
                self.labPrjInfo.set_text(self.xProject.sInfo)
            else:
                self._uiRowProjectInfo.set_visibility(False)
                self.labPrjInfo.set_text(" ")
            # endif

            self.xVariants = capi.CVariants(self.xProject)
            if not self.xVariants.HasGroup(self.xLogin.sUsername):
                self.xVariants.CreateGroup(self.xLogin.sUsername)
                self.xVariants.Serialize()
            # endif

            self.xVariantGroup = self.xVariants.GetGroup(self.xLogin.sUsername)
            self._UpdateProjectVariantSelection()

            self.UpdateProjectVariant()
            self.FindProjectVariantInstances()
            self.UpdateMainTabs()
        except Exception as xEx:
            self.xMessage.ShowException("updating project", xEx)
        finally:
            self.iBlockOnChangeProjectVariant -= 1
        # endtry

        # self.xTrialActions = CTrialActions(self.prjX.xLaunch)

        # lTrials = self.xTrialActions.lTrialFiles
        # self.selTrial.options = lTrials
        # self.selTrial.update()
        # self.selTrial.set_value(lTrials[0])

        # self.vgGlobLaunchArgs = CValueGrid(_gridData=self.gridGlobalLaunchArgs,
        #                                    _dicValues=self.xTrialActions.dicGlobalArgs,
        #                                    _xCtrlFactory=self.xCtrlFactory,
        #                                    _lExcludeRegEx=self.lExcludeLAValRegEx)

        # self.UpdateTrial()

    # enddef

    # ######################################################################################################
    def _GetShortInfo(self, _sInfo: str, _iId: int) -> str:
        sInfo = _sInfo
        if ":" in sInfo:
            sInfo = sInfo[0 : sInfo.index(":")]
        elif "." in sInfo:
            sInfo = sInfo[0 : sInfo.index(".")]
        # endif
        if len(sInfo) == 0:
            sInfo = f"{_iId}"
        # endif
        return sInfo

    # endif

    # #############################################################################################
    def _UpdateProjectVariantSelection(self, *, _xSel: int = None):
        lProjectVarIds = self.xVariantGroup.lProjectVariantIds

        dicPrjVarOptions: dict[int, str] = dict()
        iPrjVarId: int
        for iPrjVarId in lProjectVarIds:
            xPrjVar = self.xVariantGroup.GetProjectVariant(iPrjVarId)
            dicPrjVarOptions[iPrjVarId] = self._GetShortInfo(xPrjVar.sInfo, iPrjVarId)
        # endfor

        self.selProjectVariant.options = dicPrjVarOptions
        self.selProjectVariant.update()
        xSel = _xSel if _xSel is not None else lProjectVarIds[0]
        self.selProjectVariant.set_value(xSel)

    # enddef

    # #############################################################################################
    def OnChangeProjectVariant(self, _xArgs: events.ValueChangeEventArguments):
        if self.iBlockOnChangeProjectVariant == 0:
            self.UpdateProjectVariant()
        # endif

    # enddef

    # #############################################################################################
    def _UpdateLaunchFileVariantSelection(self, *, _xSel: int = None):
        lLaunchFileIds = list(self.xVariantProject.setLaunchFileIds)
        lLaunchFileIds.sort()

        dicLaunchFileOptions: dict[int, str] = dict()
        for iLaunchFileId in lLaunchFileIds:
            sInfo = self.xVariantProject.dicLaunchFileInfo.get(iLaunchFileId, "")
            dicLaunchFileOptions[iLaunchFileId] = self._GetShortInfo(sInfo, iLaunchFileId)
        # endfor

        self.selLaunchFileVariant.options = dicLaunchFileOptions
        self.selLaunchFileVariant.update()
        xSel = _xSel if _xSel is not None else lLaunchFileIds[0]
        self.selLaunchFileVariant.set_value(xSel)

    # enddef

    # #############################################################################################
    def _UpdateTrialVariantSelection(self, *, _xSel: int = None):
        lTrialVarIds = self.xVariantProject.lTrialVariantIds

        dicOptions: dict[int, str] = dict()
        for iTrialVarId in lTrialVarIds:
            sInfo = self.xVariantProject.GetTrialVariant(iTrialVarId).sInfo
            dicOptions[iTrialVarId] = self._GetShortInfo(sInfo, iTrialVarId)
        # endfor

        self.selTrialVariant.options = dicOptions
        self.selTrialVariant.update()
        xSel = _xSel if _xSel is not None else lTrialVarIds[0]
        self.selTrialVariant.set_value(xSel)

    # enddef

    # #############################################################################################
    def UpdateProjectVariant(self):
        self.iBlockOnChangeTrialVariant += 1
        self.iBlockOnChangeLaunchFileVariant += 1
        try:
            self.SaveProjectVariant()

            iPrjVarId: int = None
            xPrjVarId = self.selProjectVariant.value
            if isinstance(xPrjVarId, str):
                if xPrjVarId.startswith("+ Add new"):
                    iPrjVarId = self.xVariantGroup.AddProjectVariant()
                    self.xVariants.Serialize()
                    self._UpdateProjectVariantSelection(_xSel=iPrjVarId)
                else:
                    raise RuntimeError(f"Invalid project variant selection: {xPrjVarId}")
                # endif
            else:
                iPrjVarId = self.selProjectVariant.value
            # endif

            self.xVariantProject = self.xVariantGroup.GetProjectVariant(iPrjVarId)
            self.uiInputPrjVarInfo.set_value(self.xVariantProject.sInfo)

            self._UpdateLaunchFileVariantSelection()
            self._UpdateTrialVariantSelection()

            self.UpdateLaunchFileVariant()
            # self.UpdateTrialVariant()
        except Exception as xEx:
            self.xMessage.ShowException("updating project variant", xEx)
        finally:
            self.iBlockOnChangeTrialVariant -= 1
            self.iBlockOnChangeLaunchFileVariant -= 1
        # endtry

    # enddef

    # #############################################################################################
    def OnAddProjectVariant(self):
        self.iBlockOnChangeTrialVariant += 1
        self.iBlockOnChangeLaunchFileVariant += 1
        try:
            self.SaveProjectVariant()
            iPrjVarId = self.xVariantGroup.AddProjectVariant()
            self.xVariants.Serialize()
            self._UpdateProjectVariantSelection(_xSel=iPrjVarId)
            self.UpdateProjectVariant()
        except Exception as xEx:
            self.xMessage.ShowException("adding project variant", xEx)

        finally:
            self.iBlockOnChangeTrialVariant -= 1
            self.iBlockOnChangeLaunchFileVariant -= 1
        # endtry

    # enddef

    # #############################################################################################
    async def OnRemoveProjectVariant(self, _xArgs: events.ClickEventArguments):
        self.iBlockOnChangeProjectVariant += 1
        self.iBlockOnChangeTrialVariant += 1
        self.iBlockOnChangeLaunchFileVariant += 1
        try:
            if len(self.xVariantGroup.lProjectVariantIds) <= 1:
                await self.xMessage.AsyncShowMessage(
                    "Cannot remove the last configuration variant", _eType=EMessageType.ERROR
                )
                return
            # endif

            sResult = await self.xMessage.AskYesNo("Do you want to remove the current configuration variant?")

            if sResult == "Yes":
                self.SaveProjectVariant()
                iPrjVarId: int = int(self.selProjectVariant.value)
                self.xVariantGroup.RemoveProjectVariant(iPrjVarId)
                self.xVariants.Serialize()
                self._UpdateProjectVariantSelection(_xSel=self.xVariantGroup.lProjectVariantIds[0])
                self.UpdateProjectVariant()
            # endif
        except Exception as xEx:
            self.xMessage.ShowException("removing project variant", xEx)
        finally:
            self._CloseMenuItemFromEvent(_xArgs)

            self.iBlockOnChangeProjectVariant -= 1
            self.iBlockOnChangeTrialVariant -= 1
            self.iBlockOnChangeLaunchFileVariant -= 1
        # endtry

    # enddef

    # #############################################################################################
    def OnChangeLaunchFileVariant(self, _xArgs: events.ValueChangeEventArguments):
        if self.iBlockOnChangeLaunchFileVariant == 0:
            self.UpdateLaunchFileVariant()
        # endif

    # enddef

    # #############################################################################################
    def OnAddLaunchFileVariant(self):
        self.iBlockOnChangeLaunchFileVariant += 1
        try:
            self.SaveProjectVariant()
            iLaunchVarId = self.xVariantProject.AddLaunchFileVariant()
            self.xVariants.Serialize()
            self._UpdateLaunchFileVariantSelection(_xSel=iLaunchVarId)
            self.UpdateLaunchFileVariant()
        except Exception as xEx:
            self.xMessage.ShowException("adding launch file variant", xEx)
        finally:
            self.iBlockOnChangeLaunchFileVariant -= 1
        # endtry

    # enddef

    # #############################################################################################
    async def OnRemoveLaunchFileVariant(self, _xArgs: events.ClickEventArguments):
        self.iBlockOnChangeLaunchFileVariant += 1
        try:
            if self.xVariantProject.iLaunchFileVariantCount <= 1:
                await self.xMessage.AsyncShowMessage(
                    "Cannot remove last launch file variant", _eType=EMessageType.ERROR
                )
                return
            # endif

            sResult = await self.xMessage.AskYesNo("Do you want to remove the current launch variant?")

            if sResult == "Yes":
                self.SaveProjectVariant()
                iLaunchVarId: int = int(self.selLaunchFileVariant.value)
                self.xVariantProject.RemoveLaunchFileVariant(iLaunchVarId)
                self.xVariants.Serialize()
                self._UpdateLaunchFileVariantSelection(_xSel=self.xVariantProject.iSelectedLaunchFileId)
                self.UpdateLaunchFileVariant()
            # endif
        except Exception as xEx:
            self.xMessage.ShowException("removing launch file variant", xEx)
        finally:
            self._CloseMenuItemFromEvent(_xArgs)

            self.iBlockOnChangeLaunchFileVariant -= 1
        # endtry

    # enddef

    # #############################################################################################
    def UpdateLaunchFileVariant(self):
        self.iBlockOnChangeLaunchFileVariant += 1
        try:
            self.SaveProjectVariant()

            xLaunchVarId = self.selLaunchFileVariant.value
            if isinstance(xLaunchVarId, str):
                if xLaunchVarId.startswith("+ Add new"):
                    iLaunchVarId = self.xVariantProject.AddLaunchFileVariant()
                    self.xVariants.Serialize()
                    self._UpdateLaunchFileVariantSelection(_xSel=iLaunchVarId)
                # endif
            else:
                iLaunchVarId: int = self.selLaunchFileVariant.value
                self.xVariantProject.SelectLaunchFileVariant(iLaunchVarId)
            # endif

            sLvInfo: str = self.xVariantProject.dicLaunchFileInfo.get(iLaunchVarId, "")
            self.uiInputLfvInfo.set_value(sLvInfo)

            self.UpdateTrialVariant()

        except Exception as xEx:
            self.xMessage.ShowException("updating launch file variant", xEx)
        finally:
            self.iBlockOnChangeLaunchFileVariant -= 1
        # endtry

    # enddef

    # #############################################################################################
    def OnChangeTrialVariant(self, _xArgs: events.ValueChangeEventArguments):
        if self.iBlockOnChangeTrialVariant == 0:
            self.UpdateTrialVariant()
        # endif

    # enddef

    # #############################################################################################
    def OnAddTrialVariant(self):
        self.iBlockOnChangeTrialVariant += 1
        try:
            self.SaveProjectVariant()
            iTrialVarId = self.xVariantProject.AddTrialVariant()
            self.xVariants.Serialize()
            self._UpdateTrialVariantSelection(_xSel=iTrialVarId)
            self.UpdateTrialVariant()
        except Exception as xEx:
            self.xMessage.ShowException("adding trial variant", xEx)
        finally:
            self.iBlockOnChangeTrialVariant -= 1
        # endtry

    # enddef

    # #############################################################################################
    async def OnRemoveTrialVariant(self, _xArgs: events.ClickEventArguments):
        self.iBlockOnChangeTrialVariant += 1
        try:
            if len(self.xVariantProject.lTrialVariantIds) <= 1:
                await self.xMessage.AsyncShowMessage("Cannot remove the last trial variant", _eType=EMessageType.ERROR)
                return
            # endif

            sResult = await self.xMessage.AskYesNo("Do you want to remove the current trial variant?")

            if sResult == "Yes":
                self.SaveProjectVariant()
                iTrialVarId: int = int(self.selTrialVariant.value)
                self.xVariantProject.RemoveTrialVariant(iTrialVarId)
                self.xVariants.Serialize()

                self._UpdateTrialVariantSelection(_xSel=self.xVariantProject.lTrialVariantIds[0])
                self.UpdateTrialVariant()
            # endif
        except Exception as xEx:
            self.xMessage.ShowException("removing trial variant", xEx)
        finally:
            self._CloseMenuItemFromEvent(_xArgs)

            self.iBlockOnChangeTrialVariant -= 1
        # endtry

    # enddef

    # #############################################################################################
    def UpdateTrialVariant(self):
        self.iBlockOnChangeTrial += 1
        self.iBlockOnChangeTrialVariant += 1
        try:
            self.SaveProjectVariant()

            iTrialVarId: int = None
            xTrialVarId = self.selTrialVariant.value
            if isinstance(xTrialVarId, str):
                if xTrialVarId.startswith("+ Add new"):
                    iTrialVarId = self.xVariantProject.AddTrialVariant()
                    self.xVariants.Serialize()
                    self._UpdateTrialVariantSelection(_xSel=iTrialVarId)
                # endif
            else:
                iTrialVarId: int = self.selTrialVariant.value
            # endif

            self.xVariantTrial = self.xVariantProject.GetTrialVariant(iTrialVarId)

            self.uiInputTrialVarInfo.set_value(self.xVariantTrial.sInfo)

            lTrials = self.xVariantTrial.xTrialActions.lTrialFiles
            sSelTrial: str = self.xVariantTrial.xTrialActions.GetTrialSelection()

            self.selTrial.options = lTrials
            self.selTrial.update()
            self.selTrial.set_value(sSelTrial)
            self.selTrial.set_visibility(len(lTrials) > 1)

            self.dicLaunchGuiArgs = self.xVariantTrial.xTrialActions.dicLaunch.get("mGui")
            if isinstance(self.dicLaunchGuiArgs, dict):
                dicDti = config.CheckConfigType(self.dicLaunchGuiArgs, "/catharsys/gui/settings:1")
                if dicDti["bOK"] is False:
                    self.dicLaunchGuiArgs = None
                    self.xMessage.ShowMessage(
                        "Unsupported GUI settings configuration in launch file", _eType=EMessageType.WARNING
                    )
                # endif
            # endif

            # _funcOnChange=lambda xArgs, dicData, sName, xValue: self.OnLaunchDataChange(xArgs, dicData, sName, xValue))
            self.UpdateTrial()
        except Exception as xEx:
            self.xMessage.ShowException("updating trial variant", xEx)
        finally:
            self.iBlockOnChangeTrial -= 1
            self.iBlockOnChangeTrialVariant -= 1
        # endtry

    # enddef

    # #############################################################################################
    def OnChangeTrial(self, _xArgs: events.ValueChangeEventArguments):
        if self.iBlockOnChangeTrial == 0:
            self.UpdateTrial()
        # endif

    # enddef

    # #############################################################################################
    def UpdateTrial(self):
        self.iBlockOnChangeAction += 1
        try:
            self.SaveProjectVariant()

            sTrialName = self.selTrial.value

            # if there is a selection of trial files specified in the launch file,
            # we modify the launch file to reflect the current selection and
            # then save it.
            self.xVariantTrial.xTrialActions.SetActiveTrial(sTrialName)
            self.bLaunchDataChanged = True
            self.SaveProjectVariant()

            # print(f"create val grid: {(id(self.xVariantTrial.xTrialActions.dicGlobalArgs))}")
            self.vgGlobLaunchArgs = CValueGrid(
                _gridData=self.gridGlobalLaunchArgs,
                _sDataId="actions",
                _dicValues=self.xVariantTrial.xTrialActions.dicGlobalArgs,
                _xCtrlFactory=self.xCtrlFactory,
                _lExcludeRegEx=self.lExcludeLAValRegEx,
                _dicGuiArgs=self.dicLaunchGuiArgs,
                _funcOnChange=self.OnLaunchDataChange,
            )

            lActionPaths = self.xVariantTrial.xTrialActions.GetTrialActionPaths(sTrialName)

            if lActionPaths is None or len(lActionPaths) == 0:
                self.selAction.options = ["n/a"]
                self.selAction.update()
                self.selAction.set_value("n/a")
            else:
                sSelActPath: str = self.selAction.value
                if sSelActPath is None or sSelActPath not in lActionPaths:
                    sSelActPath = lActionPaths[0]
                # endif

                self.selAction.options = lActionPaths
                self.selAction.update()
                self.selAction.set_value(sSelActPath)
            # endif

            self.UpdateAction()
        except Exception as xEx:
            self.xMessage.ShowException("updating trial", xEx)
        finally:
            self.iBlockOnChangeAction -= 1
        # endtry

    # enddef

    # #############################################################################################
    def OnChangeAction(self, _xArgs: events.ValueChangeEventArguments):
        if self.iBlockOnChangeAction == 0:
            self.UpdateAction()
        # endif

    # enddef

    # #############################################################################################
    def UpdateAction(self):
        try:
            self.SaveProjectVariant()

            sActionPath = self.selAction.value
            xActData = self.xVariantTrial.xTrialActions.GetResolvedAction(sActionPath)
            if xActData is None:
                return
            # endif

            sActInfo: str = xActData.xLaunch.GetActionInfo(xActData.sBaseAction)
            if len(sActInfo) > 0:
                self._uiRowActionInfo.set_visibility(True)
                self.labActInfo.set_text(sActInfo)
            else:
                self._uiRowActionInfo.set_visibility(False)
                self.labActInfo.set_text(" ")
            # endif

            dicCfg = xActData.xLaunch.GetActionConfig(xActData.sBaseAction)
            self.vgActLaunchArgs = CValueGrid(
                _gridData=self.gridActionLaunchArgs,
                _sDataId=f"actions:{sActionPath}",
                _dicValues=dicCfg,
                _xCtrlFactory=self.xCtrlFactory,
                _lExcludeRegEx=self.lExcludeLAValRegEx,
                _dicGuiArgs=self.dicLaunchGuiArgs,
                _funcOnChange=self.OnLaunchDataChange,
            )
            #   _funcOnChange=lambda xArgs, dicData, sName, xValue: self.OnLaunchDataChange(xArgs, dicData, sName, xValue))

            # #############################################################################################################
            # Trial parameters
            sTrialName = self.selTrial.value
            if sTrialName not in self.xVariantTrial.xTrialActions.lTrialFiles:
                raise RuntimeError("Selected trial file '{sTrialName}' not found")
            # endif
            pathTrial = self.xVariantTrial.GetVariantAbsPath(sTrialName)
            self.dicTrialData = config.Load(pathTrial, sDTI="/catharsys/trial:1", bReplacePureVars=False)

            sTrialInfo: str = self.dicTrialData.get("sInfo")
            if sTrialInfo is not None:
                self.labTrialInfo.set_text(sTrialInfo)
                self._uiRowTrialInfo.set_visibility(True)
            else:
                self._uiRowTrialInfo.set_visibility(False)
            # endif

            self.dicTrialGuiArgs = self.dicTrialData.get("mGui")
            if isinstance(self.dicTrialGuiArgs, dict):
                dicDti = config.CheckConfigType(self.dicTrialGuiArgs, "/catharsys/gui/settings:1")
                if dicDti["bOK"] is False:
                    self.dicTrialGuiArgs = None
                    self.xMessage.ShowMessage(
                        "Unsupported GUI settings configuration in trial file", _eType=EMessageType.WARNING
                    )
                # endif
            # endif

            if "__locals__" in self.dicTrialData:
                self.vgTrialLocals = CValueGrid(
                    _gridData=self.gridTrialLocals,
                    _sDataId="trial:locals",
                    _dicValues=self.dicTrialData["__locals__"],
                    _xCtrlFactory=self.xCtrlFactory,
                    _lExcludeRegEx=self.lExcludeLAValRegEx,
                    _dicGuiArgs=self.dicTrialGuiArgs,
                    _dicDefaultGuiArgs=dict(bShowAllVars=False),
                    _funcOnChange=self.OnTrialDataChange,
                )
            else:
                self.gridTrialLocals.clear()
            # endif

            if "__globals__" in self.dicTrialData:
                self.vgTrialGlobals = CValueGrid(
                    _gridData=self.gridTrialGlobals,
                    _sDataId="trial:globals",
                    _dicValues=self.dicTrialData["__globals__"],
                    _xCtrlFactory=self.xCtrlFactory,
                    _lExcludeRegEx=self.lExcludeLAValRegEx,
                    _dicGuiArgs=self.dicTrialGuiArgs,
                    _dicDefaultGuiArgs=dict(bShowAllVars=False),
                    _funcOnChange=self.OnTrialDataChange,
                )
            else:
                self.gridTrialLocals.clear()
            # endif

            if "mConfigs" in self.dicTrialData:
                self.vgTrialConfigs = CValueGrid(
                    _gridData=self.gridTrialConfigs,
                    _sDataId="trial:configs",
                    _dicValues=self.dicTrialData["mConfigs"],
                    _xCtrlFactory=self.xCtrlFactory,
                    _lExcludeRegEx=self.lExcludeLAValRegEx,
                    _dicGuiArgs=self.dicTrialGuiArgs,
                    _dicDefaultGuiArgs={
                        "bShowAllVars": False,
                        "mControlDefaults": {"/catharsys/gui/control/select/str:1": {"bMultiple": True}},
                    },
                    _funcOnChange=self.OnTrialDataChange,
                )
            else:
                self.gridTrialConfigs.clear()
            # endif

        except Exception as xEx:
            self.xMessage.ShowException("updating action", xEx)
        # endtry

    # enddef

    # #############################################################################################
    def SaveProjectVariant(self):
        if self.xVariantProject is not None and self.xVariantTrial is not None:
            if self.bLaunchDataChanged is True:
                # print("Start save launch data")
                # print(f"id: {(id(self.xVariantTrial.xTrialActions.dicGlobalArgs))}")

                # print(self.xVariantTrial.xTrialActions.dicGlobalArgs)
                # print(f"Global args id: {(id(self.xVariantTrial.xTrialActions.dicGlobalArgs))}")
                self.xVariantTrial.xTrialActions.ApplyResolvedActions()
                config.Save(
                    self.xVariantProject.pathLaunchFile,
                    self.xVariantTrial.xTrialActions.dicLaunch,
                )

                iLaunchVarId: int = self.selLaunchFileVariant.value
                self.xVariantProject.SelectLaunchFileVariant(iLaunchVarId)
                # print(f"After select Global args id: {(id(self.xVariantTrial.xTrialActions.dicGlobalArgs))}")
                # print(self.xVariantTrial.xTrialActions.dicGlobalArgs)

                # print("SaveLaunchVariant")
                # print(f"> path: {self.xVariantLaunch.pathLaunchFile}")
                # print(self.xVariantTrial.xTrialActions.dicLaunch)
                self.bLaunchDataChanged = False
                # Save trial variants
            # endif

            if self.bTrialDataChanged is True:
                sTrialName = self.selTrial.value
                pathTrial = self.xVariantTrial.GetVariantAbsPath(sTrialName)

                config.Save(pathTrial, self.dicTrialData)
                self.bTrialDataChanged = False
            # endif

            if self.bVariantInfoChanged is True:
                self.xVariants.Serialize()
                self.bVariantInfoChanged = False
            # endif
        # endif

    # enddef

    # #############################################################################################
    def OnLaunchDataChange(
        self, _xArgs: events.ValueChangeEventArguments, _dicData: dict, _sValueName: str, _xValue
    ) -> bool:
        self.bLaunchDataChanged = True
        # print(f"Launch data changed:\n{self.xVariantTrial.xTrialActions.dicGlobalArgs}")
        # print(f"id: {(id(self.xVariantTrial.xTrialActions.dicGlobalArgs))}")
        return True

    # enddef

    # #############################################################################################
    def OnTrialDataChange(
        self, _xArgs: events.ValueChangeEventArguments, _dicData: dict, _sValueName: str, _xValue
    ) -> bool:
        self.bTrialDataChanged = True
        return True

    # enddef

    # #############################################################################################
    def _CreateLaunchInstance(self, *, _xInst: CVariantInstance) -> CLaunchInstance:
        sLabel = f"{_xInst.sProjectId}[{_xInst.iPrjVarId}:{_xInst.iTrialId}]"
        sActionPath: str = _xInst.dicMeta.get("sActionPath")
        if sActionPath is None:
            raise RuntimeError(f"Action path not available in meta data of instance: {sLabel}")
        # endif
        iLaunchFileId: int = _xInst.dicMeta.get("iLaunchFileId")
        if iLaunchFileId is None:
            raise RuntimeError(f"Launch file id not available in meta data of instance: {sLabel}")
        # endif

        sLabel += f"-{iLaunchFileId}-{sActionPath}"
        sTestId = sLabel
        iTest = 1
        dicLaunchInstances = self._GetProjectLaunchInstances()
        while sTestId in dicLaunchInstances:
            sTestId = sLabel + f" ({iTest})"
            iTest += 1
        # endwhile
        xLaunchInst = CLaunchInstance()
        xLaunchInst.sId = _xInst.sId
        xLaunchInst.sLabel = sLabel
        xLaunchInst.xInstance = _xInst
        xLaunchInst.xActHandler = None
        xLaunchInst.xJobInfo = None

        return xLaunchInst

    # enddef

    # #############################################################################################
    def _AddLaunchInstance(self, *, _xInst: CVariantInstance) -> CLaunchInstance:
        xLaunchInst = self._CreateLaunchInstance(_xInst=_xInst)
        dicLaunchInstances = self._GetProjectLaunchInstances()
        dicLaunchInstances[xLaunchInst.sId] = xLaunchInst
        return xLaunchInst

    # enddef

    # #############################################################################################
    def UpdateMainTabs(self):
        try:
            sPrjId: str = self.xProject.sId
            sPvtId: str = self._GetProductViewerTabId(sPrjId)
            dicLaunchInstances = self._GetProjectLaunchInstances()

            sId: str = None
            lHideTabsIds: list[str] = [
                sId
                for sId in self._tabsMain
                if sId not in dicLaunchInstances and sId != self._sMainTabId and sId != sPvtId
            ]
            for sId in lHideTabsIds:
                self._tabsMain.SetVisibility(sId, False)
            # endfor

            for sId in dicLaunchInstances:
                self._tabsMain.SetVisibility(sId, True)
            # endfor

            if sPvtId in self._tabsMain:
                self._tabsMain.SetVisibility(sPvtId, True)
            # endif
        except Exception as xEx:
            lLaunchInst = list(dicLaunchInstances.keys())
            sMsg = f"Error updating tabs:\nsPrjId: {sPrjId}\nsPvtId: {sPvtId}\n"
            sMsg += f"Main tabs: {self._tabsMain.lKeys}\n"
            sMsg += f"Launch instances: {lLaunchInst}\n"
            sMsg += f"Hide tabs: {lHideTabsIds}\n"
            raise CAnyError_Message(sMsg=sMsg, xChildEx=xEx)
        # endtry

    # enddef

    # #############################################################################################
    async def AsyncFindInstances(self):
        self.FindProjectVariantInstances()

    # enddef

    # #############################################################################################
    def FindProjectVariantInstances(self):
        self.butInstantiateVariant.disable()
        self.butInstantiateVariant.update()

        try:
            lInstances = self.xVariants.GetInstances()
            xInst: CVariantInstance = None
            dicLaunchInstances = self._GetProjectLaunchInstances()

            for xInst in lInstances:
                if xInst.sId not in dicLaunchInstances:
                    xLaunchInstance = self._AddLaunchInstance(_xInst=xInst)
                else:
                    xLaunchInstance = dicLaunchInstances[xInst.sId]
                # endif
                if xInst.sId not in self._tabsMain:
                    self._tabsMain.Add(_sName=xInst.sId, _sLabel=xLaunchInstance.sLabel, _sIcon="rocket")
                # endif
            # endfor
        except Exception as xEx:
            self.xMessage.ShowException("finding project variant instances", xEx)

        finally:
            self.butInstantiateVariant.enable()
        # endtry

    # enddef

    # #############################################################################################
    def _GetProductViewerTabId(self, _sPrjId: str) -> str:
        return f"prod-view:{_sPrjId}"

    # enddef

    # #############################################################################################
    def ShowProducts(self):
        try:
            sPrjId: str = self.xProject.sId
            sPvtId: str = self._GetProductViewerTabId(sPrjId)

            if sPvtId not in self._tabsMain:
                self._tabsMain.Add(_sName=sPvtId, _sLabel=sPrjId, _sIcon="visibility")
                with self._tabsMain[sPvtId]:
                    uiRowView = ui.row().classes("w-full")
                    self.dicProjectProductViewer[sPrjId] = CVariantGroupProductView(
                        _uiRow=uiRowView,
                        _xVariantGroup=self.xVariantGroup,
                        _funcOnClose=lambda: self.CloseProductView(sPvtId),
                    )
                # endwith
            # endif
            self._tabsMain.Select(sPvtId)

        except Exception as xEx:
            self.xMessage.ShowException("showing products", xEx)

        finally:
            pass
            # print("END INIT INSTANCE")
        # endtry

    # #############################################################################################
    def CloseProductView(self, _sPvtId: str):
        if _sPvtId in self._tabsMain:
            self._tabsMain.Remove(_sPvtId)
            sPrjId: str = _sPvtId.split(":")[1]
            del self.dicProjectProductViewer[sPrjId]
        # endif

    # enddef

    # #############################################################################################
    async def InstantiateVariant(self):
        self.butInstantiateVariant.disable()
        self.butInstantiateVariant.update()
        await asyncio.sleep(0.1)

        try:
            self.SaveProjectVariant()
            iProjectVarId: int = int(self.selProjectVariant.value)
            iTrialVarId: int = int(self.selTrialVariant.value)
            sActionPath: str = self.selAction.value
            dicMeta = dict(sActionPath=sActionPath, iLaunchFileId=self.xVariantProject.iSelectedLaunchFileId)

            xInstance = self.xVariants.CreateInstance(
                _sGroup=self.xLogin.sUsername, _iPrjVarId=iProjectVarId, _iTrialVarId=iTrialVarId, _dicMeta=dicMeta
            )
            xLaunchInstance = self._AddLaunchInstance(_xInst=xInstance)
            self._tabsMain.Add(_sName=xInstance.sId, _sLabel=xLaunchInstance.sLabel, _sIcon="rocket")
            self._tabsMain.Select(xInstance.sId)
        except Exception as xEx:
            self.xMessage.ShowException("instantiating variant", xEx)

        finally:
            self.butInstantiateVariant.enable()
        # endtry

    # enddef

    # #############################################################################################
    async def _InitInstance(self, _sId: str):
        try:
            # print("START INIT INSTANCE")
            dicLaunchInstances = self._GetProjectLaunchInstances()
            if _sId not in dicLaunchInstances:
                raise RuntimeError(f"Instance '{_sId}' not found")
            # endif

            xLaunchInst: CLaunchInstance = dicLaunchInstances[_sId]
            if isinstance(xLaunchInst.xActHandler, CActionHandler):
                return
            # endif

            xProject = xLaunchInst.xInstance.GetProject(xWorkspace=self.xWorkspace)
            xAction = xProject.Action(xLaunchInst.xInstance.dicMeta["sActionPath"])
            xLaunchInst.xActHandler = CActionHandler(_xAction=xAction)

            xPanel = self._tabsMain[_sId]
            xPanel.clear()
            xEx: Exception = None

            with xPanel:
                try:
                    gridLaunch = ui.grid()
                    xLaunchInst.xJobInfo = CJobInfo(
                        _uiGrid=gridLaunch,
                        _xActHandler=xLaunchInst.xActHandler,
                        _funcOnClose=lambda: self.RemoveInstance(_sId),
                        _funcOnStart=lambda: self.OnInstanceLaunchStart(_sId),
                        _funcOnEnd=lambda: self.OnInstanceLaunchEnd(_sId),
                    )
                except Exception as _xEx:
                    xEx = _xEx
                    xLaunchInst.xJobInfo = None
                # endtry
            # endwith panel
            if xEx is not None:
                self._tabsMain.Remove(_sId)
                raise CAnyError_Message(sMsg="Error creating launch action handler view", xChildEx=xEx)
            # endif

        except Exception as xEx:
            self.xMessage.ShowException("initializing instance", xEx)

        finally:
            pass
            # print("END INIT INSTANCE")
        # endtry

    # enddef

    # #############################################################################################
    async def _OnSelectMainTab(self, _xArgs: events.ValueChangeEventArguments):
        sId: str = str(_xArgs.value)
        dicLaunchInstances = self._GetProjectLaunchInstances()
        if sId in dicLaunchInstances:
            xLaunchInst = dicLaunchInstances[sId]
            if xLaunchInst.xActHandler is None:
                self.xMessage.ShowWait("Creating Configuration Instance")
                await asyncio.sleep(0.1)
                await self._InitInstance(sId)
                self.xMessage.HideWait()

            # endif
        # endif

    # enddef

    # #############################################################################################
    def RemoveInstance(self, _sId: str):
        xLaunchInst: CLaunchInstance = self._GetProjectLaunchInstances().get(_sId)
        if xLaunchInst is None:
            self.xMessage.ShowMessage(f"Launch instance '{_sId}' not available", _eType=EMessageType.ERROR)
            return
        # endif

        self._tabsMain.Remove(_sId)
        self.xVariants.RemoveInstance(xLaunchInst.xInstance)
        del self._GetProjectLaunchInstances()[_sId]

    # enddef

    # #############################################################################################
    def OnInstanceLaunchStart(self, _sId: str):
        self._tabsMain.SetIcon(_sId, "rocket_launch")

    # enddef

    # #############################################################################################
    def OnInstanceLaunchEnd(self, _sId: str):
        self._tabsMain.SetIcon(_sId, "rocket")

    # enddef


# endclass
