from app import db
from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Quote(db.Model):
    __tablename__ = 'quotes'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(200), nullable=False)
    tags: Mapped[str] = mapped_column(String(500), nullable=True)
    
    # Relationship to journal entries
    journal_entries = relationship("JournalEntry", back_populates="quote", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Quote {self.id}: {self.text[:50]}...>'

class JournalEntry(db.Model):
    __tablename__ = 'journal_entries'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_id: Mapped[int] = mapped_column(Integer, ForeignKey('quotes.id'), nullable=False)
    user_session_id: Mapped[str] = mapped_column(String(100), nullable=False)
    user_notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to quote
    quote = relationship("Quote", back_populates="journal_entries")
    
    def __repr__(self):
        return f'<JournalEntry {self.id}: Quote {self.quote_id}>'
