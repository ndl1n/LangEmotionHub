import logging

from sqlalchemy import and_, extract
from extensions import db
from models.event_journal import EventJournal
from sqlalchemy.exc import SQLAlchemyError

class EventJournalRepository:
    @staticmethod
    def create_event(user_id, event_title, event_content, event_date, event_picture):
        """新增一個事件記錄"""
        try:
            new_event = EventJournal(
                user_id=user_id,
                event_title=event_title,
                event_content=event_content,
                event_date=event_date,
                event_picture=event_picture
            )
            db.session.add(new_event)
            db.session.commit()
            return new_event
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Error creating event: {e}")
            raise e

    @staticmethod
    def get_event_by_event_id(event_id):
        """根據事件ID取得事件"""
        try:
            return EventJournal.query.filter_by(id=event_id).first()
        except SQLAlchemyError as e:
            logging.error(f"Error retrieving event with ID {event_id}: {e}")
            raise e

    @staticmethod
    def get_events_by_user_id(user_id):
        """根據使用者ID取得該使用者所有的事件記錄"""
        try:
            return EventJournal.query.filter_by(user_id=user_id).all()
        except SQLAlchemyError as e:
            logging.error(f"Error retrieving events for user ID {user_id}: {e}")
            raise e

    @staticmethod
    def update_event(event_id, event_title=None, event_content=None, updated_at=None, event_date=None ,event_picture=None):
        """更新一個事件的標題或內容"""
        try:
            event = EventJournal.query.filter_by(id=event_id).first()
            if not event:
                return None
            if event_title:
                event.event_title = event_title
            if event_content:
                event.event_content = event_content
            if updated_at:
                event.updated_at = updated_at
            if event_date:
                event.event_date = event_date
            if event_picture:
                event.event_picture = event_picture
            db.session.commit()
            return event
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Error updating event with ID {event_id}: {e}")
            raise e

    @staticmethod 
    def delete_event(event_id):
        """刪除一個事件記錄"""
        try:
            event = EventJournal.query.filter_by(id=event_id).first()
            if event:
                db.session.delete(event)
                db.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Error deleting event with ID {event_id}: {e}")
            raise e
    @staticmethod
    def get_events_by_date(user_id, target_year):
        """根據使用者ID和日期取得事件"""
        try:
            return EventJournal.query.filter(
                        and_(
                            EventJournal.user_id == user_id,
                            extract('year', EventJournal.event_date) == target_year
                        )
                    ).order_by(EventJournal.event_date.asc()).all()        
        except SQLAlchemyError as e:
            logging.error(f"Error retrieving event with user ID {user_id} and the year if {target_year}: {e}")
            raise e