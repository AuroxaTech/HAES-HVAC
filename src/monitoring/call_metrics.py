"""
HAES HVAC - Call Metrics Tracking

Tracks call performance metrics (Test 9.1-9.5):
- Response time tracking
- Call completion tracking
- Data accuracy tracking
- User satisfaction tracking
- Issue tracking
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db.models import CallMetrics
from src.db.session import get_session_factory

logger = logging.getLogger(__name__)


def track_call_start(call_id: str, request_id: str | None = None, channel: str = "voice") -> None:
    """
    Track call start for metrics (Test 9.1).
    
    Args:
        call_id: Vapi call ID
        request_id: Request ID for tracking
        channel: Channel type (voice, chat)
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        now = datetime.utcnow()
        
        # Check if metrics record exists
        existing = session.query(CallMetrics).filter(
            CallMetrics.call_id == call_id
        ).first()
        
        if not existing:
            # Create new metrics record
            metrics = CallMetrics(
                call_id=call_id,
                request_id=request_id,
                channel=channel,
                call_start_time=now,
            )
            session.add(metrics)
            session.commit()
            logger.info(f"Created call metrics record for call_id={call_id}")
        else:
            # Update existing record
            existing.call_start_time = existing.call_start_time or now
            session.commit()
    except Exception as e:
        logger.error(f"Failed to track call start: {e}")
        session.rollback()
    finally:
        session.close()


def track_greeting(call_id: str) -> None:
    """
    Track greeting time for response time metrics (Test 9.1).
    
    Args:
        call_id: Vapi call ID
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        metrics = session.query(CallMetrics).filter(
            CallMetrics.call_id == call_id
        ).first()
        
        if metrics:
            now = datetime.utcnow()
            metrics.greeting_time = now
            
            if metrics.call_start_time:
                duration = (now - metrics.call_start_time).total_seconds()
                metrics.greeting_duration_seconds = str(duration)
            
            session.commit()
            logger.debug(f"Tracked greeting for call_id={call_id}, duration={metrics.greeting_duration_seconds}")
    except Exception as e:
        logger.error(f"Failed to track greeting: {e}")
        session.rollback()
    finally:
        session.close()


def track_user_response(
    call_id: str,
    user_input_time: datetime | None = None,
    response_time_seconds: float | None = None,
) -> None:
    """
    Track user input to response time (Test 9.1).
    
    Args:
        call_id: Vapi call ID
        user_input_time: When user provided input
        response_time_seconds: Time taken to respond (in seconds)
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        metrics = session.query(CallMetrics).filter(
            CallMetrics.call_id == call_id
        ).first()
        
        if metrics:
            user_input_times = metrics.user_input_times or []
            
            entry = {
                "timestamp": (user_input_time or datetime.utcnow()).isoformat(),
                "response_time_seconds": response_time_seconds,
            }
            user_input_times.append(entry)
            metrics.user_input_times = user_input_times
            
            # Update average response time
            if response_time_seconds is not None:
                valid_times = [e.get("response_time_seconds") for e in user_input_times if e.get("response_time_seconds") is not None]
                if valid_times:
                    avg = sum(valid_times) / len(valid_times)
                    metrics.average_response_time_seconds = str(avg)
            
            # Track pauses >3 seconds
            if response_time_seconds and response_time_seconds > 3.0:
                metrics.pauses_over_3_seconds = (metrics.pauses_over_3_seconds or 0) + 1
            
            session.commit()
            logger.debug(f"Tracked user response for call_id={call_id}")
    except Exception as e:
        logger.error(f"Failed to track user response: {e}")
        session.rollback()
    finally:
        session.close()


def track_call_completion(
    call_id: str,
    completed: bool = True,
    reason: str | None = None,
) -> None:
    """
    Track call completion for completion rate metrics (Test 9.2).
    
    Args:
        call_id: Vapi call ID
        completed: Whether call was completed successfully
        reason: Completion reason (completed, dropped, transferred, error)
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        metrics = session.query(CallMetrics).filter(
            CallMetrics.call_id == call_id
        ).first()
        
        if metrics:
            now = datetime.utcnow()
            metrics.call_end_time = now
            metrics.call_completed = "true" if completed else "false"
            metrics.completion_reason = reason or ("completed" if completed else "unknown")
            session.commit()
            logger.info(f"Tracked call completion for call_id={call_id}, completed={completed}")
    except Exception as e:
        logger.error(f"Failed to track call completion: {e}")
        session.rollback()
    finally:
        session.close()


def track_data_accuracy(
    call_id: str,
    fields_collected: int,
    fields_correct: int,
    validation_errors: list[dict] | None = None,
) -> None:
    """
    Track data accuracy for accuracy metrics (Test 9.3).
    
    Args:
        call_id: Vapi call ID
        fields_collected: Total fields collected
        fields_correct: Number of correct fields
        validation_errors: List of validation errors
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        metrics = session.query(CallMetrics).filter(
            CallMetrics.call_id == call_id
        ).first()
        
        if metrics:
            metrics.fields_collected = fields_collected
            metrics.fields_correct = fields_correct
            metrics.fields_incorrect = fields_collected - fields_correct
            
            if fields_collected > 0:
                accuracy = (fields_correct / fields_collected) * 100
                metrics.accuracy_rate = str(accuracy)
            
            if validation_errors:
                metrics.validation_errors = validation_errors
            
            session.commit()
            logger.debug(f"Tracked data accuracy for call_id={call_id}, accuracy={metrics.accuracy_rate}%")
    except Exception as e:
        logger.error(f"Failed to track data accuracy: {e}")
        session.rollback()
    finally:
        session.close()


def track_user_satisfaction(
    call_id: str,
    rating: int,
    feedback: str | None = None,
) -> None:
    """
    Track user satisfaction rating (Test 9.4).
    
    Args:
        call_id: Vapi call ID
        rating: Satisfaction rating (1-5 scale)
        feedback: Optional feedback text
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        metrics = session.query(CallMetrics).filter(
            CallMetrics.call_id == call_id
        ).first()
        
        if metrics:
            if 1 <= rating <= 5:
                metrics.satisfaction_rating = rating
                metrics.satisfaction_feedback = feedback
                session.commit()
                logger.info(f"Tracked satisfaction rating for call_id={call_id}, rating={rating}")
    except Exception as e:
        logger.error(f"Failed to track user satisfaction: {e}")
        session.rollback()
    finally:
        session.close()


def track_issue(
    call_id: str,
    category: str,
    description: str,
    is_prohibited_phrase: bool = False,
) -> None:
    """
    Track issues and prohibited phrases (Test 9.5).
    
    Args:
        call_id: Vapi call ID
        category: Issue category
        description: Issue description
        is_prohibited_phrase: Whether this is a prohibited phrase
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        metrics = session.query(CallMetrics).filter(
            CallMetrics.call_id == call_id
        ).first()
        
        if metrics:
            issues = metrics.issues_detected or []
            issues.append({
                "category": category,
                "description": description,
                "timestamp": datetime.utcnow().isoformat(),
            })
            metrics.issues_detected = issues
            
            if is_prohibited_phrase:
                prohibited = metrics.prohibited_phrases_detected or []
                prohibited.append(description)
                metrics.prohibited_phrases_detected = prohibited
            
            session.commit()
            logger.info(f"Tracked issue for call_id={call_id}, category={category}")
    except Exception as e:
        logger.error(f"Failed to track issue: {e}")
        session.rollback()
    finally:
        session.close()


def get_call_metrics_summary(session: Session | None = None, days: int = 30) -> dict[str, Any]:
    """
    Get aggregated call metrics summary (Test 9.1-9.5).
    
    Args:
        session: Database session (optional)
        days: Number of days to aggregate
        
    Returns:
        Dictionary with aggregated metrics
    """
    should_close = False
    if not session:
        session_factory = get_session_factory()
        session = session_factory()
        should_close = True
    
    try:
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get total calls
        total_calls = session.query(func.count(CallMetrics.id)).filter(
            CallMetrics.created_at >= cutoff_date
        ).scalar() or 0
        
        # Get completed calls (Test 9.2)
        completed_calls = session.query(func.count(CallMetrics.id)).filter(
            CallMetrics.created_at >= cutoff_date,
            CallMetrics.call_completed == "true"
        ).scalar() or 0
        
        completion_rate = (completed_calls / total_calls * 100) if total_calls > 0 else 0
        
        # Get average response times (Test 9.1)
        avg_greeting_time = session.query(func.avg(
            func.cast(CallMetrics.greeting_duration_seconds, func.Float)
        )).filter(
            CallMetrics.created_at >= cutoff_date,
            CallMetrics.greeting_duration_seconds.isnot(None)
        ).scalar()
        
        avg_response_time = session.query(func.avg(
            func.cast(CallMetrics.average_response_time_seconds, func.Float)
        )).filter(
            CallMetrics.created_at >= cutoff_date,
            CallMetrics.average_response_time_seconds.isnot(None)
        ).scalar()
        
        # Get average data accuracy (Test 9.3)
        avg_accuracy = session.query(func.avg(
            func.cast(CallMetrics.accuracy_rate, func.Float)
        )).filter(
            CallMetrics.created_at >= cutoff_date,
            CallMetrics.accuracy_rate.isnot(None)
        ).scalar()
        
        # Get average satisfaction (Test 9.4)
        avg_satisfaction = session.query(func.avg(CallMetrics.satisfaction_rating)).filter(
            CallMetrics.created_at >= cutoff_date,
            CallMetrics.satisfaction_rating.isnot(None)
        ).scalar()
        
        # Get issue counts (Test 9.5)
        total_issues = session.query(func.count(CallMetrics.id)).filter(
            CallMetrics.created_at >= cutoff_date,
            CallMetrics.issues_detected.isnot(None)
        ).scalar() or 0
        
        return {
            "period_days": days,
            "total_calls": total_calls,
            "completed_calls": completed_calls,
            "completion_rate": round(completion_rate, 2),
            "average_greeting_time_seconds": round(avg_greeting_time, 2) if avg_greeting_time else None,
            "average_response_time_seconds": round(avg_response_time, 2) if avg_response_time else None,
            "average_data_accuracy_percent": round(avg_accuracy, 2) if avg_accuracy else None,
            "average_satisfaction_rating": round(avg_satisfaction, 2) if avg_satisfaction else None,
            "total_issues_detected": total_issues,
            "targets": {
                "completion_rate": 90.0,
                "greeting_time_seconds": 2.0,
                "response_time_seconds": 2.0,
                "data_accuracy_percent": 95.0,
                "satisfaction_rating": 4.0,
            },
            "alerts": {
                "completion_rate_below_target": completion_rate < 90.0 if total_calls > 0 else False,
                "response_time_above_target": (avg_response_time or 0) > 2.0 if avg_response_time else False,
                "accuracy_below_target": (avg_accuracy or 0) < 95.0 if avg_accuracy else False,
                "satisfaction_below_target": (avg_satisfaction or 0) < 4.0 if avg_satisfaction else False,
            },
        }
    finally:
        if should_close:
            session.close()
