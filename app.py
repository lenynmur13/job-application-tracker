import json
import os
from datetime import datetime

import mysql.connector
from flask import Flask, abort, flash, redirect, render_template, request, url_for

from database import execute, fetch_all, fetch_one

app = Flask(__name__)
# flash() stores messages in the session, which needs a secret key (override with a SECRET_KEY env var)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-only-change-me')

# Pipeline order, matching the applications.status ENUM in schema.sql
STATUSES = ['Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn']

# Column limits from schema.sql, enforced here so users get a message instead of a MySQL error
COMPANY_LIMITS = {'company_name': 100, 'industry': 50, 'website': 200, 'city': 50, 'state': 50}

# Must match the jobs.job_type ENUM in schema.sql
JOB_TYPES = ['Full-time', 'Part-time', 'Contract', 'Internship']
MAX_INT = 2147483647      # MySQL INT ceiling, so oversized salaries fail validation, not the INSERT
MAX_SKILLS, MAX_SKILL_LEN = 30, 50


@app.route('/')
def dashboard():
    # One round trip for all four totals using scalar subqueries
    totals = fetch_one('''
        SELECT (SELECT COUNT(*) FROM companies)    AS companies,
               (SELECT COUNT(*) FROM jobs)         AS jobs,
               (SELECT COUNT(*) FROM applications) AS applications,
               (SELECT COUNT(*) FROM contacts)     AS contacts
    ''')

    # GROUP BY only returns statuses that exist, so zero-fill the rest for a stable display
    rows = fetch_all('SELECT status, COUNT(*) AS count FROM applications GROUP BY status')
    counts = {r['status']: r['count'] for r in rows}
    status_counts = [(s, counts.get(s, 0)) for s in STATUSES]

    # Five most recent applications with job and company names via two JOINs
    recent = fetch_all('''
        SELECT a.application_id, a.application_date, a.status,
               j.job_title, c.company_name
        FROM applications a
        JOIN jobs j      ON a.job_id = j.job_id
        JOIN companies c ON j.company_id = c.company_id
        ORDER BY a.application_date DESC, a.application_id DESC
        LIMIT 5
    ''')

    return render_template('dashboard.html', totals=totals,
                           status_counts=status_counts, recent=recent)


# ---------------------------------------------------------------- Companies

def read_company_form():
    # Pull fields from the POST body; blank optional fields become NULL instead of ''
    data = {}
    for field in COMPANY_LIMITS:
        value = request.form.get(field, '').strip()
        data[field] = value or None
    data['notes'] = request.form.get('notes', '').strip() or None

    # Validate: name is NOT NULL in the schema, and every field must fit its column
    errors = []
    if not data['company_name']:
        errors.append('Company name is required.')
    for field, limit in COMPANY_LIMITS.items():
        if data[field] and len(data[field]) > limit:
            errors.append(f"{field.replace('_', ' ').capitalize()} must be {limit} characters or fewer.")
    return data, errors


def get_company_or_404(company_id):
    company = fetch_one('SELECT * FROM companies WHERE company_id = %s', (company_id,))
    if company is None:
        abort(404)
    return company


@app.route('/companies')
def companies():
    # Per-company job and contact counts; the subqueries avoid the row multiplication
    # a double JOIN would cause (jobs x contacts)
    rows = fetch_all('''
        SELECT c.*,
               (SELECT COUNT(*) FROM jobs     j WHERE j.company_id = c.company_id) AS job_count,
               (SELECT COUNT(*) FROM contacts k WHERE k.company_id = c.company_id) AS contact_count
        FROM companies c
        ORDER BY c.company_name
    ''')
    return render_template('companies.html', companies=rows)


@app.route('/companies/add', methods=['GET', 'POST'])
def add_company():
    if request.method == 'POST':
        data, errors = read_company_form()
        if not errors:
            try:
                execute('''
                    INSERT INTO companies (company_name, industry, website, city, state, notes)
                    VALUES (%(company_name)s, %(industry)s, %(website)s, %(city)s, %(state)s, %(notes)s)
                ''', data)
                flash(f"Added {data['company_name']}.", 'success')
                return redirect(url_for('companies'))  # POST-redirect-GET: refresh won't resubmit
            except mysql.connector.Error as e:
                errors.append(f'Database error: {e}')
        # Re-render with what the user typed so nothing is lost
        return render_template('company_form.html', company=data, errors=errors, mode='add')
    return render_template('company_form.html', company={}, errors=[], mode='add')


@app.route('/companies/<int:company_id>/edit', methods=['GET', 'POST'])
def edit_company(company_id):
    company = get_company_or_404(company_id)
    if request.method == 'POST':
        data, errors = read_company_form()
        if not errors:
            try:
                data['company_id'] = company_id
                execute('''
                    UPDATE companies
                    SET company_name = %(company_name)s, industry = %(industry)s, website = %(website)s,
                        city = %(city)s, state = %(state)s, notes = %(notes)s
                    WHERE company_id = %(company_id)s
                ''', data)
                flash(f"Updated {data['company_name']}.", 'success')
                return redirect(url_for('companies'))
            except mysql.connector.Error as e:
                errors.append(f'Database error: {e}')
        data['company_id'] = company_id
        return render_template('company_form.html', company=data, errors=errors, mode='edit')
    return render_template('company_form.html', company=company, errors=[], mode='edit')


@app.route('/companies/<int:company_id>/delete', methods=['POST'])
def delete_company(company_id):
    # POST only: a GET link could be triggered by crawlers or prefetching
    company = get_company_or_404(company_id)
    try:
        # ON DELETE CASCADE in schema.sql also removes this company's jobs, contacts and their applications
        execute('DELETE FROM companies WHERE company_id = %s', (company_id,))
        flash(f"Deleted {company['company_name']} and its related jobs, contacts and applications.", 'success')
    except mysql.connector.Error as e:
        flash(f'Could not delete: {e}', 'error')
    return redirect(url_for('companies'))


# --------------------------------------------------------------------- Jobs

def parse_skills(text):
    # "Python, SQL\nflask, python" -> ['Python', 'SQL', 'flask']: split on commas/newlines,
    # trim, drop blanks, drop case-insensitive duplicates (keeps first spelling)
    seen, skills = set(), []
    for part in (text or '').replace('\n', ',').split(','):
        skill = part.strip()
        if skill and skill.lower() not in seen:
            seen.add(skill.lower())
            skills.append(skill)
    return skills


def skills_from_db(value):
    # A JSON column can come back as str, bytes, or already-decoded depending on the connector version
    if value is None:
        return []
    if isinstance(value, (bytes, bytearray)):
        value = value.decode('utf-8')
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return []
    return [str(s) for s in value] if isinstance(value, list) else []


def parse_salary(raw, label, errors):
    # Tolerates "$70,000"; returns an int, or None when blank/invalid (invalid adds an error)
    raw = raw.replace('$', '').replace(',', '').strip()
    if not raw:
        return None
    if not raw.isdigit():
        errors.append(f'{label} must be a whole number (no decimals or negatives).')
        return None
    value = int(raw)
    if value > MAX_INT:
        errors.append(f'{label} is too large.')
        return None
    return value


def read_job_form():
    # Returns (params for SQL, strings to redisplay in the form, list of error messages)
    f = {k: request.form.get(k, '').strip() for k in
         ['company_id', 'job_title', 'job_type', 'salary_min', 'salary_max',
          'job_url', 'date_posted', 'requirements', 'job_description']}
    errors = []

    # Company must be a real row, because the FK would reject anything else
    company_id = int(f['company_id']) if f['company_id'].isdigit() else None
    if company_id is None or fetch_one('SELECT company_id FROM companies WHERE company_id = %s', (company_id,)) is None:
        errors.append('Choose a company from the list.')
        company_id = None

    if not f['job_title']:
        errors.append('Job title is required.')
    elif len(f['job_title']) > 100:
        errors.append('Job title must be 100 characters or fewer.')

    if f['job_type'] not in JOB_TYPES:
        errors.append('Choose a valid job type.')

    salary_min = parse_salary(f['salary_min'], 'Minimum salary', errors)
    salary_max = parse_salary(f['salary_max'], 'Maximum salary', errors)
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        errors.append('Minimum salary cannot be greater than maximum salary.')

    if len(f['job_url']) > 300:
        errors.append('Job URL must be 300 characters or fewer.')

    date_posted = None
    if f['date_posted']:
        try:
            date_posted = datetime.strptime(f['date_posted'], '%Y-%m-%d').date()
        except ValueError:
            errors.append('Date posted must be a valid date (YYYY-MM-DD).')

    # Skills -> JSON array for jobs.requirements (NULL when empty so Job Match can skip it)
    skills = parse_skills(f['requirements'])
    if len(skills) > MAX_SKILLS:
        errors.append(f'List at most {MAX_SKILLS} skills.')
    if any(len(s) > MAX_SKILL_LEN for s in skills):
        errors.append(f'Each skill must be {MAX_SKILL_LEN} characters or fewer.')

    params = {
        'company_id': company_id, 'job_title': f['job_title'], 'job_type': f['job_type'],
        'salary_min': salary_min, 'salary_max': salary_max, 'job_url': f['job_url'] or None,
        'date_posted': date_posted, 'requirements': json.dumps(skills) if skills else None,
        'job_description': f['job_description'] or None,
    }
    return params, f, errors


def get_job_or_404(job_id):
    job = fetch_one('SELECT * FROM jobs WHERE job_id = %s', (job_id,))
    if job is None:
        abort(404)
    return job


def job_to_form(job):
    # Turn a DB row into the plain strings the form fields expect
    return {
        'company_id': str(job['company_id']), 'job_title': job['job_title'] or '',
        'job_type': job['job_type'] or 'Full-time',
        'salary_min': '' if job['salary_min'] is None else str(job['salary_min']),
        'salary_max': '' if job['salary_max'] is None else str(job['salary_max']),
        'job_url': job['job_url'] or '',
        'date_posted': job['date_posted'].isoformat() if job['date_posted'] else '',
        'requirements': ', '.join(skills_from_db(job['requirements'])),
        'job_description': job['job_description'] or '',
    }


def render_job_form(form, errors, mode, job_id=None):
    # The dropdown needs every company; the template shows a prompt if there are none
    company_list = fetch_all('SELECT company_id, company_name FROM companies ORDER BY company_name')
    return render_template('job_form.html', form=form, errors=errors, mode=mode, job_id=job_id,
                           company_list=company_list, job_types=JOB_TYPES)


@app.route('/jobs')
def jobs():
    # Company name via JOIN; application count via subquery to keep one row per job
    rows = fetch_all('''
        SELECT j.*, c.company_name,
               (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS application_count
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        ORDER BY j.date_posted DESC, j.job_id DESC
    ''')
    for row in rows:
        row['skills'] = skills_from_db(row['requirements'])  # templates can't parse JSON
    return render_template('jobs.html', jobs=rows)


@app.route('/jobs/add', methods=['GET', 'POST'])
def add_job():
    if request.method == 'POST':
        params, form, errors = read_job_form()
        if not errors:
            try:
                execute('''
                    INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max,
                                      job_url, date_posted, requirements, job_description)
                    VALUES (%(company_id)s, %(job_title)s, %(job_type)s, %(salary_min)s, %(salary_max)s,
                            %(job_url)s, %(date_posted)s, %(requirements)s, %(job_description)s)
                ''', params)
                flash(f"Added {params['job_title']}.", 'success')
                return redirect(url_for('jobs'))
            except mysql.connector.Error as e:
                errors.append(f'Database error: {e}')
        return render_job_form(form, errors, 'add')
    return render_job_form({'job_type': 'Full-time'}, [], 'add')


@app.route('/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
def edit_job(job_id):
    job = get_job_or_404(job_id)
    if request.method == 'POST':
        params, form, errors = read_job_form()
        if not errors:
            try:
                params['job_id'] = job_id
                execute('''
                    UPDATE jobs
                    SET company_id = %(company_id)s, job_title = %(job_title)s, job_type = %(job_type)s,
                        salary_min = %(salary_min)s, salary_max = %(salary_max)s, job_url = %(job_url)s,
                        date_posted = %(date_posted)s, requirements = %(requirements)s,
                        job_description = %(job_description)s
                    WHERE job_id = %(job_id)s
                ''', params)
                flash(f"Updated {params['job_title']}.", 'success')
                return redirect(url_for('jobs'))
            except mysql.connector.Error as e:
                errors.append(f'Database error: {e}')
        return render_job_form(form, errors, 'edit', job_id)
    return render_job_form(job_to_form(job), [], 'edit', job_id)


@app.route('/jobs/<int:job_id>/delete', methods=['POST'])
def delete_job(job_id):
    job = get_job_or_404(job_id)
    try:
        # ON DELETE CASCADE also removes the applications tied to this job
        execute('DELETE FROM jobs WHERE job_id = %s', (job_id,))
        flash(f"Deleted {job['job_title']} and its applications.", 'success')
    except mysql.connector.Error as e:
        flash(f'Could not delete: {e}', 'error')
    return redirect(url_for('jobs'))


# ----------------------------------------------------------------- Contacts

def get_all_companies():
    return fetch_all('SELECT company_id, company_name FROM companies ORDER BY company_name')


def read_contact_form():
    # Keep the text exactly as typed; blanks become NULL later in contact_values()
    data = {
        'company_id': request.form.get('company_id', '').strip(),
        'contact_name': request.form.get('contact_name', '').strip(),
        'title': request.form.get('title', '').strip(),
        'email': request.form.get('email', '').strip(),
        'phone': request.form.get('phone', '').strip(),
        'linkedin_url': request.form.get('linkedin_url', '').strip(),
        'notes': request.form.get('notes', '').strip(),
    }

    errors = []

    # Company must be picked and must exist (contacts.company_id is a foreign key)
    if not data['company_id'].isdigit():
        errors.append('Please choose a company.')
    elif fetch_one('SELECT company_id FROM companies WHERE company_id = %s', (data['company_id'],)) is None:
        errors.append('That company does not exist.')

    # Name is required (NOT NULL in the table)
    if data['contact_name'] == '':
        errors.append('Contact name is required.')
    elif len(data['contact_name']) > 100:
        errors.append('Contact name must be 100 characters or fewer.')

    if len(data['title']) > 100:
        errors.append('Title must be 100 characters or fewer.')

    # Very basic email check: something@something
    if data['email'] != '':
        if '@' not in data['email'] or data['email'].startswith('@') or data['email'].endswith('@'):
            errors.append('Email must look like name@example.com.')
        elif len(data['email']) > 100:
            errors.append('Email must be 100 characters or fewer.')

    if len(data['phone']) > 20:
        errors.append('Phone must be 20 characters or fewer.')

    if len(data['linkedin_url']) > 200:
        errors.append('LinkedIn URL must be 200 characters or fewer.')

    return data, errors


def contact_values(data):
    # Convert the form text into what MySQL expects (blank -> NULL)
    values = dict(data)
    values['company_id'] = int(data['company_id'])
    for field in ['title', 'email', 'phone', 'linkedin_url', 'notes']:
        values[field] = data[field] or None

    # Without http(s):// the browser treats the link as a page on this site, so add it
    url = values['linkedin_url']
    if url and not url.startswith('http'):
        values['linkedin_url'] = 'https://' + url
    return values


def get_contact_or_404(contact_id):
    contact = fetch_one('SELECT * FROM contacts WHERE contact_id = %s', (contact_id,))
    if contact is None:
        abort(404)
    return contact


@app.route('/contacts')
def contacts():
    rows = fetch_all('''
        SELECT k.*, c.company_name
        FROM contacts k
        JOIN companies c ON k.company_id = c.company_id
        ORDER BY k.contact_name
    ''')
    return render_template('contacts.html', contacts=rows)


@app.route('/contacts/add', methods=['GET', 'POST'])
def add_contact():
    if request.method == 'POST':
        data, errors = read_contact_form()
        if not errors:
            try:
                execute('''
                    INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes)
                    VALUES (%(company_id)s, %(contact_name)s, %(title)s, %(email)s,
                            %(phone)s, %(linkedin_url)s, %(notes)s)
                ''', contact_values(data))
                flash('Added ' + data['contact_name'] + '.', 'success')
                return redirect(url_for('contacts'))
            except mysql.connector.Error as e:
                errors.append('Database error: ' + str(e))
        return render_template('contact_form.html', contact=data, errors=errors, mode='add',
                               companies=get_all_companies())
    return render_template('contact_form.html', contact={}, errors=[], mode='add',
                           companies=get_all_companies())


@app.route('/contacts/<int:contact_id>/edit', methods=['GET', 'POST'])
def edit_contact(contact_id):
    contact = get_contact_or_404(contact_id)
    if request.method == 'POST':
        data, errors = read_contact_form()
        if not errors:
            try:
                values = contact_values(data)
                values['contact_id'] = contact_id
                execute('''
                    UPDATE contacts
                    SET company_id = %(company_id)s, contact_name = %(contact_name)s, title = %(title)s,
                        email = %(email)s, phone = %(phone)s, linkedin_url = %(linkedin_url)s,
                        notes = %(notes)s
                    WHERE contact_id = %(contact_id)s
                ''', values)
                flash('Updated ' + data['contact_name'] + '.', 'success')
                return redirect(url_for('contacts'))
            except mysql.connector.Error as e:
                errors.append('Database error: ' + str(e))
        return render_template('contact_form.html', contact=data, errors=errors, mode='edit',
                               companies=get_all_companies())
    return render_template('contact_form.html', contact=contact, errors=[], mode='edit',
                           companies=get_all_companies())


@app.route('/contacts/<int:contact_id>/delete', methods=['POST'])
def delete_contact(contact_id):
    contact = get_contact_or_404(contact_id)
    try:
        execute('DELETE FROM contacts WHERE contact_id = %s', (contact_id,))
        flash('Deleted ' + contact['contact_name'] + '.', 'success')
    except mysql.connector.Error as e:
        flash('Could not delete: ' + str(e), 'error')
    return redirect(url_for('contacts'))


# -------------------------------------------------------------- Applications

def interview_rounds(value):
    # interview_data looks like {"rounds": [{"type": ..., "date": ..., "interviewer": ..., "result": ...}]}
    # MySQL can hand it back as text, so turn it into a Python list of rounds (empty if missing)
    if value is None:
        return []
    if isinstance(value, bytes):
        value = value.decode()
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return []
    if isinstance(value, dict) and isinstance(value.get('rounds'), list):
        return value['rounds']
    return []


def get_all_jobs():
    # For the job dropdown: "Job title - Company"
    return fetch_all('''
        SELECT j.job_id, j.job_title, c.company_name
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        ORDER BY c.company_name, j.job_title
    ''')


def read_application_form():
    # Keep the text exactly as typed; it is converted in application_values() when saving
    data = {
        'job_id': request.form.get('job_id', '').strip(),
        'application_date': request.form.get('application_date', '').strip(),
        'status': request.form.get('status', '').strip(),
        'resume_version': request.form.get('resume_version', '').strip(),
        'cover_letter_sent': request.form.get('cover_letter_sent') == 'on',  # checkbox
        'notes': request.form.get('notes', '').strip(),
        'interview_date': request.form.get('interview_date', '').strip(),
        'interview_type': request.form.get('interview_type', '').strip(),
        'interviewer': request.form.get('interviewer', '').strip(),
        'interview_result': request.form.get('interview_result', '').strip(),
    }

    errors = []

    # Job must be picked and must exist (applications.job_id is a foreign key)
    if not data['job_id'].isdigit():
        errors.append('Please choose a job.')
    elif fetch_one('SELECT job_id FROM jobs WHERE job_id = %s', (data['job_id'],)) is None:
        errors.append('That job does not exist.')

    # Application date is required (NOT NULL in the table), format YYYY-MM-DD
    if data['application_date'] == '':
        errors.append('Application date is required.')
    else:
        try:
            datetime.strptime(data['application_date'], '%Y-%m-%d')
        except ValueError:
            errors.append('Application date must look like 2025-01-31.')

    # Status has to be one of the ENUM values
    if data['status'] not in STATUSES:
        errors.append('Please choose a status.')

    if len(data['resume_version']) > 50:
        errors.append('Resume version must be 50 characters or fewer.')

    # Interview fields are all optional
    if data['interview_date'] != '':
        try:
            datetime.strptime(data['interview_date'], '%Y-%m-%d')
        except ValueError:
            errors.append('Interview date must look like 2025-01-31.')
    if len(data['interview_type']) > 50:
        errors.append('Interview type must be 50 characters or fewer.')
    if len(data['interviewer']) > 100:
        errors.append('Interviewer must be 100 characters or fewer.')
    if len(data['interview_result']) > 50:
        errors.append('Interview result must be 50 characters or fewer.')

    return data, errors


def application_values(data, old_rounds):
    # Convert the form text into what MySQL expects
    values = {}
    values['job_id'] = int(data['job_id'])
    values['application_date'] = data['application_date']
    values['status'] = data['status']
    values['resume_version'] = data['resume_version'] or None
    values['cover_letter_sent'] = 1 if data['cover_letter_sent'] else 0
    values['notes'] = data['notes'] or None

    # The form edits the first interview round; keep any later rounds that were already saved
    first_round = {}
    if data['interview_type']:
        first_round['type'] = data['interview_type']
    if data['interview_date']:
        first_round['date'] = data['interview_date']
    if data['interviewer']:
        first_round['interviewer'] = data['interviewer']
    if data['interview_result']:
        first_round['result'] = data['interview_result']

    rounds = old_rounds[1:]
    if first_round:
        rounds.insert(0, first_round)

    # No interview info at all -> store NULL instead of an empty object
    values['interview_data'] = json.dumps({'rounds': rounds}) if rounds else None
    return values


def application_to_form(application):
    # Turn a row from the database back into form text for the edit page
    rounds = interview_rounds(application['interview_data'])
    first = rounds[0] if rounds else {}
    data = {}
    data['job_id'] = str(application['job_id'])
    data['application_date'] = str(application['application_date'])
    data['status'] = application['status'] or 'Applied'
    data['resume_version'] = application['resume_version'] or ''
    data['cover_letter_sent'] = bool(application['cover_letter_sent'])
    data['notes'] = application['notes'] or ''
    data['interview_date'] = first.get('date', '')
    data['interview_type'] = first.get('type', '')
    data['interviewer'] = first.get('interviewer', '')
    data['interview_result'] = first.get('result', '')
    return data


def get_application_or_404(application_id):
    application = fetch_one('SELECT * FROM applications WHERE application_id = %s', (application_id,))
    if application is None:
        abort(404)
    return application


@app.route('/applications')
def applications():
    rows = fetch_all('''
        SELECT a.*, j.job_title, c.company_name
        FROM applications a
        JOIN jobs j      ON a.job_id = j.job_id
        JOIN companies c ON j.company_id = c.company_id
        ORDER BY a.application_date DESC, a.application_id DESC
    ''')
    # Pull the first interview round out of the JSON so the template can show it
    for row in rows:
        rounds = interview_rounds(row['interview_data'])
        row['interview'] = rounds[0] if rounds else None
    return render_template('applications.html', applications=rows)


@app.route('/applications/add', methods=['GET', 'POST'])
def add_application():
    if request.method == 'POST':
        data, errors = read_application_form()
        if not errors:
            try:
                execute('''
                    INSERT INTO applications (job_id, application_date, status, resume_version,
                                              cover_letter_sent, interview_data, notes)
                    VALUES (%(job_id)s, %(application_date)s, %(status)s, %(resume_version)s,
                            %(cover_letter_sent)s, %(interview_data)s, %(notes)s)
                ''', application_values(data, []))
                flash('Application added.', 'success')
                return redirect(url_for('applications'))
            except mysql.connector.Error as e:
                errors.append('Database error: ' + str(e))
        return render_template('application_form.html', application=data, errors=errors, mode='add',
                               jobs=get_all_jobs(), statuses=STATUSES)

    # First visit: today's date and "Applied" preselected
    blank = {'application_date': datetime.today().strftime('%Y-%m-%d'), 'status': 'Applied'}
    return render_template('application_form.html', application=blank, errors=[], mode='add',
                           jobs=get_all_jobs(), statuses=STATUSES)


@app.route('/applications/<int:application_id>/edit', methods=['GET', 'POST'])
def edit_application(application_id):
    application = get_application_or_404(application_id)
    if request.method == 'POST':
        data, errors = read_application_form()
        if not errors:
            try:
                old_rounds = interview_rounds(application['interview_data'])
                values = application_values(data, old_rounds)
                values['application_id'] = application_id
                execute('''
                    UPDATE applications
                    SET job_id = %(job_id)s, application_date = %(application_date)s, status = %(status)s,
                        resume_version = %(resume_version)s, cover_letter_sent = %(cover_letter_sent)s,
                        interview_data = %(interview_data)s, notes = %(notes)s
                    WHERE application_id = %(application_id)s
                ''', values)
                flash('Application updated.', 'success')
                return redirect(url_for('applications'))
            except mysql.connector.Error as e:
                errors.append('Database error: ' + str(e))
        return render_template('application_form.html', application=data, errors=errors, mode='edit',
                               jobs=get_all_jobs(), statuses=STATUSES)

    return render_template('application_form.html', application=application_to_form(application),
                           errors=[], mode='edit', jobs=get_all_jobs(), statuses=STATUSES)


@app.route('/applications/<int:application_id>/delete', methods=['POST'])
def delete_application(application_id):
    get_application_or_404(application_id)
    try:
        execute('DELETE FROM applications WHERE application_id = %s', (application_id,))
        flash('Application deleted.', 'success')
    except mysql.connector.Error as e:
        flash('Could not delete: ' + str(e), 'error')
    return redirect(url_for('applications'))


# ---------------------------------------------------------------- Job Match

def match_jobs(user_skills):
    # Compare the user's skills with each job's required skills.
    # Returns (matches sorted best first, number of jobs skipped for having no skills listed)
    rows = fetch_all('''
        SELECT j.job_id, j.job_title, j.job_type, j.job_url, j.requirements, c.company_name
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
    ''')

    # Lowercase so "python" matches "Python"
    have = []
    for skill in user_skills:
        have.append(skill.lower())

    matches = []
    skipped = 0
    for row in rows:
        required = skills_from_db(row['requirements'])
        if len(required) == 0:
            skipped = skipped + 1  # nothing to compare against, so a percentage would be meaningless
            continue

        matched = []
        missing = []
        for skill in required:
            if skill.lower() in have:
                matched.append(skill)
            else:
                missing.append(skill)

        percent = int(len(matched) * 100 / len(required) + 0.5)  # round half up: 2 of 3 -> 67
        matches.append({
            'job_title': row['job_title'],
            'company_name': row['company_name'],
            'job_type': row['job_type'],
            'job_url': row['job_url'],
            'percent': percent,
            'matched': matched,
            'missing': missing,
            'total': len(required),
        })

    # Highest percent first; ties go to the job with more matched skills, then A-Z by title
    matches.sort(key=lambda m: (-m['percent'], -len(m['matched']), m['job_title']))
    return matches, skipped


@app.route('/job-match')
def job_match():
    skills_text = request.args.get('skills', '').strip()
    searched = 'skills' in request.args  # true once the form has been submitted
    matches = []
    skipped = 0
    error = None

    if searched:
        user_skills = parse_skills(skills_text)
        if len(user_skills) == 0:
            error = 'Enter at least one skill, separated by commas.'
        else:
            matches, skipped = match_jobs(user_skills)

    return render_template('job_match.html', skills_text=skills_text, searched=searched,
                           matches=matches, skipped=skipped, error=error)


if __name__ == '__main__':
    app.run(debug=True)

    #