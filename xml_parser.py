import requests
import zipfile
import os
import hashlib
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine, Column, String, Boolean, ForeignKey, Text, Integer
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import logging

# Настройка логирования
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Константы
CACHE_DIR = "cache"
EXTRACT_DIR = "data"
BASE_URL = "https://islod.obrnadzor.gov.ru/opendata/"
BASE_DB_URL = 'sqlite:///education.db'

Base = declarative_base()

class OrganizationProgramAssociation(Base):
    __tablename__ = 'organization_program_association'
    organization_external_id = Column(String, ForeignKey('educational_organizations.Id'), primary_key=True)
    program_external_id = Column(String, ForeignKey('educational_programs.Id'), primary_key=True)

class EducationalOrganization(Base):
    __tablename__ = 'educational_organizations'
    Id = Column(String, primary_key=True)
    HeadEduOrgId = Column(String)
    FullName = Column(Text)
    ShortName = Column(String)
    IsBranch = Column(Boolean)
    PostAddress = Column(Text)
    Phone = Column(String)
    Fax = Column(String)
    Email = Column(String)
    WebSite = Column(String)
    OGRN = Column(String)
    INN = Column(String)
    KPP = Column(String)
    HeadPost = Column(String)
    HeadName = Column(String)
    FormName = Column(String)
    KindName = Column(String)
    TypeName = Column(String)
    RegionName = Column(String)
    FederalDistrictShortName = Column(String)
    FederalDistrictName = Column(String)

    programs = relationship(
        "EducationalProgram",
        secondary="organization_program_association",
        back_populates="organizations"
    )

class EducationalProgram(Base):
    __tablename__ = 'educational_programs'
    Id = Column(String, primary_key=True)
    TypeName = Column(String)
    EduLevelName = Column(String)
    ProgrammName = Column(Text)
    ProgrammCode = Column(String)
    UGSCode = Column(String)
    UGSName = Column(String)
    EduNormativePeriod = Column(String)
    Qualification = Column(String)
    IsAccredited = Column(String)
    IsCanceled = Column(String)
    IsSuspended = Column(String)

    organizations = relationship(
        "EducationalOrganization",
        secondary="organization_program_association",
        back_populates="programs"
    )

def file_hash(content):
    return hashlib.sha256(content).hexdigest()

def save_to_cache(url, content):
    os.makedirs(CACHE_DIR, exist_ok=True)
    file_name = url.split("/")[-1]
    path = os.path.join(CACHE_DIR, file_name)
    with open(path, "wb") as f:
        f.write(content)
    return path

def has_file_changed(url, content):
    hash_path = os.path.join(CACHE_DIR, "hashes.txt")
    if not os.path.exists(hash_path):
        return True

    with open(hash_path, "r") as f:
        for line in f:
            if line.startswith(url.split("/")[-1] + ":"):
                return line.strip().split(":")[1] != file_hash(content)
    return True

def update_hash(url, content):
    file_name = url.split("/")[-1]
    hash_path = os.path.join(CACHE_DIR, "hashes.txt")
    hashes = {}

    if os.path.exists(hash_path):
        with open(hash_path, "r") as f:
            for line in f:
                if ":" in line:
                    name, h = line.strip().split(":")
                    hashes[name] = h

    hashes[file_name] = file_hash(content)

    with open(hash_path, "w") as f:
        for name, h in hashes.items():
            f.write(f"{name}:{h}\n")

def extract_archive(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"Архив распакован в: {extract_to}")

def clean_directory(directory, keep_files):
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isfile(item_path) and item not in keep_files:
            os.remove(item_path)

def download_if_updated(zip_url):
    try:
        response = requests.get(zip_url, timeout=10)
        response.raise_for_status()

        if has_file_changed(zip_url, response.content):
            print("Загружаем обновленный архив...")
            cached_path = save_to_cache(zip_url, response.content)
            update_hash(zip_url, response.content)
            extract_archive(cached_path, EXTRACT_DIR)
    except requests.RequestException as e:
        print(f"Ошибка загрузки: {e}")
        raise

def get_text(element, tag):
    elem = element.find(tag)
    return elem.text.strip() if (elem is not None and elem.text is not None) else ""

def get_bool(element, tag):
    elem = element.find(tag)
    if elem is None or elem.text is None:
        return "1" if tag == "IsAccredited" else "0"  # Инвертируем для IsAccredited
    text = elem.text.strip().lower()
    if tag == "IsAccredited":
        return "0" if text in ('1', 'true', 't', 'yes', 'y', 'да') else "1"
    else:
        return "1" if text in ('1', 'true', 't', 'yes', 'y', 'да') else "0"

def parse_xml(xml_file):
    organizations = {}
    programs = {}
    associations = []

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Парсинг организаций
        for org_elem in root.findall(".//ActualEducationOrganization"):
            org_id = get_text(org_elem, "Id")
            if org_id not in organizations:
                organizations[org_id] = EducationalOrganization(
                    Id=org_id,
                    HeadEduOrgId=get_text(org_elem, "HeadEduOrgId"),
                    FullName=get_text(org_elem, "FullName"),
                    ShortName=get_text(org_elem, "ShortName"),
                    IsBranch=get_bool(org_elem, "IsBranch") == "1",
                    PostAddress=get_text(org_elem, "PostAddress"),
                    Phone=get_text(org_elem, "Phone"),
                    Fax=get_text(org_elem, "Fax"),
                    Email=get_text(org_elem, "Email"),
                    WebSite=get_text(org_elem, "WebSite"),
                    OGRN=get_text(org_elem, "OGRN"),
                    INN=get_text(org_elem, "INN"),
                    KPP=get_text(org_elem, "KPP"),
                    HeadPost=get_text(org_elem, "HeadPost"),
                    HeadName=get_text(org_elem, "HeadName"),
                    FormName=get_text(org_elem, "FormName"),
                    KindName=get_text(org_elem, "KindName"),
                    TypeName=get_text(org_elem, "TypeName"),
                    RegionName=get_text(org_elem, "RegionName"),
                    FederalDistrictShortName=get_text(org_elem, "FederalDistrictShortName"),
                    FederalDistrictName=get_text(org_elem, "FederalDistrictName")
                )

        # Парсинг программ и связей
        for supplement in root.findall(".//Supplement"):
            for prog_elem in supplement.findall(".//EducationalProgram"):
                prog_id = get_text(prog_elem, "Id")
                org_id = get_text(supplement.find(".//ActualEducationOrganization"), "Id")

                if prog_id not in programs:
                    programs[prog_id] = EducationalProgram(
                        Id=prog_id,
                        TypeName=get_text(prog_elem, "TypeName"),
                        EduLevelName=get_text(prog_elem, "EduLevelName"),
                        ProgrammName=get_text(prog_elem, "ProgrammName"),
                        ProgrammCode=get_text(prog_elem, "ProgrammCode"),
                        UGSCode=get_text(prog_elem, "UGSCode"),
                        UGSName=get_text(prog_elem, "UGSName"),
                        EduNormativePeriod=get_text(prog_elem, "EduNormativePeriod"),
                        Qualification=get_text(prog_elem, "Qualification"),
                        IsAccredited=get_bool(prog_elem, "IsAccredited"),
                        IsCanceled=get_bool(prog_elem, "IsCanceled"),
                        IsSuspended=get_bool(prog_elem, "IsSuspended")
                    )

                if org_id in organizations and prog_id in programs:
                    associations.append(OrganizationProgramAssociation(
                        organization_external_id=org_id,
                        program_external_id=prog_id
                    ))

        return list(organizations.values()), list(programs.values()), associations

    except ET.ParseError as e:
        print(f"Ошибка парсинга XML: {e}")
        raise

def main():
    try:
        # Поиск актуального архива
        actual_zip_url = None
        for days_ago in range(1, 4):
            date_str = (datetime.now() - timedelta(days=days_ago)).strftime("%Y%m%d")
            zip_url = f"{BASE_URL}data-{date_str}-structure-20160713.zip"
            try:
                if requests.head(zip_url, timeout=5).status_code == 200:
                    actual_zip_url = zip_url
                    break
            except requests.RequestException:
                continue

        if not actual_zip_url:
            raise Exception("Не удалось найти актуальный архив за последние 3 дня")

        # Загрузка и обработка данных
        download_if_updated(actual_zip_url)
        clean_directory("cache", ["hashes.txt", os.path.basename(actual_zip_url)])
        clean_directory("data", [f"data-{date_str}-structure-20160713.xml"])

        # Инициализация БД
        engine = create_engine(BASE_DB_URL)
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

        # Сохранение данных
        with sessionmaker(bind=engine)() as session:
            xml_file = os.path.join(EXTRACT_DIR, f"data-{date_str}-structure-20160713.xml")
            organizations, programs, associations = parse_xml(xml_file)

            session.add_all(organizations)
            session.add_all(programs)
            session.add_all(associations)
            session.commit()

            print(f"\nУспешно загружено:")
            print(f"- Организаций: {len(organizations)}")
            print(f"- Образовательных программ: {len(programs)}")
            print(f"- Связей между организациями и программами: {len(associations)}")

            # Пример вывода первых 5 связей
            print("\nПример связей:")
            for assoc in associations[:5]:
                print(f"{assoc.organization_external_id} {assoc.program_external_id}")

    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        raise

if __name__ == "__main__":
    main()
