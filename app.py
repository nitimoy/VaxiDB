from flask import Flask, request, jsonify, render_template, flash, redirect, url_for, session as flask_session
from sqlalchemy import create_engine, DateTime, func, case
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from datetime import datetime, timezone
from flask_mail import Mail, Message
import urllib.parse
import os
import requests
from contextlib import contextmanager
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__, static_folder='static', template_folder='templates')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)
app.secret_key = os.getenv('SECRET_KEY', 'SECRET_KEY')

# PostgreSQL setup
username = os.getenv('DB_USERNAME', 'DB_USERNAME')
password = os.getenv('DB_PASSWORD', 'DB_PASSWORD')
host = os.getenv('DB_HOST', 'DB_HOST')
port = os.getenv('DB_PORT', 'DB_PORT')
dbname = os.getenv('DB_NAME', 'DB_NAME')

# Email deails
email_user = os.getenv('EMAIL_USER', 'EMAIL_USER')
email_pass = os.getenv('EMAIL_PASS', 'EMAIL_PASS')

encoded_password = urllib.parse.quote(password)
DATABASE_URI = f'postgresql://{username}:{encoded_password}@{host}:{port}/{dbname}'
engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

# Configuration for Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = email_user
app.config['MAIL_PASSWORD'] = email_pass
app.config['MAIL_DEFAULT_SENDER'] = email_user

mail = Mail(app)
Base = declarative_base()

class Protein(Base):
    __tablename__ = 'protein'
    id = Column(Integer, primary_key=True)
    protein_id = Column(String(120), index=True)
    protein_name = Column(String(360), index=True)
    predicted_antigenic_score = Column(Float)
    predicted_antigenic_probability = Column(String(120))
    predicted_signal_peptide = Column(String(120))
    number_of_tmhs = Column(Integer)
    localizations = Column(String(120))
    vaccine_candidate_probability = Column(String(120))
    experimentally_validated_antigen = Column(String(120))
    pmid = Column(String(120))
    submission_id_iedb = Column(String(120))
    doi = Column(String(120))
    file_id = Column(Integer, ForeignKey('file.id'), nullable=False, index=True)

class File(Base):
    __tablename__ = 'file'
    id = Column(Integer, primary_key=True)
    proteome_id = Column(String(120), unique=True, nullable=False)
    upload_date = Column(DateTime, nullable=False)
    organism_type = Column(String(50), nullable=False)
    organism_name = Column(String(120))

class Visit(Base):
    __tablename__ = 'visit'
    id = Column(Integer, primary_key=True)
    ip_address = Column(String(45), nullable=False, unique=True)
    city = Column(String(100))
    country = Column(String(100))
    visit_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    visit_count = Column(Integer, default=1)

def to_dict(instance):
    """Convert SQLAlchemy model instance to dictionary."""
    if isinstance(instance.__class__, DeclarativeMeta):
        return {column.name: getattr(instance, column.name) for column in instance.__table__.columns}
    return {}

def get_geolocation(ip_address):
    token = os.getenv('GEOLOCATION_API_TOKEN', 'GEOLOCATION_API_TOKEN')  
    url = f'https://ipinfo.io/{ip_address}/json?token={token}'
    response = requests.get(url)
    data = response.json()
    return {
        'city': data.get('city', 'Unknown'),
        'country': data.get('country', 'Unknown')
    }

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()

def get_client_ip():
    """Retrieve the client IP address, considering the possible use of proxies."""
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
    else:
        ip = request.remote_addr
    return ip

@app.before_request
def track_user_location():
    if 'logged_ip' not in flask_session:
        ip_address = get_client_ip()
        app.logger.info(f"Client IP Address: {ip_address}")
        try:
            with session_scope() as db_session:
                visit = db_session.query(Visit).filter_by(ip_address=ip_address).first()
                if visit:
                    visit.visit_count += 1
                    visit.visit_time = datetime.now(timezone.utc)
                else:
                    geolocation_data = get_geolocation(ip_address)
                    visit = Visit(ip_address=ip_address, city=geolocation_data['city'], country=geolocation_data['country'])
                    db_session.add(visit)
            flask_session['logged_ip'] = True
        except Exception as e:
            app.logger.error(f"Error tracking user location: {e}")

@app.route('/')
def index():
    with session_scope() as session:
        visit_count = session.query(func.sum(Visit.visit_count)).scalar() or 0
        unique_visitors = session.query(Visit).count()
    return render_template('index.html', visit_count=visit_count, unique_visitors=unique_visitors)


@app.route('/search')
def search():
    with session_scope() as session:
        visit_count = session.query(func.sum(Visit.visit_count)).scalar() or 0
        unique_visitors = session.query(Visit).count()
    return render_template('search.html', visit_count=visit_count, unique_visitors=unique_visitors)

@app.route('/vaccine_design', methods=['GET', 'POST'])
def vaccine_design():
    with session_scope() as session:
        visit_count = session.query(func.sum(Visit.visit_count)).scalar() or 0
        unique_visitors = session.query(Visit).count()
    
    results = None
    vaccine_name = None
    if request.method == 'POST':
        data = request.form.to_dict(flat=False)
        vaccine_name = data.get('vaccine_name', ['Vaccine'])[0]
        results = submit()
    
    return render_template('vaccine_design.html', visit_count=visit_count, unique_visitors=unique_visitors, results=results, vaccine_name = vaccine_name)

def submit():
    data = request.form.to_dict(flat=False)

    adjuvant_linker = data.get('adjuvant_linker', [''])[0]
    adjuvant = data.get('adjuvant', [''])[0]
    adjuvant_other = data.get('adjuvant_other', [''])[0]
    adjuvant_linker_other = data.get('adjuvant_linker_other', [''])[0]

    epitope_order = data.get('epitope_order', ['bcell,mhc1,mhc2'])[0].split(',')

    b_cell_epitopes = data.get('b_cell_epitope', [''])[0].splitlines()
    b_cell_linker = data.get('b_cell_linker', [''])[0]
    b_cell_linker_other = data.get('b_cell_linker_other', [''])[0]

    mhc_class_i_epitopes = data.get('mhc_class_i_epitope', [''])[0].splitlines()
    mhc_class_i_linker = data.get('mhc_class_i_linker', [''])[0]
    mhc_class_i_linker_other = data.get('mhc_class_i_linker_other', [''])[0]

    mhc_class_ii_epitopes = data.get('mhc_class_ii_epitope', [''])[0].splitlines()
    mhc_class_ii_linker = data.get('mhc_class_ii_linker', [''])[0]
    mhc_class_ii_linker_other = data.get('mhc_class_ii_linker_other', [''])[0]

    his_tag = data.get('his_tag', [''])[0]
    his_tag_other = data.get('his_tag_other', [''])[0]

    def generate_pattern(sequence):
        n = len(sequence)
        pattern = [sequence.copy()]
        original_reversed = sequence[::-1]

        if n <= 5:
            # Shift the sequence by 1 position
            for i in range(1, n):
                sequence = sequence[1:] + sequence[:1]
                if sequence in pattern or sequence == original_reversed:
                    break  # Stop if sequence repeats or reaches the reversed sequence
                pattern.append(sequence.copy())
        elif n <= 15:
            # Shift the sequence by 2 positions
            for i in range(1, (n + 1) // 2):
                sequence = sequence[2:] + sequence[:2]
                if sequence in pattern or sequence == original_reversed:
                    break  # Stop if sequence repeats or reaches the reversed sequence
                pattern.append(sequence.copy())
        else:
            # Shift the sequence by 3 positions
            for i in range(1, (n + 1) // 3):
                sequence = sequence[3:] + sequence[:3]
                if sequence in pattern or sequence == original_reversed:
                    break  # Stop if sequence repeats or reaches the reversed sequence
                pattern.append(sequence.copy())

        # Ensure the last pattern is the reversed original sequence, not a repeated intermediate step
        if pattern[-1] != original_reversed:
            pattern.append(original_reversed)

        return pattern

    b_cell_patterns = generate_pattern(b_cell_epitopes) if b_cell_epitopes else []
    mhc_class_i_patterns = generate_pattern(mhc_class_i_epitopes) if mhc_class_i_epitopes else []
    mhc_class_ii_patterns = generate_pattern(mhc_class_ii_epitopes) if mhc_class_ii_epitopes else []

    def format_output(adjuvant, adjuvant_linker, epitope_order, b_cell_pattern, b_cell_linker, mhc_class_i_pattern, mhc_class_i_linker, mhc_class_ii_pattern, mhc_class_ii_linker, his_tag):
        output = f"<span style='color:#2ECC71'>{adjuvant_linker}</span><span style='color:#C0392B'>{adjuvant}</span><span style='color:#2ECC71'>{adjuvant_linker}</span>"
        
        epitope_sections = {
            'bcell': lambda: ''.join(f"<span style='color:#A569BD'>{epitope}</span><span style='color:#117864'>{b_cell_linker}</span>" for epitope in b_cell_pattern),
            'mhc1': lambda: ''.join(f"<span style='color:#17202A'>{epitope}</span><span style='color:#CA1F7B'>{mhc_class_i_linker}</span>" for epitope in mhc_class_i_pattern),
            'mhc2': lambda: ''.join(f"<span style='color:#BA4A00'>{epitope}</span><span style='color:#5DADE2'>{mhc_class_ii_linker}</span>" for epitope in mhc_class_ii_pattern)
        }
        
        for epitope_type in epitope_order:
            output += epitope_sections[epitope_type]()
        
        output += f"<span style='color:#7D6608'>{his_tag}</span>"
        return output

    final_outputs = []

    max_patterns = max(len(b_cell_patterns), len(mhc_class_i_patterns), len(mhc_class_ii_patterns))
    for i in range(max_patterns):
        b_cell = b_cell_patterns[i % len(b_cell_patterns)] if b_cell_patterns else []
        mhc_i = mhc_class_i_patterns[i % len(mhc_class_i_patterns)] if mhc_class_i_patterns else []
        mhc_ii = mhc_class_ii_patterns[i % len(mhc_class_ii_patterns)] if mhc_class_ii_patterns else []

        final_outputs.append(format_output(
            adjuvant_other or adjuvant,
            adjuvant_linker_other or adjuvant_linker,
            epitope_order,
            b_cell,
            b_cell_linker_other or b_cell_linker,
            mhc_i,
            mhc_class_i_linker_other or mhc_class_i_linker,
            mhc_ii,
            mhc_class_ii_linker_other or mhc_class_ii_linker,
            his_tag_other or his_tag
        ))

    return final_outputs

@app.route('/about')
def about():
    with session_scope() as session:
        visit_count = session.query(func.sum(Visit.visit_count)).scalar() or 0
        unique_visitors = session.query(Visit).count()
    return render_template('about.html', visit_count=visit_count, unique_visitors=unique_visitors)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        organization = request.form.get('organization', 'N/A')
        message = request.form['message']

        if not name or not email or not message:
            flash('Please fill out all required fields.')
            return redirect(url_for('contact'))

        try:
            msg = Message(
                subject=f"New Contact Us Message from {name}",
                sender=app.config['MAIL_DEFAULT_SENDER'],
                recipients=[app.config['MAIL_DEFAULT_SENDER']]
            )
            msg.body = f"""
            Name: {name}
            Email: {email}
            Organization: {organization}
            Message: {message}
            """
            mail.send(msg)
            flash('Your message has been sent successfully!')
            return redirect(url_for('contact'))

        except Exception as e:
            app.logger.error(f'Error sending email: {str(e)}')
            flash(f'An error occurred: {str(e)}')
            return redirect(url_for('contact'))
        
    with session_scope() as session:
        visit_count = session.query(func.sum(Visit.visit_count)).scalar() or 0
        unique_visitors = session.query(Visit).count()
    return render_template('contact.html', visit_count=visit_count, unique_visitors=unique_visitors)

@app.route('/search_protein', methods=['GET'])
def search_protein():
    protein_id = request.args.get('protein_id')
    protein_name = request.args.get('protein_name')
    proteome_id = request.args.get('proteome_id')

    if not protein_id and not protein_name:
        return jsonify({"error": "Either protein_id or protein_name parameter is required"}), 400

    with session_scope() as session:
        query = session.query(Protein)

        if protein_id:
            query = query.filter_by(protein_id=protein_id)

        if protein_name:
            trimmed_protein_name = protein_name.strip()
            query = query.filter(func.trim(Protein.protein_name) == trimmed_protein_name)
            
            if proteome_id:
                query = query.join(File).filter(File.id == proteome_id)

        # Order the results based on the specified criteria
        vaccine_candidate_order = case(
            (Protein.vaccine_candidate_probability == 'Highly Probable', 1),
            (Protein.vaccine_candidate_probability == 'Probable', 2),
            (Protein.vaccine_candidate_probability == 'Negative', 3),
            else_=4
        )
        
        experimentally_validated_order = case(
            (Protein.experimentally_validated_antigen == 'YES', 1),
            (Protein.experimentally_validated_antigen == 'NO', 2),
            else_=3
        )
        
        protein_query = query.order_by(
            vaccine_candidate_order,
            experimentally_validated_order,
            Protein.id  # Adding a stable sort key
        ).all()

        if protein_query:
            protein_data = [to_dict(protein) for protein in protein_query]
            return jsonify(protein_data), 200
        else:
            return jsonify([]), 200

@app.route('/search_proteome_organism', methods=['GET'])
def search_proteome_organism():
    proteome_id = request.args.get('proteome_id')
    organism_name = request.args.get('organism_name')

    if not proteome_id and not organism_name:
        return jsonify({"error": "Either proteome_id or organism_name parameter is required"}), 400

    try:
        with session_scope() as session:
            query = session.query(Protein)

            if proteome_id:
                query = query.join(File).filter(File.proteome_id == proteome_id)

            if organism_name:
                query = query.join(File).filter(File.organism_name == organism_name)

            # Order the results based on the specified criteria
            vaccine_candidate_order = case(
                (Protein.vaccine_candidate_probability == 'Highly Probable', 1),
                (Protein.vaccine_candidate_probability == 'Probable', 2),
                (Protein.vaccine_candidate_probability == 'Negative', 3),
                else_=4
            )

            experimentally_validated_order = case(
                (Protein.experimentally_validated_antigen == 'YES', 1),
                (Protein.experimentally_validated_antigen == 'NO', 2),
                else_=3
            )

            protein_query = query.order_by(
                vaccine_candidate_order,
                experimentally_validated_order,
                Protein.id  # Adding a stable sort key
            ).all()

            if protein_query:
                protein_data = [to_dict(protein) for protein in protein_query]
                return jsonify(protein_data), 200
            else:
                return jsonify([]), 200

    except OperationalError as oe:
        # Handle database connection issues
        session.rollback()
        app.logger.error(f"OperationalError: {str(oe)}")
        return jsonify([]), 200

    except SQLAlchemyError as e:
        # Rollback the session in case of error
        session.rollback()
        # Log the error for debugging
        app.logger.error(f"SQLAlchemyError: {str(e)}")
        return jsonify([]), 200

@app.route('/get_protein_data', methods=['GET'])
def get_protein_data():
    file_id = request.args.get('file_id')
    if not file_id:
        return jsonify({"error": "File ID is required"}), 400

    with session_scope() as session:
        query = session.query(Protein).filter(Protein.file_id == file_id)
        
        # Order the results based on the specified criteria
        vaccine_candidate_order = case(
            (Protein.vaccine_candidate_probability == 'Highly Probable', 1),
            (Protein.vaccine_candidate_probability == 'Probable', 2),
            (Protein.vaccine_candidate_probability == 'Negative', 3),
            else_=4
        )
        
        experimentally_validated_order = case(
            (Protein.experimentally_validated_antigen == 'YES', 1),
            (Protein.experimentally_validated_antigen == 'NO', 2),
            else_=3
        )
        
        protein_query = query.order_by(
            vaccine_candidate_order,
            experimentally_validated_order,
            Protein.id  # Adding a stable sort key
        ).all()

        if protein_query:
            protein_data = [to_dict(protein) for protein in protein_query]
            return jsonify(protein_data), 200
        else:
            return jsonify([]), 200

@app.route('/suggest_protein', methods=['GET'])
def suggest_protein():
    query_param = request.args.get('query')
    if not query_param:
        return jsonify([]), 200

    with session_scope() as session:
        suggestions = session.query(Protein.protein_name).filter(Protein.protein_name.ilike(f'%{query_param}%')).limit(10).all()
        suggestion_list = [s[0] for s in suggestions]
        return jsonify(suggestion_list), 200

@app.route('/suggest_proteome_organism', methods=['GET'])
def suggest_proteome_organism():
    query_param = request.args.get('query')
    if not query_param:
        return jsonify([]), 200

    with session_scope() as session:
        query = session.query(File).filter(File.organism_name.ilike(f'%{query_param}%')).all()
        suggestions = [file.organism_name for file in query]
        return jsonify(suggestions), 200

@app.route('/get_proteome_data', methods=['GET'])
def get_proteome_data():
    organism_type = request.args.get('organism_type')
    if not organism_type:
        return jsonify({"error": "Organism type is required"}), 400

    with session_scope() as session:
        files = session.query(File).filter(File.organism_type == organism_type).all()
        if files:
            file_data = [to_dict(file) for file in files]
            return jsonify(file_data), 200
        else:
            return jsonify([]), 200

@app.route('/get_proteome_data_by_protein_name', methods=['GET'])
def get_proteome_data_by_protein_name():
    protein_name = request.args.get('protein_name')
    if not protein_name:
        return jsonify([]), 400

    with session_scope() as session:
        proteome_data = (
            session.query(File.id, File.proteome_id, File.organism_name)
            .join(Protein, Protein.file_id == File.id)
            .filter(Protein.protein_name == protein_name)
            .distinct(File.proteome_id, File.organism_name)  # Ensure unique pairs
            .all()
        )
        result = [{'id': item.id, 'proteome_id': item.proteome_id, 'organism_name': item.organism_name} for item in proteome_data]
        return jsonify(result), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

