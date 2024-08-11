import bcrypt
from sqlmodel import Session, select

from app.mail_sending import has_api_key, send_registration_mail
from app.models import User, UserRegistration
from app.validators import validate_new_user_name


def user_create(
    session: Session,
    name: str,
    password: str,
    email: str,
    with_registration: bool = False,
):
    validate_new_user_name(session, name)
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )
    user = User(name=name, password_hash=password_hash, email=email)
    session.add(user)
    session.commit()
    session.refresh(user)
    if with_registration and has_api_key:
        token = bcrypt.hashpw(name.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        session.add(UserRegistration(token=token, user_id=user.id))
        session.commit()
        send_registration_mail(user.email, token)
        return user
    user.is_activated = True
    session.commit()
    session.refresh(user)
    return user


def user_list(session: Session):
    return session.exec(select(User).where(User.is_activated)).all()


def user_delete(session: Session, user_id: int):
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise ValueError("Invalid user")
    session.delete(user)
    session.commit()
    return user


def user_update(
    session: Session,
    user_id: int,
    name: str = None,
    password: str = None,
    email: str = None,
):
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise ValueError("Invalid user")
    if name:
        user.name = name
    if password:
        user.password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
    if email:
        user.email = email
    session.commit()
    session.refresh(user)
    return user


def user_activate(session: Session, token: str):
    user_registration = session.exec(
        select(UserRegistration).where(UserRegistration.token == token)
    ).first()
    if not user_registration:
        raise ValueError("Invalid token")
    user = session.exec(
        select(User).where(User.id == user_registration.user_id)
    ).first()
    session.delete(user_registration)
    if not user:
        session.commit()
        raise ValueError("Invalid user")
    user.is_activated = True
    session.commit()
    session.refresh(user)
    return user


def user_login(session: Session, name: str, password: str):
    user = session.exec(select(User).where(User.name == name)).first()
    if not user:
        raise ValueError("Invalid user")
    if not user.is_activated:
        registration = session.exec(
            select(UserRegistration).where(UserRegistration.user_id == user.id)
        ).first() or UserRegistration(
            token=bcrypt.hashpw(name.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            user_id=user.id,
        )
        send_registration_mail(user.email, registration.token)
        raise ValueError("User not activated yet, please check your email")
    if bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
        return user
    raise ValueError("Invalid password")
