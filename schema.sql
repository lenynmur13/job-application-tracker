-- Job Application Tracker schema COP4751.
CREATE DATABASE IF NOT EXISTS job_tracker;
USE job_tracker;

-- Drop children before parents so FK constraints don't block the drops
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS companies;

CREATE TABLE companies (
    company_id   INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    industry     VARCHAR(50),
    website      VARCHAR(200),
    city         VARCHAR(50),
    state        VARCHAR(50),
    notes        TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE jobs (
    job_id          INT AUTO_INCREMENT PRIMARY KEY,
    company_id      INT NOT NULL,
    job_title       VARCHAR(100) NOT NULL,
    job_type        ENUM('Full-time','Part-time','Contract','Internship') DEFAULT 'Full-time',
    salary_min      INT,
    salary_max      INT,
    job_url         VARCHAR(300),                
    date_posted     DATE,
    requirements    JSON,                       
    job_description TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- CASCADE so deleting a company removes its jobs instead of failing on the FK
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE TABLE applications (
    application_id    INT AUTO_INCREMENT PRIMARY KEY,
    job_id            INT NOT NULL,
    application_date  DATE NOT NULL,
    status            ENUM('Applied','Screening','Interview','Offer','Rejected','Withdrawn') DEFAULT 'Applied',
    resume_version    VARCHAR(50),
    cover_letter_sent BOOLEAN DEFAULT FALSE,
    interview_data    JSON,                     
    notes             TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE TABLE contacts (
    contact_id   INT AUTO_INCREMENT PRIMARY KEY,
    company_id   INT NOT NULL,
    contact_name VARCHAR(100) NOT NULL,          
    title        VARCHAR(100),                   
    email        VARCHAR(100),
    phone        VARCHAR(20),
    linkedin_url VARCHAR(200),
    notes        TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

-- Dates are fixed (not CURDATE()) so every re-run produces identical data.

INSERT INTO companies (company_name, industry, website, city, state, notes) VALUES
    ('Tech Solutions Inc',  'Technology',      'www.techsolutions.com',     'Miami',         'Florida',       NULL),
    ('Data Analytics Corp', 'Data Science',    'www.dataanalytics.com',     'Austin',        'Texas',         NULL),
    ('Cloud Systems LLC',   'Cloud Computing', 'www.cloudsystems.com',      'Seattle',       'Washington',    NULL),
    ('Digital Innovations', 'Software',        'www.digitalinnovations.com','San Francisco', 'California',    'Applied to Senior Developer position on 2025-01-17'),  
    ('Smart Tech Group',    'AI/ML',           'www.smarttech.com',         'Boston',        'Massachusetts', NULL),
    ('New Tech Corp',       'Technology',      NULL,                        'Denver',        'Colorado',      NULL); 

-- job_id 1-7 from assignment 2, 8-17 from assignment 3, 18 from assignment 4
-- requirements is new (not in the old queries): placeholder skills so Job Match has data; jobs 1 and 3 mirror the spec's example
INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, date_posted, requirements) VALUES
    (1, 'Software Developer',      'Full-time',  70000,  90000, '2025-01-15', JSON_ARRAY('Python','SQL','Flask')),
    (1, 'Database Administrator',  'Full-time',  75000,  95000, '2025-01-10', JSON_ARRAY('SQL','MySQL','Database Design','Linux')),
    (2, 'Data Analyst',            'Full-time',  65000,  85000, '2025-01-12', JSON_ARRAY('Python','SQL','Tableau')),
    (3, 'Cloud Engineer',          'Full-time',  80000, 100000, '2025-01-08', JSON_ARRAY('AWS','Docker','Linux','Python')),
    (4, 'Junior Developer',        'Full-time',  55000,  70000, '2025-01-14', JSON_ARRAY('Python','HTML','CSS','Git')),
    (4, 'Senior Developer',        'Full-time',  95000, 120000, '2025-01-14', JSON_ARRAY('Python','Flask','SQL','System Design','Git')),
    (5, 'ML Engineer',             'Full-time',  90000, 115000, '2025-01-11', JSON_ARRAY('Python','TensorFlow','Pandas','SQL')),
    (1, 'QA Engineer',             'Full-time',  60000,  80000, '2025-01-05', JSON_ARRAY('Selenium','Python','Test Automation','SQL')),
    (2, 'Business Analyst',        'Full-time',  65000,  85000, '2025-01-06', JSON_ARRAY('SQL','Excel','Tableau','Communication')),
    (2, 'Data Scientist',          'Full-time',  85000, 110000, '2025-01-07', JSON_ARRAY('Python','Pandas','Machine Learning','SQL')),
    (3, 'DevOps Engineer',         'Full-time',  80000, 105000, '2025-01-08', JSON_ARRAY('Docker','Kubernetes','Linux','CI/CD')),
    (3, 'Security Analyst',        'Full-time',  75000,  95000, '2025-01-09', JSON_ARRAY('Networking','Linux','Python','Security')),
    (4, 'UI/UX Designer',          'Full-time',  60000,  80000, '2025-01-10', JSON_ARRAY('Figma','HTML','CSS','User Research')),
    (5, 'Product Manager',         'Full-time',  90000, 120000, '2025-01-11', JSON_ARRAY('Communication','Agile','SQL','Roadmapping')),
    (1, 'Technical Writer',        'Contract',   55000,  75000, '2025-01-12', JSON_ARRAY('Documentation','Markdown','Git','Communication')),
    (2, 'Intern - Data',           'Internship', 30000,  40000, '2025-01-13', JSON_ARRAY('Python','SQL','Excel')),
    (4, 'Intern - Development',    'Internship', 32000,  42000, '2025-01-14', JSON_ARRAY('Python','Git','HTML')),
    (6, 'Software Architect',      'Full-time', 120000, 150000, '2025-01-18', JSON_ARRAY('System Design','Python','AWS','SQL')); 

-- Statuses mapped to the spec ENUM: 'Interview Scheduled'/'Interview Completed' -> 'Interview', 'Phone Screen' -> 'Screening'
-- interview_data is new: placeholder JSON for the apps that reached an interview stage
INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent, interview_data) VALUES
    (1, '2025-01-16', 'Applied',   'v2.1', TRUE,  NULL),
    (3, '2025-01-13', 'Interview', 'v2.1', TRUE,  JSON_OBJECT('rounds', JSON_ARRAY(JSON_OBJECT('type','Technical interview','date','2025-01-20','interviewer','Michael Chen','result','Completed')))),
    (4, '2025-01-09', 'Interview', 'v2.0', FALSE, JSON_OBJECT('rounds', JSON_ARRAY(JSON_OBJECT('type','Technical interview','date','2025-01-14','interviewer','Emily Williams','result','Completed')))),
    (5, '2025-01-15', 'Applied',   'v2.1', TRUE,  NULL),
    (7, '2025-01-12', 'Screening', 'v2.1', TRUE,  JSON_OBJECT('rounds', JSON_ARRAY(JSON_OBJECT('type','Phone screen','date','2025-01-16','interviewer','Lisa Garcia','result','Pending')))),
    (6, '2025-01-17', 'Applied',   'v3.0', TRUE,  NULL);

-- first_name + last_name merged into contact_name, job_title renamed to title
INSERT INTO contacts (company_id, contact_name, title, email) VALUES
    (1, 'Sarah Johnson',  'HR Manager',          'sjohnson@techsolutions.com'),
    (2, 'Michael Chen',   'Technical Recruiter', 'mchen@dataanalytics.com'),
    (3, 'Emily Williams', 'Hiring Manager',      'ewilliams@cloudsystems.com'),
    (4, 'David Brown',    'Senior Developer',    NULL),
    (5, 'Lisa Garcia',    'Talent Acquisition',  'lgarcia@smarttech.com'),
    (4, 'Robert Kim',     'Engineering Manager', 'rkim@digitalinnovations.com');