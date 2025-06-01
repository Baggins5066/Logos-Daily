import os
import tempfile
from datetime import datetime
import random
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from app import app, db
from models import Quote, JournalEntry
from utils import get_session_id, get_daily_quote, update_streak, import_quotes_from_csv, import_quotes_from_json, add_sample_quotes

# Admin credentials (in production, use proper user management)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = generate_password_hash(os.environ.get("ADMIN_PASSWORD", "admin123"))

@app.route('/')
def index():
    """Homepage displaying daily quote and streak information"""
    # Ensure we have some quotes in the database
    add_sample_quotes()
    
    # Update user streak
    streak_info = update_streak()
    
    # Get today's quote (default logic)
    daily_quote = get_daily_quote()
    
    # Check if user has saved today's quote
    session_id = get_session_id()
    is_saved = False
    if daily_quote:
        existing_entry = JournalEntry.query.filter_by(
            quote_id=daily_quote.id,
            user_session_id=session_id
        ).first()
        is_saved = existing_entry is not None
    
    now = datetime.now()
    
    return render_template('index.html', 
                         quote=daily_quote, 
                         streak=streak_info,
                         is_saved=is_saved,
                         now=now)

@app.route('/save_quote', methods=['POST'])
def save_quote():
    """Save the daily quote to user's library"""
    quote_id = request.form.get('quote_id')
    if not quote_id:
        flash('No quote specified', 'error')
        return redirect(url_for('index'))
    
    session_id = get_session_id()
    
    # Check if already saved
    existing_entry = JournalEntry.query.filter_by(
        quote_id=quote_id,
        user_session_id=session_id
    ).first()
    
    if existing_entry:
        flash('Quote already saved to your library!', 'info')
    else:
        # Create new library entry
        library_entry = JournalEntry(
            quote_id=quote_id,
            user_session_id=session_id,
            user_notes=""
        )
        db.session.add(library_entry)
        db.session.commit()
        flash('Quote saved to your library!', 'success')
    
    return redirect(url_for('index'))

@app.route('/save_quote_and_redirect', methods=['POST'])
def save_quote_and_redirect():
    """Save the daily quote to user's library and redirect to library with focus"""
    quote_id = request.form.get('quote_id')
    if not quote_id:
        flash('No quote specified', 'error')
        return redirect(url_for('index'))
    
    session_id = get_session_id()
    
    # Check if already saved
    existing_entry = JournalEntry.query.filter_by(
        quote_id=quote_id,
        user_session_id=session_id
    ).first()
    
    if not existing_entry:
        # Create new library entry
        library_entry = JournalEntry(
            quote_id=quote_id,
            user_session_id=session_id,
            user_notes=""
        )
        db.session.add(library_entry)
        db.session.commit()
        flash('Quote saved to your library!', 'success')
        entry_id = library_entry.id
    else:
        entry_id = existing_entry.id
    
    # Redirect to library with focus parameter
    return redirect(url_for('library', focus_entry=entry_id))

@app.route('/save_quote_and_add_notes', methods=['POST'])
def save_quote_and_add_notes():
    """Save the daily quote to user's library with notes and redirect to library"""
    quote_id = request.form.get('quote_id')
    notes = request.form.get('notes', '').strip()
    
    if not quote_id:
        flash('No quote specified', 'error')
        return redirect(url_for('index'))
    
    session_id = get_session_id()
    
    # Check if already saved
    existing_entry = JournalEntry.query.filter_by(
        quote_id=quote_id,
        user_session_id=session_id
    ).first()
    
    if not existing_entry:
        # Create new library entry
        library_entry = JournalEntry(
            quote_id=quote_id,
            user_session_id=session_id,
            user_notes=notes
        )
        db.session.add(library_entry)
        db.session.commit()
        flash('Quote and thoughts saved to your library!', 'success')
    else:
        # Update existing entry with notes
        existing_entry.user_notes = notes
        existing_entry.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Your thoughts have been updated!', 'success')
    
    # Redirect to library
    return redirect(url_for('library'))

@app.route('/library')
def library():
    """Display user's library with saved quotes"""
    session_id = get_session_id()
    focus_entry_id = request.args.get('focus_entry')
    
    # Get all library entries for this user
    entries = JournalEntry.query.filter_by(user_session_id=session_id)\
                              .order_by(JournalEntry.created_at.desc())\
                              .all()
    
    return render_template('library.html', entries=entries, focus_entry_id=focus_entry_id)

@app.route('/update_notes', methods=['POST'])
def update_notes():
    """Update notes for a library entry"""
    entry_id = request.form.get('entry_id')
    notes = request.form.get('notes', '')
    
    session_id = get_session_id()
    
    # Find the entry and verify ownership
    entry = JournalEntry.query.filter_by(
        id=entry_id,
        user_session_id=session_id
    ).first()
    
    if entry:
        entry.user_notes = notes
        db.session.commit()
        flash('Notes updated successfully!', 'success')
    else:
        flash('Library entry not found', 'error')
    
    return redirect(url_for('library'))

@app.route('/delete_entry', methods=['POST'])
def delete_entry():
    """Delete a library entry"""
    entry_id = request.form.get('entry_id')
    session_id = get_session_id()
    
    # Find the entry and verify ownership
    entry = JournalEntry.query.filter_by(
        id=entry_id,
        user_session_id=session_id
    ).first()
    
    if entry:
        db.session.delete(entry)
        db.session.commit()
        flash('Library entry deleted', 'success')
    else:
        flash('Library entry not found', 'error')
    
    return redirect(url_for('library'))

@app.route('/admin')
def admin():
    """Admin panel for quote management"""
    # Check admin authentication
    if not session.get('admin_authenticated'):
        return redirect(url_for('admin_login'))
    
    # Get quote statistics
    total_quotes = Quote.query.count()
    total_entries = JournalEntry.query.count()
    
    return render_template('admin.html', 
                         total_quotes=total_quotes,
                         total_entries=total_entries)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_authenticated'] = True
            flash('Admin login successful', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_authenticated', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/admin/upload', methods=['POST'])
def admin_upload():
    """Upload quotes from CSV or JSON file"""
    if not session.get('admin_authenticated'):
        flash('Admin access required', 'error')
        return redirect(url_for('admin_login'))
    
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('admin'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('admin'))
    
    if file:
        filename = secure_filename(file.filename)
        file_ext = filename.lower().split('.')[-1]
        
        if file_ext not in ['csv', 'json']:
            flash('Invalid file type. Please upload CSV or JSON files only.', 'error')
            return redirect(url_for('admin'))
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp_file:
            file.save(tmp_file.name)
            temp_path = tmp_file.name
        
        try:
            if file_ext == 'csv':
                imported_count = import_quotes_from_csv(temp_path)
            else:  # json
                imported_count = import_quotes_from_json(temp_path)
            
            flash(f'Successfully imported {imported_count} quotes!', 'success')
            
        except Exception as e:
            flash(f'Error importing quotes: {str(e)}', 'error')
        
        finally:
            # Clean up temp file
            os.unlink(temp_path)
    
    return redirect(url_for('admin'))

@app.route('/refresh_quote', methods=['POST'])
def refresh_quote():
    """Show a random quote (for testing)"""
    # Pick a random quote from the database
    from models import Quote
    quote_ids = [q.id for q in Quote.query.all()]
    if quote_ids:
        random_id = random.choice(quote_ids)
        # Store this random quote in session for display
        session['daily_quote_id'] = random_id
    else:
        session.pop('daily_quote_id', None)
    return redirect(url_for('show_random_quote'))

@app.route('/show_random_quote')
def show_random_quote():
    from models import Quote
    streak_info = update_streak()
    random_id = session.get('daily_quote_id')
    quote = Quote.query.get(random_id) if random_id else None
    session_id = get_session_id()
    is_saved = False
    if quote:
        existing_entry = JournalEntry.query.filter_by(
            quote_id=quote.id,
            user_session_id=session_id
        ).first()
        is_saved = existing_entry is not None
    now = datetime.now()
    return render_template('index.html', 
                         quote=quote, 
                         streak=streak_info,
                         is_saved=is_saved,
                         now=now)

@app.template_filter('truncate_words')
def truncate_words(text, length=50):
    """Template filter to truncate text by words"""
    if not text:
        return ""
    words = text.split()
    if len(words) <= length:
        return text
    return ' '.join(words[:length]) + '...'
