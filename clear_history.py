#!/usr/bin/env python3

from app import app, db, SubjectHistory

def clear_history_data():
    with app.app_context():
        try:
            count = SubjectHistory.query.count()
            print(f'Found {count} existing history records')
            SubjectHistory.query.delete()
            db.session.commit()
            print('All SubjectHistory data cleared successfully!')
            print('You can now start adding fresh history records.')
        except Exception as e:
            print(f'Error: {e}')

if __name__ == "__main__":
    clear_history_data()
