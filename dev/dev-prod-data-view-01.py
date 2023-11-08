import anytree
from pathlib import Path
from nicegui import ui, Tailwind

import catharsys.api as capi
from catharsys.api.products.cls_variant_group_products import CVariantGroupProducts
from catharsys.api.products.cls_group import CGroup
from catharsys.config.cls_variant_group import CVariantGroup
from catharsys.gui.web.widgets.cls_variant_group_product_view import CVariantGroupProductView


wsX = capi.CWorkspace()
wsX.PrintInfo()
# prjX = wsX.Project("gui/dev-01")
prjX = wsX.Project("anytruth/test-01")
xVariants = capi.CVariants(prjX)
xVarGrp = xVariants.GetGroup("prc2hi")

uiRowMain = ui.row().classes("w-full")

xView = CVariantGroupProductView(_uiRow=uiRowMain, _xVariantGroup=xVarGrp)
ui.run(reload=False)
