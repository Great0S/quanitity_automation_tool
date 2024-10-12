from typing import Optional, List, Union
from pydantic import BaseModel, Field

class PTTAVMProductSchema(BaseModel):
    aciklama: Optional[str] = Field(None, alias='a:Aciklama')
    agirlik: str = Field(None, alias='a:Agirlik')
    aktif: bool = Field(default=False, alias='a:Aktif')
    alt_kategori_id: int = Field(0, alias='a:AltKategoriId')
    ana_kategori_id: int = Field(0, alias='a:AnaKategoriId')
    barkod: str = Field(alias='a:Barkod')
    boy_x: float = Field(0, alias='a:BoyX')
    boy_y: float = Field(0, alias='a:BoyY')
    boy_z: float = Field(0, alias='a:BoyZ')
    desi: float = Field(0, alias='a:Desi')
    durum: str = Field(alias='a:Durum')
    garanti_suresi: int = Field(0, alias='a:GarantiSuresi')
    garanti_veren_firma: Optional[str] = Field(None, alias='a:GarantiVerenFirma')
    gtin: Optional[str] = Field(None, alias='a:Gtin')
    iskonto: float = Field(0, alias='a:Iskonto')
    kdv_oran: float = Field(0, alias='a:KDVOran')
    kdvli: float = Field(0, alias='a:KDVli')
    kdvsiz: float = Field(0, alias='a:KDVsiz')
    kargo_profil_id: int = Field(0, alias='a:KargoProfilId')
    kategori_bilgisi_guncelle: bool = Field(default=False, alias='a:KategoriBilgisiGuncelle')
    mevcut: bool = Field(default=False, alias='a:Mevcut')
    miktar: int = Field(0, alias='a:Miktar')
    resim1_url: Optional[str] = Field(None, alias='a:Resim1Url')
    resim2_url: Optional[str] = Field(None, alias='a:Resim2Url')
    resim3_url: Optional[str] = Field(None, alias='a:Resim3Url')
    row_count: int = Field(0, alias='a:RowCount')
    shop_id: str = Field(alias='a:ShopId')
    single_box: int = Field(1, alias='a:SingleBox')
    tag: str = Field(alias='a:Tag')
    urun_adi: str = Field(alias='a:UrunAdi')
    urun_id: str = Field(alias='a:UrunId')
    urun_kodu: str = Field(alias='a:UrunKodu')
    urun_url: str = Field(alias='a:UrunUrl')
    uzun_aciklama: str = Field(alias='a:UzunAciklama')
    yeni_kategori_id: int = Field(1557, alias='a:YeniKategoriId')

    class Config:
        populate_by_name = True


class PTTAVMProductUpdateSchema(BaseModel):
    aktif: bool = Field(..., alias='a:Aktif')
    barkod: str = Field(..., alias='a:Barkod')
    kdv_oran: float = Field(..., alias='a:KDVOran')
    kdvli: float = Field(..., alias='a:KDVli')
    kdvsiz: float = Field(0, alias='a:KDVsiz')  # Assuming default value is 0
    miktar: int = Field(..., alias='a:Miktar')
    shop_id: str = Field(..., alias='a:ShopId')

    class Config:
        populate_by_name = True


class PTTAVMProductResponseSchema(BaseModel):
    status_code: int
    message: str
    data: Optional[Union[dict, str]] = None

    class Config:
        from_attributes = True

