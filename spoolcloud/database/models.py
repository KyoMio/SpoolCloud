"""SQLAlchemy data models."""

from datetime import datetime
from typing import Optional
import enum

from sqlalchemy import ForeignKey, Integer, String, Text, Boolean, JSON
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class NotificationChannel(str, enum.Enum):
    SERVERCHAN = "serverchan"
    BARK = "bark"
    SYNOCHAT = "synochat"


class NotificationType(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(16), default=UserRole.USER.value)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    api_keys: Mapped[list["APIKey"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    presets: Mapped[list["FilamentPreset"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notification_config: Mapped[Optional["NotificationConfig"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    internal_notifications: Mapped[list["InternalNotification"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    
    vendors: Mapped[list["Vendor"]] = relationship(back_populates="user")
    filaments: Mapped[list["Filament"]] = relationship(back_populates="user")
    spools: Mapped[list["Spool"]] = relationship(back_populates="user")
    
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_invite_codes: Mapped[list["InviteCode"]] = relationship(back_populates="created_by", foreign_keys="InviteCode.created_by_user_id")
    used_invite_code: Mapped[Optional["InviteCode"]] = relationship(back_populates="used_by", foreign_keys="InviteCode.used_by_user_id", uselist=False)



class APIKey(Base):
    __tablename__ = "api_key"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    user: Mapped["User"] = relationship(back_populates="api_keys")
    key_prefix: Mapped[str] = mapped_column(String(16))
    key_hash: Mapped[str] = mapped_column(String(256), index=True)
    label: Mapped[str] = mapped_column(String(64))
    last_used_at: Mapped[Optional[datetime]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class FilamentPreset(Base):
    __tablename__ = "filament_preset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    user: Mapped["User"] = relationship(back_populates="presets")
    name: Mapped[str] = mapped_column(String(64))
    
    filaments: Mapped[list["Filament"]] = relationship(back_populates="preset")


class NotificationConfig(Base):
    __tablename__ = "notification_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), unique=True, index=True)
    user: Mapped["User"] = relationship(back_populates="notification_config")
    channel: Mapped[str] = mapped_column(String(32))  # serverchan, bark, synochat, email, webhook
    webhook_url: Mapped[str] = mapped_column(Text, nullable=True)  # Primary URL for webhooks
    config_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string for channel-specific config
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class InternalNotification(Base):
    __tablename__ = "internal_notification"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    user: Mapped["User"] = relationship(back_populates="internal_notifications")
    title: Mapped[str] = mapped_column(String(128))
    message: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(16), default=NotificationType.INFO.value)
    data: Mapped[Optional[dict]] = mapped_column(JSON)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class Vendor(Base):
    __tablename__ = "vendor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user.id"), index=True)
    user: Mapped[Optional["User"]] = relationship(back_populates="vendors")
    registered: Mapped[datetime] = mapped_column()
    name: Mapped[str] = mapped_column(String(64))
    empty_spool_weight: Mapped[Optional[float]] = mapped_column(comment="The weight of an empty spool.")
    comment: Mapped[Optional[str]] = mapped_column(String(1024))
    filaments: Mapped[list["Filament"]] = relationship(back_populates="vendor")
    external_id: Mapped[Optional[str]] = mapped_column(String(256))
    extra: Mapped[list["VendorField"]] = relationship(
        back_populates="vendor",
        cascade="save-update, merge, delete, delete-orphan",
        lazy="joined",
    )


class Filament(Base):
    __tablename__ = "filament"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user.id"), index=True)
    user: Mapped[Optional["User"]] = relationship(back_populates="filaments")
    preset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("filament_preset.id"), index=True)
    preset: Mapped[Optional["FilamentPreset"]] = relationship(back_populates="filaments")
    registered: Mapped[datetime] = mapped_column()
    name: Mapped[Optional[str]] = mapped_column(String(64))
    vendor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("vendor.id"))
    vendor: Mapped[Optional["Vendor"]] = relationship(back_populates="filaments")
    spools: Mapped[list["Spool"]] = relationship(back_populates="filament")
    material: Mapped[Optional[str]] = mapped_column(String(64))
    price: Mapped[Optional[float]] = mapped_column()
    density: Mapped[float] = mapped_column()
    diameter: Mapped[float] = mapped_column()
    weight: Mapped[Optional[float]] = mapped_column(comment="The filament weight of a full spool (net weight).")
    spool_weight: Mapped[Optional[float]] = mapped_column(comment="The weight of an empty spool.")
    article_number: Mapped[Optional[str]] = mapped_column(String(64))
    comment: Mapped[Optional[str]] = mapped_column(String(1024))
    settings_extruder_temp: Mapped[Optional[int]] = mapped_column(comment="Overridden extruder temperature.")
    settings_bed_temp: Mapped[Optional[int]] = mapped_column(comment="Overridden bed temperature.")
    color_hex: Mapped[Optional[str]] = mapped_column(String(8))
    multi_color_hexes: Mapped[Optional[str]] = mapped_column(String(128))
    multi_color_direction: Mapped[Optional[str]] = mapped_column(String(16))
    external_id: Mapped[Optional[str]] = mapped_column(String(256))
    extra: Mapped[list["FilamentField"]] = relationship(
        back_populates="filament",
        cascade="save-update, merge, delete, delete-orphan",
        lazy="joined",
    )


class Spool(Base):
    __tablename__ = "spool"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user.id"), index=True)
    user: Mapped[Optional["User"]] = relationship(back_populates="spools")
    registered: Mapped[datetime] = mapped_column()
    first_used: Mapped[Optional[datetime]] = mapped_column()
    last_used: Mapped[Optional[datetime]] = mapped_column()
    price: Mapped[Optional[float]] = mapped_column()
    filament_id: Mapped[int] = mapped_column(ForeignKey("filament.id"))
    filament: Mapped["Filament"] = relationship(back_populates="spools")
    initial_weight: Mapped[Optional[float]] = mapped_column()
    spool_weight: Mapped[Optional[float]] = mapped_column()
    used_weight: Mapped[float] = mapped_column()
    location: Mapped[Optional[str]] = mapped_column(String(64))
    lot_nr: Mapped[Optional[str]] = mapped_column(String(64))
    comment: Mapped[Optional[str]] = mapped_column(String(1024))
    archived: Mapped[Optional[bool]] = mapped_column()
    extra: Mapped[list["SpoolField"]] = relationship(
        back_populates="spool",
        cascade="save-update, merge, delete, delete-orphan",
        lazy="joined",
    )


class Setting(Base):
    __tablename__ = "setting"

    key: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    value: Mapped[str] = mapped_column(Text())
    last_updated: Mapped[datetime] = mapped_column()


class VendorField(Base):
    __tablename__ = "vendor_field"

    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"), primary_key=True, index=True)
    vendor: Mapped["Vendor"] = relationship(back_populates="extra")
    key: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    value: Mapped[str] = mapped_column(Text())


class FilamentField(Base):
    __tablename__ = "filament_field"

    filament_id: Mapped[int] = mapped_column(ForeignKey("filament.id"), primary_key=True, index=True)
    filament: Mapped["Filament"] = relationship(back_populates="extra")
    key: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    value: Mapped[str] = mapped_column(Text())


class SpoolField(Base):
    __tablename__ = "spool_field"

    spool_id: Mapped[int] = mapped_column(ForeignKey("spool.id"), primary_key=True, index=True)
    spool: Mapped["Spool"] = relationship(back_populates="extra")
    key: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    value: Mapped[str] = mapped_column(Text())


class InviteCode(Base):
    """Invite code model for user registration."""
    __tablename__ = "invite_code"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    created_by: Mapped["User"] = relationship(back_populates="created_invite_codes", foreign_keys=[created_by_user_id])
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    used_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user.id"), nullable=True, index=True)
    used_by: Mapped[Optional["User"]] = relationship(back_populates="used_invite_code", foreign_keys=[used_by_user_id])
    used_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

