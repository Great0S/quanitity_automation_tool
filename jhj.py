

from api.pazarama_api import getPazarama_productsList
from api.pttavm_api import getpttavm_procuctskdata


pro = getPazarama_productsList(True)
print(pro[1])
pass