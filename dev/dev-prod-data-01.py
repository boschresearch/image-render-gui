import anytree
from pathlib import Path
import catharsys.api as capi
from catharsys.api.products.cls_variant_group_products import CVariantGroupProducts
from catharsys.api.products.cls_group import CGroup

wsX = capi.CWorkspace()
wsX.PrintInfo()
# prjX = wsX.Project("gui/dev-01")
prjX = wsX.Project("anytruth/test-01")
xVariants = capi.CVariants(prjX)
xVarGrp = xVariants.GetGroup("prc2hi")

xProdData = CVariantGroupProducts(_xVariantGroup=xVarGrp)
pathProd: Path = prjX.xConfig.pathLaunch / "production.json5"
xProdData.FromFile(pathProd)
xProdData.ScanArtefacts()

xProdGrp: CGroup = xProdData.dicGroups["main"]
print(anytree.RenderTree(xProdGrp.xTree))

lGrpVarValueLists = xProdGrp.GetGroupVarValueLists()
print(lGrpVarValueLists)

# lGrpVarValueLists[1] = ["rq0004"]

dicArtVarValueLists, dictArtVarTypeLists = xProdGrp.GetArtefactVarValues(lGrpVarValueLists)
for sArtType, lValueLists in dicArtVarValueLists.items():
    print(f"{sArtType}: {lValueLists}")
# endfor

sArtType = "images"
lGrpPath = [x[0] for x in lGrpVarValueLists]
lArtPath = [x[0] for x in dicArtVarValueLists[sArtType]]

ndGrp = xProdGrp.GetGroupVarNode(lGrpPath)
ndArt = xProdGrp.GetArtVarNode(_xNode=ndGrp, _sArtType=sArtType, _lArtPath=lArtPath)
print(ndArt)
