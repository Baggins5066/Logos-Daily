import os
import tempfile
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from app import app, db
from models import Quote, JournalEntry
from utils import get_session_id, get_daily_quote, update_streak, import_quotes_from_csv, import_quotes_from_json, add_sample_quotes
from openai_service import explain_quote, chat_about_quote

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
    
    # Get today's quote
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
    
    return render_template('index.html', 
                         quote=daily_quote, 
                         streak=streak_info,
                         is_saved=is_saved)

@app.route('/save_quote', methods=['POST'])
def save_quote():
    """Save the daily quote to user's journal"""
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
        flash('Quote already saved to your journal!', 'info')
    else:
        # Create new journal entry
        journal_entry = JournalEntry(
            quote_id=quote_id,
            user_session_id=session_id,
            user_notes=""
        )
        db.session.add(journal_entry)
        db.session.commit()
        flash('Quote saved to your journal!', 'success')
    
    return redirect(url_for('index'))

@app.route('/save_quote_and_redirect', methods=['POST'])
def save_quote_and_redirect():
    """Save the daily quote to user's journal and redirect to journal with focus"""
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
        # Create new journal entry
        journal_entry = JournalEntry(
            quote_id=quote_id,
            user_session_id=session_id,
            user_notes=""
        )
        db.session.add(journal_entry)
        db.session.commit()
        flash('Quote saved to your journal!', 'success')
        entry_id = journal_entry.id
    else:
        entry_id = existing_entry.id
    
    # Redirect to journal with focus parameter
    return redirect(url_for('journal', focus_entry=entry_id))

@app.route('/save_quote_and_add_notes', methods=['POST'])
def save_quote_and_add_notes():
    """Save the daily quote to user's journal with notes and redirect to journal"""
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
        # Create new journal entry
        journal_entry = JournalEntry(
            quote_id=quote_id,
            user_session_id=session_id,
            user_notes=notes
        )
        db.session.add(journal_entry)
        db.session.commit()
        flash('Quote and thoughts saved to your journal!', 'success')
    else:
        # Update existing entry with notes
        existing_entry.user_notes = notes
        existing_entry.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Your thoughts have been updated!', 'success')
    
    # Redirect to journal
    return redirect(url_for('journal'))

@app.route('/journal')
def journal():
    """Display user's journal with saved quotes"""
    session_id = get_session_id()
    focus_entry_id = request.args.get('focus_entry')
    
    # Get all journal entries for this user
    entries = JournalEntry.query.filter_by(user_session_id=session_id)\
                              .order_by(JournalEntry.created_at.desc())\
                              .all()
    
    return render_template('journal.html', entries=entries, focus_entry_id=focus_entry_id)

@app.route('/update_notes', methods=['POST'])
def update_notes():
    """Update notes for a journal entry"""
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
        flash('Journal entry not found', 'error')
    
    return redirect(url_for('journal'))

@app.route('/delete_entry', methods=['POST'])
def delete_entry():
    """Delete a journal entry"""
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
        flash('Journal entry deleted', 'success')
    else:
        flash('Journal entry not found', 'error')
    
    return redirect(url_for('journal'))

@app.route('/explain_quote', methods=['POST'])
def explain_quote_route():
    """Get AI explanation for a quote"""
    quote_id = request.form.get('quote_id')
    
    if not quote_id:
        return jsonify({'error': 'No quote specified'}), 400
    
    quote = Quote.query.get(quote_id)
    if not quote:
        return jsonify({'error': 'Quote not found'}), 404
    
    explanation = explain_quote(quote.text, quote.author)
    
    # Store explanation in session for display
    session['current_explanation'] = {
        'quote_id': quote_id,
        'explanation': explanation
    }
    
    return jsonify({'explanation': explanation})

@app.route('/chat', methods=['POST'])
def chat():
    """Chat about the current quote"""
    quote_id = request.form.get('quote_id')
    message = request.form.get('message', '').strip()
    
    if not quote_id or not message:
        return jsonify({'error': 'Quote ID and message required'}), 400
    
    quote = Quote.query.get(quote_id)
    if not quote:
        return jsonify({'error': 'Quote not found'}), 404
    
    # Get conversation history from session
    conversation_key = f'conversation_{quote_id}'
    conversation_history = session.get(conversation_key, [])
    
    # Get AI response
    ai_response = chat_about_quote(quote.text, quote.author, message, conversation_history)
    
    # Update conversation history
    conversation_history.extend([
        {"role": "user", "content": message},
        {"role": "assistant", "content": ai_response}
    ])
    
    # Keep only last 10 messages to avoid session size issues
    if len(conversation_history) > 10:
        conversation_history = conversation_history[-10:]
    
    session[conversation_key] = conversation_history
    
    return jsonify({
        'user_message': message,
        'ai_response': ai_response
    })

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

@app.template_filter('truncate_words')
def truncate_words(text, length=50):
    """Template filter to truncate text by words"""
    if not text:
        return ""
    words = text.split()
    if len(words) <= length:
        return text
    return ' '.join(words[:length]) + '...'

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
