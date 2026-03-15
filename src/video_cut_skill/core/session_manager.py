"""Session manager for interactive video editing."""

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from video_cut_skill.config import get_config
from video_cut_skill.exceptions import SessionNotFoundError
from video_cut_skill.models.session import EditSession, SessionState


class SessionManager:
    """Manages editing sessions supporting multi-round iteration.

    This manager maintains session state in memory with optional
    disk persistence for recovery.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize session manager.

        Args:
            cache_dir: Directory for session persistence.
                      Defaults to config setting.
        """
        config = get_config()

        # Active sessions in memory
        self._sessions: Dict[str, EditSession] = {}

        # Disk persistence
        if cache_dir:
            self._cache_dir = cache_dir
        else:
            self._cache_dir = config.session.get_cache_path() / "sessions"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        self._persistence_enabled = config.session.persistence_enabled

    def create_session(self, video_path: str) -> str:
        """Create a new editing session.

        Args:
            video_path: Path to the video file

        Returns:
            Session ID
        """
        video_hash = self._compute_video_hash(video_path)
        session_id = f"{video_hash[:16]}_{uuid.uuid4().hex[:8]}"

        session = EditSession(
            session_id=session_id,
            video_path=video_path,
            video_hash=video_hash,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            state=SessionState.CREATED,
        )

        self._sessions[session_id] = session

        # Persist if enabled
        if self._persistence_enabled:
            self._persist_session(session)

        return session_id

    def get_session(self, session_id: str) -> Optional[EditSession]:
        """Get a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            EditSession or None if not found
        """
        # Check memory first
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Try to load from disk
        if self._persistence_enabled:
            return self._load_from_disk(session_id)

        return None

    def get_session_or_raise(self, session_id: str) -> EditSession:
        """Get a session or raise exception.

        Args:
            session_id: Session identifier

        Returns:
            EditSession

        Raises:
            SessionNotFoundError: If session not found
        """
        session = self.get_session(session_id)
        if not session:
            raise SessionNotFoundError(f"Session not found: {session_id}")
        return session

    def update_session(self, session_id: str, **kwargs) -> None:
        """Update session attributes.

        Args:
            session_id: Session identifier
            **kwargs: Attributes to update

        Raises:
            SessionNotFoundError: If session not found
        """
        session = self.get_session_or_raise(session_id)

        # Update attributes
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)

        # Update activity timestamp
        session.last_activity = datetime.now()

        # Persist if enabled
        if self._persistence_enabled:
            self._persist_session(session)

    def delete_session(self, session_id: str) -> None:
        """Delete a session.

        Args:
            session_id: Session identifier
        """
        # Remove from memory
        if session_id in self._sessions:
            del self._sessions[session_id]

        # Remove from disk
        if self._persistence_enabled:
            session_file = self._get_session_path(session_id)
            if session_file.exists():
                session_file.unlink()

    def list_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List all active sessions.

        Returns:
            Dictionary of session_id -> session info
        """
        result = {}
        for session_id, session in self._sessions.items():
            result[session_id] = {
                "video_path": session.video_path,
                "state": session.state.name,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
            }
        return result

    def cleanup_expired(self, max_age_days: int = 7) -> int:
        """Clean up expired sessions.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of sessions cleaned up
        """
        cutoff = datetime.now() - timedelta(days=max_age_days)
        expired = []

        # Check memory sessions
        for session_id, session in self._sessions.items():
            if session.last_activity < cutoff:
                expired.append(session_id)

        # Remove expired
        for session_id in expired:
            self.delete_session(session_id)

        # Clean disk sessions
        if self._persistence_enabled:
            for session_file in self._cache_dir.glob("*.json"):
                mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
                if mtime < cutoff:
                    session_file.unlink()

        return len(expired)

    def _compute_video_hash(self, video_path: str) -> str:
        """Compute hash for video file.

        Uses file size, mtime, and first 1MB of content.

        Args:
            video_path: Path to video file

        Returns:
            MD5 hash string
        """
        path = Path(video_path)

        if not path.exists():
            # If file doesn't exist, use path hash
            return hashlib.md5(str(path).encode()).hexdigest()

        stat = path.stat()

        hasher = hashlib.md5()
        hasher.update(f"{stat.st_size}:{stat.st_mtime}".encode())

        # Read first 1MB
        try:
            with open(video_path, "rb") as f:
                hasher.update(f.read(1024 * 1024))
        except Exception:
            pass

        return hasher.hexdigest()

    def _get_session_path(self, session_id: str) -> Path:
        """Get path to session file."""
        return self._cache_dir / f"{session_id}.json"

    def _persist_session(self, session: EditSession) -> None:
        """Persist session to disk.

        Args:
            session: Session to persist
        """
        session_file = self._get_session_path(session.session_id)
        try:
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception:
            # Ignore persistence errors
            pass

    def _load_from_disk(self, session_id: str) -> Optional[EditSession]:
        """Load session from disk.

        Args:
            session_id: Session identifier

        Returns:
            EditSession or None
        """
        session_file = self._get_session_path(session_id)
        if not session_file.exists():
            return None

        try:
            with open(session_file, encoding="utf-8") as f:
                data = json.load(f)
            session = EditSession.from_dict(data)
            # Restore to memory
            self._sessions[session_id] = session
            return session
        except Exception:
            # Corrupted or incompatible format
            return None
