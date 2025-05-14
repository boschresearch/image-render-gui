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

import asyncio
from typing import Union, Optional
from nicegui import ui, events, app, Client, Tailwind
from fastapi.responses import RedirectResponse

import uuid
from timeit import default_timer as timer

import catharsys.api as capi
from catharsys.config.cls_variant_group import CVariantGroup
from catharsys.config.cls_variant_project import CVariantProject
from catharsys.config.cls_variant_trial import CVariantTrial

from .login import CLogin, CPageLogin, EAuthResult
from ..widgets.cls_message import CMessage, EMessageType
from ..widgets.cls_variant_group_product_view import CVariantGroupProductView


class CPageProductViewer:
    dicClients: dict[uuid.UUID, "CPageProductViewer"] = {}
    bIsRegistered: bool = False
    xLogin: CLogin = None

    def __init__(self, _wsX: capi.CWorkspace, _sProjectId: str, _sVariantGroup: str, _xClient: Client):
        self.wsX: capi.CWorkspace = _wsX
        self.sProjectId: str = _sProjectId
        self.sVariantGroup: str = _sVariantGroup

        self.prjX: capi.CProject = None
        self.actX: capi.CAction = None
        self.xVariants: capi.CVariants = None
        self.xVariantGroup: CVariantGroup = None
        self.xVariantProject: CVariantProject = None
        self.xVariantTrial: CVariantTrial = None

        self.sStyleTextTitle = "text-lg font-medium"
        self.sStyleTextDescSmall = "text-sm italic"

        self.xClientId: str = _xClient.id
        CPageProductViewer.dicClients[self.xClientId] = self

        self.xMessage = CMessage()
        self.xProductViewer: CVariantGroupProductView = None

    # enddef

    # #############################################################################################
    @staticmethod
    def OnDisconnect(xClient: Client):
        # print("on_disconnect")
        CPageProductViewer.RemoveClient(xClient)
        # print(f"Disconnecting: {xClient.id}")
        # print(CPageWorkspace.dicClients)

    # enddef

    # #############################################################################################
    @staticmethod
    def Register(_wsX: capi.CWorkspace, _xLogin: CLogin):
        if CPageProductViewer.bIsRegistered is True:
            raise RuntimeError("Product viewer page already registered")
        # endif
        CPageProductViewer.bIsRegistered = True
        CPageProductViewer.xLogin = _xLogin

        app.on_disconnect(CPageProductViewer.OnDisconnect)

        @ui.page("/productview/{project_id}/{variant_group}/{id}")
        # The argument MUST be called 'client'. If nicegui finds this parameter name in the
        # function interface it strips it and passes in the client object.
        # Arguments with other names are passed on to FastAPI.
        def page_main(client: Client, project_id: str, variant_group: str, id: str) -> Optional[RedirectResponse]:
            # print("page_main")

            eResult: EAuthResult = CPageProductViewer.xLogin.TestPublicLinkId(
                f"productview/{project_id}/{variant_group}", id
            )
            if eResult == EAuthResult.VALID:
                sProjectId: str = project_id.replace("+", "/")
                sVariantGroup: str = variant_group.replace("+", "/")

                xPageView = CPageProductViewer.dicClients.get(client.id)
                if xPageView is None:
                    xPageView = CPageProductViewer(_wsX, sProjectId, sVariantGroup, client)
                    xPageView.Create()
                # endif
            else:
                sMsg: str = CPageProductViewer.xLogin.GetAuthResultMessage(eResult)
                CMessage().ShowMessageScreen(_sText=sMsg, _sIcon="thunderstorm")
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

        xPageView = CPageProductViewer.dicClients.get(sClientId)
        if xPageView is not None:
            # xPageWs.OnRemove()
            xPageView.xClientId = None
            del CPageProductViewer.dicClients[sClientId]
        # endif

    # enddef

    # #############################################################################################
    def __del__(self):
        # print("Destructor")
        CPageProductViewer.RemoveClient(self.xClientId)

    # enddef

    # #############################################################################################
    def Create(self):
        try:
            if self.sProjectId not in self.wsX.dicProjects:
                self.xMessage.ShowMessageScreen(
                    _sText=f"Project '{self.sProjectId}' not available", _sIcon="thunderstorm"
                )
                return
            # endif

            self.prjX = self.wsX.Project(self.sProjectId)
            self.xVariants = capi.CVariants(self.prjX)
            self.xVariantGroup = self.xVariants.GetGroup(self.sVariantGroup, _bDoRaise=False)
            if self.xVariantGroup is None:
                self.xMessage.ShowMessageScreen(
                    _sText=f"Variant group '{self.sVariantGroup}' not available", _sIcon="thunderstorm"
                )
                return
            # endif

            self._darkMode = ui.dark_mode()
            self._darkMode.enable()

            with ui.header(elevated=True):
                ui.label(f"View {self.wsX.sName} v{self.wsX.sVersion}, {self.sProjectId}").classes("text-h4")
            # endwith

            self._DoCreateContent()

        except Exception as xEx:
            self.xMessage.ShowMessage(f"EXCEPTION creating product viewer:\n{(str(xEx))}")
        # endtry

    # enddef

    # #############################################################################################
    @ui.refreshable
    def _DoCreateContent(self):

        uiRowView = ui.row().classes("w-full")
        self.xProductViewer = CVariantGroupProductView(
            _uiRow=uiRowView,
            _xVariantGroup=self.xVariantGroup,
            # _funcOnClose=lambda: self.CloseProductView(sPrjId),
        )
    # enddef

# endclass
