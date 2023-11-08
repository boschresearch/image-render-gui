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

import trustme
import argparse
import threading
import webbrowser
import time
from typing import Tuple
from pathlib import Path
from datetime import datetime
import catharsys.api as capi
from catharsys.setup.util import GetCathUserPath
from catharsys.setup import conda
from anybase.cls_any_error import CAnyError
from anybase import config
import uuid
import socket

# import catharsys.gui.web.pages.workspace as page_ws
from catharsys.gui.web.pages.workspace import CPageWorkspace
from catharsys.gui.web.pages.product_viewer import CPageProductViewer
from catharsys.gui.web.pages.login import CLogin, CPageLogin
from catharsys.gui.web.pages.reset_pw import CPageResetPw
from catharsys.gui.web.util import paths as guipaths

from nicegui import ui, app, Client, helpers

g_dicClients: dict[str, Client] = {}
g_iTimeout: int = 0
g_dtLastDisconnect: datetime = datetime.now()


def OnConnect(xClient: Client):
    global g_dicClients
    g_dicClients[xClient.id] = xClient


# enddef


def OnDisconnect(xClient: Client):
    global g_dicClients, g_dtLastDisconnect

    if xClient.id in g_dicClients:
        del g_dicClients[xClient.id]
    # enddef

    g_dtLastDisconnect = datetime.now()


# enddef


def OnTimerTestShutdown():
    global g_dicClients, g_iTimeout, g_dtLastDisconnect

    # print("Testing for shutdown")
    if len(g_dicClients) > 0 or g_iTimeout <= 0:
        return
    # endif

    dtDelta = datetime.now() - g_dtLastDisconnect
    # print(f"Time delta: {(dtDelta.total_seconds())}")
    if int(dtDelta.total_seconds()) >= g_iTimeout:
        app.shutdown()
    # endif


# enddef


def ScheduleBrowser(_sHost: str, _iPort: int, _bUseSsl: bool) -> Tuple[threading.Thread, threading.Event]:
    evCancel = threading.Event()

    def ThreadMain(_sHost: str, _iPort: int) -> None:
        while not helpers.is_port_open(_sHost, _iPort):
            if evCancel.is_set():
                return
            # endif
            time.sleep(0.1)
        # endwhile
        sPrefix: str = "https://" if _bUseSsl is True else "http://"
        webbrowser.open(f"{sPrefix}{_sHost}:{_iPort}/")

    # enddef

    _sHost = _sHost if _sHost != "0.0.0.0" else "127.0.0.1"
    xThread = threading.Thread(target=ThreadMain, args=(_sHost, _iPort), daemon=True)
    xThread.start()
    return xThread, evCancel


# enddef


def FindFreePort() -> int:
    xSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    xSocket.bind(("", 0))
    xSocket.listen(1)
    iPort: int = xSocket.getsockname()[1]
    xSocket.close()

    return iPort


# enddef

# ########################################################################################################################
# ########################################################################################################################

try:
    # ###########################################################################################
    # Runtime Arguments

    parseMain = argparse.ArgumentParser(
        prog="webapp-workspace", description="Catharsys Workspace WebApp", exit_on_error=True
    )

    parseMain.add_argument("-l", "--launch", nargs=1, dest="launch_file", default=[None])
    parseMain.add_argument("--path", nargs=1, dest="workspace_path", default=[None])
    parseMain.add_argument("--timeout", dest="timeout", nargs=1, default=[None])
    parseMain.add_argument("--no-ssl", dest="no_ssl", action="store_true", default=False)

    xArgs = parseMain.parse_args()

    sFileBasenameLaunch = xArgs.launch_file[0]
    pathWorkspace: Path = None

    bNoSsl: bool = xArgs.no_ssl

    if xArgs.workspace_path[0] is not None:
        pathWorkspace = Path(xArgs.workspace_path[0])
    # endif

    try:
        if xArgs.timeout[0] is not None:
            g_iTimeout = int(xArgs.timeout[0])
        else:
            g_iTimeout = 10
        # endif
    except Exception:
        raise RuntimeError(f"Timeout value has to be an integer but was '{xArgs.timeout}'")
    # endtry
    # ###########################################################################################
    # Load USER arguments from config file.
    # By default this contains a secret key for encrypting the cookies.
    # This config will be updated with the workspace gui config, loaded from the workspace.
    pathUser = GetCathUserPath(_bCheckExists=False)
    pathGui = pathUser / "gui"
    # print(f"pathGui: {pathGui}")

    pathGui.mkdir(exist_ok=True, parents=True)
    pathCfgFile = pathGui / "gui-web-config.json"

    dicCfg: dict = None
    if pathCfgFile.exists():
        dicCfg = config.Load(pathCfgFile, sDTI="/catharsys/gui/web:1")
    else:
        dicCfg = {
            "sSecretKey": uuid.uuid4().hex,
        }
        config.Save(pathCfgFile, dicCfg, sDTI="/catharsys/gui/web:1.0")
    # endif

    # ###########################################################################################
    # Get workspace info
    wsX = capi.CWorkspace(xWorkspace=pathWorkspace, sFileBasenameLaunch=sFileBasenameLaunch)

    # ###########################################################################################
    # Load WORKSPACE arguments config file
    sCondaEnv = conda.GetActiveEnvName()
    if sCondaEnv is None:
        raise RuntimeError(
            "Currently not in an Anaconda Python environment.\n"
            "Activate an approriate environment with 'conda activate [Catharsys Env]\n\n"
        )
    # endif

    pathWsCfg: Path = wsX.pathWorkspace / ".catharsys" / sCondaEnv
    # if not pathWsCfg.exists():
    #     raise RuntimeError(f"Workspace not initialized: {(pathWsCfg.as_posix())}")
    # # endif

    pathWsCfgGui = pathWsCfg / "gui"
    # print(f"pathWsCfgGui: {pathWsCfgGui}")

    pathWsCfgGui.mkdir(parents=True, exist_ok=True)
    pathWsCfgFile = pathWsCfgGui / "gui-web-config.json"

    bSaveWsCfg: bool = False
    dicWsCfg: dict = None
    if pathWsCfgFile.exists():
        dicWsCfg = config.Load(pathWsCfgFile, sDTI="/catharsys/gui/web:1")
    else:
        # iPort = 8080 if bNoSsl is True else 4443
        dicWsCfg = {
            "iPort": 0,
        }
        bSaveWsCfg = True
    # endif

    iPort: int = dicWsCfg.get("iPort", 0)
    if iPort == 0:
        iPort = FindFreePort()
        print(f"Automatically assigned port '{iPort}'")
        dicWsCfg["iPort"] = iPort
        bSaveWsCfg = True
    # endif

    sSslCertFile: str = None
    if bNoSsl is False:
        pathCertFile: Path = None
        sPathCertFile: str = dicWsCfg.get("sPathCertFile")
        if sPathCertFile is None:
            xCA = trustme.CA()
            xServerCert = xCA.issue_server_cert("localhost", "127.0.0.1", "::1")
            pathCertFile = pathWsCfgGui / "localhost-cert.pem"
            xServerCert.private_key_and_cert_chain_pem.write_to_path(pathCertFile.as_posix())

            dicWsCfg["sPathCertFile"] = pathCertFile.relative_to(wsX.pathWorkspace).as_posix()
            bSaveWsCfg = True
        else:
            pathCertFile = wsX.pathWorkspace / Path(sPathCertFile)
        # endif

        sSslCertFile = pathCertFile.as_posix()
    # endif

    if bSaveWsCfg is True:
        config.Save(pathWsCfgFile, dicWsCfg, sDTI="/catharsys/gui/web:1.0")
    # endif

    dicCfg.update(dicWsCfg)

    # ###########################################################################################
    # Create pages
    app.on_connect(OnConnect)
    app.on_disconnect(OnDisconnect)

    ui.dark_mode().enable()

    pathAuth = guipaths.GetSettingsPath(wsX.pathWorkspace)
    xLogin = CLogin(pathAuth)

    CPageLogin.Register(xLogin)
    CPageResetPw.Register(xLogin)
    CPageWorkspace.Register(wsX, xLogin)
    CPageProductViewer.Register(wsX, xLogin)

    ui.timer(max(g_iTimeout, 5), OnTimerTestShutdown)
    if bNoSsl is False:
        ScheduleBrowser("127.0.0.1", iPort, True)
    # endif

    ui.run(
        title=wsX.sName,
        show=bNoSsl,
        reload=False,
        storage_secret=dicCfg["sSecretKey"],
        port=iPort,
        ssl_certfile=sSslCertFile,
    )

except Exception as xEx:
    CAnyError.Print(xEx, sMsg="Error running Workspace GUI web app")
# endtry
