import hashlib
import json
import csv
from datetime import datetime, date
from flask import session
from app import db
from models import Quote

def get_session_id():
    """Get or create a session ID for the user"""
    if 'session_id' not in session:
        # Create a simple session ID based on timestamp and some randomness
        session_data = str(datetime.utcnow().timestamp())
        session['session_id'] = hashlib.md5(session_data.encode()).hexdigest()
    return session['session_id']

def get_daily_quote():
    """Get a deterministic quote for today's date"""
    today = date.today()
    # Use date as seed for deterministic "random" selection
    date_seed = int(today.strftime("%Y%m%d"))
    
    # Get total number of quotes
    total_quotes = Quote.query.count()
    if total_quotes == 0:
        return None
    
    # Use date seed to select a quote deterministically
    quote_index = date_seed % total_quotes
    quote = Quote.query.offset(quote_index).first()
    
    return quote

def update_streak():
    """Update user's streak based on last visit"""
    today = date.today()
    session_id = get_session_id()
    
    # Get streak data from session
    last_visit_str = session.get('last_visit_date')
    current_streak = session.get('current_streak', 0)
    highest_streak = session.get('highest_streak', 0)
    
    if last_visit_str:
        last_visit = datetime.strptime(last_visit_str, "%Y-%m-%d").date()
        days_diff = (today - last_visit).days
        
        if days_diff == 0:
            # Same day, no change
            pass
        elif days_diff == 1:
            # Consecutive day, increment streak
            current_streak += 1
            highest_streak = max(highest_streak, current_streak)
        else:
            # Missed days, reset streak
            current_streak = 1
    else:
        # First visit
        current_streak = 1
        highest_streak = max(highest_streak, current_streak)
    
    # Update session
    session['last_visit_date'] = today.strftime("%Y-%m-%d")
    session['current_streak'] = current_streak
    session['highest_streak'] = highest_streak
    
    return {
        'current_streak': current_streak,
        'highest_streak': highest_streak
    }

def import_quotes_from_csv(file_path):
    """Import quotes from a CSV file"""
    imported_count = 0
    try:
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            # Try to detect if there's a header
            sample = csvfile.read(1024)
            csvfile.seek(0)
            sniffer = csv.Sniffer()
            has_header = sniffer.has_header(sample)
            
            reader = csv.reader(csvfile)
            if has_header:
                next(reader)  # Skip header row
            
            for row in reader:
                if len(row) >= 2:  # At least text and author
                    text = row[0].strip()
                    author = row[1].strip()
                    tags = row[2].strip() if len(row) > 2 else ""
                    
                    if text and author:
                        # Check if quote already exists
                        existing = Quote.query.filter_by(text=text, author=author).first()
                        if not existing:
                            quote = Quote(text=text, author=author, tags=tags)
                            db.session.add(quote)
                            imported_count += 1
            
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    
    return imported_count

def import_quotes_from_json(file_path):
    """Import quotes from a JSON file"""
    imported_count = 0
    try:
        with open(file_path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)
            
            # Handle different JSON structures
            if isinstance(data, list):
                quotes_list = data
            elif isinstance(data, dict) and 'quotes' in data:
                quotes_list = data['quotes']
            else:
                raise ValueError("JSON format not recognized. Expected array or object with 'quotes' key.")
            
            for quote_data in quotes_list:
                if isinstance(quote_data, dict):
                    text = quote_data.get('text', '').strip()
                    author = quote_data.get('author', '').strip()
                    tags = quote_data.get('tags', '')
                    
                    if text and author:
                        # Check if quote already exists
                        existing = Quote.query.filter_by(text=text, author=author).first()
                        if not existing:
                            quote = Quote(text=text, author=author, tags=tags)
                            db.session.add(quote)
                            imported_count += 1
            
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    
    return imported_count

def add_sample_quotes():
    """Add some initial philosophical quotes if database is empty"""
    if Quote.query.count() == 0:
        sample_quotes = [
            {
                "text": "The unexamined life is not worth living.",
                "author": "Socrates",
                "tags": "Ancient Philosophy, Self-Knowledge"
            },
            {
                "text": "I think, therefore I am.",
                "author": "René Descartes",
                "tags": "Rationalism, Existence"
            },
            {
                "text": "Man is condemned to be free; because once thrown into the world, he is responsible for everything he does.",
                "author": "Jean-Paul Sartre",
                "tags": "Existentialism, Freedom, Responsibility"
            },
            {
                "text": "The only way to deal with an unfree world is to become so absolutely free that your very existence is an act of rebellion.",
                "author": "Albert Camus",
                "tags": "Existentialism, Freedom, Rebellion"
            },
            {
                "text": "You have power over your mind - not outside events. Realize this, and you will find strength.",
                "author": "Marcus Aurelius",
                "tags": "Stoicism, Mental Strength"
            }
        ]
        
        for quote_data in sample_quotes:
            quote = Quote(**quote_data)
            db.session.add(quote)
        
        db.session.commit()
        return len(sample_quotes)
    return 0
