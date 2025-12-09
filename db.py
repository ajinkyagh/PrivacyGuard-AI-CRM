import sqlite3
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import json

DATABASE_PATH = "leads.db"

def get_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create leads table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workflow_id TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            source TEXT NOT NULL,
            interest TEXT,
            budget_range TEXT,
            existing_customer BOOLEAN DEFAULT FALSE,
            score REAL DEFAULT 0.0,
            classification TEXT DEFAULT 'cold',
            stage TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create interactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            agent TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads (id)
        )
    """)
    
    # Create scheduled_actions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            action_name TEXT NOT NULL,
            scheduled_for TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads (id)
        )
    """)
    
    conn.commit()
    conn.close()
    logging.info("Database initialized successfully")

def insert_lead(workflow_id: str, lead_data: Dict[str, Any], score: float, classification: str) -> int:
    """Insert a new lead and return the lead ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO leads (workflow_id, name, phone, email, source, interest, budget_range, 
                          existing_customer, score, classification)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        workflow_id,
        lead_data.get('name'),
        lead_data.get('phone'),
        lead_data.get('email'),
        lead_data.get('source'),
        lead_data.get('interest'),
        lead_data.get('budget_range'),
        lead_data.get('existing_customer', False),
        score,
        classification
    ))
    
    lead_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return lead_id

def update_lead(lead_id: int, **kwargs) -> bool:
    """Update lead with given fields"""
    if not kwargs:
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Build dynamic update query
    set_clauses = []
    values = []
    for key, value in kwargs.items():
        set_clauses.append(f"{key} = ?")
        values.append(value)
    
    values.append(lead_id)
    
    query = f"UPDATE leads SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
    cursor.execute(query, values)
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def log_interaction(lead_id: int, agent: str, action: str, status: str, details: Any = None) -> bool:
    """Log an interaction for a lead"""
    conn = get_connection()
    cursor = conn.cursor()
    
    details_json = json.dumps(details) if details else None
    
    cursor.execute("""
        INSERT INTO interactions (lead_id, agent, action, status, details)
        VALUES (?, ?, ?, ?, ?)
    """, (lead_id, agent, action, status, details_json))
    
    conn.commit()
    conn.close()
    return True

def schedule_action(lead_id: int, action_name: str, scheduled_for: datetime, status: str = "pending") -> bool:
    """Schedule an action for a lead"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO scheduled_actions (lead_id, action_name, scheduled_for, status)
        VALUES (?, ?, ?, ?)
    """, (lead_id, action_name, scheduled_for, status))
    
    conn.commit()
    conn.close()
    return True

def fetch_dashboard_stats() -> Dict[str, Any]:
    """Fetch dashboard statistics"""
    conn = get_connection()
    cursor = conn.cursor()

    # Total leads
    cursor.execute("SELECT COUNT(*) as total FROM leads")
    total_leads = cursor.fetchone()['total']

    # Leads by stage
    cursor.execute("""
        SELECT stage, COUNT(*) as count 
        FROM leads 
        GROUP BY stage
    """)
    stage_counts = {row['stage']: row['count'] for row in cursor.fetchall()}

    # Leads by classification
    cursor.execute("""
        SELECT classification, COUNT(*) as count 
        FROM leads 
        GROUP BY classification
    """)
    classification_counts = {row['classification']: row['count'] for row in cursor.fetchall()}

    # Recent interactions
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM interactions 
        WHERE timestamp > datetime('now', '-24 hours')
    """)
    recent_interactions = cursor.fetchone()['count']

    # Conversion rate - fixed calculation
    won_leads = stage_counts.get('closed_won', 0)
    lost_leads = stage_counts.get('closed_lost', 0)
    total_closed_leads = won_leads + lost_leads
    conversion_rate = (won_leads / total_closed_leads * 100) if total_closed_leads > 0 else 0

    # Pipeline value - parse budget ranges properly
    cursor.execute("""
        SELECT budget_range 
        FROM leads 
        WHERE stage IN ('qualified', 'opportunity', 'closed_won')
        AND budget_range IS NOT NULL
    """)
    budget_ranges = cursor.fetchall()
    
    pipeline_value = 0
    for row in budget_ranges:
        budget_str = row['budget_range']
        if budget_str:
            # Parse budget range (e.g., "₹2-3 Crores", "₹5+ Crores")
            try:
                # Remove currency symbol and convert to lowercase
                budget_clean = budget_str.replace('₹', '').lower()
                
                if 'crore' in budget_clean:
                    if '+' in budget_clean:
                        # Handle "5+ crores" - use the number as minimum
                        num = float(budget_clean.split('+')[0].strip())
                        pipeline_value += num
                    elif '-' in budget_clean:
                        # Handle "2-3 crores" - use average
                        parts = budget_clean.split('-')
                        start = float(parts[0].strip())
                        end = float(parts[1].split()[0].strip())
                        pipeline_value += (start + end) / 2
                    else:
                        # Handle single number like "3 crores"
                        num = float(budget_clean.split()[0].strip())
                        pipeline_value += num
            except (ValueError, IndexError):
                # If parsing fails, skip this entry
                continue

    conn.close()

    return {
        "total_leads": total_leads,
        "stage_counts": stage_counts,
        "classification_counts": classification_counts,
        "recent_interactions": recent_interactions,
        "conversion_rate": round(conversion_rate, 1),
        "pipeline_value": pipeline_value
    }

def fetch_pipeline_counts() -> Dict[str, int]:
    """Fetch pipeline stage counts"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT stage, COUNT(*) as count 
        FROM leads 
        GROUP BY stage
    """)
    
    counts = {row['stage']: row['count'] for row in cursor.fetchall()}
    conn.close()
    
    return counts

def fetch_pipeline_leads() -> List[Dict[str, Any]]:
    """Fetch leads for pipeline view"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, phone, email, source, interest, budget_range, 
               score, classification, stage, created_at
        FROM leads 
        ORDER BY created_at DESC
        LIMIT 100
    """)
    
    leads = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return leads

def fetch_leads(limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch leads with limit"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, phone, email, source, interest, budget_range, 
               score, classification, stage, created_at, updated_at
        FROM leads 
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    
    leads = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return leads

def fetch_interactions(lead_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch interactions for a specific lead"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, agent, action, status, details, timestamp
        FROM interactions 
        WHERE lead_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (lead_id, limit))
    
    interactions = []
    for row in cursor.fetchall():
        interaction = dict(row)
        if interaction['details']:
            try:
                interaction['details'] = json.loads(interaction['details'])
            except:
                pass
        interactions.append(interaction)
    
    conn.close()
    return interactions

def fetch_forecast_revenue() -> Dict[str, Any]:
    """Fetch revenue forecast data"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Simple revenue forecast based on leads and their budget ranges
    cursor.execute("""
        SELECT budget_range, COUNT(*) as count
        FROM leads 
        WHERE stage IN ('qualified', 'proposal', 'negotiation', 'closed_won')
        GROUP BY budget_range
    """)
    
    budget_data = {row['budget_range']: row['count'] for row in cursor.fetchall()}
    
    # Calculate estimated revenue (simplified)
    total_estimated = 0
    for budget_range, count in budget_data.items():
        if 'crore' in budget_range.lower():
            # Extract number from budget range (simplified)
            try:
                avg_value = 5.0  # Default average in crores
                if '-' in budget_range:
                    parts = budget_range.split('-')
                    avg_value = (float(parts[0]) + float(parts[1].split()[0])) / 2
                total_estimated += avg_value * count
            except:
                total_estimated += 5.0 * count
    
    conn.close()
    
    return {
        "estimated_revenue": total_estimated,
        "budget_breakdown": budget_data,
        "currency": "INR Crores"
    }



