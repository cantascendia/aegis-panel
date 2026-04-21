from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import ConfigDict, BaseModel

# Passlib bcrypt configuration.
#
# AUDIT.md section 4, finding P0-5: the upstream code trusted passlib's
# default work factor. As of passlib 1.7.x the default is 12, which
# matches OWASP 2023 guidance — but relying on the library default
# means a passlib downgrade or a future library change could silently
# weaken every password hash going forward.
#
# We pin rounds=12 explicitly. Raising this to 13 costs ~2x CPU on
# every admin login; do it deliberately once CPU headroom is known.
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/admins/token"
)  # Admin view url


class Token(BaseModel):
    access_token: str
    is_sudo: bool
    token_type: str = "bearer"


class Admin(BaseModel):
    id: int | None = None
    username: str
    is_sudo: bool
    enabled: bool = True
    all_services_access: bool = False
    modify_users_access: bool = True
    service_ids: list = []
    subscription_url_prefix: str = ""
    model_config = ConfigDict(from_attributes=True)


class AdminCreate(Admin):
    username: str
    password: str

    @property
    def hashed_password(self):
        return pwd_context.hash(self.password)


class AdminResponse(Admin):
    id: int
    users_data_usage: int


class AdminModify(Admin):
    password: str
    is_sudo: bool

    @property
    def hashed_password(self):
        return (
            pwd_context.hash(self.password)
            if self.password is not None
            else None
        )


class AdminPartialModify(AdminModify):
    """__annotations__ = {
        k: v | None for k, v in AdminModify.__annotations__.items()
    }"""

    password: str | None = None
    username: str | None = None
    is_sudo: bool | None = None
    enabled: bool | None = None
    all_services_access: bool | None = None
    modify_users_access: bool | None = None
    service_ids: list | None = None
    subscription_url_prefix: str | None = None


class AdminInDB(Admin):
    username: str
    hashed_password: str

    def verify_password(self, plain_password):
        return pwd_context.verify(plain_password, self.hashed_password)
