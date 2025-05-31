from flask import Flask, render_template, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from xml_parser import EducationalOrganization, EducationalProgram, OrganizationProgramAssociation
import os
import math

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Настройка подключения к БД
DB_PATH = 'education.db'
engine = create_engine(f'sqlite:///{DB_PATH}')
Session = sessionmaker(bind=engine)


@app.route('/')
def index():
    # Параметры пагинации и сортировки
    page = request.args.get('page', 1, type=int)
    per_page = 20
    sort_field = request.args.get('sort', 'Id')
    sort_order = request.args.get('order', 'asc')

    # Параметры фильтрации
    region = request.args.get('region', '')
    program_name = request.args.get('program_name', '')
    ugs_name = request.args.get('ugs_name', '')
    form_name = request.args.get('form_name', '')

    with Session() as session:
        # Базовый запрос организаций
        query = session.query(EducationalOrganization)

        # Применяем фильтры
        if region:
            query = query.filter(EducationalOrganization.RegionName.ilike(f'%{region}%'))
        if form_name:
            query = query.filter(EducationalOrganization.FormName.ilike(f'%{form_name}%'))

        # Фильтры по связанным таблицам (программы)
        if program_name or ugs_name:
            query = query.join(
                OrganizationProgramAssociation,
                EducationalOrganization.Id == OrganizationProgramAssociation.organization_external_id
            ).join(
                EducationalProgram,
                OrganizationProgramAssociation.program_external_id == EducationalProgram.Id
            )
            if program_name:
                query = query.filter(EducationalProgram.ProgrammName.ilike(f'%{program_name}%'))
            if ugs_name:
                query = query.filter(EducationalProgram.UGSName.ilike(f'%{ugs_name}%'))

        # Применяем сортировку
        if sort_order == 'asc':
            query = query.order_by(getattr(EducationalOrganization, sort_field).asc())
        else:
            query = query.order_by(getattr(EducationalOrganization, sort_field).desc())

        # Ручная реализация пагинации
        total_count = query.count()
        total_pages = math.ceil(total_count / per_page)
        offset = (page - 1) * per_page
        organizations = query.offset(offset).limit(per_page).all()

        # Получаем уникальные значения для фильтров
        regions = session.query(
            EducationalOrganization.RegionName
        ).distinct().all()

        forms = session.query(
            EducationalOrganization.FormName
        ).distinct().all()

        program_names = session.query(
            EducationalProgram.ProgrammName
        ).distinct().all()

        ugs_names = session.query(
            EducationalProgram.UGSName
        ).distinct().all()

    # Рассчитываем диапазон страниц для отображения
    start_page = max(1, page - 4)
    end_page = min(total_pages, page + 4)

    # Если в начале, показываем первые 8 страниц
    if page <= 5:
        start_page = 1
        end_page = min(8, total_pages)

    # Если в конце, показываем последние 8 страниц
    elif page >= total_pages - 4:
        start_page = max(1, total_pages - 7)
        end_page = total_pages

    # Формируем список страниц для отображения
    page_range = list(range(start_page, end_page + 1))

    return render_template(
        'index.html',
        organizations=organizations,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_count=total_count,
        page_range=page_range,
        regions=[r[0] for r in regions if r[0]],
        program_names=[p[0] for p in program_names if p[0]],
        ugs_names=[u[0] for u in ugs_names if u[0]],
        forms=[f[0] for f in forms if f[0]],
        sort_field=sort_field,
        sort_order=sort_order,
        current_filters={
            'region': region,
            'program_name': program_name,
            'ugs_name': ugs_name,
            'form_name': form_name
        }
    )


@app.route('/organization/<org_id>')
def organization_detail(org_id):
    with Session() as session:
        org = session.query(EducationalOrganization).get(org_id)
        programs = session.query(EducationalProgram).join(
            OrganizationProgramAssociation,
            EducationalProgram.Id == OrganizationProgramAssociation.program_external_id
        ).filter(
            OrganizationProgramAssociation.organization_external_id == org_id
        ).all()
    return render_template('organization.html', organization=org, programs=programs)


if __name__ == '__main__':
    # Создаем папку для шаблонов если ее нет
    os.makedirs('templates', exist_ok=True)

    # Создаем HTML шаблоны с современным дизайном
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Реестр образовательных организаций</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Montserrat:wght@600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #2c3e50;
            --secondary: #3498db;
            --accent: #e74c3c;
            --light: #ecf0f1;
            --dark: #34495e;
            --success: #27ae60;
            --warning: #f39c12;
            --card-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
            --hover-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Roboto', sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #e4edf5 100%);
            color: #333;
            line-height: 1.6;
            padding: 20px;
            min-height: 100vh;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: white;
            border-radius: 15px;
            box-shadow: var(--card-shadow);
            position: relative;
            overflow: hidden;
        }

        header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 5px;
            background: linear-gradient(90deg, var(--secondary), var(--success), var(--warning));
        }

        h1 {
            font-family: 'Montserrat', sans-serif;
            color: var(--primary);
            font-size: 2.5rem;
            margin-bottom: 10px;
        }

        .subtitle {
            color: var(--dark);
            font-size: 1.1rem;
            max-width: 700px;
            margin: 0 auto 15px;
        }

        .stats {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 15px;
        }

        .stat-card {
            background: white;
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
            text-align: center;
            min-width: 150px;
        }

        .stat-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--secondary);
            margin-bottom: 5px;
        }

        .stat-label {
            color: var(--dark);
            font-size: 0.9rem;
        }

        .filters {
            background: white;
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: var(--card-shadow);
        }

        .filter-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .filter-group {
            margin-bottom: 0;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: var(--primary);
        }

        select {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e6ed;
            border-radius: 8px;
            background: white;
            font-size: 16px;
            transition: all 0.3s;
            appearance: none;
            background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
            background-repeat: no-repeat;
            background-position: right 1rem center;
            background-size: 1em;
        }

        select:focus {
            border-color: var(--secondary);
            outline: none;
            box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.2);
        }

        .filter-actions {
            display: flex;
            justify-content: flex-end;
            gap: 15px;
            margin-top: 10px;
        }

        .btn {
            padding: 12px 25px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .btn-primary {
            background: var(--secondary);
            color: white;
            box-shadow: 0 4px 10px rgba(52, 152, 219, 0.3);
        }

        .btn-primary:hover {
            background: #2980b9;
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(52, 152, 219, 0.4);
        }

        .btn-reset {
            background: #f0f3f7;
            color: var(--dark);
        }

        .btn-reset:hover {
            background: #e0e6ed;
            transform: translateY(-2px);
        }

        .table-container {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: var(--card-shadow);
            margin-bottom: 30px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        thead {
            background: linear-gradient(to right, var(--primary), var(--dark));
            color: white;
        }

        th {
            padding: 18px 20px;
            text-align: left;
            font-weight: 600;
            font-size: 16px;
            position: relative;
            cursor: pointer;
            transition: background 0.3s;
        }

        th:hover {
            background: rgba(0, 0, 0, 0.2);
        }

        th.sorted-asc::after {
            content: "▲";
            position: absolute;
            right: 15px;
            font-size: 14px;
        }

        th.sorted-desc::after {
            content: "▼";
            position: absolute;
            right: 15px;
            font-size: 14px;
        }

        tbody tr {
            border-bottom: 1px solid #f0f3f7;
            transition: background 0.2s;
        }

        tbody tr:hover {
            background: #f8fafc;
        }

        td {
            padding: 16px 20px;
            color: #2d3748;
        }

        .org-name {
            font-weight: 500;
            color: var(--primary);
            transition: color 0.2s;
        }

        a {
            text-decoration: none;
            color: inherit;
        }

        .org-name:hover {
            color: var(--secondary);
        }

        .contacts {
            font-size: 14px;
            color: #4a5568;
        }

        .pagination-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
            background: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: var(--card-shadow);
        }

        .pagination-info {
            font-size: 15px;
            color: var(--dark);
            font-weight: 500;
        }

        .pagination {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .page-item {
            list-style: none;
        }

        .page-link {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            border-radius: 10px;
            background: white;
            color: var(--primary);
            font-weight: 500;
            text-decoration: none;
            border: 2px solid #e0e6ed;
            transition: all 0.3s;
        }

        .page-link:hover {
            background: #f0f3f7;
            transform: translateY(-2px);
        }

        .page-link.active {
            background: var(--secondary);
            color: white;
            border-color: var(--secondary);
        }

        .page-link.disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .page-link.jump {
            width: auto;
            padding: 0 15px;
        }

        footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #718096;
            font-size: 14px;
        }

        @media (max-width: 768px) {
            .filter-grid {
                grid-template-columns: 1fr;
            }

            .filter-actions {
                flex-direction: column;
            }

            .pagination-container {
                flex-direction: column;
            }

            h1 {
                font-size: 2rem;
            }

            .stats {
                flex-direction: column;
                align-items: center;
            }

            .stat-card {
                width: 100%;
                max-width: 300px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1><i class="fas fa-graduation-cap"></i> Реестр образовательных организаций</h1>
            <p class="subtitle">Поиск и фильтрация образовательных учреждений и программ по всей России</p>

            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{{ organizations|length }}</div>
                    <div class="stat-label">на странице</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ total_count }}</div>
                    <div class="stat-label">всего организаций</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ total_pages }}</div>
                    <div class="stat-label">страниц</div>
                </div>
            </div>
        </header>

        <div class="filters">
            <form method="GET">
                <div class="filter-grid">
                    <div class="filter-group">
                        <label for="region"><i class="fas fa-map-marker-alt"></i> Регион:</label>
                        <select id="region" name="region">
                            <option value="">Все регионы</option>
                            {% for region in regions %}
                                <option value="{{ region }}" {% if current_filters.region == region %}selected{% endif %}>
                                    {{ region }}
                                </option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="filter-group">
                        <label for="form_name"><i class="fas fa-user-graduate"></i> Форма обучения:</label>
                        <select id="form_name" name="form_name">
                            <option value="">Все формы</option>
                            {% for form in forms %}
                                <option value="{{ form }}" {% if current_filters.form_name == form %}selected{% endif %}>
                                    {{ form }}
                                </option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="filter-group">
                        <label for="program_name"><i class="fas fa-book"></i> Образовательная программа:</label>
                        <select id="program_name" name="program_name">
                            <option value="">Все программы</option>
                            {% for program in program_names %}
                                <option value="{{ program }}" {% if current_filters.program_name == program %}selected{% endif %}>
                                    {{ program|truncate(70) }}
                                </option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="filter-group">
                        <label for="ugs_name"><i class="fas fa-layer-group"></i> Укрупненная группа специальностей:</label>
                        <select id="ugs_name" name="ugs_name">
                            <option value="">Все группы</option>
                            {% for ugs in ugs_names %}
                                <option value="{{ ugs }}" {% if current_filters.ugs_name == ugs %}selected{% endif %}>
                                    {{ ugs }}
                                </option>
                            {% endfor %}
                        </select>
                    </div>
                </div>

                <div class="filter-actions">
                    <button type="button" class="btn btn-reset" onclick="resetFilters()">
                        <i class="fas fa-undo"></i> Сбросить фильтры
                    </button>
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-filter"></i> Применить фильтры
                    </button>
                </div>
            </form>
        </div>

        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th onclick="sortTable('FullName')" 
                            {% if sort_field == 'FullName' %}class="sorted-{{ sort_order }}"{% endif %}>
                            Название организации
                        </th>
                        <th onclick="sortTable('RegionName')" 
                            {% if sort_field == 'RegionName' %}class="sorted-{{ sort_order }}"{% endif %}>
                            Регион
                        </th>
                        <th onclick="sortTable('FormName')" 
                            {% if sort_field == 'FormName' %}class="sorted-{{ sort_order }}"{% endif %}>
                            Форма обучения
                        </th>
                        <th onclick="sortTable('TypeName')" 
                            {% if sort_field == 'TypeName' %}class="sorted-{{ sort_order }}"{% endif %}>
                            Тип организации
                        </th>
                        <th>Контакты</th>
                    </tr>
                </thead>
                <tbody>
                    {% for org in organizations %}
                    <tr>
                        <td>
                            <a href="{{ url_for('organization_detail', org_id=org.Id) }}" class="org-name">
                                <i class="fas fa-school"></i> {{ org.ShortName or org.FullName }}
                            </a>
                        </td>
                        <td>{{ org.RegionName }}</td>
                        <td>{{ org.FormName }}</td>
                        <td>{{ org.TypeName }}</td>
                        <td class="contacts">
                            {% if org.Phone %}
                                <div><i class="fas fa-phone"></i> {{ org.Phone }}</div>
                            {% endif %}
                            {% if org.Email %}
                                <div><i class="fas fa-envelope"></i> {{ org.Email }}</div>
                            {% endif %}
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="5" style="text-align: center; padding: 30px;">
                            <i class="fas fa-search" style="font-size: 40px; margin-bottom: 15px; color: #ccc;"></i>
                            <h3 style="color: #777;">Организации не найдены</h3>
                            <p>Попробуйте изменить параметры фильтрации</p>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="pagination-container">
            <div class="pagination-info">
                Страница {{ page }} из {{ total_pages }} | Показано {{ organizations|length }} из {{ total_count }} организаций
            </div>

            <ul class="pagination">
                {% if page > 1 %}
                    <li class="page-item">
                        <a class="page-link jump" href="{{ url_for('index', page=1, sort=sort_field, order=sort_order, region=current_filters.region, form_name=current_filters.form_name, program_name=current_filters.program_name, ugs_name=current_filters.ugs_name) }}">
                            <i class="fas fa-angle-double-left"></i> Первая
                        </a>
                    </li>
                    <li class="page-item">
                        <a class="page-link" href="{{ url_for('index', page=page-1, sort=sort_field, order=sort_order, region=current_filters.region, form_name=current_filters.form_name, program_name=current_filters.program_name, ugs_name=current_filters.ugs_name) }}">
                            <i class="fas fa-angle-left"></i>
                        </a>
                    </li>
                {% endif %}

                {% for p in page_range %}
                    <li class="page-item">
                        <a class="page-link {% if p == page %}active{% endif %}" href="{{ url_for('index', page=p, sort=sort_field, order=sort_order, region=current_filters.region, form_name=current_filters.form_name, program_name=current_filters.program_name, ugs_name=current_filters.ugs_name) }}">
                            {{ p }}
                        </a>
                    </li>
                {% endfor %}

                {% if page < total_pages %}
                    <li class="page-item">
                        <a class="page-link" href="{{ url_for('index', page=page+1, sort=sort_field, order=sort_order, region=current_filters.region, form_name=current_filters.form_name, program_name=current_filters.program_name, ugs_name=current_filters.ugs_name) }}">
                            <i class="fas fa-angle-right"></i>
                        </a>
                    </li>
                    <li class="page-item">
                        <a class="page-link jump" href="{{ url_for('index', page=total_pages, sort=sort_field, order=sort_order, region=current_filters.region, form_name=current_filters.form_name, program_name=current_filters.program_name, ugs_name=current_filters.ugs_name) }}">
                            Последняя <i class="fas fa-angle-double-right"></i>
                        </a>
                    </li>
                {% endif %}
            </ul>
        </div>

        <footer>
            <p>© 2023 Реестр образовательных организаций | Данные предоставлены Рособрнадзором</p>
        </footer>
    </div>

    <script>
        function sortTable(field) {
            const url = new URL(window.location.href);
            const params = url.searchParams;

            if (params.get('sort') === field) {
                params.set('order', params.get('order') === 'asc' ? 'desc' : 'asc');
            } else {
                params.set('sort', field);
                params.set('order', 'asc');
            }

            window.location.href = url.toString();
        }

        function resetFilters() {
            window.location.href = "{{ url_for('index') }}";
        }
    </script>
</body>
</html>''')

    with open('templates/organization.html', 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ organization.ShortName or organization.FullName }}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Montserrat:wght@600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #2c3e50;
            --secondary: #3498db;
            --accent: #e74c3c;
            --light: #ecf0f1;
            --dark: #34495e;
            --success: #27ae60;
            --warning: #f39c12;
            --card-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
            --hover-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Roboto', sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #e4edf5 100%);
            color: #333;
            line-height: 1.6;
            padding: 20px;
            min-height: 100vh;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
        }

        .back-link {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 25px;
            padding: 10px 20px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
            text-decoration: none;
            color: var(--primary);
            font-weight: 500;
            transition: all 0.3s;
        }

        .back-link:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(0, 0, 0, 0.12);
            background: var(--secondary);
            color: white;
        }

        .org-info {
            background: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: var(--card-shadow);
            position: relative;
            overflow: hidden;
        }

        .org-info::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 5px;
            background: linear-gradient(90deg, var(--secondary), var(--success), var(--warning));
        }

        .org-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 1px solid #f0f3f7;
        }

        .org-title {
            flex: 1;
            min-width: 300px;
        }

        h1 {
            font-family: 'Montserrat', sans-serif;
            color: var(--primary);
            font-size: 2rem;
            margin-bottom: 10px;
        }

        .org-meta {
            background: #f8fafc;
            padding: 15px;
            border-radius: 10px;
            min-width: 250px;
        }

        .meta-item {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }

        .meta-item:last-child {
            margin-bottom: 0;
        }

        .meta-icon {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: var(--light);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--secondary);
        }

        .meta-content {
            flex: 1;
        }

        .meta-label {
            font-size: 0.85rem;
            color: #718096;
        }

        .meta-value {
            font-weight: 500;
            color: var(--dark);
        }

        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .info-group {
            margin-bottom: 20px;
        }

        .info-label {
            font-weight: 500;
            color: var(--primary);
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .info-value {
            padding-left: 26px;
            color: #2d3748;
        }

        .programs-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 15px;
        }

        h2 {
            font-family: 'Montserrat', sans-serif;
            color: var(--primary);
            font-size: 1.8rem;
        }

        .program-count {
            background: var(--secondary);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 1.1rem;
        }

        .programs-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: var(--card-shadow);
        }

        .programs-table th {
            background: linear-gradient(to right, var(--primary), var(--dark));
            color: white;
            padding: 16px 20px;
            text-align: left;
            font-weight: 600;
        }

        .programs-table td {
            padding: 15px 20px;
            border-bottom: 1px solid #f0f3f7;
            color: #2d3748;
        }

        .programs-table tr:nth-child(even) {
            background-color: #f8f9fa;
        }

        .programs-table tr:hover {
            background-color: #f0f9ff;
        }

        .program-name {
            font-weight: 500;
            color: var(--primary);
        }

        .status-badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }

        .status-accredited {
            background: rgba(39, 174, 96, 0.15);
            color: #27ae60;
        }

        .status-canceled {
            background: rgba(231, 76, 60, 0.15);
            color: #e74c3c;
        }

        .status-suspended {
            background: rgba(243, 156, 18, 0.15);
            color: #f39c12;
        }

        .no-programs {
            background: white;
            padding: 40px;
            text-align: center;
            border-radius: 15px;
            box-shadow: var(--card-shadow);
        }

        .no-programs i {
            font-size: 50px;
            color: #cbd5e0;
            margin-bottom: 20px;
        }

        .no-programs h3 {
            color: #718096;
            margin-bottom: 10px;
        }

        footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #718096;
            font-size: 14px;
        }

        @media (max-width: 768px) {
            .org-header {
                flex-direction: column;
            }

            .info-grid {
                grid-template-columns: 1fr;
            }

            h1 {
                font-size: 1.8rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="{{ url_for('index') }}" class="back-link">
            <i class="fas fa-arrow-left"></i> Назад к списку
        </a>

        <div class="org-info">
            <div class="org-header">
                <div class="org-title">
                    <h1>{{ organization.ShortName or organization.FullName }}</h1>
                    <p>{{ organization.FullName }}</p>
                </div>

                <div class="org-meta">
                    <div class="meta-item">
                        <div class="meta-icon">
                            <i class="fas fa-map-marker-alt"></i>
                        </div>
                        <div class="meta-content">
                            <div class="meta-label">Регион</div>
                            <div class="meta-value">{{ organization.RegionName }}</div>
                        </div>
                    </div>

                    <div class="meta-item">
                        <div class="meta-icon">
                            <i class="fas fa-graduation-cap"></i>
                        </div>
                        <div class="meta-content">
                            <div class="meta-label">Форма обучения</div>
                            <div class="meta-value">{{ organization.FormName }}</div>
                        </div>
                    </div>

                    <div class="meta-item">
                        <div class="meta-icon">
                            <i class="fas fa-university"></i>
                        </div>
                        <div class="meta-content">
                            <div class="meta-label">Тип организации</div>
                            <div class="meta-value">{{ organization.TypeName }}</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="info-grid">
                <div class="info-group">
                    <div class="info-label"><i class="fas fa-home"></i> Адрес</div>
                    <div class="info-value">{{ organization.PostAddress }}</div>
                </div>

                <div class="info-group">
                    <div class="info-label"><i class="fas fa-phone"></i> Контакты</div>
                    <div class="info-value">
                        {% if organization.Phone %}Тел: {{ organization.Phone }}<br>{% endif %}
                        {% if organization.Fax %}Факс: {{ organization.Fax }}<br>{% endif %}
                        {% if organization.Email %}Email: {{ organization.Email }}{% endif %}
                    </div>
                </div>

                <div class="info-group">
                    <div class="info-label"><i class="fas fa-globe"></i> Веб-сайт</div>
                    <div class="info-value">
                        {% if organization.WebSite %}
                            <a href="{{ organization.WebSite }}" target="_blank">{{ organization.WebSite }}</a>
                        {% else %}
                            Не указан
                        {% endif %}
                    </div>
                </div>

                <div class="info-group">
                    <div class="info-label"><i class="fas fa-user-tie"></i> Руководство</div>
                    <div class="info-value">
                        {{ organization.HeadName }}<br>
                        <em>{{ organization.HeadPost }}</em>
                    </div>
                </div>
            </div>
        </div>

        <div class="programs-header">
            <h2>Образовательные программы</h2>
            <div class="program-count">{{ programs|length }} программ</div>
        </div>

        {% if programs %}
        <table class="programs-table">
            <thead>
                <tr>
                    <th>Название программы</th>
                    <th>Уровень образования</th>
                    <th>Квалификация</th>
                    <th>Статус</th>
                </tr>
            </thead>
            <tbody>
                {% for program in programs %}
                <tr>
                    <td class="program-name">{{ program.ProgrammName }}</td>
                    <td>{{ program.EduLevelName }}</td>
                    <td>{{ program.Qualification }}</td>
                    <td>
                        {% if program.IsAccredited %}
                            <span class="status-badge status-accredited">Аккредитована</span>
                        {% elif program.IsCanceled %}
                            <span class="status-badge status-canceled">Отменена</span>
                        {% elif program.IsSuspended %}
                            <span class="status-badge status-suspended">Приостановлена</span>
                        {% else %}
                            -
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="no-programs">
            <i class="fas fa-book-open"></i>
            <h3>Нет доступных образовательных программ</h3>
            <p>Для этой организации не найдено образовательных программ</p>
        </div>
        {% endif %}

        <footer>
            <p>© 2023 Реестр образовательных организаций | Данные предоставлены Рособрнадзором</p>
        </footer>
    </div>
</body>
</html>''')

    app.run(debug=True)