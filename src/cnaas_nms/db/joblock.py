import datetime
from typing import Optional, Dict

from sqlalchemy import Column, String, DateTime, Boolean, Integer

import cnaas_nms.db.base
from cnaas_nms.db.session import sqla_session


class JoblockError(Exception):
    pass


class Joblock(cnaas_nms.db.base.Base):
    __tablename__ = 'joblock'
    jobid = Column(String(24), unique=True, primary_key=True)  # mongodb ObjectId, 12-byte hex
    name = Column(String(32), unique=True, nullable=False)
    start_time = Column(DateTime, default=datetime.datetime.now)  # onupdate=now
    abort = Column(Boolean, default=False)

    def as_dict(self) -> dict:
        """Return JSON serializable dict."""
        d = {}
        for col in self.__table__.columns:
            value = getattr(self, col.name)
            if issubclass(value.__class__, cnaas_nms.db.base.Base):
                continue
            elif issubclass(value.__class__, datetime.datetime):
                value = str(value)
            d[col.name] = value
        return d

    @classmethod
    def acquire_lock(cls, session: sqla_session, name: str, job_id: str) -> bool:
        curlock = session.query(Joblock).filter(Joblock.name == name).one_or_none()
        if curlock:
            return False
        newlock = Joblock(jobid=job_id, name=name, start_time=datetime.datetime.now())
        session.add(newlock)
        session.commit()
        return True

    @classmethod
    def release_lock(cls, session: sqla_session, name: Optional[str] = None,
                     job_id: Optional[str] = None):
        if job_id:
            curlock = session.query(Joblock).filter(Joblock.jobid == job_id).one_or_none()
        elif name:
            curlock = session.query(Joblock).filter(Joblock.name == name).one_or_none()
        else:
            raise ValueError("Either name or jobid must be set to release lock")

        if not curlock:
            raise JoblockError("Current lock could not be found")

        session.delete(curlock)
        session.commit()
        return True

    @classmethod
    def get_lock(cls, session: sqla_session, name: Optional[str] = None,
                 job_id: Optional[str] = None) -> Optional[Dict[str, str]]:
        """

        Args:
            session: SQLAlchemy session context manager
            name: name of job/lock
            jobid: jobid

        Returns:
            Dict example: {'name': 'syncto', 'jobid': '5d5aa92dba050d64aa2966dc',
            'start_time': '2019-08-23 10:45:07.788892', 'abort': False}

        """
        if job_id:
            curlock: Joblock = session.query(Joblock).filter(Joblock.jobid == job_id).one_or_none()
        elif name:
            curlock: Joblock = session.query(Joblock).filter(Joblock.name == name).one_or_none()
        else:
            raise ValueError("Either name or jobid must be set to release lock")

        if curlock:
            return curlock.as_dict()
        else:
            return None

    @classmethod
    def clear_locks(cls, session: sqla_session):
        """Clear/release all locks in the database."""
        return session.query(Joblock).delete()
