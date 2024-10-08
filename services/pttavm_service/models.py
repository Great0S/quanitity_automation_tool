from sqlalchemy import Column, Integer, String, Float, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PTTAVMProduct(Base):
    __tablename__ = 'pttavm_products'

    id = Column(Integer, primary_key=True)
    aciklama = Column(Text, nullable=True)
    admin_code = Column(String, nullable=True)
    agirlik = Column(String)
    aktif = Column(Boolean, default=False)
    alt_kategori_adi = Column(String, nullable=True)
    alt_kategori_id = Column(Integer, default=0)
    ana_kategori_id = Column(Integer, default=0)
    barkod = Column(String)
    boy_x = Column(Float, default=0)
    boy_y = Column(Float, default=0)
    boy_z = Column(Float, default=0)
    desi = Column(Float, default=0)
    durum = Column(String)
    garanti_suresi = Column(Integer, default=0)
    garanti_veren_firma = Column(String, nullable=True)
    gtin = Column(String, nullable=True)
    iskonto = Column(Float, default=0)
    kdv_oran = Column(Float, default=0)
    kdvli = Column(Float, default=0)
    kdvsiz = Column(Float, default=0)
    kargo_profil_id = Column(Integer, default=0)
    kategori_bilgisi_guncelle = Column(Boolean, default=False)
    mevcut = Column(Boolean, default=False)
    miktar = Column(Integer, default=0)
    resim1_url = Column(String, nullable=True)
    resim2_url = Column(String, nullable=True)
    resim3_url = Column(String, nullable=True)
    row_count = Column(Integer, default=0)
    shop_id = Column(String)
    single_box = Column(Integer, default=0)
    tag = Column(Text)
    tahmini_kargo_suresi = Column(String, nullable=True)
    tedarikci_alt_kategori_adi = Column(String, nullable=True)
    tedarikci_alt_kategori_id = Column(Integer, default=0)
    tedarikci_sanal_kategori_id = Column(Integer, default=0)
    urun_adi = Column(String)
    urun_id = Column(String)
    urun_kodu = Column(String)
    urun_url = Column(String)
    uzun_aciklama = Column(Text)
    yeni_kategori_id = Column(Integer, default=0)

    def __repr__(self):
        return f"<PTTAVMProduct(urun_adi='{self.urun_adi}', barkod='{self.barkod}', miktar={self.miktar})>"

    @classmethod
    def from_dict(cls, data):
        return cls(
            aciklama=data.get('a:Aciklama'),
            admin_code=data.get('a:AdminCode', {}).get('@i:nil'),
            agirlik=data.get('a:Agirlik', ''),
            aktif=data.get('a:Aktif', 'false').lower() == 'true',
            alt_kategori_adi=data.get('a:AltKategoriAdi', {}).get('@i:nil'),
            alt_kategori_id=int(data.get('a:AltKategoriId', 0)),
            ana_kategori_id=int(data.get('a:AnaKategoriId', 0)),
            barkod=data.get('a:Barkod', ''),
            boy_x=float(data.get('a:BoyX', 0)),
            boy_y=float(data.get('a:BoyY', 0)),
            boy_z=float(data.get('a:BoyZ', 0)),
            desi=float(data.get('a:Desi', 0)),
            durum=data.get('a:Durum', ''),
            garanti_suresi=int(data.get('a:GarantiSuresi', 0)),
            garanti_veren_firma=data.get('a:GarantiVerenFirma'),
            gtin=data.get('a:Gtin'),
            iskonto=float(data.get('a:Iskonto', 0)),
            kdv_oran=float(data.get('a:KDVOran', 0)),
            kdvli=float(data.get('a:KDVli', 0)),
            kdvsiz=float(data.get('a:KDVsiz', 0)),
            kargo_profil_id=int(data.get('a:KargoProfilId', 0)),
            kategori_bilgisi_guncelle=data.get('a:KategoriBilgisiGuncelle', '0') == '1',
            mevcut=data.get('a:Mevcut', 'false').lower() == 'true',
            miktar=int(data.get('a:Miktar', 0)),
            resim1_url=data.get('a:Resim1Url'),
            resim2_url=data.get('a:Resim2Url'),
            resim3_url=data.get('a:Resim3Url'),
            row_count=int(data.get('a:RowCount', 0)),
            shop_id=data.get('a:ShopId', ''),
            single_box=int(data.get('a:SingleBox', 0)),
            tag=data.get('a:Tag', ''),
            tahmini_kargo_suresi=data.get('a:TahminiKargoSuresi', {}).get('@i:nil'),
            tedarikci_alt_kategori_adi=data.get('a:TedarikciAltKategoriAdi', {}).get('@i:nil'),
            tedarikci_alt_kategori_id=int(data.get('a:TedarikciAltKategoriId', 0)),
            tedarikci_sanal_kategori_id=int(data.get('a:TedarikciSanalKategoriId', 0)),
            urun_adi=data.get('a:UrunAdi', ''),
            urun_id=data.get('a:UrunId', ''),
            urun_kodu=data.get('a:UrunKodu', ''),
            urun_url=data.get('a:UrunUrl', ''),
            uzun_aciklama=data.get('a:UzunAciklama', ''),
            yeni_kategori_id=int(data.get('a:YeniKategoriId', 0))
        )

# Example usage:
# product_data = {...}  # Your JSON data
# product = PTTAVMProduct.from_dict(product_data)
# session.add(product)
# session.commit()