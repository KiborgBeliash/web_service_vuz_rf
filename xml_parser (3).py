import requests
import zipfile
import os
import hashlib
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Константы
CACHE_DIR = "cache"
EXTRACT_DIR = "data"
BASE_URL = "https://islod.obrnadzor.gov.ru/opendata/"
BASE_DB_URL = 'sqlite:///education.db'

Base = declarative_base()


# Ассоциативная таблица для связи many-to-many
class OrganizationProgramAssociation(Base):
    __tablename__ = 'organization_program_association'
    organization_external_id = Column(String, ForeignKey('educational_organizations.external_id'), primary_key=True)
    program_external_id = Column(String, ForeignKey('educational_programs.external_id'), primary_key=True)


class EducationalOrganization(Base):
    __tablename__ = 'educational_organizations'
    external_id = Column(String, primary_key=True)
    head_edu_org_id = Column(String)
    full_name = Column(String)
    short_name = Column(String)
    is_branch = Column(Boolean)
    post_address = Column(String)
    fax = Column(String)
    phone = Column(String)
    email = Column(String)
    web_site = Column(String)
    orgn = Column(String)
    inn = Column(String)
    kpp = Column(String)
    head_post = Column(String)
    head_name = Column(String)
    form_name = Column(String)
    kind_name = Column(String)
    type_name = Column(String)
    region_name = Column(String)
    federal_district_short_name = Column(String)
    federal_district_name = Column(String)

    programs = relationship(
        "EducationalProgram",
        secondary="organization_program_association",
        back_populates="organizations"
    )


class EducationalProgram(Base):
    __tablename__ = 'educational_programs'
    external_id = Column(String, primary_key=True)
    programm_code = Column(String)
    programm_name = Column(String)
    edu_normative_period = Column(String)
    qualification = Column(String)
    program_type = Column(String)
    ugs_code = Column(String)
    is_accredited = Column(Boolean)
    is_canceled = Column(Boolean)
    is_suspended = Column(Boolean)

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
    return elem.text == "1" if elem is not None else False


def parse_xml(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        organizations = {}
        programs = []
        associations = []

        # Парсим организации
        for org_elem in root.findall(".//ActualEducationOrganization"):
            external_id = get_text(org_elem, "Id")

            if external_id not in organizations:
                organizations[external_id] = EducationalOrganization(
                    external_id=external_id,
                    head_edu_org_id=get_text(org_elem, "HeadEduOrgId"),
                    full_name=get_text(org_elem, "FullName"),
                    short_name=get_text(org_elem, "ShortName"),
                    is_branch=get_bool(org_elem, "IsBranch"),
                    post_address=get_text(org_elem, "PostAddress"),
                    fax=get_text(org_elem, "Fax"),
                    phone=get_text(org_elem, "Phone"),
                    email=get_text(org_elem, "Email"),
                    web_site=get_text(org_elem, "WebSite"),
                    orgn=get_text(org_elem, "ORGN"),
                    inn=get_text(org_elem, "INN"),
                    kpp=get_text(org_elem, "KPP"),
                    head_post=get_text(org_elem, "HeadPost"),
                    head_name=get_text(org_elem, "HeadName"),
                    form_name=get_text(org_elem, "FormName"),
                    kind_name=get_text(org_elem, "KindName"),
                    type_name=get_text(org_elem, "TypeName"),
                    region_name=get_text(org_elem, "RegionName"),
                    federal_district_short_name=get_text(org_elem, "FederalDistrictShortName"),
                    federal_district_name=get_text(org_elem, "FederalDistrictName")
                )

        # Парсим программы и связи
        program_ids = set()
        for prog_elem in root.findall(".//EducationalPrograms/EducationalProgram"):
            program_external_id = get_text(prog_elem, "Id")
            org_external_id = get_text(prog_elem, "EduOrgId")

            if program_external_id not in program_ids:
                programs.append(EducationalProgram(
                    external_id=program_external_id,
                    programm_code=get_text(prog_elem, "ProgrammCode"),
                    programm_name=get_text(prog_elem, "ProgrammName"),
                    edu_normative_period=get_text(prog_elem, "EduNormativePeriod"),
                    qualification=get_text(prog_elem, "Qualification"),
                    program_type=get_text(prog_elem, "TypeName"),
                    ugs_code=get_text(prog_elem, "UGSCode"),
                    is_accredited=not get_bool(prog_elem, "IsAccredited"),  # Инвертируем значение
                    is_canceled=get_bool(prog_elem, "IsCanceled"),
                    is_suspended=get_bool(prog_elem, "IsSuspended")
                ))
                program_ids.add(program_external_id)

            if org_external_id in organizations:
                associations.append(OrganizationProgramAssociation(
                    organization_external_id=org_external_id,
                    program_external_id=program_external_id
                ))

        return list(organizations.values()), programs, associations

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

    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        raise


if __name__ == "__main__":
    main()