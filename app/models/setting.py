from sqlalchemy import Column, String, Text
from app.core.database import Base

class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(255), primary_key=True, index=True)
    value = Column(Text, nullable=False)
