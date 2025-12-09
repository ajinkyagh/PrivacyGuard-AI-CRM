import sqlite3

conn = sqlite3.connect('leads.db')
cursor = conn.cursor()

print("\n" + "="*70)
print("📊 LUXURY CRM DATABASE STATUS")
print("="*70 + "\n")

# Leads Summary
cursor.execute("SELECT COUNT(*) FROM leads")
total_leads = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM leads WHERE classification='hot_lead'")
hot_leads = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM leads WHERE stage='qualified'")
qualified = cursor.fetchone()[0]

print(f"✅ Total Leads: {total_leads}")
print(f"🔥 Hot Leads: {hot_leads}")
print(f"📈 Qualified: {qualified}")

# Recent Leads
print("\n" + "-"*70)
print("🎯 RECENT LEADS")
print("-"*70)
cursor.execute("""
    SELECT id, name, phone, score, classification, stage 
    FROM leads 
    ORDER BY id DESC 
    LIMIT 5
""")

for row in cursor.fetchall():
    lead_id, name, phone, score, classification, stage = row
    print(f"\n[{lead_id}] {name}")
    print(f"    Phone: {phone}")
    print(f"    Score: {score} | Class: {classification}")
    print(f"    Stage: {stage}")

# Scheduled Actions
print("\n" + "-"*70)
print("📅 SCHEDULED ACTIONS")
print("-"*70)
cursor.execute("""
    SELECT id, lead_id, action_name, scheduled_for, status 
    FROM scheduled_actions 
    ORDER BY id DESC 
    LIMIT 5
""")

rows = cursor.fetchall()
if rows:
    for row in rows:
        action_id, lead_id, action_name, scheduled_for, status = row
        print(f"\n[Action #{action_id}] {action_name}")
        print(f"    Lead ID: {lead_id}")
        print(f"    Scheduled: {scheduled_for}")
        print(f"    Status: {status}")
else:
    print("\n  (No scheduled actions yet)")

# Interactions
print("\n" + "-"*70)
print("💬 RECENT INTERACTIONS")
print("-"*70)
cursor.execute("""
    SELECT lead_id, agent, action, status, timestamp 
    FROM interactions 
    ORDER BY timestamp DESC 
    LIMIT 10
""")

for row in cursor.fetchall():
    lead_id, agent, action, status, timestamp = row
    print(f"\n[{timestamp}] Lead #{lead_id}")
    print(f"    {agent} → {action} ({status})")

# Pipeline Distribution
print("\n" + "-"*70)
print("📊 PIPELINE DISTRIBUTION")
print("-"*70)
stages = ['new', 'contacted', 'qualified', 'opportunity', 'closed_won', 'closed_lost']
for stage in stages:
    cursor.execute("SELECT COUNT(*) FROM leads WHERE stage=?", (stage,))
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"  {stage.upper()}: {count}")

print("\n" + "="*70 + "\n")

conn.close()
